#!/usr/bin/env python3
"""Read a Trigpoint ledger and report problems without writing anything.

Exit codes: 0 clean or warnings only, 1 at least one error, 2 ledger unreadable.
Suitable as a CI gate.
"""

from __future__ import annotations

import pathlib
import sys
from typing import List

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from trigpoint_ledger import Problem, has_errors, parse_ledger, validate

DEFAULT_LEDGER = "ROADMAP.md"


def report(problems: List[Problem], ledger_path: str) -> str:
    if not problems:
        return "{0}: no problems found.".format(ledger_path)
    lines = []
    for problem in sorted(problems, key=lambda item: (item.severity, item.line_number)):
        location = (
            "{0}:{1}".format(ledger_path, problem.line_number)
            if problem.line_number
            else ledger_path
        )
        lines.append(
            "{0}  {1}  {2}".format(problem.severity.upper(), location, problem.message)
        )
    error_count = sum(1 for problem in problems if problem.severity == "error")
    warning_count = len(problems) - error_count
    lines.append(
        "{0} error(s), {1} warning(s) in {2}".format(
            error_count, warning_count, ledger_path
        )
    )
    return "\n".join(lines)


def main(argv: List[str]) -> int:
    ledger_path = argv[0] if argv else DEFAULT_LEDGER
    path = pathlib.Path(ledger_path)
    if not path.is_file():
        sys.stderr.write("cannot read ledger: {0}\n".format(ledger_path))
        return 2
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exception:
        sys.stderr.write("cannot read ledger: {0} ({1})\n".format(ledger_path, exception))
        return 2
    problems = validate(parse_ledger(text))
    sys.stdout.write(report(problems, ledger_path) + "\n")
    return 1 if has_errors(problems) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
