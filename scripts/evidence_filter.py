from __future__ import annotations

import re


DEFAULT_MIN_RERANK_SCORE = 0.08


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def required_terms_match(text: str, required_terms: list[str] | tuple[str, ...] | None) -> bool:
    terms = [normalize_text(term) for term in (required_terms or []) if normalize_text(term)]
    if not terms:
        return True
    haystack = normalize_text(text)
    return any(term in haystack for term in terms)


def min_score_for_route(route: dict | None) -> float:
    intent = (route or {}).get("intent", "")
    if intent in {"historical_person", "dynasty_or_ruler", "historical_empire", "site_monument"}:
        return 0.08
    if intent in {"gis_satellite", "excavation_report", "manuscript_text"}:
        return 0.07
    return DEFAULT_MIN_RERANK_SCORE


def filter_embedding_hits(hits: list[dict], route: dict | None = None) -> list[dict]:
    required_terms = (route or {}).get("required_terms", [])
    threshold = min_score_for_route(route)
    filtered = []
    for hit in hits:
        text = f"{hit.get('title', '')} {hit.get('text', '')} {hit.get('url', '')}"
        score = float(hit.get("rerank_score", hit.get("score", 0.0)) or 0.0)
        if score < threshold:
            continue
        if not required_terms_match(text, required_terms):
            continue
        filtered.append(hit)
    return filtered
