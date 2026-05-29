from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[0]
sys.path.insert(0, str(SCRIPT_DIR))

from vector_db import SQLITE_FILE, VectorStore  # noqa: E402
from question_router import expand_question, format_route, route_question  # noqa: E402


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def search_embeddings(question: str, top_k: int = 5, route: dict | None = None) -> list[dict]:
    if not SQLITE_FILE.exists():
        raise FileNotFoundError(
            f"{SQLITE_FILE} does not exist. Run scripts/build_embeddings.py first."
        )
    route = route or route_question(question)
    retrieval_question = expand_question(question, route)
    store = VectorStore(SQLITE_FILE)
    try:
        return store.search(retrieval_question, top_k=top_k, route=route)
    finally:
        store.close()


def format_result(result: dict) -> str:
    text = result["text"]
    excerpt = text[:500] + ("..." if len(text) > 500 else "")
    return (
        f"Score: {result['score']:.3f}\n"
        f"Title: {result['title']}\n"
        f"Document category: {result.get('document_category', '')}\n"
        f"Page: {result['page']}\n"
        f"URL: {result['url']}\n"
        f"Rerank: {result.get('rerank_reason', '')}\n"
        f"Excerpt: {excerpt}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Search local heritage embeddings.")
    parser.add_argument("question")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    route = route_question(args.question)
    print(f"Question route: {format_route(route)}")
    expanded = expand_question(args.question, route)
    if expanded != args.question:
        print(f"Expanded retrieval query: {expanded}")
    print("-" * 80)

    for result in search_embeddings(args.question, top_k=args.top_k, route=route):
        print(format_result(result))
        print("-" * 80)


if __name__ == "__main__":
    main()
