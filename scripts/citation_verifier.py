from __future__ import annotations

import re
from collections import defaultdict


CITATION_RE = re.compile(r"\[(S\d+)(?:[,\s|]+([^\]]+))?\]")
CONTEXT_LABEL_RE = re.compile(r"\[(S\d+)\s*\|\s*Page\s+([^\]]+)\]")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
STOPWORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "because",
    "been",
    "being",
    "but",
    "can",
    "could",
    "did",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "into",
    "its",
    "may",
    "might",
    "not",
    "only",
    "such",
    "that",
    "the",
    "their",
    "then",
    "there",
    "these",
    "this",
    "was",
    "were",
    "when",
    "where",
    "which",
    "with",
}


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return {word for word in words if len(word) > 2 and word not in STOPWORDS}


def split_context_by_source(context: str) -> dict[str, dict]:
    matches = list(CONTEXT_LABEL_RE.finditer(context or ""))
    sources: dict[str, dict] = {}
    for index, match in enumerate(matches):
        source_id = match.group(1)
        page = match.group(2).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(context)
        block = context[start:end].strip()
        entry = sources.setdefault(source_id, {"pages": set(), "text": ""})
        entry["pages"].add(page)
        entry["text"] = f"{entry['text']}\n{block}".strip()
    return sources


def pages_from_source_lines(source_lines: list[str] | None) -> dict[str, set[str]]:
    pages: dict[str, set[str]] = defaultdict(set)
    for line in source_lines or []:
        citation = CITATION_RE.search(line)
        if not citation:
            continue
        source_id = citation.group(1)
        for page in re.findall(r"\b(?:page|pages)\s+([a-zA-Z0-9,\s]+)", line, flags=re.IGNORECASE):
            for item in re.split(r"[,\s]+", page):
                item = item.strip()
                if item:
                    pages[source_id].add(item)
    return dict(pages)


def cited_page_numbers(citation_detail: str | None) -> set[str]:
    if not citation_detail:
        return set()
    pages = set()
    for page in re.findall(r"\bpage\s+([a-zA-Z0-9]+)", citation_detail, flags=re.IGNORECASE):
        pages.add(page.strip())
    return pages


def clean_sentence(sentence: str) -> str:
    return CITATION_RE.sub("", sentence).strip()


def citation_overlap(sentence: str, source_text: str) -> float:
    claim_terms = tokenize(clean_sentence(sentence))
    if not claim_terms:
        return 1.0
    source_terms = tokenize(source_text)
    if not source_terms:
        return 0.0
    return len(claim_terms & source_terms) / len(claim_terms)


def verify_citations(answer: str, context: str, source_lines: list[str] | None = None) -> dict:
    context_sources = split_context_by_source(context)
    source_line_pages = pages_from_source_lines(source_lines)
    available_ids = set(context_sources) | set(source_line_pages)
    cited_ids = set()
    issues = []
    warnings = []
    checked_claims = 0
    weak_claims = []

    for sentence in SENTENCE_RE.split((answer or "").strip()):
        sentence = sentence.strip()
        citations = list(CITATION_RE.finditer(sentence))
        if not citations:
            continue

        for citation in citations:
            source_id = citation.group(1)
            cited_ids.add(source_id)
            detail = citation.group(2)
            if available_ids and source_id not in available_ids:
                issues.append(f"{source_id} is cited but was not available in retrieved context or source list.")
                continue

            cited_pages = cited_page_numbers(detail)
            known_pages = set(context_sources.get(source_id, {}).get("pages", set()))
            known_pages |= source_line_pages.get(source_id, set())
            if cited_pages and known_pages and not cited_pages <= known_pages:
                issues.append(
                    f"{source_id} cites page(s) {', '.join(sorted(cited_pages))}, "
                    f"but available page(s) are {', '.join(sorted(known_pages))}."
                )

        combined_source_text = "\n".join(context_sources.get(citation.group(1), {}).get("text", "") for citation in citations)
        if combined_source_text:
            checked_claims += 1
            overlap = citation_overlap(sentence, combined_source_text)
            if overlap < 0.20:
                weak_claims.append((overlap, clean_sentence(sentence)))

    for overlap, sentence in weak_claims[:3]:
        warnings.append(f"Low citation/source overlap ({overlap:.2f}) for claim: {sentence[:180]}")

    status = "pass" if not issues and not warnings else "review"
    return {
        "status": status,
        "issues": issues,
        "warnings": warnings,
        "available_ids": sorted(available_ids),
        "cited_ids": sorted(cited_ids),
        "checked_claims": checked_claims,
    }
