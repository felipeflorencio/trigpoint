"""Re-run the commands a ledger already records, and untick what stopped being true.

`check_drift.py` enforces that a ticked task CARRIES evidence. Nothing enforces
that the evidence is STILL TRUE. Those are different guarantees, and the gap
between them is the failure this plugin exists to close: a plan that stopped
being true with nothing announcing it.

Every `**Verified:**` line already holds the command that proved the task, in
backticks. This module re-runs it. A command that no longer exits zero unticks
its box and records why, leaving the original evidence in place, because that
evidence was true on the day it was written and the history is worth keeping.

Rules this module will not break:

- It runs ONLY a command already written in the ledger, never one it composed.
- It runs nothing until a human has approved that exact command once, by hash.
  Without that gate, cloning a repository would run its author's commands here.
- Verify commands are read-only assertions by contract. Nothing here commits,
  pushes, deploys, deletes or rotates, and no code path exists that could.
- Nothing is ever ticked. A machine can prove a claim false; deciding that work
  is finished stays with a person.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

from trigpoint_ledger import (
    REGRESSED_MARKER,
    TASK_LINE,
    VERIFIED,
    Ledger,
    Task,
    parse_ledger,
)

TAIL_LIMIT = 240
DEFAULT_TIMEOUT = 120
STATE_DIRECTORY = ".trigpoint"
APPROVALS_FILE = "approved-commands.json"
PAUSE_FILE = "paused"
EVIDENCE_MARKER = "**Verified:**"

BACKTICKED = re.compile(r"`([^`]+)`")

PASSED = "passed"
FAILED = "failed"
COULD_NOT_RUN = "could-not-run"


@dataclass
class Outcome:
    """What re-running one recorded command established.

    An exit code answers two different questions at once and the ledger only
    cares about one of them. `FAILED` means the command ran and contradicted
    the claim. `COULD_NOT_RUN` means Trigpoint never got an answer -- it could
    not start the command, or gave up waiting -- which is not evidence about
    the claim and must never untick anything. The tool only ever unticks, so a
    wrong untick corrupts the plan of record while a missed one merely delays
    a catch; everything ambiguous therefore resolves to leaving the box alone
    and saying so out loud.
    """

    exit_code: int
    tail: str
    at: str
    status: str = ""

    def __post_init__(self) -> None:
        if not self.status:
            self.status = PASSED if self.exit_code == 0 else FAILED


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ------------------------------------------------------------------ reading


def recorded_command(evidence: Optional[str]) -> Optional[str]:
    """The command an evidence line records, which is its first backticked span.

    Evidence records the command and the date it was proven, and nothing else.
    Recorded output was never checked -- verification consults the exit code
    only -- so printing it put a number in the ledger that nothing stood
    behind. Ledgers written before that rule still carry a `command` ->
    `output` tail; taking the FIRST span reads both forms correctly, so older
    ledgers keep working untouched.
    """
    if not evidence:
        return None
    match = BACKTICKED.search(evidence)
    if not match:
        return None
    command = match.group(1).strip()
    return command or None


def selectable(ledger: Ledger) -> List[Tuple[Task, str]]:
    """Ticked tasks whose evidence ASSERTS something, paired with the command.

    Unticked tasks are never re-run. There is nothing to contradict yet, and
    running a command for work that has not started produces noise, not news.

    `**Recorded:**` evidence is skipped whatever it contains. It states that
    something happened, which no re-run can confirm or deny, and its backticks
    quote names rather than commands -- running them would be running text the
    author never meant as an instruction.
    """
    selected: List[Tuple[Task, str]] = []
    for track in ledger.tracks:
        for task in track.tasks:
            if not task.done or task.evidence_kind != VERIFIED:
                continue
            command = recorded_command(task.evidence)
            if command:
                selected.append((task, command))
    return selected


# ------------------------------------------------------------------ approvals


def command_hash(command: str) -> str:
    return hashlib.sha256(command.strip().encode("utf-8")).hexdigest()[:16]


def is_approved(command: str, approvals: Dict[str, str]) -> bool:
    return command_hash(command) in approvals


def approve(command: str, approvals: Dict[str, str]) -> Dict[str, str]:
    updated = dict(approvals)
    updated[command_hash(command)] = command.strip()
    return updated


def approvals_path(repository_root: str) -> str:
    return os.path.join(repository_root, STATE_DIRECTORY, APPROVALS_FILE)


def load_approvals(repository_root: str) -> Dict[str, str]:
    path = approvals_path(repository_root)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            loaded = json.load(handle)
    except (ValueError, OSError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def save_approvals(repository_root: str, approvals: Dict[str, str]) -> None:
    path = approvals_path(repository_root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(approvals, handle, indent=2, sort_keys=True)


# ------------------------------------------------------------------ running


def _tail(text: str) -> str:
    """The most useful last words of a command's output, on one line.

    A raw character tail of a failing test run is mostly a truncated traceback,
    which is noise in a ledger. The last two non-empty lines are almost always
    the summary a reader wants -- "Ran 12 tests" then "FAILED (failures=2)" --
    so those are preferred, and the character limit still applies on top.
    """
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return ""
    summary = " ".join(lines[-2:]) if len(lines) > 1 else lines[-1]
    flattened = " ".join(summary.split()).replace("`", "'")
    return flattened[-TAIL_LIMIT:]


def run_command(command: str, cwd: str, timeout: int = DEFAULT_TIMEOUT,
                runner: Callable = subprocess.run) -> Outcome:
    """Run one recorded command. Never raises: a failure to run is a failure."""
    try:
        completed = runner(
            command, shell=True, cwd=cwd, capture_output=True,
            text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return Outcome(124, "timed out after {0}s".format(timeout), today(), COULD_NOT_RUN)
    except OSError as error:
        return Outcome(127, _tail(str(error)), today(), COULD_NOT_RUN)

    output = (getattr(completed, "stdout", "") or "") + (getattr(completed, "stderr", "") or "")
    status = PASSED if completed.returncode == 0 else FAILED
    return Outcome(completed.returncode, _tail(output), today(), status)


# ------------------------------------------------------------------ writing


def _task_block_end(lines: List[str], start: int) -> int:
    """Index of the last line belonging to the task that starts at `start`."""
    end = start
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if not line.strip():
            continue
        if not line[:1].isspace():
            break
        end = index
    return end


def _regressed_note(indent: str, command: str, outcome: Outcome) -> str:
    return "{0}{1} `{2}` -> exit {3}. `{4}`. {5}".format(
        indent, REGRESSED_MARKER, command, outcome.exit_code, outcome.tail, outcome.at
    )


def apply_regressions(markdown_text: str, outcomes: Dict[str, Outcome]) -> Tuple[str, List[str]]:
    """Untick every task whose recorded command stopped passing.

    Applies what matches and writes regardless, reporting applied and failed
    separately. A batch that insists every task be found before writing any of
    them discards good edits because of one bad identifier.
    """
    lines = markdown_text.split("\n")
    ledger = parse_ledger(markdown_text)
    known = {
        task.task_id: (task, command)
        for task, command in selectable(ledger)
    }

    applied: List[str] = []
    failed: List[str] = []
    insertions: List[Tuple[int, str]] = []

    for task_id in sorted(outcomes):
        outcome = outcomes[task_id]
        if task_id not in known:
            failed.append("{0} not found as a ticked task carrying a command".format(task_id))
            continue
        if outcome.status == PASSED:
            applied.append("{0} still passing".format(task_id))
            continue
        if outcome.status == COULD_NOT_RUN:
            failed.append(
                "{0} could not be run, so it was left alone: {1}".format(
                    task_id, outcome.tail or "no reason given"
                )
            )
            continue

        task, command = known[task_id]
        index = task.line_number - 1
        lines[index] = lines[index].replace("- [x]", "- [ ]", 1).replace("- [X]", "- [ ]", 1)

        end = _task_block_end(lines, index)
        indent = ""
        for candidate in lines[index + 1:end + 1]:
            if candidate.strip().startswith(EVIDENCE_MARKER):
                indent = candidate[: len(candidate) - len(candidate.lstrip())]
                break
        if not indent:
            indent = "      "

        existing = [
            position
            for position in range(index + 1, end + 1)
            if lines[position].strip().startswith(REGRESSED_MARKER)
        ]
        note = _regressed_note(indent, command, outcome)
        if existing:
            lines[existing[0]] = note
        else:
            insertions.append((end + 1, note))
        applied.append("{0} unticked, its recorded check now exits {1}".format(
            task_id, outcome.exit_code))

    for offset, pair in enumerate(sorted(insertions)):
        position, note = pair
        lines.insert(position + offset, note)

    return "\n".join(lines), applied + failed


# ------------------------------------------------------------------ driving


def write_atomically(target_path: str, contents: str) -> None:
    """Replace a file's contents without ever leaving it half-written.

    `open(path, "w")` truncates before the first byte is written. Applying each
    regression as it is found multiplies how often the process sits inside that
    window, and does so on exactly the path the Stop hook's budget kills. A
    ledger cut in half is a worse outcome than the silent discard that writing
    incrementally removed.

    Atomicity alone is not enough: it must replace the SAME file, with the same
    permissions. `scripts/build_dashboard.py` and `scripts/install_block.py`
    both resolve through a symlink and carry the existing mode across, and
    `open(path, "w")` did both by accident. A first version here did neither,
    so a symlinked ROADMAP.md was replaced by a regular file and the regression
    never reached the real ledger, and a 0644 ledger quietly became 0600.
    """
    target = os.path.realpath(target_path)
    existing_mode = os.stat(target).st_mode if os.path.isfile(target) else None
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="",
        dir=os.path.dirname(target) or ".", delete=False,
    )
    try:
        handle.write(contents)
        handle.close()
        if existing_mode is not None:
            os.chmod(handle.name, existing_mode & 0o7777)
        os.replace(handle.name, target)
    except Exception:
        handle.close()
        if os.path.exists(handle.name):
            os.unlink(handle.name)
        raise


def paused(repository_root: str) -> bool:
    return os.path.exists(os.path.join(repository_root, STATE_DIRECTORY, PAUSE_FILE))


def verify_ledger(ledger_path: str, runner: Callable = subprocess.run,
                  timeout: int = DEFAULT_TIMEOUT) -> Tuple[List[str], List[str]]:
    """Re-run every approved recorded command and apply the regressions.

    Returns (report, awaiting_approval). Writes the ledger only when something
    actually changed, and never commits.

    Each outcome is applied and written as soon as it is produced, rather than
    collected and written once at the end. The Stop hook that calls this has a
    180-second budget; a pass that ran past it used to be killed with every
    regression it had already found still in memory, writing nothing and
    printing nothing. Silence at the end of a turn reads as a clean ledger, so
    that was the one path on which this tool reported a plan as fine while
    holding proof that it was not. Writing as it goes means an interrupted pass
    keeps everything it established and only leaves the remainder unchecked.

    A command standing behind several tasks runs once, and its outcome is
    applied to all of them. Within one pass, over one tree, running the same
    command twice cannot produce two answers worth having.
    """
    repository_root = os.path.dirname(os.path.abspath(ledger_path))
    with open(ledger_path, encoding="utf-8", newline="") as handle:
        original = handle.read()

    approvals = load_approvals(repository_root)
    awaiting: List[str] = []
    tasks_by_command: Dict[str, List[str]] = {}

    for task, command in selectable(parse_ledger(original)):
        if not is_approved(command, approvals):
            awaiting.append("{0}: {1}".format(task.task_id, command))
            continue
        tasks_by_command.setdefault(command, []).append(task.task_id)

    report: List[str] = []
    for command, task_ids in tasks_by_command.items():
        outcome = run_command(command, repository_root, timeout, runner)
        with open(ledger_path, encoding="utf-8", newline="") as handle:
            current = handle.read()
        outcomes: Dict[str, Outcome] = {task_id: outcome for task_id in task_ids}
        updated, applied = apply_regressions(current, outcomes)
        if updated != current:
            write_atomically(ledger_path, updated)
        report.extend(applied)

    return report, awaiting


# ------------------------------------------------------------------ cli


def _usage() -> str:
    return (
        "usage: trigpoint_verify.py [LEDGER]\n"
        "       trigpoint_verify.py --approve 'COMMAND' [--root DIRECTORY]\n"
    )


def main(argv: List[str]) -> int:
    arguments = argv[1:]

    if arguments and arguments[0] == "--approve":
        if len(arguments) < 2:
            sys.stderr.write(_usage())
            return 2
        command = arguments[1]
        root = "."
        if "--root" in arguments:
            position = arguments.index("--root")
            if position + 1 < len(arguments):
                root = arguments[position + 1]
        save_approvals(root, approve(command, load_approvals(root)))
        print("approved: {0}".format(command.strip()))
        return 0

    ledger = arguments[0] if arguments else "ROADMAP.md"
    if not os.path.exists(ledger):
        sys.stderr.write("no ledger at {0}\n".format(ledger))
        return 2

    report, awaiting = verify_ledger(ledger)
    for line in report:
        print(line)
    for line in awaiting:
        print("awaiting approval {0}".format(line))
    if not report and not awaiting:
        print("nothing to re-run: no ticked task records a command.")
    return 1 if any("unticked" in line for line in report) else 0


if __name__ == "__main__":
    import sys as _sys

    raise SystemExit(main(_sys.argv))
