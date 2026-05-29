from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from build_embeddings import build_embeddings
from discover_pdfs import discover_pdfs
from validate_links import validate_links


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "data" / "logs"
LOG_FILE = LOG_DIR / "auto_ingest.log"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamped = f"{utc_now()} {message}"
    print(message)
    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(stamped + "\n")


def run_pipeline(
    validate_limit: int,
    source_limit: int,
    pdf_limit_per_source: int,
    embed_limit: int,
    include_pending_sources: bool,
) -> None:
    log("Auto-ingest pipeline started.")

    log(f"Validating up to {validate_limit} pending/stale links.")
    validate_links(limit=validate_limit, mode="stale", stale_days=30)

    log(f"Discovering PDFs from up to {source_limit} source pages.")
    added = discover_pdfs(
        source_limit=source_limit,
        pdf_limit_per_source=pdf_limit_per_source,
        include_pending=include_pending_sources,
    )
    log(f"PDF discovery added {added} new candidate PDFs.")

    log(f"Building/updating embeddings for up to {embed_limit} PDF or webpage sources.")
    build_embeddings(limit=embed_limit, append=True)

    log("Auto-ingest pipeline finished.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate links, discover PDFs, and update embeddings.")
    parser.add_argument("--validate-limit", type=int, default=25)
    parser.add_argument("--source-limit", type=int, default=10)
    parser.add_argument("--pdf-limit-per-source", type=int, default=5)
    parser.add_argument("--embed-limit", type=int, default=10)
    parser.add_argument("--include-pending-sources", action="store_true")
    args = parser.parse_args()

    run_pipeline(
        validate_limit=args.validate_limit,
        source_limit=args.source_limit,
        pdf_limit_per_source=args.pdf_limit_per_source,
        embed_limit=args.embed_limit,
        include_pending_sources=args.include_pending_sources,
    )


if __name__ == "__main__":
    main()
