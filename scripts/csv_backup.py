from __future__ import annotations

import csv
import shutil
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_FILE = PROJECT_ROOT / "metadata" / "heritage_links.csv"
BACKUP_DIR = PROJECT_ROOT / "metadata" / "backups"


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def backup_csv(reason: str = "manual") -> Path | None:
    if not CSV_FILE.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    safe_reason = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in reason)[:40]
    backup_path = BACKUP_DIR / f"heritage_links_{timestamp()}_{safe_reason}.csv"
    shutil.copy2(CSV_FILE, backup_path)
    return backup_path


def list_backups() -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(BACKUP_DIR.glob("heritage_links_*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)


def latest_backup() -> Path | None:
    backups = list_backups()
    return backups[0] if backups else None


def write_csv_with_backup(
    fieldnames: list[str],
    rows: list[dict[str, str]],
    reason: str,
    csv_file: Path = CSV_FILE,
) -> Path | None:
    backup_path = backup_csv(reason=reason)
    normalized_fieldnames = list(fieldnames)
    for row in rows:
        for column in row:
            if column not in normalized_fieldnames:
                normalized_fieldnames.append(column)
        for column in normalized_fieldnames:
            row.setdefault(column, "")

    with csv_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=normalized_fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return backup_path


def restore_backup(backup_path: Path | None = None) -> Path:
    selected = backup_path or latest_backup()
    if selected is None:
        raise FileNotFoundError("No heritage_links.csv backups found.")
    if not selected.exists():
        raise FileNotFoundError(f"Backup not found: {selected}")

    backup_csv(reason="before_restore")
    shutil.copy2(selected, CSV_FILE)
    return selected
