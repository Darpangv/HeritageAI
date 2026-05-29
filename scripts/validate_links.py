from __future__ import annotations

import argparse
import csv
import ssl
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from document_categories import DOCUMENT_CATEGORY_COLUMNS, classify_document_category
from csv_backup import write_csv_with_backup
from source_quality import QUALITY_COLUMNS, quality_for


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_FILE = PROJECT_ROOT / "metadata" / "heritage_links.csv"
LOG_DIR = PROJECT_ROOT / "data" / "logs"
LOG_FILE = LOG_DIR / "link_validation.log"
TIMEOUT_SECONDS = 12
USER_AGENT = "Indian-Heritage-AI-LinkValidator/1.0"
RECHECK_STATUSES = {"verified", "redirect", "pdf", "broken"}
REPAIR_COLUMNS = ["final_url", "replacement_link", "replacement_status", "replacement_checked"]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamped = f"{utc_now()} {message}"
    print(message)
    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(stamped + "\n")


def classify(status_code: int | None, content_type: str, final_url: str, original_url: str) -> str:
    if status_code is None:
        return "broken"
    if "application/pdf" in content_type.lower() or final_url.lower().endswith(".pdf"):
        return "pdf"
    if 200 <= status_code < 300:
        if final_url.rstrip("/") != original_url.rstrip("/"):
            return "redirect"
        return "verified"
    if 300 <= status_code < 400:
        return "redirect"
    return "broken"


def normalized_url(url: str) -> str:
    return url.strip().rstrip("/")


def candidate_replacements(url: str) -> list[str]:
    candidates = []
    clean_url = url.strip()

    if clean_url.startswith("http://"):
        candidates.append("https://" + clean_url.removeprefix("http://"))
    elif clean_url.startswith("https://"):
        candidates.append("http://" + clean_url.removeprefix("https://"))

    for scheme in ("https://", "http://"):
        if clean_url.startswith(scheme):
            rest = clean_url.removeprefix(scheme)
            if rest.startswith("www."):
                candidates.append(scheme + rest.removeprefix("www."))
            else:
                candidates.append(scheme + "www." + rest)

    if clean_url.endswith("/"):
        candidates.append(clean_url.rstrip("/"))
    else:
        candidates.append(clean_url + "/")

    seen = set()
    unique = []
    for candidate in candidates:
        key = normalized_url(candidate)
        if key != normalized_url(url) and key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def check_link(url: str, insecure: bool = False) -> dict[str, str]:
    context = ssl._create_unverified_context() if insecure else None
    request = Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})

    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS, context=context) as response:
            status_code = response.getcode()
            content_type = response.headers.get("Content-Type", "")
            final_url = response.geturl()
    except HTTPError as error:
        status_code = error.code
        content_type = error.headers.get("Content-Type", "") if error.headers else ""
        final_url = error.url or url
    except URLError:
        request = Request(url, method="GET", headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=TIMEOUT_SECONDS, context=context) as response:
                status_code = response.getcode()
                content_type = response.headers.get("Content-Type", "")
                final_url = response.geturl()
        except Exception as error:
            return {
                "status": "broken",
                "http_status": "",
                "content_type": "",
                "final_url": "",
                "notes": f"{type(error).__name__}: {error}",
            }
    except Exception as error:
        return {
            "status": "broken",
            "http_status": "",
            "content_type": "",
            "final_url": "",
            "notes": f"{type(error).__name__}: {error}",
        }

    status = classify(status_code, content_type, final_url, url)
    note = "" if final_url.rstrip("/") == url.rstrip("/") else f"Redirects to {final_url}"
    return {
        "status": status,
        "http_status": str(status_code),
        "content_type": content_type.split(";")[0],
        "final_url": final_url,
        "notes": note,
    }


def find_replacement(url: str, insecure: bool = False) -> dict[str, str]:
    for candidate in candidate_replacements(url):
        result = check_link(candidate, insecure=insecure)
        if result["status"] in {"verified", "redirect", "pdf"}:
            return {
                "replacement_link": result.get("final_url") or candidate,
                "replacement_status": result["status"],
            }
    return {"replacement_link": "", "replacement_status": "not_found"}


def load_rows() -> tuple[list[str], list[dict[str, str]]]:
    with CSV_FILE.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    for column in [
        "status",
        "http_status",
        "content_type",
        "last_checked",
        "notes",
        *REPAIR_COLUMNS,
        *QUALITY_COLUMNS,
        *DOCUMENT_CATEGORY_COLUMNS,
    ]:
        if column not in fieldnames:
            fieldnames.append(column)
        for row in rows:
            row.setdefault(column, "")

    return fieldnames, rows


def save_rows(fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    backup = write_csv_with_backup(fieldnames, rows, reason="validate_links")
    if backup:
        log(f"Backup saved: {backup}")


def should_validate(row: dict[str, str], mode: str, stale_days: int) -> bool:
    status = row.get("status", "").strip().lower() or "pending"
    last_checked = parse_utc(row.get("last_checked", ""))

    if mode == "all":
        return True
    if mode == "pending":
        return status == "pending" or not last_checked
    if mode == "broken":
        return status == "broken"
    if mode == "redirect":
        return status == "redirect"
    if mode == "stale":
        if status == "pending" or not last_checked:
            return True
        if status in RECHECK_STATUSES:
            return last_checked <= datetime.now(timezone.utc) - timedelta(days=stale_days)
    raise ValueError("mode must be all, pending, broken, redirect, or stale")


def row_for_replacement(original: dict[str, str], link: str, status: str, checked_at: str) -> dict[str, str]:
    row = dict(original)
    row["title"] = f"{original.get('title', '').strip()} (replacement)".strip()
    row["link"] = link
    row["status"] = status
    row["http_status"] = ""
    row["content_type"] = ""
    row["last_checked"] = checked_at
    row["notes"] = f"Replacement discovered from {original.get('link', '')}"
    row["final_url"] = link
    row["replacement_link"] = ""
    row["replacement_status"] = ""
    row["replacement_checked"] = checked_at
    row.update(quality_for(row))
    row.update(classify_document_category(row))
    return row


def validate_links(
    limit: int | None = None,
    insecure: bool = False,
    mode: str = "stale",
    stale_days: int = 30,
    add_replacements: bool = False,
) -> None:
    fieldnames, rows = load_rows()
    checked_at = utc_now()
    existing_links = {normalized_url(row.get("link", "")) for row in rows if row.get("link")}
    replacements_added = 0
    selected_rows = [row for row in rows if should_validate(row, mode=mode, stale_days=stale_days)]
    if limit:
        selected_rows = selected_rows[:limit]

    if not selected_rows:
        log(f"No links need validation. mode={mode} stale_days={stale_days}")
        return

    for index, row in enumerate(selected_rows, start=1):
        url = row["link"].strip()
        log(f"[{index}/{len(selected_rows)}] Checking {url}")
        result = check_link(url, insecure=insecure)
        row["status"] = result["status"]
        row["http_status"] = result["http_status"]
        row["content_type"] = result["content_type"]
        row["last_checked"] = checked_at
        row["final_url"] = result.get("final_url", "")
        if result["notes"]:
            row["notes"] = result["notes"]

        replacement_link = ""
        replacement_status = ""
        if result["status"] == "redirect" and result.get("final_url"):
            replacement_link = result["final_url"]
            replacement_status = "redirect_target"
        elif result["status"] == "broken":
            repair = find_replacement(url, insecure=insecure)
            replacement_link = repair["replacement_link"]
            replacement_status = repair["replacement_status"]
            if replacement_link:
                row["notes"] = f"{row.get('notes', '')} | Suggested replacement: {replacement_link}".strip(" |")

        row["replacement_link"] = replacement_link
        row["replacement_status"] = replacement_status
        row["replacement_checked"] = checked_at if replacement_status else ""
        row.update(quality_for(row))
        row.update(classify_document_category(row))

        if add_replacements and replacement_link:
            replacement_key = normalized_url(replacement_link)
            if replacement_key not in existing_links:
                rows.append(row_for_replacement(row, replacement_link, "pending", checked_at))
                existing_links.add(replacement_key)
                replacements_added += 1
                log(f"Added replacement candidate: {replacement_link}")

    save_rows(fieldnames, rows)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row.get("status", "unknown")] = counts.get(row.get("status", "unknown"), 0) + 1
    log("Validation complete.")
    for status, count in sorted(counts.items()):
        log(f"{status}: {count}")
    if replacements_added:
        log(f"replacement candidates added: {replacements_added}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate URLs in metadata/heritage_links.csv.")
    parser.add_argument("--limit", type=int, help="Validate only the first N selected rows.")
    parser.add_argument("--insecure", action="store_true", help="Skip TLS certificate verification.")
    parser.add_argument(
        "--mode",
        choices=["stale", "pending", "broken", "redirect", "all"],
        default="stale",
        help="stale validates pending plus old checked links; broken/redirect focus repair checks.",
    )
    parser.add_argument("--stale-days", type=int, default=30, help="Recheck checked links after this many days.")
    parser.add_argument(
        "--add-replacements",
        action="store_true",
        help="Add discovered redirect targets or replacement candidates as new pending rows.",
    )
    args = parser.parse_args()

    validate_links(
        limit=args.limit,
        insecure=args.insecure,
        mode=args.mode,
        stale_days=args.stale_days,
        add_replacements=args.add_replacements,
    )


if __name__ == "__main__":
    main()
