from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[0]
sys.path.insert(0, str(SCRIPT_DIR))

from heritage_agent import download_pdf, extract_pdf_pages, is_pdf_url, tokenize  # noqa: E402
from vector_db import SQLITE_FILE, VECTOR_DIR, TfidfVectorizer, VectorStore, embed_text  # noqa: E402


CSV_FILE = PROJECT_ROOT / "metadata" / "heritage_links.csv"
VECTOR_DIR = PROJECT_ROOT / "data" / "vector_store"
VECTOR_FILE = VECTOR_DIR / "heritage_chunks.jsonl"


def chunk_text(text: str, chunk_chars: int = 1200, overlap_chars: int = 180) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_chars, len(text))
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(0, end - overlap_chars)
    return chunks


def load_rows(query: str | None = None) -> list[dict[str, str]]:
    with CSV_FILE.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if not query:
        return rows

    terms = tokenize(query)
    filtered = []
    for row in rows:
        searchable = " ".join(
            [
                row.get("title", ""),
                row.get("category", ""),
                row.get("region", ""),
                row.get("source", ""),
                row.get("notes", ""),
                row.get("link", ""),
            ]
        )
        if tokenize(searchable) & terms:
            filtered.append(row)
    return filtered


def get_provider() -> str:
    import os

    return os.environ.get("HERITAGE_EMBEDDING_PROVIDER", "local").lower()


def build_embeddings(query: str | None = None, limit: int | None = None, append: bool = False) -> None:
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    store = VectorStore(SQLITE_FILE)
    if not append:
        store.clear()

    rows = load_rows(query=query)
    pdf_rows = [
        row
        for row in rows
        if row.get("link", "").strip()
        and row.get("usable_for_rag", "yes").lower() != "no"
        and row.get("priority", "").lower() != "exclude"
    ]
    if limit:
        selected_rows = []
        for row in pdf_rows:
            if is_pdf_url(row["link"].strip()):
                selected_rows.append(row)
            if len(selected_rows) >= limit:
                break
        rows = selected_rows

    raw_records = []
    for row in rows:
        url = row.get("link", "").strip()
        if not url:
            continue

        print(f"Checking source: {row.get('title', url)}")
        if not is_pdf_url(url):
            print("  skipped: not a direct PDF")
            continue

        try:
            pdf_path = download_pdf(url)
            pages = extract_pdf_pages(pdf_path)
        except Exception as error:
            print(f"  skipped: {type(error).__name__}: {error}")
            continue

        record_count = 0
        for page in pages:
            for chunk_index, chunk in enumerate(chunk_text(str(page["text"])), start=1):
                raw_records.append(
                    {
                        "id": f"{pdf_path.stem}:p{page['page']}:c{chunk_index}",
                        "title": row.get("title", ""),
                        "source": row.get("source", ""),
                        "url": url,
                        "pdf_path": str(pdf_path),
                        "page": page["page"],
                        "chunk_index": chunk_index,
                        "text": chunk,
                    }
                )
                record_count += 1
        print(f"  extracted {record_count} chunks")

    records = []
    provider = get_provider()
    if provider == "local":
        if append:
            existing_rows = store.connection.execute("SELECT * FROM chunks").fetchall()
            existing_ids = {record["id"] for record in raw_records}
            for row in existing_rows:
                if row["id"] in existing_ids:
                    continue
                raw_records.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "source": row["source"],
                        "url": row["url"],
                        "pdf_path": row["pdf_path"],
                        "page": row["page"],
                        "chunk_index": row["chunk_index"],
                        "text": row["text"],
                    }
                )
            store.clear()

        vectorizer = TfidfVectorizer.fit([record["text"] for record in raw_records])
        store.set_metadata("tfidf_vectorizer", vectorizer.to_json())
        store.set_metadata("embedding_provider", "local")
        embedding_model = f"local-tfidf-{len(vectorizer.vocabulary)}"
        for record in raw_records:
            record["embedding_model"] = embedding_model
            record["embedding"] = vectorizer.transform(record["text"])
            records.append(record)
            store.upsert_chunk(record)
        print(f"Embedded {len(records)} chunks with {embedding_model}")
    else:
        for raw_record in raw_records:
            embedding, embedding_model = embed_text(raw_record["text"])
            record = {
                **raw_record,
                "embedding_model": embedding_model,
                "embedding": embedding,
            }
            records.append(record)
            store.upsert_chunk(record)
        print(f"Embedded {len(records)} chunks with provider={provider}")

    store.commit()
    with VECTOR_FILE.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Saved {len(records)} chunks to {VECTOR_FILE}")
    print(f"Saved {store.count()} chunks to {SQLITE_FILE}")
    store.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build local embeddings for heritage PDF chunks.")
    parser.add_argument("--query", help="Only embed sources matching this query.")
    parser.add_argument("--limit", type=int, help="Only inspect the first N matching sources.")
    parser.add_argument("--append", action="store_true", help="Append/update instead of rebuilding the DB.")
    args = parser.parse_args()

    build_embeddings(query=args.query, limit=args.limit, append=args.append)


if __name__ == "__main__":
    main()
