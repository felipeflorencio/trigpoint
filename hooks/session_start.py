#!/usr/bin/env python3
"""State the plan at the start of every session in an initialised project.

A person who wrote a plan on Monday still roughly remembers it on Friday. An
agent starting on Friday knows nothing except what is in files and what reaches
its context. The ledger is that agent's memory, and this hook is the read of it
that cannot be forgotten, because nobody has to remember to do it.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _project import PLUGIN_ROOT, STATE_DIRECTORY, initialised_root, ledger_path  # noqa: E402

from trigpoint_ledger import (  # noqa: E402
    RECORDED,
    VERIFIED,
    count_checkbox_lines,
    parse_ledger,
    validate,
)
from trigpoint_render import heading_text  # noqa: E402
from trigpoint_verify import recorded_command  # noqa: E402

MAX_TRACKS_LISTED = 12
VERSION_FILE = "version"


def plugin_version() -> str:
    """The version of the plugin these hooks were shipped in."""
    manifest = os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json")
    try:
        with open(manifest, encoding="utf-8") as handle:
            return str(json.load(handle).get("version", "")) or "unknown"
    except (OSError, ValueError):
        return "unknown"


def vendored_version_warning(start_directory: str) -> str:
    """Say so when the copies in `.trigpoint/` are older than the plugin.

    The hooks run the plugin's code; the gate the user is told to run is a copy
    vendored at install time. When those disagree, the session-start hook can
    be teaching a rule the vendored gate rejects, and nothing on either side
    knows. Only the mismatch is reported here: re-copying is the user's call,
    because it overwrites files in their repository.
    """
    root = initialised_root(start_directory)
    if root is None:
        return ""
    running = plugin_version()
    stamp_path = os.path.join(root, STATE_DIRECTORY, VERSION_FILE)
    try:
        with open(stamp_path, encoding="utf-8") as handle:
            vendored = handle.read().strip()
    except (OSError, ValueError):
        # ValueError covers UnicodeDecodeError. A stamp nobody can read is a
        # stamp that does not match, and taking the whole hook down with a
        # traceback is worse than any staleness it was about to report.
        vendored = ""
    if vendored == running:
        return ""
    return (
        "TRIGPOINT WARNING: the scripts vendored in .trigpoint/ are from {0}, and this "
        "plugin is {1}. The gate you are told to run is the vendored copy, so it may "
        "reject evidence these hooks tell you to write. Re-copy the five scripts from "
        "the plugin into .trigpoint/, or re-run the trigpoint skill.".format(
            vendored or "an unrecorded version", running
        )
    )


def _open_tracks(ledger):
    return [track for track in ledger.tracks if track.done_count < track.task_count]


def build_state(markdown_text: str, start_directory: Optional[str] = None) -> str:
    ledger = parse_ledger(markdown_text)
    total = ledger.task_count
    done = ledger.done_count

    if total == 0:
        checkbox_lines = count_checkbox_lines(markdown_text)
        seen = (
            ""
            if not checkbox_lines
            else " although {0} checkbox line(s) are present".format(checkbox_lines)
        )
        return (
            "TRIGPOINT LEDGER. WARNING: ROADMAP.md parsed as ZERO tasks{0}. The drift "
            "gate is not protecting this repository until that is fixed, and a clean "
            "report from it currently means nothing was read rather than nothing was "
            "wrong. A section becomes a track by carrying a **Scope:** line, and a task "
            "line reads `- [ ] **1.1** text`.".format(seen)
        )

    ticked = [task for track in ledger.tracks for task in track.tasks if task.done]
    proven = sum(
        1
        for task in ticked
        if task.evidence_kind == VERIFIED and recorded_command(task.evidence)
    )
    recorded = sum(1 for task in ticked if task.evidence_kind == RECORDED)
    attested = done - proven - recorded

    lines = [
        "TRIGPOINT LEDGER. This repository keeps its plan of record in ROADMAP.md. "
        "Read it before starting work, and keep it current as you go.",
        "State: {0} of {1} tasks done - {2} carrying a re-runnable command, "
        "{3} recording something that happened, {4} resting on a written note "
        "only.".format(done, total, proven, recorded, attested),
    ]

    open_tracks = _open_tracks(ledger)
    if open_tracks:
        lines.append("")
        lines.append("Open tracks:")
        for track in open_tracks[:MAX_TRACKS_LISTED]:
            lines.append(
                "  - {0}: {1} of {2} done, blocked by {3}".format(
                    heading_text(track),
                    track.done_count,
                    track.task_count,
                    track.blocked_by or "nothing",
                )
            )
        if len(open_tracks) > MAX_TRACKS_LISTED:
            lines.append("  - and {0} more".format(len(open_tracks) - MAX_TRACKS_LISTED))

    unblocked = [
        task
        for track in ledger.tracks
        if (track.blocked_by or "nothing").strip().lower() in ("nothing", "none", "-")
        for task in track.tasks
        if not task.done
    ]
    if unblocked:
        lines.append("")
        lines.append(
            "Next unblocked: "
            + ", ".join(task.task_id for task in unblocked[:5])
            + "."
        )

    errors = [problem for problem in validate(ledger) if problem.severity == "error"]
    if errors:
        lines.append("")
        lines.append("The ledger currently has {0} error(s). Fix them before adding "
                     "work; run the drift gate to see them.".format(len(errors)))

    warning = vendored_version_warning(start_directory) if start_directory else ""
    if warning:
        lines.append("")
        lines.append(warning)

    lines.append("")
    lines.append(
        "Ticking rule: a box is ticked only with evidence. Never on assumption. Use a "
        "**Verified:** line carrying the command that was run when the work can be "
        "re-checked by running something; those commands are re-run at the end of a "
        "working turn and a box whose command stops passing is unticked again, so an "
        "optimistic tick does not survive. Use a **Recorded:** line stating what happened "
        "and when for work no command can re-check, such as a release published or a "
        "migration run; it is never re-run and never unticked by machine. Do not invent a "
        "command to satisfy the gate: a proxy that passes whatever the truth is, is worse "
        "than an honest record."
    )
    return "\n".join(lines)


def main() -> int:
    path = ledger_path(os.getcwd())
    if path is None:
        return 0
    with open(path, encoding="utf-8") as handle:
        markdown_text = handle.read()
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": build_state(markdown_text, os.getcwd()),
        }
    }), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
