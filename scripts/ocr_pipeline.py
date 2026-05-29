from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OCR_DIR = PROJECT_ROOT / "data" / "ocr"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
DEFAULT_TESSERACT_LANGS = "eng+hin+san+kan+tel+tam+mal+ben+guj+mar+ori+pan+urd"

SCRIPT_RANGES = {
    "Devanagari": (0x0900, 0x097F),
    "Bengali": (0x0980, 0x09FF),
    "Gurmukhi": (0x0A00, 0x0A7F),
    "Gujarati": (0x0A80, 0x0AFF),
    "Oriya/Odia": (0x0B00, 0x0B7F),
    "Tamil": (0x0B80, 0x0BFF),
    "Telugu": (0x0C00, 0x0C7F),
    "Kannada": (0x0C80, 0x0CFF),
    "Malayalam": (0x0D00, 0x0D7F),
    "Sinhala": (0x0D80, 0x0DFF),
    "Arabic/Persian/Urdu": (0x0600, 0x06FF),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-")
    return cleaned[:80] or "ocr-document"


def optional_import(module_name: str):
    try:
        return __import__(module_name)
    except ImportError:
        return None


def preprocess_image(image_path: Path):
    pil = optional_import("PIL")
    if pil is None:
        raise RuntimeError("Pillow is required for image OCR. Install with: pip install Pillow")

    from PIL import Image, ImageFilter, ImageOps

    image = Image.open(image_path)
    image = ImageOps.exif_transpose(image)
    image = image.convert("L")
    image = ImageOps.autocontrast(image)
    image = image.filter(ImageFilter.MedianFilter(size=3))
    image = image.point(lambda pixel: 255 if pixel > 170 else 0)
    return image


def run_tesseract(image, langs: str) -> dict:
    pytesseract = optional_import("pytesseract")
    if pytesseract is None:
        raise RuntimeError("pytesseract is required for OCR. Install with: pip install pytesseract")

    data = pytesseract.image_to_data(image, lang=langs, output_type=pytesseract.Output.DICT)
    words = []
    confidences = []
    for text, confidence in zip(data.get("text", []), data.get("conf", [])):
        cleaned = (text or "").strip()
        if not cleaned:
            continue
        words.append(cleaned)
        try:
            value = float(confidence)
            if value >= 0:
                confidences.append(value)
        except ValueError:
            pass

    full_text = " ".join(words)
    average_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    return {
        "text": re.sub(r"\s+", " ", full_text).strip(),
        "confidence": round(average_confidence, 2),
        "word_count": len(words),
    }


def detect_scripts(text: str) -> list[dict]:
    counts = {}
    for char in text or "":
        codepoint = ord(char)
        for script, (start, end) in SCRIPT_RANGES.items():
            if start <= codepoint <= end:
                counts[script] = counts.get(script, 0) + 1
                break
    latin = len(re.findall(r"[A-Za-z]", text or ""))
    if latin:
        counts["Latin"] = latin
    total = sum(counts.values()) or 1
    return [
        {"script": script, "characters": count, "share": round(count / total, 3)}
        for script, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)
    ]


def confidence_label(confidence: float, word_count: int) -> str:
    if word_count < 8:
        return "very_low"
    if confidence >= 80:
        return "high"
    if confidence >= 55:
        return "medium"
    if confidence >= 30:
        return "low"
    return "very_low"


def translate_to_english(text: str, source_label: str) -> str:
    if not text.strip():
        return ""
    try:
        from chatgpt_brain import ask_chatgpt
    except Exception as error:
        return f"Translation unavailable: {type(error).__name__}: {error}"

    prompt = (
        "Translate the OCR text to English. Preserve uncertain words in brackets. "
        "Do not invent missing text. If the script/language is uncertain, state that first."
    )
    return ask_chatgpt(
        question=f"{prompt}\n\nSource label: {source_label}",
        context=text[:12000],
        sources=[],
    )


def extract_pdf_text(pdf_path: Path) -> list[dict]:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError("pypdf is required for PDF text inspection. Install with: pip install pypdf") from error

    reader = PdfReader(str(pdf_path))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = re.sub(r"\s+", " ", page.extract_text() or "").strip()
        pages.append(
            {
                "page": index,
                "text": text,
                "word_count": len(text.split()),
                "confidence": 100.0 if text else 0.0,
                "confidence_label": "embedded_text" if text else "needs_image_ocr",
                "scripts": detect_scripts(text),
                "method": "pdf_embedded_text" if text else "pdf_page_image_ocr_not_available",
            }
        )
    return pages


def process_image_file(path: Path, langs: str, translate: bool) -> list[dict]:
    image = preprocess_image(path)
    result = run_tesseract(image, langs)
    scripts = detect_scripts(result["text"])
    page = {
        "page": 1,
        "text": result["text"],
        "word_count": result["word_count"],
        "confidence": result["confidence"],
        "confidence_label": confidence_label(result["confidence"], result["word_count"]),
        "scripts": scripts,
        "method": "tesseract_image_ocr",
    }
    if translate:
        page["english_translation"] = translate_to_english(result["text"], path.name)
    return [page]


def write_outputs(source_path: Path, pages: list[dict]) -> tuple[Path, Path]:
    OCR_DIR.mkdir(parents=True, exist_ok=True)
    base = slug(source_path.stem)
    json_path = OCR_DIR / f"{base}.ocr.json"
    md_path = OCR_DIR / f"{base}.ocr.md"
    payload = {
        "source_file": str(source_path),
        "created_at": utc_now(),
        "pages": pages,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [f"# OCR Result: {source_path.name}", "", f"Created: {payload['created_at']}", ""]
    for page in pages:
        script_text = ", ".join(f"{item['script']} {item['share']}" for item in page.get("scripts", [])) or "unknown"
        lines.extend(
            [
                f"## Page {page['page']}",
                "",
                f"- Method: {page.get('method', 'unknown')}",
                f"- Confidence: {page.get('confidence_label')} ({page.get('confidence')})",
                f"- Scripts: {script_text}",
                "",
                "### OCR Text",
                "",
                page.get("text") or "[No text extracted]",
                "",
            ]
        )
        if page.get("english_translation"):
            lines.extend(["### English Translation", "", page["english_translation"], ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def process_document(path: Path, langs: str, translate: bool = False) -> tuple[Path, Path]:
    if not path.exists():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        pages = extract_pdf_text(path)
    elif suffix in IMAGE_EXTENSIONS:
        pages = process_image_file(path, langs=langs, translate=translate)
    else:
        raise RuntimeError(f"Unsupported OCR input type: {suffix}")
    return write_outputs(path, pages)


def main() -> None:
    parser = argparse.ArgumentParser(description="OCR scanned heritage images/PDFs and report script/confidence.")
    parser.add_argument("path", help="Image or PDF path to inspect.")
    parser.add_argument("--langs", default=DEFAULT_TESSERACT_LANGS, help="Tesseract language codes.")
    parser.add_argument("--translate", action="store_true", help="Translate extracted OCR text to English with the ChatGPT brain.")
    args = parser.parse_args()

    try:
        json_path, md_path = process_document(Path(args.path), langs=args.langs, translate=args.translate)
    except Exception as error:
        print(f"OCR failed: {type(error).__name__}: {error}")
        sys.exit(1)

    print(f"OCR JSON saved to {json_path}")
    print(f"OCR Markdown saved to {md_path}")


if __name__ == "__main__":
    main()
