from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = PROJECT_ROOT / "data" / "conversation_memory"
MEMORY_DB = MEMORY_DIR / "conversations.sqlite"
STOPWORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "can",
    "does",
    "for",
    "from",
    "how",
    "into",
    "its",
    "tell",
    "that",
    "the",
    "their",
    "then",
    "there",
    "these",
    "this",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "with",
}


def normalize_session_id(session_id: str | None) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "-", session_id or "default").strip("-")
    return cleaned[:80] or "default"


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9]+", (text or "").lower())
    terms = {word for word in words if len(word) > 2 and word not in STOPWORDS}
    normalized = set(terms)
    for term in terms:
        if len(term) > 4 and term.endswith("s"):
            normalized.add(term[:-1])
    return normalized


def connect() -> sqlite3.Connection:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(MEMORY_DB)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            route TEXT NOT NULL DEFAULT ''
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id, created_at)")
    connection.commit()
    return connection


def add_turn(session_id: str | None, question: str, answer: str, route: str = "") -> None:
    connection = connect()
    try:
        connection.execute(
            """
            INSERT INTO turns (session_id, created_at, question, answer, route)
            VALUES (?, ?, ?, ?, ?)
            """,
            (normalize_session_id(session_id), int(time.time()), question.strip(), answer.strip(), route.strip()),
        )
        connection.commit()
    finally:
        connection.close()


def list_turns(session_id: str | None, limit: int = 20) -> list[dict]:
    connection = connect()
    try:
        rows = connection.execute(
            """
            SELECT * FROM turns
            WHERE session_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (normalize_session_id(session_id), limit),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def search_turns(session_id: str | None, query: str, limit: int = 5) -> list[dict]:
    query_terms = tokenize(query)
    if not query_terms:
        return []

    candidates = list_turns(session_id, limit=80)
    scored = []
    for row in candidates:
        haystack = f"{row.get('question', '')} {row.get('answer', '')[:1200]}"
        terms = tokenize(haystack)
        overlap = len(query_terms & terms)
        if overlap:
            scored.append((overlap, row["created_at"], row))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [row for _, _, row in scored[:limit]]


def build_memory_context(session_id: str | None, question: str, limit: int = 4) -> str:
    relevant = search_turns(session_id, question, limit=limit)
    if not relevant:
        return ""

    lines = [
        "Conversation memory from earlier turns. This is user/session context, not source evidence.",
        "Do not cite conversation memory as a RAG source.",
    ]
    for index, row in enumerate(relevant, start=1):
        answer = re.sub(r"\[(?:S\d+)(?:[,\s|][^\]]*)?\]", "", row.get("answer", ""))
        answer = re.sub(r"\s+", " ", answer).strip()
        lines.append(f"Memory {index} question: {row.get('question', '').strip()}")
        lines.append(f"Memory {index} answer summary: {answer[:700]}")
    return "\n".join(lines)


def clear_session(session_id: str | None) -> int:
    connection = connect()
    try:
        cursor = connection.execute("DELETE FROM turns WHERE session_id = ?", (normalize_session_id(session_id),))
        connection.commit()
        return int(cursor.rowcount)
    finally:
        connection.close()


def stats() -> dict:
    connection = connect()
    try:
        total = connection.execute("SELECT COUNT(*) AS count FROM turns").fetchone()["count"]
        sessions = connection.execute("SELECT COUNT(DISTINCT session_id) AS count FROM turns").fetchone()["count"]
        return {"turns": int(total), "sessions": int(sessions), "path": str(MEMORY_DB)}
    finally:
        connection.close()
