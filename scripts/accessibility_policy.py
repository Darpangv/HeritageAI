from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RULES_FILE = PROJECT_ROOT / "docs" / "end_user_accessibility_rules.md"

ACCESSIBILITY_PROMPT = """
End-user accessibility and archaeology usage rules:
- Use clear, plain English by default.
- Keep paragraphs short and scannable.
- Explain specialist archaeology terms briefly when important.
- Avoid unexplained abbreviations.
- Cite source-backed claims with RAG source IDs such as [S1] or [S1, page 4].
- End answers with source links when the application provides them.
- State uncertainty when evidence is incomplete, OCR-poor, multilingual, damaged, or ambiguous.
- Never invent dates, dynasties, site details, inscriptions, excavation findings, or interpretations.
- Do not provide instructions for illegal digging, artifact removal, trafficking, trespass, or evading heritage protection.
- Do not expose exact coordinates or operational access details for vulnerable, unprotected, or sensitive archaeological sites unless clearly official and already public.
- Distinguish evidence from interpretation.
- Encourage lawful visiting, conservation, and respect for local communities.
""".strip()


DISALLOWED_PATTERNS = [
    "how to dig",
    "where to dig",
    "metal detector",
    "remove artifact",
    "sell artifact",
    "smuggle",
    "loot",
    "secret site",
    "unprotected site coordinates",
]


def load_rules_text() -> str:
    if RULES_FILE.exists():
        return RULES_FILE.read_text(encoding="utf-8")
    return ACCESSIBILITY_PROMPT


def is_restricted_archaeology_request(question: str) -> bool:
    text = question.lower()
    return any(pattern in text for pattern in DISALLOWED_PATTERNS)


def restricted_response() -> str:
    return (
        "I cannot help with illegal digging, artifact removal, trafficking, trespass, "
        "or exposing vulnerable site access details.\n\n"
        "I can help with lawful alternatives: official site records, conservation guidance, "
        "museum/archive research, published excavation reports, GIS layers from public portals, "
        "or heritage education material."
    )
