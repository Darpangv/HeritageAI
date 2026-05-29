from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import ssl
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_FILE = PROJECT_ROOT / "metadata" / "heritage_links.csv"
PDF_DIR = PROJECT_ROOT / "data" / "pdfs"
EXTRACT_DIR = PROJECT_ROOT / "data" / "extracted"
USER_AGENT = "Indian-Heritage-AI-Agent/1.0"
OPENAI_API_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-5-mini"
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
}


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return {word for word in words if len(word) > 2 and word not in STOPWORDS}


def score_text(question_terms: set[str], text: str) -> int:
    haystack = tokenize(text)
    return len(question_terms & haystack)


def request_url(url: str, method: str = "GET", timeout: int = 20):
    context = ssl.create_default_context()
    request = Request(url, method=method, headers={"User-Agent": USER_AGENT})
    return urlopen(request, timeout=timeout, context=context)


def load_links() -> list[dict[str, str]]:
    with CSV_FILE.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def search_database(question: str, limit: int = 5, route: dict | None = None) -> list[dict[str, str]]:
    terms = tokenize(question)
    preferred_categories = set((route or {}).get("preferred_categories", []))
    boost_terms = tokenize(" ".join((route or {}).get("boost_terms", [])))
    terms = terms | boost_terms
    rows = []
    for row in load_links():
        searchable = " ".join(
            [
                row.get("title", ""),
                row.get("category", ""),
                row.get("region", ""),
                row.get("source", ""),
                row.get("document_category", ""),
                row.get("notes", ""),
                row.get("link", ""),
            ]
        )
        score = score_text(terms, searchable)
        if row.get("document_category") in preferred_categories:
            score += 3
        if row.get("usable_for_rag", "yes").lower() == "no":
            score -= 2
        if score:
            row = dict(row)
            row["_score"] = str(score)
            rows.append(row)

    rows.sort(key=lambda item: int(item["_score"]), reverse=True)
    return rows[:limit]


def is_pdf_url(url: str) -> bool:
    if url.lower().split("?", 1)[0].endswith(".pdf"):
        return True
    try:
        with request_url(url, method="HEAD", timeout=12) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            return "application/pdf" in content_type
    except Exception:
        return False


def discover_pdf_links(page_url: str, question: str, limit: int = 5) -> list[dict[str, str]]:
    from web_ingestion import extract_pdf_links, parse_web_document

    try:
        with request_url(page_url, timeout=20) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except Exception as error:
        return [{"url": page_url, "text": "", "error": f"{type(error).__name__}: {error}"}]

    document = parse_web_document(page_url, html)
    terms = tokenize(question)
    candidates = []
    seen = set()
    for link in extract_pdf_links(document):
        url = link["url"]
        if url in seen:
            continue
        seen.add(url)
        label = f"{link.get('text', '')} {url}"
        candidates.append({**link, "_score": score_text(terms, label)})

    candidates.sort(key=lambda item: item["_score"], reverse=True)
    return candidates[:limit]


def extract_source_page(url: str, question: str, route: dict | None = None) -> dict[str, str | int] | None:
    from web_ingestion import extract_relevant_text, parse_web_document

    try:
        with request_url(url, timeout=20) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type:
                return None
            html = response.read().decode("utf-8", errors="ignore")
    except Exception:
        return None

    document = parse_web_document(url, html)
    text = document.text
    if not text:
        return None

    required_terms = [term.lower() for term in (route or {}).get("required_terms", [])]
    terms = tokenize(question) | tokenize(" ".join((route or {}).get("boost_terms", [])))
    excerpt = extract_relevant_text(document, terms=terms, required_terms=required_terms)
    if not excerpt:
        return None
    return {"page": "web", "text": excerpt}


def download_pdf(url: str) -> Path:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    path = PDF_DIR / f"{digest}.pdf"
    if path.exists() and path.stat().st_size > 0:
        return path

    with request_url(url, timeout=60) as response:
        path.write_bytes(response.read())
    return path


def extract_pdf_pages(pdf_path: Path) -> list[dict[str, str | int]]:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError("Install pypdf first: python -m pip install pypdf") from error

    reader = PdfReader(str(pdf_path))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append({"page": index, "text": re.sub(r"\s+", " ", text).strip()})
    return pages


def select_relevant_pages(question: str, pages: list[dict[str, str | int]], limit: int = 5):
    terms = tokenize(question)
    scored = []
    for page in pages:
        score = score_text(terms, str(page["text"]))
        if score:
            scored.append({**page, "_score": score})
    scored.sort(key=lambda item: item["_score"], reverse=True)
    return scored[:limit] if scored else pages[:limit]


def build_context(selected_pages: list[dict[str, str | int]], max_chars: int = 12000) -> str:
    chunks = []
    used = 0
    for page in selected_pages:
        text = str(page["text"])
        excerpt = text[:2500]
        citation_id = page.get("citation_id")
        label = f"[{citation_id} | Page {page['page']}]" if citation_id else f"[Page {page['page']}]"
        block = f"{label}\n{excerpt}"
        if used + len(block) > max_chars:
            break
        chunks.append(block)
        used += len(block)
    return "\n\n".join(chunks)


def call_openai(question: str, context: str, sources: list[str] | None = None) -> str:
    from chatgpt_brain import ask_chatgpt

    return ask_chatgpt(question=question, context=context, sources=sources)


def apply_answer_quality_guard(question: str, answer: str, context: str, source_lines: list[str]) -> str:
    from answer_quality_guard import guard_answer

    return guard_answer(question=question, answer=answer, context=context, source_lines=source_lines)


def unique_source_lines(sources: list[dict]) -> list[str]:
    seen = set()
    lines = []
    for source in sources:
        url = str(source.get("url", "")).strip()
        citation_id = str(source.get("citation_id", "")).strip()
        key = "|".join(
            [
                url,
                str(source.get("page", "")),
                ",".join(str(item) for item in source.get("pages", []) or []),
            ]
        )
        if not url or key in seen:
            continue
        seen.add(key)
        title = str(source.get("title") or source.get("source") or "Source").strip()
        pages = source.get("pages")
        page = source.get("page")
        if pages:
            page_text = f" pages {', '.join(str(item) for item in pages)}"
        elif page:
            page_text = f" page {page}"
        else:
            page_text = ""
        prefix = f"[{citation_id}] " if citation_id else ""
        lines.append(f"- {prefix}{title}{page_text}: {url}")
    return lines


def append_sources(answer: str, source_lines: list[str]) -> str:
    if not source_lines:
        return answer
    return f"{answer.rstrip()}\n\nSources:\n" + "\n".join(source_lines)


def assign_citation_ids(items: list[dict], key_fields: list[str]) -> list[dict]:
    citation_by_key = {}
    next_index = 1
    assigned = []
    for item in items:
        key = tuple(str(item.get(field, "")) for field in key_fields)
        if key not in citation_by_key:
            citation_by_key[key] = f"S{next_index}"
            next_index += 1
        assigned.append({**item, "citation_id": citation_by_key[key]})
    return assigned


def answer_question(question: str, db_limit: int = 5, pdf_limit: int = 3, page_limit: int = 5) -> None:
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    from accessibility_policy import is_restricted_archaeology_request, restricted_response
    from question_router import expand_question, format_route, inventory_answer, route_question, source_list_answer

    if is_restricted_archaeology_request(question):
        result_text = append_sources(restricted_response(), ["- [S1] docs/end_user_accessibility_rules.md"])
        output_path = EXTRACT_DIR / "last_answer.md"
        output_path.write_text(
            "\n\n".join([f"# Question\n\n{question}", "# Answer", result_text]),
            encoding="utf-8",
        )
        print("\nAnswer:\n")
        print(result_text)
        print(f"\nSaved result to {output_path}")
        return

    route = route_question(question)
    print(f"Question route: {format_route(route)}")
    retrieval_question = expand_question(question, route)
    if retrieval_question != question:
        print(f"Expanded retrieval query: {retrieval_question}")

    if route.get("answer_mode") == "source_inventory":
        answer = inventory_answer(question)
        result_text = append_sources(answer, ["- [S1] metadata/heritage_links.csv"])
        output_path = EXTRACT_DIR / "last_answer.md"
        output_path.write_text(
            "\n\n".join([f"# Question\n\n{question}", "# Answer", result_text]),
            encoding="utf-8",
        )
        print("\nAnswer:\n")
        print(result_text)
        print(f"\nSaved result to {output_path}")
        return

    if route.get("answer_mode") == "source_list":
        answer = source_list_answer(question, route)
        result_text = append_sources(answer, ["- [S1] metadata/heritage_links.csv"])
        output_path = EXTRACT_DIR / "last_answer.md"
        output_path.write_text(
            "\n\n".join([f"# Question\n\n{question}", "# Answer", result_text]),
            encoding="utf-8",
        )
        print("\nAnswer:\n")
        print(result_text)
        print(f"\nSaved result to {output_path}")
        return

    try:
        from search_embeddings import search_embeddings

        embedding_hits = search_embeddings(question, top_k=page_limit, route=route)
    except Exception:
        embedding_hits = []

    if embedding_hits:
        required_terms = [term.lower() for term in route.get("required_terms", [])]
        if required_terms:
            embedding_hits = [
                hit
                for hit in embedding_hits
                if any(term in f"{hit.get('title', '')} {hit.get('text', '')}".lower() for term in required_terms)
            ]

    if embedding_hits:
        print("Reranked embedding matches:")
        for hit in embedding_hits:
            print(f"- {hit['title']} page {hit['page']} (rerank {hit['score']:.3f})")

        cited_hits = assign_citation_ids(embedding_hits, ["url", "page"])
        selected_pages = [
            {
                "citation_id": hit["citation_id"],
                "page": hit["page"],
                "text": hit["text"],
            }
            for hit in cited_hits
        ]
        context = build_context(selected_pages)
        source_lines = unique_source_lines(
            [
                {
                    "citation_id": hit["citation_id"],
                    "title": hit["title"],
                    "url": hit["url"],
                    "page": hit["page"],
                }
                for hit in cited_hits
            ]
        )
        answer = call_openai(question, context, sources=source_lines)
        answer = apply_answer_quality_guard(question, answer, context, source_lines)
        result_text = append_sources(answer, source_lines)

        output_path = EXTRACT_DIR / "last_answer.md"
        output = [
            f"# Question\n\n{question}",
            "# Answer",
            result_text,
        ]
        output_path.write_text("\n\n".join(output), encoding="utf-8")
        print("\nAnswer:\n")
        print(result_text)
        print(f"\nSaved result to {output_path}")
        return

    database_hits = search_database(retrieval_question, limit=db_limit, route=route)
    if not database_hits:
        print("No matching heritage database entries found.")
        return

    print("Database matches:")
    for row in database_hits:
        print(f"- {row['title']} ({row['link']})")

    source_page_candidates = []
    pdf_candidates = []
    for row in database_hits:
        url = row["link"]
        if is_pdf_url(url):
            pdf_candidates.append({"url": url, "text": row["title"], "source": row["title"]})
        else:
            source_page = extract_source_page(url, retrieval_question, route=route)
            if source_page:
                source_page_candidates.append(
                    {
                        "title": row["title"],
                        "url": url,
                        "page": source_page["page"],
                        "text": source_page["text"],
                    }
                )
            for candidate in discover_pdf_links(url, retrieval_question, limit=pdf_limit):
                if candidate.get("error"):
                    print(f"Could not inspect {url}: {candidate['error']}")
                    continue
                pdf_candidates.append({**candidate, "source": row["title"]})

    if source_page_candidates:
        cited_pages = assign_citation_ids(source_page_candidates, ["url", "page"])
        selected_pages = [
            {
                "citation_id": item["citation_id"],
                "page": item["page"],
                "text": item["text"],
            }
            for item in cited_pages
        ]
        context = build_context(selected_pages)
        source_lines = unique_source_lines(cited_pages)
        answer = call_openai(question, context, sources=source_lines)
        answer = apply_answer_quality_guard(question, answer, context, source_lines)
        result_text = append_sources(answer, source_lines)
        output_path = EXTRACT_DIR / "last_answer.md"
        output_path.write_text(
            "\n\n".join([f"# Question\n\n{question}", "# Answer", result_text]),
            encoding="utf-8",
        )
        print("\nAnswer:\n")
        print(result_text)
        print(f"\nSaved result to {output_path}")
        return

    if not pdf_candidates:
        print("No PDF candidates found from the matching database entries.")
        print("Add direct PDF URLs to metadata/heritage_links.csv or choose a source page that lists PDFs.")
        return

    pdf_candidates = pdf_candidates[:pdf_limit]
    all_selected_pages = []
    used_sources = []
    for source_index, candidate in enumerate(pdf_candidates, start=1):
        url = candidate["url"]
        print(f"Opening PDF: {url}")
        try:
            pdf_path = download_pdf(url)
            pages = extract_pdf_pages(pdf_path)
        except Exception as error:
            print(f"Skipped PDF because extraction failed: {type(error).__name__}: {error}")
            continue
        selected = select_relevant_pages(retrieval_question, pages, limit=page_limit)
        citation_id = f"S{source_index}"
        for page in selected:
            page["citation_id"] = citation_id
        all_selected_pages.extend(selected)
        used_sources.append(
            {
                "citation_id": citation_id,
                "title": candidate.get("source") or candidate.get("text") or "PDF source",
                "url": url,
                "file": str(pdf_path),
                "pages": [page["page"] for page in selected],
            }
        )

    if not all_selected_pages:
        print("PDFs were found, but no extractable text was available.")
        return

    context = build_context(all_selected_pages)
    source_lines = unique_source_lines(used_sources)
    answer = call_openai(question, context, sources=source_lines)
    answer = apply_answer_quality_guard(question, answer, context, source_lines)
    result_text = append_sources(answer, source_lines)

    output_path = EXTRACT_DIR / "last_answer.md"
    output = [
        f"# Question\n\n{question}",
        "# Answer",
        result_text,
    ]
    output_path.write_text("\n\n".join(output), encoding="utf-8")
    print("\nAnswer:\n")
    print(result_text)
    print(f"\nSaved result to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Heritage AI question-to-PDF-to-answer pipeline.")
    parser.add_argument("question", help="Question to answer from heritage PDF sources.")
    parser.add_argument("--db-limit", type=int, default=5)
    parser.add_argument("--pdf-limit", type=int, default=3)
    parser.add_argument("--page-limit", type=int, default=5)
    args = parser.parse_args()

    answer_question(
        question=args.question,
        db_limit=args.db_limit,
        pdf_limit=args.pdf_limit,
        page_limit=args.page_limit,
    )


if __name__ == "__main__":
    main()
