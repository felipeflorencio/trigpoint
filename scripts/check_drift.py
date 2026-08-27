#!/usr/bin/env python3
"""Read a Trigpoint ledger and report problems without writing anything.

Exit codes: 0 clean or warnings only, 1 at least one error, 2 ledger unreadable,
3 nothing was checked because the parser claimed no tasks in this file.
Suitable as a CI gate.

Exit 3 exists because "no problems found" and "I read nothing" were once the
same output. A gate whose success is indistinguishable from a gate that is not
running protects nobody, and the common way to reach that state is not a broken
parser but a ROADMAP.md that has never been converted.
"""

from __future__ import annotations

import pathlib
import sys
from typing import List

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

try:
    from trigpoint_ledger import (
        Problem,
        count_checkbox_lines,
        count_task_shaped_lines,
        has_errors,
        parse_ledger,
        validate,
    )
except ImportError as import_error:  # a half-updated .trigpoint/ copy
    # Exit 1 means "your ledger has errors" and CI would report a broken
    # install as a broken plan. The scripts are vendored and refreshed by hand,
    # so copying some of them and not others is a real state a user reaches.
    sys.stderr.write(
        "cannot run the drift gate: the copied Trigpoint scripts do not match each "
        "other ({0}). Re-copy all five scripts into .trigpoint/ from the plugin, or "
        "re-run the trigpoint skill.\n".format(import_error)
    )
    raise SystemExit(2)

DEFAULT_LEDGER = "ROADMAP.md"
NOTHING_CHECKED = 3


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


def describe_coverage(ledger, checkbox_lines: int, ledger_path: str) -> str:
    """State what was actually read, so a pass is never a bare assertion."""
    ticked = [task for track in ledger.tracks for task in track.tasks if task.done]
    criteria = len(ledger.done_criteria)
    unaccounted = max(0, checkbox_lines - ledger.task_count - criteria)
    return (
        "{0}: {1} task(s) in {2} track(s) and {3} definition-of-done criteria; "
        "{4} ticked, {5} carrying evidence; {6} checkbox line(s) read, "
        "{7} not claimed as either.".format(
            ledger_path,
            ledger.task_count,
            len(ledger.tracks),
            criteria,
            len(ticked),
            sum(1 for task in ticked if task.evidence),
            checkbox_lines,
            unaccounted,
        )
    )


def nothing_checked_message(checkbox_lines: int, ledger_path: str,
                            tracks: int = 0, task_shaped: int = 0) -> str:
    """Say why nothing was checked, and say something true.

    Refusing to pass is right; asserting a false cause for it is not. A ledger
    whose tracks were recognised but whose tasks are not written yet was told
    the file might not be a ledger at all, one line under a summary saying a
    track had been found. The track count separates the two cases, and only
    one of them is a document this parser failed to understand.
    """
    seen = (
        ""
        if not checkbox_lines
        else " although {0} checkbox line(s) are present".format(checkbox_lines)
    )
    if task_shaped and not tracks:
        return (
            "{0}: {1} line(s) are already task-shaped but sit in no track, so none of them "
            "was checked{2}. A section becomes a track by carrying a **Scope:** line "
            "directly under its heading; without one its tasks are invisible. Add that "
            "line to each track heading. This is not a pass.".format(
                ledger_path, task_shaped, seen
            )
        )
    if tracks:
        return (
            "{0}: {1} track(s) recognised but no tasks written in them{2}. A task line "
            "reads `- [ ] **1.1** text`. There is nothing here to check yet, so this is "
            "not a pass.".format(ledger_path, tracks, seen)
        )
    return (
        "{0}: no tasks parsed{1}. Either this file is not a Trigpoint ledger, or the "
        "parser has stopped recognising it. A section becomes a track by carrying a "
        "**Scope:** line, and a task line reads `- [ ] **1.1** text`. NOTHING WAS "
        "CHECKED; this is not a pass.".format(ledger_path, seen)
    )


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
    ledger = parse_ledger(text)
    checkbox_lines = count_checkbox_lines(text)
    sys.stdout.write(describe_coverage(ledger, checkbox_lines, ledger_path) + "\n")
    if ledger.task_count == 0:
        sys.stderr.write(
            nothing_checked_message(
                checkbox_lines, ledger_path, len(ledger.tracks),
                count_task_shaped_lines(text),
            )
            + "\n"
        )
        return NOTHING_CHECKED
    problems = validate(ledger)
    sys.stdout.write(report(problems, ledger_path) + "\n")
    return 1 if has_errors(problems) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
