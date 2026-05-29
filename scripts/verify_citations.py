from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from citation_verifier import verify_citations  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify RAG citation IDs and source overlap for an answer.")
    parser.add_argument("answer_file", help="Path to the answer markdown/text file.")
    parser.add_argument("--context-file", help="Optional file containing the retrieved context.")
    parser.add_argument("--context", default="", help="Retrieved context text.")
    parser.add_argument("--source", action="append", default=[], help="Source line such as '- [S1] Title page 1: URL'.")
    args = parser.parse_args()

    answer = Path(args.answer_file).read_text(encoding="utf-8", errors="replace")
    context = args.context
    if args.context_file:
        context = Path(args.context_file).read_text(encoding="utf-8", errors="replace")

    report = verify_citations(answer=answer, context=context, source_lines=args.source)
    print(f"status={report['status']}")
    print(f"checked_claims={report['checked_claims']}")
    print(f"available_ids={','.join(report['available_ids'])}")
    print(f"cited_ids={','.join(report['cited_ids'])}")
    for issue in report["issues"]:
        print(f"issue={issue}")
    for warning in report["warnings"]:
        print(f"warning={warning}")


if __name__ == "__main__":
    main()
