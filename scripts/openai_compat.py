from __future__ import annotations

import os


DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


def openai_base_url() -> str:
    return os.environ.get("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL).rstrip("/")


def openai_endpoint(path: str) -> str:
    return f"{openai_base_url()}/{path.lstrip('/')}"
