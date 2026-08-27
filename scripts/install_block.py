#!/usr/bin/env python3
"""Write the Trigpoint instruction block into a repository's CLAUDE.md.

Delimited and idempotent: re-running updates the block in place rather than
stacking copies.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys
import tempfile
from typing import List

BEGIN_MARKER = "<!-- trigpoint:begin -->"
END_MARKER = "<!-- trigpoint:end -->"
VALID_MODES = ("automatic", "manual")

BLOCK_BODY = """## The ledger

`ROADMAP.md` is this repository's plan of record. Read it before starting work.

- Work only on tracks whose **Blocked by** is satisfied.
- A box is ticked ONLY after its verification has actually run. Record the
  command and its output on a `**Verified:**` line. Never tick on assumption.
- Work discovered mid-flight that is not in the ledger gets ADDED to the right
  track when it is found, not done silently.
- A finding that contradicts the ledger is raised, not quietly edited away.
- After any tick or addition, run `python3 .trigpoint/build_dashboard.py`.
  The progress table and the dashboard are generated. Never hand-edit them.
- Evidence is a `**Verified:**` line naming a command, which is re-run and can
  untick its box, or a `**Recorded:**` line stating what happened, for work no
  command can re-check. Never invent a command to satisfy the gate.
- `python3 .trigpoint/check_drift.py` exits non-zero when a box is ticked with
  no evidence recorded.

Mode: {mode}"""


def render_block(mode: str) -> str:
    return "{0}\n{1}\n{2}\n".format(
        BEGIN_MARKER, BLOCK_BODY.format(mode=mode), END_MARKER
    )


def upsert_block(existing_text: str, block: str) -> str:
    uses_crlf = "\r\n" in existing_text
    block_to_use = block
    if uses_crlf:
        block_to_use = block.replace("\n", "\r\n")
    pattern = re.compile(
        re.escape(BEGIN_MARKER) + r"(?:(?!" + re.escape(BEGIN_MARKER) + r").)*?" + re.escape(END_MARKER), re.DOTALL
    )
    if pattern.search(existing_text):
        return pattern.sub(lambda _: block_to_use.rstrip("\n").rstrip("\r"), existing_text, count=1)
    if uses_crlf:
        separator = "" if not existing_text or existing_text.endswith("\r\n\r\n") else "\r\n"
        if existing_text and not existing_text.endswith("\r\n"):
            separator = "\r\n\r\n"
    else:
        separator = "" if not existing_text or existing_text.endswith("\n\n") else "\n"
        if existing_text and not existing_text.endswith("\n"):
            separator = "\n\n"
    return "{0}{1}{2}".format(existing_text, separator, block_to_use)


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Install the Trigpoint CLAUDE.md block")
    parser.add_argument("--claude-md", default="CLAUDE.md")
    parser.add_argument("--mode", choices=VALID_MODES, default="automatic")
    arguments = parser.parse_args(argv)

    target = pathlib.Path(arguments.claude_md).resolve()
    existing_text = ""
    existing_mode = None
    if target.is_file():
        with open(target, "r", encoding="utf-8", newline="") as file:
            existing_text = file.read()
        existing_mode = os.stat(target).st_mode
    result_text = upsert_block(existing_text, render_block(arguments.mode))
    target_directory = target.parent
    temporary_file = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", dir=target_directory, delete=False
    )
    try:
        temporary_file.write(result_text)
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
    begin_count = result_text.count(BEGIN_MARKER)
    end_count = result_text.count(END_MARKER)
    if begin_count != end_count:
        sys.stderr.write(
            "WARNING: {0} contains an unmatched {1} marker. Remove it by hand.\n".format(
                target, BEGIN_MARKER
            )
        )
    sys.stdout.write(
        "applied: trigpoint block in {0}, mode {1}\n".format(
            arguments.claude_md, arguments.mode
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
