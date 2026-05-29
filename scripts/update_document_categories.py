from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from csv_backup import write_csv_with_backup
from document_categories import DOCUMENT_CATEGORY_COLUMNS, classify_document_category


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_FILE = PROJECT_ROOT / "metadata" / "heritage_links.csv"


def main() -> None:
    with CSV_FILE.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    for column in DOCUMENT_CATEGORY_COLUMNS:
        if column not in fieldnames:
            fieldnames.append(column)

    counts: Counter[str] = Counter()
    for row in rows:
        row.update(classify_document_category(row))
        counts[row["document_category"]] += 1

    backup = write_csv_with_backup(fieldnames, rows, reason="update_document_categories")

    print(f"Updated document categories for {len(rows)} links.")
    if backup:
        print(f"Backup saved: {backup}")
    for category, count in counts.most_common():
        print(f"{category}: {count}")


if __name__ == "__main__":
    main()
