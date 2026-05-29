from __future__ import annotations

import argparse

from question_router import format_route, route_question


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect how a question will be routed.")
    parser.add_argument("question")
    args = parser.parse_args()

    route = route_question(args.question)
    print(format_route(route))


if __name__ == "__main__":
    main()
