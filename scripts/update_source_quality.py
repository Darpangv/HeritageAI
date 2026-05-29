from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from csv_backup import write_csv_with_backup
from source_quality import QUALITY_COLUMNS, quality_for


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_FILE = PROJECT_ROOT / "metadata" / "heritage_links.csv"


def main() -> None:
    with CSV_FILE.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    for column in QUALITY_COLUMNS:
        if column not in fieldnames:
            fieldnames.append(column)

    for row in rows:
        row.update(quality_for(row))

    backup = write_csv_with_backup(fieldnames, rows, reason="update_source_quality")

    priorities = Counter(row["priority"] for row in rows)
    usable = Counter(row["usable_for_rag"] for row in rows)
    print(f"Updated source quality for {len(rows)} links.")
    if backup:
        print(f"Backup saved: {backup}")
    print("Priority:", dict(sorted(priorities.items())))
    print("Usable for RAG:", dict(sorted(usable.items())))


if __name__ == "__main__":
    main()
