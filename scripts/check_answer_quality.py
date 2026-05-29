from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from answer_quality_guard import evaluate_answer_quality, guard_answer  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Check an answer with the Heritage AI Answer Quality Guard.")
    parser.add_argument("answer_file", help="Path to a markdown/text answer file.")
    parser.add_argument("--question", default="No question provided.")
    parser.add_argument("--context", default="")
    parser.add_argument("--source", action="append", default=[], help="Source line such as '- [S1] Title: URL'.")
    parser.add_argument("--show-guarded", action="store_true")
    args = parser.parse_args()

    answer = Path(args.answer_file).read_text(encoding="utf-8", errors="replace")
    report = evaluate_answer_quality(args.question, answer, args.context, args.source)
    print(f"status={report['status']}")
    print(f"score={report['score']}")
    citation_report = report.get("citation_verifier", {})
    if citation_report:
        print(f"citation_status={citation_report.get('status')}")
        print(f"citation_checked_claims={citation_report.get('checked_claims')}")
    for issue in report["issues"]:
        print(f"issue={issue}")
    for warning in report["warnings"]:
        print(f"warning={warning}")

    if args.show_guarded:
        print("\n--- guarded answer ---\n")
        print(guard_answer(args.question, answer, args.context, args.source))


if __name__ == "__main__":
    main()
