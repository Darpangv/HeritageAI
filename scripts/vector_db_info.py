from __future__ import annotations

import sqlite3
import csv
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQLITE_FILE = PROJECT_ROOT / "data" / "vector_store" / "heritage_vectors.sqlite"
CSV_FILE = PROJECT_ROOT / "metadata" / "heritage_links.csv"


def main() -> None:
    if not SQLITE_FILE.exists():
        print(f"Vector database not found: {SQLITE_FILE}")
        print("Run run_build_embeddings.bat first.")
        return

    connection = sqlite3.connect(SQLITE_FILE)
    connection.row_factory = sqlite3.Row
    total = connection.execute("SELECT COUNT(*) AS count FROM chunks").fetchone()["count"]
    models = connection.execute(
        """
        SELECT embedding_model, COUNT(*) AS count
        FROM chunks
        GROUP BY embedding_model
        ORDER BY count DESC
        """
    ).fetchall()
    sources = connection.execute(
        """
        SELECT title, COUNT(*) AS count
        FROM chunks
        GROUP BY title
        ORDER BY count DESC
        """
    ).fetchall()
    connection.close()

    print(f"Vector DB: {SQLITE_FILE}")
    print(f"Total chunks: {total}")
    print("\nEmbedding models:")
    for row in models:
        print(f"- {row['embedding_model']}: {row['count']}")
    print("\nSources:")
    for row in sources:
        print(f"- {row['title']}: {row['count']}")

    if CSV_FILE.exists():
        with CSV_FILE.open(newline="", encoding="utf-8") as file:
            csv_rows = list(csv.DictReader(file))
        priority = Counter(row.get("priority", "unknown") for row in csv_rows)
        usable = Counter(row.get("usable_for_rag", "unknown") for row in csv_rows)
        print("\nSource quality:")
        print(f"- usable_for_rag=yes: {usable.get('yes', 0)}")
        print(f"- usable_for_rag=no: {usable.get('no', 0)}")
        for key in ["high", "medium", "low", "exclude"]:
            print(f"- priority={key}: {priority.get(key, 0)}")


if __name__ == "__main__":
    main()
