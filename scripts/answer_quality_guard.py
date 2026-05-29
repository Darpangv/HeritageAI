from __future__ import annotations

import re


CITATION_RE = re.compile(r"\[(S\d+)(?:[,\s|][^\]]*)?\]")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

FACTUAL_MARKERS = {
    "century",
    "dynasty",
    "empire",
    "king",
    "queen",
    "ruler",
    "reign",
    "temple",
    "monument",
    "inscription",
    "excavation",
    "site",
    "period",
    "capital",
    "built",
    "founded",
    "dated",
    "located",
    "architecture",
    "archaeological",
}

UNCERTAINTY_WORDS = {
    "unclear",
    "uncertain",
    "incomplete",
    "limited",
    "ambiguous",
    "not enough",
    "not available",
    "weak",
    "may",
    "might",
}


def source_ids_from_lines(source_lines: list[str] | None) -> set[str]:
    ids: set[str] = set()
    for line in source_lines or []:
        ids.update(CITATION_RE.findall(line))
    return ids


def citation_ids_in_answer(answer: str) -> set[str]:
    return set(CITATION_RE.findall(answer or ""))


def has_uncertainty_language(answer: str) -> bool:
    lowered = answer.lower()
    return any(word in lowered for word in UNCERTAINTY_WORDS)


def likely_factual_sentence(sentence: str) -> bool:
    lowered = sentence.lower()
    if any(marker in lowered for marker in FACTUAL_MARKERS):
        return True
    if re.search(r"\b(?:[1-9]\d{2,3}|[0-9]+(?:st|nd|rd|th)\s+century)\b", lowered):
        return True
    # Two or more capitalized words often indicate named people, sites, or dynasties.
    return len(re.findall(r"\b[A-Z][a-z]{2,}\b", sentence)) >= 2


def uncited_factual_sentences(answer: str) -> list[str]:
    flagged = []
    for sentence in SENTENCE_RE.split(answer.strip()):
        cleaned = sentence.strip()
        if not cleaned or cleaned.startswith("Sources:"):
            continue
        if CITATION_RE.search(cleaned):
            continue
        if likely_factual_sentence(cleaned):
            flagged.append(cleaned)
    return flagged[:3]


def evaluate_answer_quality(
    question: str,
    answer: str,
    context: str,
    source_lines: list[str] | None = None,
) -> dict:
    from citation_verifier import verify_citations

    source_ids = source_ids_from_lines(source_lines)
    answer_ids = citation_ids_in_answer(answer)
    invalid_ids = sorted(answer_ids - source_ids) if source_ids else []
    issues = []
    warnings = []
    citation_report = verify_citations(answer, context, source_lines)

    if source_ids and not answer_ids:
        issues.append("No inline RAG citations were found even though sources were available.")
    if invalid_ids:
        issues.append(f"The answer cites unknown source IDs: {', '.join(invalid_ids)}.")

    unsupported = uncited_factual_sentences(answer)
    if source_ids and unsupported:
        warnings.append(
            "Some factual-looking sentences are not directly cited: "
            + " | ".join(sentence[:160] for sentence in unsupported)
        )

    if len(context.strip()) < 500:
        warnings.append("Retrieved context is short, so the answer should be treated as limited evidence.")
        if not has_uncertainty_language(answer):
            issues.append("Weak context was not clearly acknowledged in the answer.")

    if source_ids and not any(source_id in context for source_id in source_ids):
        warnings.append("Source IDs were provided, but not all IDs appear in the retrieved context labels.")

    for issue in citation_report["issues"]:
        issues.append(f"Citation verifier: {issue}")
    for warning in citation_report["warnings"]:
        warnings.append(f"Citation verifier: {warning}")

    score = 100
    score -= 30 * len(issues)
    score -= 10 * len(warnings)
    score = max(0, score)
    status = "pass" if score >= 70 and not issues else "review"
    return {
        "status": status,
        "score": score,
        "issues": issues,
        "warnings": warnings,
        "source_ids": sorted(source_ids),
        "answer_ids": sorted(answer_ids),
        "citation_verifier": citation_report,
        "question": question,
    }


def guard_answer(
    question: str,
    answer: str,
    context: str,
    source_lines: list[str] | None = None,
) -> str:
    report = evaluate_answer_quality(question, answer, context, source_lines)
    if report["status"] == "pass":
        return answer

    notes = []
    for issue in report["issues"]:
        notes.append(f"- Issue: {issue}")
    for warning in report["warnings"]:
        notes.append(f"- Warning: {warning}")

    guard_block = "\n".join(
        [
            "Answer Quality Guard:",
            f"- Status: {report['status']}",
            f"- Score: {report['score']}/100",
            *notes,
            "- Use this answer with caution until the weak points above are resolved.",
        ]
    )
    return f"{answer.rstrip()}\n\n{guard_block}"
