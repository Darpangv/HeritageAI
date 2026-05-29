from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from accessibility_policy import ACCESSIBILITY_PROMPT


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BRAIN_DIR = PROJECT_ROOT / "data" / "brain"
BRAIN_LOG = BRAIN_DIR / "last_brain_response.json"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-5-mini"

HERITAGE_SYSTEM_PROMPT = """
You are the ChatGPT brain for Indian Heritage AI.

Your job:
- Answer from the retrieved heritage context.
- Prefer factual, grounded explanations over dramatic storytelling.
- Cite factual claims with source IDs such as [S1], [S2].
- Cite page numbers whenever the context provides them.
- Use only the supplied sources and retrieved context.
- If the context is weak or incomplete, say what is missing.
- Do not invent dynasties, dates, sites, inscriptions, or source claims.
- Do not cite a source ID that is not listed in the retrieved context or source list.
- If a factual sentence cannot be tied to a retrieved source, mark it as uncertain or omit it.
- Keep answers useful for students, researchers, and heritage-tourism builders.

{accessibility_prompt}
""".strip()

HERITAGE_SYSTEM_PROMPT = HERITAGE_SYSTEM_PROMPT.format(accessibility_prompt=ACCESSIBILITY_PROMPT)


def current_time() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def extract_response_text(result: dict) -> str:
    if result.get("output_text"):
        return result["output_text"]

    parts = []
    for item in result.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                parts.append(content.get("text", ""))
    return "\n".join(parts).strip()


def format_openai_error(error: HTTPError) -> str:
    body = error.read().decode("utf-8", errors="ignore")
    message = body
    try:
        payload = json.loads(body)
        message = payload.get("error", {}).get("message", body)
    except json.JSONDecodeError:
        pass

    if error.code == 401:
        return (
            "OpenAI returned HTTP 401. The API key is missing, invalid, or revoked.\n"
            "Set a fresh key locally with: $env:OPENAI_API_KEY=\"your_new_key\""
        )
    if error.code == 429:
        return (
            "OpenAI returned HTTP 429. Your PDF/vector retrieval worked, but the GPT brain "
            "is blocked by rate limits or quota.\n\n"
            "Fixes:\n"
            "1. Check OpenAI billing/credits.\n"
            "2. Wait a few minutes and retry.\n"
            "3. Use a fresh rotated API key.\n"
            "4. Try a smaller model with: $env:HERITAGE_CHAT_MODEL=\"gpt-5-mini\"\n\n"
            f"OpenAI message:\n{message}"
        )
    return f"OpenAI returned HTTP {error.code}.\n\nOpenAI message:\n{message}"


def ask_chatgpt(
    question: str,
    context: str,
    sources: list[str] | None = None,
    model: str | None = None,
) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return (
            "OPENAI_API_KEY is not set, so the ChatGPT brain is not connected yet.\n\n"
            "Retrieved context:\n\n"
            f"{context}"
        )

    selected_model = model or os.environ.get("HERITAGE_CHAT_MODEL") or os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL
    source_text = "\n".join(f"- {source}" for source in (sources or []))
    payload = {
        "model": selected_model,
        "instructions": HERITAGE_SYSTEM_PROMPT,
        "input": (
            f"Question:\n{question}\n\n"
            f"Sources:\n{source_text}\n\n"
            f"Retrieved context:\n{context}\n\n"
            "Write the final answer with inline citations. Use source IDs from the retrieved "
            "context, for example [S1] or [S2], after claims that depend on a source. "
            "Include page citations like [S1, page 1] when available. "
            "The application will append the source-link list below the answer."
        ),
        "text": {"verbosity": "medium"},
    }

    data = json.dumps(payload).encode("utf-8")
    request = Request(
        OPENAI_RESPONSES_URL,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with urlopen(request, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        return format_openai_error(error)

    BRAIN_LOG.write_text(
        json.dumps(
            {
                "created_at": current_time(),
                "model": selected_model,
                "question": question,
                "sources": sources or [],
                "response": result,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return extract_response_text(result) or "The model returned no output text."


def main() -> None:
    parser = argparse.ArgumentParser(description="Test the ChatGPT brain connection.")
    parser.add_argument("question")
    parser.add_argument("--context", default="No retrieval context provided.")
    parser.add_argument("--model", help="Override HERITAGE_CHAT_MODEL for this run.")
    args = parser.parse_args()

    print(ask_chatgpt(args.question, args.context, model=args.model))


if __name__ == "__main__":
    main()
