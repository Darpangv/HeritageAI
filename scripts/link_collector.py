from __future__ import annotations

import argparse
import csv
from pathlib import Path
from urllib.parse import urlparse

from document_categories import DOCUMENT_CATEGORY_COLUMNS, classify_document_category
from csv_backup import write_csv_with_backup
from source_metadata import NEW_SOURCE_COLUMNS, mark_new_source
from source_quality import QUALITY_COLUMNS, quality_for


PROJECT_ROOT = Path(__file__).resolve().parents[1]
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
    *DOCUMENT_CATEGORY_COLUMNS,
    *NEW_SOURCE_COLUMNS,
]


def normalize_url(url: str) -> str:
    url = url.strip()
    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"https://{url}"
    return url


def initialize_database() -> None:
    CSV_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not CSV_FILE.exists():
        with CSV_FILE.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=COLUMNS)
            writer.writeheader()


def load_database() -> list[dict[str, str]]:
    initialize_database()
    with CSV_FILE.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    for row in rows:
        for column in COLUMNS:
            row.setdefault(column, "")
    return rows


def save_database(rows: list[dict[str, str]]) -> None:
    fieldnames = list(COLUMNS)
    for row in rows:
        for column in row:
            if column not in fieldnames:
                fieldnames.append(column)
        for column in fieldnames:
            row.setdefault(column, "")

    write_csv_with_backup(fieldnames, rows, reason="link_collector")


def add_link(
    title: str,
    category: str,
    region: str,
    source: str,
    link: str,
    notes: str = "",
) -> bool:
    rows = load_database()
    normalized_link = normalize_url(link)
    existing_links = {row["link"].strip().lower() for row in rows}

    if normalized_link.lower() in existing_links:
        print("Link already exists.")
        return False

    new_row = {
        "title": title.strip(),
        "category": category.strip(),
        "region": region.strip(),
        "source": source.strip(),
        "link": normalized_link,
        "status": "pending",
        "http_status": "",
        "content_type": "",
        "last_checked": "",
        "notes": notes.strip(),
    }
    new_row.update(quality_for(new_row))
    new_row.update(classify_document_category(new_row))
    mark_new_source(new_row, discovered_from="manual")
    rows.insert(0, new_row)
    save_database(rows)
    print("Link added successfully.")
    return True


def show_links() -> None:
    rows = load_database()
    if not rows:
        print("No links found.")
        return

    for index, row in enumerate(rows, start=1):
        status = row.get("status", "pending")
        print(f"{index}. [{status}] {row['title']} - {row['link']}")


def interactive_menu() -> None:
    initialize_database()
    while True:
        print("\nINDIAN HERITAGE LINK COLLECTOR")
        print("1. Add link")
        print("2. Show links")
        print("3. Exit")

        choice = input("Choose option: ").strip()
        if choice == "1":
            add_link(
                title=input("Title: "),
                category=input("Category: "),
                region=input("Region: "),
                source=input("Source: "),
                link=input("Link: "),
                notes=input("Notes (optional): "),
            )
        elif choice == "2":
            show_links()
        elif choice == "3":
            print("Goodbye.")
            break
        else:
            print("Invalid option.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect heritage source links.")
    parser.add_argument("--title")
    parser.add_argument("--category")
    parser.add_argument("--region")
    parser.add_argument("--source")
    parser.add_argument("--link")
    parser.add_argument("--notes", default="")
    parser.add_argument("--list", action="store_true", help="List current links.")
    args = parser.parse_args()

    if args.list:
        show_links()
        return

    if args.link:
        required = [args.title, args.category, args.region, args.source]
        if not all(required):
            parser.error("--title, --category, --region, and --source are required with --link")
        add_link(args.title, args.category, args.region, args.source, args.link, args.notes)
        return

    interactive_menu()


if __name__ == "__main__":
    main()
