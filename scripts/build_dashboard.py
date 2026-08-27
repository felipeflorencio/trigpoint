#!/usr/bin/env python3
"""Regenerate the ledger's progress table and the dashboard HTML.

Applies what matches and writes regardless. A missing region is reported, never
a reason to discard the rest of the work. This script never commits.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys
import tempfile
from typing import List, Optional

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from trigpoint_ledger import (
    CRITERION_LINE,
    count_checkbox_lines,
    HEADING_LINE,
    METADATA_LINE,
    TASK_LINE,
    _lines_outside_fences,
    has_errors,
    parse_ledger,
    validate,
)
from trigpoint_render import render_dashboard, render_progress_table, replace_marked_region

HEADLINE_LINE = re.compile(r"^\*\*Headline:\*\*[ \t]*(?P<headline>.+?)[ \t]*$")
LANES_RUN_LINE = re.compile(r"^\*\*Lanes run:\*\*[ \t]*(?P<lanes>.+?)[ \t]*$")
LANES_SKIPPED_LINE = re.compile(r"^\*\*Lanes not run:\*\*[ \t]*(?P<lanes>.+?)[ \t]*$")
TITLE_LINE = re.compile(r"^#[ \t]+(?P<title>.+?)[ \t]*$")


def _first_line_match(lines: List[str], pattern: "re.Pattern[str]", group: str) -> Optional[str]:
    for line in lines:
        match = pattern.match(line)
        if match:
            return match.group(group).strip()
    return None


def _read_metadata_field(
    lines: List[str], pattern: "re.Pattern[str]", group: str
) -> Optional[str]:
    """Read a one-line metadata field plus any hard-wrapped continuation.

    `**Headline:**`, `**Lanes run:**` and `**Lanes not run:**` can each be wrapped
    by an author across two physical source lines, and markdown treats that as
    one paragraph rather than a truncated line. A non-blank line immediately
    following the field's own line is absorbed and joined with a single space.
    Absorption stops at the first line that is blank, that opens a different
    metadata field, that is a task line, that is a definition-of-done criterion
    line, that is fenced, or that is a heading.

    A marker line can match `pattern` while still carrying no value of its own:
    trailing whitespace after the colon (`**Headline:**  `) matches and strips
    to an empty string just as an entirely bare marker line fails to match at
    all. Continuation only ever extends a value that already exists, so an
    empty own value returns None immediately without looking at what follows
    it -- otherwise unrelated prose right after a blank marker line would
    become the field, which is the same class of failure this function exists
    to close, just aimed at the marker line instead of the continuation.

    This ledger's raw lines are never pre-filtered for fences (this script has
    no section boundaries to filter within), so a marker line inside a fenced
    example is just as visible to a naive scan as a real one. Fence state is
    computed exactly once here, via `_lines_outside_fences` imported directly
    from `trigpoint_ledger` -- the same single fence-toggle implementation the
    ledger parser uses, not a second copy of the rule -- into a set of line
    numbers that are NOT inside a fence. Both the initial marker scan and the
    continuation scan consult that same set, so a fenced example field can
    never be read as the real one and a continuation can never cross into
    fenced content.
    """
    numbered_lines = list(enumerate(lines, start=1))
    unfenced_line_numbers = {
        line_number for line_number, _ in _lines_outside_fences(numbered_lines)
    }
    for index, (line_number, line) in enumerate(numbered_lines):
        if line_number not in unfenced_line_numbers:
            continue
        match = pattern.match(line)
        if not match:
            continue
        own_value = match.group(group).strip()
        if not own_value:
            return None
        parts = [own_value]
        for continuation_number, continuation in numbered_lines[index + 1 :]:
            if not continuation.strip():
                break
            if continuation_number not in unfenced_line_numbers:
                break
            if METADATA_LINE.match(continuation):
                break
            if TASK_LINE.match(continuation):
                break
            if CRITERION_LINE.match(continuation):
                break
            if HEADING_LINE.match(continuation):
                break
            parts.append(continuation.strip())
        return " ".join(parts)
    return None


def _write_ledger_atomically(path: pathlib.Path, text: str) -> None:
    """Write the ledger the same way install_block.py writes CLAUDE.md.

    ROADMAP.md is the plan of record, so it gets the same guarantee the
    CLAUDE.md installer already proved out: resolve the target to its real
    path so a symlink is written through rather than replaced with a plain
    file, write a temporary file in that resolved parent directory, carry
    over the existing file's permission bits so a plain `write_text` cannot
    quietly reset them, then atomically replace the target with `os.replace`.
    """
    target = path.resolve()
    existing_mode = os.stat(target).st_mode if target.is_file() else None
    target_directory = target.parent
    temporary_file = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=target_directory, delete=False
    )
    try:
        temporary_file.write(text)
        temporary_file.close()
        if existing_mode is not None:
            os.chmod(temporary_file.name, existing_mode)
        else:
            current_umask = os.umask(0)
            os.umask(current_umask)
            os.chmod(temporary_file.name, 0o666 & ~current_umask)
        os.replace(temporary_file.name, target)
    except Exception:
        temporary_file.close()
        if os.path.exists(temporary_file.name):
            os.unlink(temporary_file.name)
        raise


def _split_lanes(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


STATE_DIRECTORY = ".trigpoint"
PAUSE_FILE = "paused"
DISABLE_VARIABLE = "TRIGPOINT_DISABLE"


def find_state_root(start_directory):
    """The nearest ancestor holding `.trigpoint/`, or None."""
    current = os.path.abspath(start_directory)
    while True:
        if os.path.isdir(os.path.join(current, STATE_DIRECTORY)):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Regenerate ledger table and dashboard")
    parser.add_argument("--ledger", default="ROADMAP.md")
    parser.add_argument("--output", default="roadmap-dashboard.html")
    parser.add_argument("--title", default=None)
    arguments = parser.parse_args(argv)

    ledger_path = pathlib.Path(arguments.ledger)
    if not ledger_path.is_file():
        sys.stderr.write("cannot read ledger: {0}\n".format(arguments.ledger))
        return 2

    # The third of the three CLIs that read a ledger. The other two were taught
    # to refuse a file they parsed as nothing; this one kept exiting 0 and
    # writing a dashboard reading "0 of 0 tasks complete across 0 tracks" over a
    # real plan it could not read. A plausible artefact is worse than an error,
    # because nobody goes looking behind it.
    state_root = find_state_root(str(ledger_path.parent))
    if state_root and (pathlib.Path(state_root) / STATE_DIRECTORY / PAUSE_FILE).exists():
        print("paused: .trigpoint/paused exists, so nothing was regenerated. "
              "Remove that file to resume.")
        return 0
    if state_root and os.environ.get(DISABLE_VARIABLE):
        print("{0} is set, so nothing was regenerated.".format(DISABLE_VARIABLE))
        return 0

    original_text = ledger_path.read_text(encoding="utf-8")
    ledger = parse_ledger(original_text)
    if ledger.task_count == 0:
        sys.stderr.write(
            "{0}: no tasks parsed{1}. Nothing was regenerated, because a dashboard "
            "built from a ledger this tool could not read says \"0 of 0 tasks\" over "
            "a real plan and looks like an answer.\n".format(
                arguments.ledger,
                "" if not count_checkbox_lines(original_text)
                else " although {0} checkbox line(s) are present".format(
                    count_checkbox_lines(original_text)),
            )
        )
        return 3
    original_lines = original_text.splitlines()

    applied: List[str] = []
    failed: List[str] = []

    updated_text, region_found = replace_marked_region(
        original_text, "progress", render_progress_table(ledger)
    )
    if region_found:
        if updated_text != original_text:
            _write_ledger_atomically(ledger_path, updated_text)
        applied.append("progress table")
    else:
        failed.append(
            "progress table: no <!-- trigpoint:progress:begin --> region in "
            + arguments.ledger
        )

    title = arguments.title or _first_line_match(original_lines, TITLE_LINE, "title") or "Roadmap"
    headline = (
        _read_metadata_field(original_lines, HEADLINE_LINE, "headline")
        or "No headline recorded in the ledger."
    )
    html = render_dashboard(
        ledger,
        title=title,
        headline=headline,
        lanes_run=_split_lanes(_read_metadata_field(original_lines, LANES_RUN_LINE, "lanes")),
        lanes_skipped=_split_lanes(
            _read_metadata_field(original_lines, LANES_SKIPPED_LINE, "lanes")
        ),
    )
    output_path = pathlib.Path(arguments.output)
    output_path.write_text(html, encoding="utf-8")
    applied.append("dashboard html -> {0}".format(arguments.output))

    for entry in applied:
        sys.stdout.write("applied: {0}\n".format(entry))
    for entry in failed:
        sys.stdout.write("NOT applied: {0}\n".format(entry))

    problems = validate(ledger)
    for problem in problems:
        sys.stdout.write(
            "{0} {1}:{2} {3}\n".format(
                problem.severity.upper(),
                arguments.ledger,
                problem.line_number,
                problem.message,
            )
        )
    return 1 if has_errors(problems) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
