from __future__ import annotations

from datetime import datetime, timezone


NEW_SOURCE_COLUMNS = ["is_new", "added_at", "discovered_from", "review_status", "reviewed_at", "reviewed_by"]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def mark_new_source(row: dict[str, str], discovered_from: str = "", added_at: str | None = None) -> dict[str, str]:
    row["is_new"] = "yes"
    row["added_at"] = added_at or utc_now()
    row["discovered_from"] = discovered_from
    row["review_status"] = "pending_review"
    row["reviewed_at"] = ""
    row["reviewed_by"] = ""
    return row


def ensure_new_source_columns(fieldnames: list[str], rows: list[dict[str, str]]) -> list[str]:
    normalized = list(fieldnames)
    for column in NEW_SOURCE_COLUMNS:
        if column not in normalized:
            normalized.append(column)
        for row in rows:
            row.setdefault(column, "")
    return normalized
