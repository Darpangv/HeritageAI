from __future__ import annotations

import re


STOPWORDS = {
    "about",
    "also",
    "and",
    "are",
    "can",
    "for",
    "from",
    "how",
    "into",
    "list",
    "out",
    "the",
    "this",
    "what",
    "when",
    "where",
    "which",
    "who",
    "with",
}
CONTEXT_BLOCK_RE = re.compile(r"\[(S\d+)\s*\|\s*Page\s+([^\]]+)\]\s*(.*?)(?=\n\n\[S\d+\s*\|\s*Page\s+|\Z)", re.DOTALL)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9]+", (text or "").lower())
    return {word for word in words if len(word) > 2 and word not in STOPWORDS}


def split_sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    cleaned = re.sub(r"\b(?:Title|Description|H1|H2|H3):\s*", "", cleaned)
    return [sentence.strip() for sentence in SENTENCE_RE.split(cleaned) if len(sentence.strip()) > 35]


def score_sentence(question_terms: set[str], sentence: str) -> int:
    sentence_terms = tokenize(sentence)
    score = len(question_terms & sentence_terms) * 3
    lowered = sentence.lower()
    if any(term in lowered for term in ("archaeolog", "empire", "king", "monument", "ruler", "site", "temple")):
        score += 1
    if re.search(r"\b(?:1[0-9]{3}|[0-9]+(?:st|nd|rd|th)\s+century)\b", sentence):
        score += 1
    return score


def local_source_answer(question: str, context: str, sources: list[str] | None = None) -> str:
    question_terms = tokenize(question)
    candidates = []

    for match in CONTEXT_BLOCK_RE.finditer(context or ""):
        source_id, page, block = match.groups()
        for sentence in split_sentences(block):
            score = score_sentence(question_terms, sentence)
            if score <= 0:
                continue
            citation = f"[{source_id}, page {page}]" if page else f"[{source_id}]"
            candidates.append((score, source_id, sentence, citation))

    candidates.sort(key=lambda item: item[0], reverse=True)
    selected = []
    seen = set()
    for _, source_id, sentence, citation in candidates:
        key = re.sub(r"\W+", "", sentence.lower())[:180]
        if key in seen:
            continue
        seen.add(key)
        selected.append((source_id, sentence, citation))
        if len(selected) >= 5:
            break

    if not selected:
        return (
            "I found sources, but the retrieved text is not strong enough to answer this confidently. "
            "Please approve or add better source material for this topic, then rebuild embeddings."
        )

    lines = [
        "OpenAI is not connected, so this is a local source-based answer from the retrieved evidence.",
        "",
    ]
    for index, (_, sentence, citation) in enumerate(selected, start=1):
        lines.append(f"{index}. {sentence} {citation}")

    if sources:
        lines.extend(["", "Evidence note: I used only the retrieved cited source text above."])
    return "\n".join(lines)
