from __future__ import annotations

import argparse
from pathlib import Path

from csv_backup import list_backups, restore_backup


def main() -> None:
    parser = argparse.ArgumentParser(description="List or restore heritage_links.csv backups.")
    parser.add_argument("--list", action="store_true", help="List available backups.")
    parser.add_argument("--backup", help="Restore this specific backup path.")
    args = parser.parse_args()

    if args.list:
        backups = list_backups()
        if not backups:
            print("No backups found.")
            return
        for backup in backups:
            print(backup)
        return

    restored = restore_backup(Path(args.backup) if args.backup else None)
    print(f"Restored backup: {restored}")


if __name__ == "__main__":
    main()
