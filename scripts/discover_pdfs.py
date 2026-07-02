from __future__ import annotations

import argparse
import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

from csv_backup import write_csv_with_backup
from heritage_agent import request_url
from source_metadata import NEW_SOURCE_COLUMNS, ensure_new_source_columns, mark_new_source
from source_quality import QUALITY_COLUMNS, quality_for
from web_ingestion import extract_pdf_links, parse_web_document


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_FILE = PROJECT_ROOT / "metadata" / "heritage_links.csv"
LOG_DIR = PROJECT_ROOT / "data" / "logs"
LOG_FILE = LOG_DIR / "pdf_discovery.log"

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
    *NEW_SOURCE_COLUMNS,
]

SOURCE_STATUSES = {"verified", "redirect"}
SKIP_CATEGORIES = {"tool"}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamped = f"{utc_now()} {message}"
    print(message)
    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(stamped + "\n")


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path.rstrip('/')}"


def is_probably_pdf(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    if not path.endswith(".pdf"):
        return False
    if "example" in path or "example.com" in parsed.netloc.lower():
        return False
    return True


def title_from_pdf(url: str, label: str = "") -> str:
    if label and len(label.strip()) > 4:
        cleaned = re.sub(r"\s+", " ", label).strip()
        return cleaned[:120]

    path = unquote(urlparse(url).path.strip("/"))
    last = path.split("/")[-1] if path else urlparse(url).netloc
    last = re.sub(r"\.pdf$", "", last, flags=re.IGNORECASE)
    last = re.sub(r"[-_]+", " ", last).strip()
    return last.title() if last else url


def load_rows() -> list[dict[str, str]]:
    with CSV_FILE.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    for row in rows:
        for column in COLUMNS:
            row.setdefault(column, "")
    return rows


def save_rows(rows: list[dict[str, str]]) -> None:
    fieldnames = ensure_new_source_columns(list(COLUMNS), rows)
    backup = write_csv_with_backup(fieldnames, rows, reason="discover_pdfs")
    if backup:
        log(f"Backup saved: {backup}")


def eligible_sources(rows: list[dict[str, str]], include_pending: bool) -> list[dict[str, str]]:
    statuses = set(SOURCE_STATUSES)
    if include_pending:
        statuses.add("pending")

    selected = []
    for row in rows:
        url = row.get("link", "").strip()
        status = row.get("status", "pending").strip().lower()
        category = row.get("category", "").strip().lower()
        if not url or is_probably_pdf(url):
            continue
        if status not in statuses:
            continue
        if category in SKIP_CATEGORIES:
            continue
        selected.append(row)
    return selected


def discover_from_source(row: dict[str, str], pdf_limit: int) -> list[dict[str, str]]:
    url = row["link"].strip()
    try:
        with request_url(url, timeout=25) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except Exception as error:
        log(f"Skipped source {url}: {type(error).__name__}: {error}")
        return []

    document = parse_web_document(url, html)

    discovered = []
    seen = set()
    for link in extract_pdf_links(document):
        pdf_url = link["url"].split("#", 1)[0]
        if not is_probably_pdf(pdf_url):
            continue
        key = normalize_url(pdf_url)
        if key in seen:
            continue
        seen.add(key)
        candidate = {
            "title": title_from_pdf(pdf_url, link.get("text", "")),
            "category": "PDF",
            "region": row.get("region", ""),
            "source": row.get("source", "") or urlparse(url).netloc,
            "link": pdf_url,
            "status": "pending",
            "http_status": "",
            "content_type": "",
            "last_checked": "",
            "notes": f"Discovered from {row.get('title', url)}: {url}",
        }
        candidate.update(quality_for(candidate))
        mark_new_source(candidate, discovered_from=url)
        discovered.append(candidate)
        if len(discovered) >= pdf_limit:
            break
    return discovered


def discover_pdfs(
    source_limit: int | None = None,
    pdf_limit_per_source: int = 10,
    include_pending: bool = False,
) -> int:
    rows = load_rows()
    existing = {normalize_url(row["link"]) for row in rows if row.get("link")}
    sources = eligible_sources(rows, include_pending=include_pending)
    if source_limit:
        sources = sources[:source_limit]

    added = []
    for index, row in enumerate(sources, start=1):
        log(f"[{index}/{len(sources)}] Discovering PDFs from {row['link']}")
        for candidate in discover_from_source(row, pdf_limit=pdf_limit_per_source):
            key = normalize_url(candidate["link"])
            if key in existing:
                continue
            existing.add(key)
            rows.insert(0, candidate)
            added.append(candidate)
            log(f"  added {candidate['link']}")

    save_rows(rows)
    log(f"PDF discovery complete. Added {len(added)} PDFs. CSV now has {len(rows)} rows.")
    return len(added)


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover PDF links from verified heritage source pages.")
    parser.add_argument("--source-limit", type=int, help="Inspect only the first N eligible sources.")
    parser.add_argument("--pdf-limit-per-source", type=int, default=10)
    parser.add_argument("--include-pending", action="store_true", help="Also inspect pending source pages.")
    args = parser.parse_args()

    discover_pdfs(
        source_limit=args.source_limit,
        pdf_limit_per_source=args.pdf_limit_per_source,
        include_pending=args.include_pending,
    )


if __name__ == "__main__":
    main()
