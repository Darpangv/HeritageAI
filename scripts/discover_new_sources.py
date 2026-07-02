from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from urllib.parse import urlparse

from csv_backup import write_csv_with_backup
from document_categories import DOCUMENT_CATEGORY_COLUMNS, classify_document_category
from heritage_agent import request_url
from source_metadata import NEW_SOURCE_COLUMNS, ensure_new_source_columns, mark_new_source, utc_now
from source_quality import QUALITY_COLUMNS, quality_for
from web_ingestion import parse_web_document


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_FILE = PROJECT_ROOT / "metadata" / "heritage_links.csv"
LOG_DIR = PROJECT_ROOT / "data" / "logs"
LOG_FILE = LOG_DIR / "new_source_discovery.log"

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
    *DOCUMENT_CATEGORY_COLUMNS,
    *NEW_SOURCE_COLUMNS,
]

DEFAULT_SEEDS = [
    {
        "url": "https://asi.nic.in/",
        "source": "Archaeological Survey of India",
        "region": "India",
        "category": "ASI Online Source",
    },
    {
        "url": "https://asi.nic.in/publications/",
        "source": "Archaeological Survey of India",
        "region": "India",
        "category": "ASI Publication",
    },
    {
        "url": "https://asi.nic.in/excavations/",
        "source": "Archaeological Survey of India",
        "region": "India",
        "category": "ASI Excavation",
    },
    {
        "url": "https://nmma.nic.in/",
        "source": "National Mission on Monuments and Antiquities",
        "region": "India",
        "category": "Government Heritage Source",
    },
    {
        "url": "https://ignca.gov.in/",
        "source": "IGNCA",
        "region": "India",
        "category": "Government Heritage Source",
    },
]

ARCHAEOLOGY_TERMS = (
    "archaeology",
    "archaeological",
    "antiquity",
    "antiquities",
    "asi",
    "conservation",
    "cultural heritage",
    "excavation",
    "epigraphy",
    "heritage",
    "inscription",
    "monument",
    "museum",
    "numismatic",
    "prehistoric",
    "temple",
)

SKIP_EXTENSIONS = (
    ".css",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".png",
    ".svg",
    ".webp",
    ".zip",
)


def log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamped = f"{utc_now()} {message}"
    print(message)
    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(stamped + "\n")


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return f"{scheme}://{netloc}{path}".lower()


def load_rows() -> tuple[list[str], list[dict[str, str]]]:
    with CSV_FILE.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    for column in COLUMNS:
        if column not in fieldnames:
            fieldnames.append(column)
        for row in rows:
            row.setdefault(column, "")
    return ensure_new_source_columns(fieldnames, rows), rows


def save_rows(fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    backup = write_csv_with_backup(fieldnames, rows, reason="discover_new_sources")
    if backup:
        log(f"Backup saved: {backup}")


def read_seeds(seed_file: Path | None) -> list[dict[str, str]]:
    if seed_file is None:
        return DEFAULT_SEEDS
    with seed_file.open(newline="", encoding="utf-8") as file:
        return [row for row in csv.DictReader(file) if row.get("url")]


def clean_title(text: str, fallback_url: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip(" -|")
    if len(text) >= 4:
        return text[:140]

    path = urlparse(fallback_url).path.strip("/").split("/")[-1]
    path = re.sub(r"\.[a-z0-9]+$", "", path, flags=re.IGNORECASE)
    path = re.sub(r"[-_]+", " ", path).strip()
    return path.title()[:140] if path else urlparse(fallback_url).netloc


def is_candidate_link(url: str, text: str, same_domain: str, include_external: bool) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    lowered_url = url.lower()
    if lowered_url.endswith(SKIP_EXTENSIONS):
        return False
    if not include_external and parsed.netloc.lower() != same_domain.lower():
        return False
    haystack = f"{text} {url}".lower()
    return any(term in haystack for term in ARCHAEOLOGY_TERMS) or lowered_url.endswith(".pdf")


def row_from_link(seed: dict[str, str], url: str, text: str) -> dict[str, str]:
    parsed = urlparse(url)
    is_pdf = parsed.path.lower().endswith(".pdf")
    row = {
        "title": clean_title(text, url),
        "category": "PDF" if is_pdf else seed.get("category", "Online Article"),
        "region": seed.get("region", "India"),
        "source": seed.get("source") or parsed.netloc,
        "link": url,
        "status": "pending",
        "http_status": "",
        "content_type": "",
        "last_checked": "",
        "notes": f"New online source discovered from {seed['url']}",
    }
    row.update(quality_for(row))
    row.update(classify_document_category(row))
    mark_new_source(row, discovered_from=seed["url"])
    return row


def discover_from_seed(seed: dict[str, str], limit: int, include_external: bool) -> list[dict[str, str]]:
    url = seed["url"].strip()
    try:
        with request_url(url, timeout=30) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except Exception as error:
        log(f"Skipped seed {url}: {type(error).__name__}: {error}")
        return []

    document = parse_web_document(url, html)
    same_domain = urlparse(url).netloc
    candidates = []
    seen = set()
    for link in document.links:
        candidate_url = link.get("url", "").split("#", 1)[0]
        label = link.get("text", "")
        if not is_candidate_link(candidate_url, label, same_domain, include_external):
            continue
        key = normalize_url(candidate_url)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(row_from_link(seed, candidate_url, label))
        if len(candidates) >= limit:
            break
    return candidates


def discover_new_sources(seed_file: Path | None, per_seed_limit: int, include_external: bool) -> int:
    fieldnames, rows = load_rows()
    existing = {normalize_url(row.get("link", "")) for row in rows if row.get("link")}
    added = []

    seeds = read_seeds(seed_file)
    for index, seed in enumerate(seeds, start=1):
        log(f"[{index}/{len(seeds)}] Scanning {seed['url']}")
        for row in discover_from_seed(seed, limit=per_seed_limit, include_external=include_external):
            key = normalize_url(row["link"])
            if key in existing:
                continue
            existing.add(key)
            rows.insert(0, row)
            added.append(row)
            log(f"  new: {row['title']} - {row['link']}")

    save_rows(fieldnames, rows)
    log(f"New source discovery complete. Added {len(added)} links. CSV now has {len(rows)} rows.")
    return len(added)


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover new ASI/heritage links and tag them as new.")
    parser.add_argument("--seed-file", type=Path, help="Optional CSV with url,source,region,category columns.")
    parser.add_argument("--per-seed-limit", type=int, default=10)
    parser.add_argument("--include-external", action="store_true", help="Allow candidate links outside the seed domain.")
    args = parser.parse_args()
    discover_new_sources(args.seed_file, args.per_seed_limit, args.include_external)


if __name__ == "__main__":
    main()
