from __future__ import annotations

import csv
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from csv_backup import write_csv_with_backup
from source_quality import QUALITY_COLUMNS, quality_for


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
TRANSCRIPT_FILE = WORKSPACE_ROOT / "share-transcript.md"
CSV_FILE = PROJECT_ROOT / "metadata" / "heritage_links.csv"

COLUMNS = [
    "title",
    "category",
    "region",
    "source",
    "link",
    "status",
    "http_status",
    "content_type",
    "last_checked",
    "notes",
    *QUALITY_COLUMNS,
]

TRAILING_CHARS = "\"'“”‘’`>)]}.,;:|\\"


def clean_url(raw: str) -> str:
    url = raw.strip().strip(TRAILING_CHARS)
    url = re.split(r",(pending|verified|broken|redirect|pdf)(\s|$)", url, maxsplit=1)[0]
    url = url.rstrip("\ue201\ue100\ue101")
    url = url.rstrip(TRAILING_CHARS)
    return url


def normalize_for_dedupe(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return f"{scheme}://{netloc}{path}"


def title_from_url(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    path = unquote(parsed.path.strip("/"))
    if not path:
        return domain

    last = path.split("/")[-1]
    last = re.sub(r"\.(pdf|html|asp|aspx|php)$", "", last, flags=re.IGNORECASE)
    last = re.sub(r"[-_]+", " ", last).strip()
    if last:
        return f"{last.title()} ({domain})"
    return domain


def infer_category(url: str) -> str:
    lower = url.lower()
    if lower.endswith(".pdf") or "/pdf/" in lower or "document" in lower:
        return "PDF"
    if any(term in lower for term in ["archive", "archives", "library", "digitallibrary", "collections"]):
        return "Archive"
    if any(term in lower for term in ["gis", "bhuvan", "earth", "map", "geodata", "naturalearth"]):
        return "GIS"
    if any(term in lower for term in ["dataset", "data.gov", "datacatalog", "aikosh"]):
        return "Dataset"
    if any(term in lower for term in ["arxiv", "scholar", "springer", "mdpi", "isprs"]):
        return "Research"
    if any(term in lower for term in ["unesco", "whc"]):
        return "Heritage"
    if any(term in lower for term in ["streamlit", "vercel", "render", "railway", "github", "python", "postman", "ollama", "openai"]):
        return "Tool"
    return "Heritage Source"


def infer_region(url: str) -> str:
    lower = url.lower()
    india_terms = [
        ".in",
        "india",
        "asi.nic",
        "ignca",
        "intach",
        "hampi",
        "vijayanagara",
        "tamil",
        "tnarch",
        "panjab",
        "gandhi",
        "bhuvan",
        "sanskrit",
        "muktalib",
        "kasturi",
    ]
    return "India" if any(term in lower for term in india_terms) else "Global"


def source_from_url(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    parts = domain.split(".")
    if len(parts) >= 2:
        return parts[-2].title()
    return domain.title()


def extract_urls() -> list[str]:
    text = TRANSCRIPT_FILE.read_text(encoding="utf-8", errors="ignore")
    raw_urls = re.findall(r"https?://[^\s<>\]]+", text)
    urls = []
    seen = set()
    for raw in raw_urls:
        url = clean_url(raw)
        if not url.startswith(("http://", "https://")):
            continue
        key = normalize_for_dedupe(url)
        if key in seen:
            continue
        seen.add(key)
        urls.append(url)
    return urls


def load_csv() -> list[dict[str, str]]:
    with CSV_FILE.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    for row in rows:
        for column in COLUMNS:
            row.setdefault(column, "")
    return rows


def save_csv(rows: list[dict[str, str]]) -> None:
    write_csv_with_backup(COLUMNS, rows, reason="import_links_from_transcript")


def main() -> None:
    rows = load_csv()
    existing = {normalize_for_dedupe(row["link"]) for row in rows if row.get("link")}
    added = []

    for url in extract_urls():
        key = normalize_for_dedupe(url)
        if key in existing:
            continue
        row = {
            "title": title_from_url(url),
            "category": infer_category(url),
            "region": infer_region(url),
            "source": source_from_url(url),
            "link": url,
            "status": "pending",
            "http_status": "",
            "content_type": "",
            "last_checked": "",
            "notes": "Imported from shared ChatGPT transcript",
        }
        row.update(quality_for(row))
        rows.append(row)
        added.append(url)
        existing.add(key)

    save_csv(rows)
    print(f"Imported {len(added)} new links.")
    print(f"CSV now has {len(rows)} links.")
    for url in added:
        print(url)


if __name__ == "__main__":
    main()
