from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from conversation_memory import build_memory_context, clear_session, list_turns, stats  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage local conversation memory.")
    parser.add_argument("--session-id", default="default")
    parser.add_argument("--list", action="store_true", help="List recent memory turns.")
    parser.add_argument("--query", help="Preview relevant memory for a question.")
    parser.add_argument("--clear", action="store_true", help="Clear memory for the selected session.")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    if args.clear:
        deleted = clear_session(args.session_id)
        print(f"Deleted {deleted} memory turns for session {args.session_id}.")
        return

    if args.query:
        print(build_memory_context(args.session_id, args.query, limit=args.limit) or "No relevant memory found.")
        return

    if args.list:
        rows = list_turns(args.session_id, limit=args.limit)
        if not rows:
            print("No memory turns found.")
            return
        for row in rows:
            print(f"[{row['id']}] {row['question']}")
        return

    info = stats()
    print(f"Memory DB: {info['path']}")
    print(f"Sessions: {info['sessions']}")
    print(f"Turns: {info['turns']}")


if __name__ == "__main__":
    main()
