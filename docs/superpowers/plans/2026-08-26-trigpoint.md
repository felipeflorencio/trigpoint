# Trigpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a public Claude Code plugin that audits a codebase, runs a question ladder to produce a plan of record, generates a dashboard from that plan, and keeps both true for the life of the work.

**Architecture:** A markdown ledger is the single source of truth. A stdlib-only Python parser reads it; one CLI rewrites the ledger's progress table in place and renders a self-contained HTML dashboard, another runs the same parse read-only as a CI gate. The authoring process itself lives in a skill, and the scripts are copied into each target repository so CI and collaborators do not need the plugin installed.

**Tech Stack:** Python 3.9+ standard library only. `unittest` for tests. Markdown, JSON, HTML. No third-party packages at any point.

**Spec:** `docs/superpowers/specs/2026-08-26-trigpoint-design.md`

## Global Constraints

- **Python standard library only.** No third-party imports in `scripts/` or `tests/`. The scripts are copied into arbitrary repositories and must run on a bare CI checkout with no install step.
- **Python 3.9 floor.** No `match` statements, no `X | Y` type syntax at runtime. `from __future__ import annotations` at the top of every module.
- **Tests run with** `python3 -m unittest discover -s tests -v` from the repository root. No test runner is installed.
- **Writing style, in every file that ships:** no em dashes, no en dashes, no curly quotes, no ellipsis characters. Plain hyphen, straight quotes, three dots.
- **Variable naming:** no single-character names, no abbreviations. `track_identifier`, not `tid`. `line_number`, not `i`.
- **No fixture, sample or user-specific data in shipping code.** Test fixtures live in `tests/` only.
- **Commit messages carry no AI or tool attribution.** Subject and body only.
- **Generated regions are never hand-edited.** Anything between `<!-- trigpoint:...:begin -->` and `<!-- trigpoint:...:end -->` is written by a script.
- **Partial application rule.** Any script that applies several edits applies what matches, writes regardless, and reports applied and failed separately. It never aborts the whole write because one pattern missed, and it never commits in the same command as an edit.

---

## File Structure

```
scripts/
  trigpoint_ledger.py      Parse + model + validate. Pure functions, no file IO.
  trigpoint_render.py      Ledger -> HTML string. Pure function, no file IO.
  build_dashboard.py       CLI. Rewrites the ledger progress table, writes the HTML.
  check_drift.py           CLI. Same parse, read-only, non-zero exit on error.
  install_block.py         CLI. Writes the delimited CLAUDE.md block, idempotently.
tests/
  test_ledger_parse.py     Task 1
  test_ledger_validate.py  Task 2
  test_check_drift.py      Task 3
  test_progress_table.py   Task 4
  test_render.py           Task 5
  test_build_dashboard.py  Task 6
  test_install_block.py    Task 7
  fixtures/
    minimal_ledger.md
skills/trigpoint/
  SKILL.md
  references/*.md
  templates/*
commands/
  trigpoint.md
  trigpoint-sync.md
.claude-plugin/
  plugin.json
  marketplace.json
```

`trigpoint_ledger.py` holds the data model and every rule about what a ledger means. `trigpoint_render.py` holds every decision about what the dashboard looks like. Neither touches the filesystem, so both are tested by passing strings. The three CLI files own all file IO and nothing else.

---

### Task 1: Ledger parser

The data model and the parse. Everything else in the repository reads its output.

**Files:**
- Create: `scripts/trigpoint_ledger.py`
- Create: `tests/test_ledger_parse.py`
- Create: `tests/fixtures/minimal_ledger.md`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Task(task_id: str, text: str, done: bool, evidence: Optional[str], line_number: int)`
  - `Track(track_identifier: str, name: str, scope: str, blocked_by: str, tasks: List[Task])` with properties `task_count: int` and `done_count: int`
  - `DoneCriterion(text: str, done: bool, line_number: int)`
  - `Ledger(tracks: List[Track], done_criteria: List[DoneCriterion])` with properties `task_count: int` and `done_count: int`
  - `parse_ledger(markdown_text: str) -> Ledger`

- [ ] **Step 1: Write the fixture**

Create `tests/fixtures/minimal_ledger.md`:

```markdown
# Example - Roadmap

**The ledger.**

## Progress at a glance

<!-- trigpoint:progress:begin -->
<!-- trigpoint:progress:end -->

## T1 Foundation

**Scope:** Make it boot from clean
**Blocked by:** nothing

Prose about the track that must not be parsed as a task.

- [ ] **1.1** Write the migration
- [x] **1.2** Set validate mode
      **Verified:** `./run boot` -> started clean. 2026-08-27

## T2 Security

**Scope:** Credentials and authorization
**Blocked by:** T1

- [x] **2.1** Rotate the keys   **Verified:** `./check secrets` -> 0 found. 2026-08-27

## Hand-off contracts

Prose only. This section has no Scope line and is not a track.

- [ ] **X.1** A task-shaped line outside a track, which must be ignored

## Definition of done

- [ ] 1. A fresh clone boots with no manual intervention
- [x] 2. The health endpoint returns 200
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_ledger_parse.py`:

```python
from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from trigpoint_ledger import parse_ledger

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "minimal_ledger.md"


class ParseLedgerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = parse_ledger(FIXTURE.read_text(encoding="utf-8"))

    def test_only_sections_with_a_scope_line_are_tracks(self) -> None:
        identifiers = [track.track_identifier for track in self.ledger.tracks]
        self.assertEqual(["T1", "T2"], identifiers)

    def test_track_metadata_is_read(self) -> None:
        foundation = self.ledger.tracks[0]
        self.assertEqual("Foundation", foundation.name)
        self.assertEqual("Make it boot from clean", foundation.scope)
        self.assertEqual("nothing", foundation.blocked_by)

    def test_tasks_are_collected_with_their_state(self) -> None:
        foundation = self.ledger.tracks[0]
        self.assertEqual(["1.1", "1.2"], [task.task_id for task in foundation.tasks])
        self.assertFalse(foundation.tasks[0].done)
        self.assertTrue(foundation.tasks[1].done)

    def test_prose_is_not_parsed_as_a_task(self) -> None:
        self.assertEqual(2, self.ledger.tracks[0].task_count)

    def test_evidence_on_a_continuation_line_is_captured(self) -> None:
        task = self.ledger.tracks[0].tasks[1]
        self.assertEqual("`./run boot` -> started clean. 2026-08-27", task.evidence)
        self.assertEqual("Set validate mode", task.text)

    def test_evidence_inline_on_the_task_line_is_captured(self) -> None:
        task = self.ledger.tracks[1].tasks[0]
        self.assertEqual("`./check secrets` -> 0 found. 2026-08-27", task.evidence)
        self.assertEqual("Rotate the keys", task.text)

    def test_task_without_evidence_has_none(self) -> None:
        self.assertIsNone(self.ledger.tracks[0].tasks[0].evidence)

    def test_task_lines_outside_a_track_are_ignored(self) -> None:
        every_task_id = [
            task.task_id for track in self.ledger.tracks for task in track.tasks
        ]
        self.assertNotIn("X.1", every_task_id)

    def test_definition_of_done_is_collected_separately(self) -> None:
        self.assertEqual(2, len(self.ledger.done_criteria))
        self.assertFalse(self.ledger.done_criteria[0].done)
        self.assertTrue(self.ledger.done_criteria[1].done)

    def test_counts_roll_up(self) -> None:
        self.assertEqual(3, self.ledger.task_count)
        self.assertEqual(2, self.ledger.done_count)
        self.assertEqual(1, self.ledger.tracks[1].task_count)

    def test_line_numbers_are_one_based_and_point_at_the_task(self) -> None:
        lines = FIXTURE.read_text(encoding="utf-8").splitlines()
        task = self.ledger.tracks[0].tasks[0]
        self.assertIn("**1.1**", lines[task.line_number - 1])

    def test_empty_document_parses_to_an_empty_ledger(self) -> None:
        empty = parse_ledger("")
        self.assertEqual([], empty.tracks)
        self.assertEqual(0, empty.task_count)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m unittest tests.test_ledger_parse -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'trigpoint_ledger'`

- [ ] **Step 4: Write the implementation**

Create `scripts/trigpoint_ledger.py`:

```python
"""Parse a Trigpoint ledger.

Pure functions over strings. No filesystem access and no third-party imports,
because this module is copied into arbitrary repositories and must run on a
bare CI checkout.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

SECTION_HEADING = re.compile(r"^##\s+(?P<heading>\S.*?)\s*$")
SCOPE_LINE = re.compile(r"^\*\*Scope:\*\*\s*(?P<scope>.+?)\s*$")
BLOCKED_LINE = re.compile(r"^\*\*Blocked by:\*\*\s*(?P<blocked_by>.+?)\s*$")
TASK_LINE = re.compile(
    r"^\s*-\s+\[(?P<mark>[ xX])\]\s+\*\*(?P<task_id>[^*]+?)\*\*\s*(?P<text>.*)$"
)
CRITERION_LINE = re.compile(r"^\s*-\s+\[(?P<mark>[ xX])\]\s+(?P<text>\S.*?)\s*$")
HEADING_PARTS = re.compile(r"^(?P<identifier>[A-Za-z][A-Za-z0-9]*)(?:\s+(?P<name>.+))?$")

EVIDENCE_MARKER = "**Verified:**"
DONE_HEADING_PREFIX = "definition of done"


@dataclass
class Task:
    task_id: str
    text: str
    done: bool
    evidence: Optional[str]
    line_number: int


@dataclass
class DoneCriterion:
    text: str
    done: bool
    line_number: int


@dataclass
class Track:
    track_identifier: str
    name: str
    scope: str
    blocked_by: str
    tasks: List[Task] = field(default_factory=list)

    @property
    def task_count(self) -> int:
        return len(self.tasks)

    @property
    def done_count(self) -> int:
        return sum(1 for task in self.tasks if task.done)


@dataclass
class Ledger:
    tracks: List[Track] = field(default_factory=list)
    done_criteria: List[DoneCriterion] = field(default_factory=list)

    @property
    def task_count(self) -> int:
        return sum(track.task_count for track in self.tracks)

    @property
    def done_count(self) -> int:
        return sum(track.done_count for track in self.tracks)


NumberedLine = Tuple[int, str]


def parse_ledger(markdown_text: str) -> Ledger:
    ledger = Ledger()
    for heading, numbered_lines in _split_sections(markdown_text):
        scope = _first_match(numbered_lines, SCOPE_LINE, "scope")
        if scope is not None:
            blocked_by = _first_match(numbered_lines, BLOCKED_LINE, "blocked_by") or ""
            identifier, name = _split_heading(heading)
            ledger.tracks.append(
                Track(
                    track_identifier=identifier,
                    name=name,
                    scope=scope,
                    blocked_by=blocked_by,
                    tasks=_extract_tasks(numbered_lines),
                )
            )
        elif heading.strip().lower().startswith(DONE_HEADING_PREFIX):
            ledger.done_criteria.extend(_extract_criteria(numbered_lines))
    return ledger


def _split_sections(markdown_text: str) -> List[Tuple[str, List[NumberedLine]]]:
    sections: List[Tuple[str, List[NumberedLine]]] = []
    heading: Optional[str] = None
    collected: List[NumberedLine] = []
    for index, line in enumerate(markdown_text.splitlines(), start=1):
        match = SECTION_HEADING.match(line)
        if match:
            if heading is not None:
                sections.append((heading, collected))
            heading = match.group("heading")
            collected = []
        elif heading is not None:
            collected.append((index, line))
    if heading is not None:
        sections.append((heading, collected))
    return sections


def _first_match(
    numbered_lines: List[NumberedLine], pattern: "re.Pattern[str]", group: str
) -> Optional[str]:
    for _, line in numbered_lines:
        match = pattern.match(line)
        if match:
            return match.group(group).strip()
    return None


def _split_heading(heading: str) -> Tuple[str, str]:
    match = HEADING_PARTS.match(heading.strip())
    if not match:
        return heading.strip(), heading.strip()
    identifier = match.group("identifier")
    name = match.group("name")
    return identifier, (name.strip() if name else identifier)


def _extract_tasks(numbered_lines: List[NumberedLine]) -> List[Task]:
    tasks: List[Task] = []
    pending_task: Optional[Task] = None
    pending_block: List[str] = []

    for line_number, line in numbered_lines:
        match = TASK_LINE.match(line)
        if match:
            if pending_task is not None:
                tasks.append(_apply_evidence(pending_task, pending_block))
            pending_task = Task(
                task_id=match.group("task_id").strip(),
                text=match.group("text").strip(),
                done=match.group("mark").lower() == "x",
                evidence=None,
                line_number=line_number,
            )
            pending_block = [match.group("text")]
        elif pending_task is None:
            continue
        elif not line.strip():
            continue
        elif line[:1].isspace():
            pending_block.append(line)
        else:
            tasks.append(_apply_evidence(pending_task, pending_block))
            pending_task = None
            pending_block = []

    if pending_task is not None:
        tasks.append(_apply_evidence(pending_task, pending_block))
    return tasks


def _apply_evidence(task: Task, block_lines: List[str]) -> Task:
    block = "\n".join(block_lines)
    position = block.find(EVIDENCE_MARKER)
    if position != -1:
        evidence = block[position + len(EVIDENCE_MARKER) :]
        task.evidence = " ".join(evidence.split()) or None
    first_line = block_lines[0] if block_lines else ""
    if EVIDENCE_MARKER in first_line:
        first_line = first_line.split(EVIDENCE_MARKER)[0]
    task.text = " ".join(first_line.split())
    return task


def _extract_criteria(numbered_lines: List[NumberedLine]) -> List[DoneCriterion]:
    criteria: List[DoneCriterion] = []
    for line_number, line in numbered_lines:
        match = CRITERION_LINE.match(line)
        if match:
            criteria.append(
                DoneCriterion(
                    text=match.group("text").strip(),
                    done=match.group("mark").lower() == "x",
                    line_number=line_number,
                )
            )
    return criteria
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 12 tests.

- [ ] **Step 6: Commit**

```bash
git add scripts/trigpoint_ledger.py tests/test_ledger_parse.py tests/fixtures/minimal_ledger.md
git commit -m "Add ledger parser

A section is a track when it carries a Scope line, which keeps prose sections
such as the contracts table from being read as tracks. Evidence is captured
both inline and from continuation lines."
```

---

### Task 2: Validation rules

The rule that makes automatic mode safe: a ticked box without recorded evidence is an error, not a warning.

**Files:**
- Modify: `scripts/trigpoint_ledger.py`
- Create: `tests/test_ledger_validate.py`

**Interfaces:**
- Consumes: `Ledger`, `Track`, `Task` from Task 1.
- Produces:
  - `Problem(severity: str, line_number: int, message: str)` where `severity` is `"error"` or `"warning"`
  - `validate(ledger: Ledger) -> List[Problem]`
  - `has_errors(problems: List[Problem]) -> bool`

- [ ] **Step 1: Write the failing test**

Create `tests/test_ledger_validate.py`:

```python
from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from trigpoint_ledger import has_errors, parse_ledger, validate


def build(body: str) -> str:
    return "# Example\n\n" + body


class ValidateTest(unittest.TestCase):
    def test_ticked_task_without_evidence_is_an_error(self) -> None:
        ledger = parse_ledger(
            build(
                "## T1 Foundation\n\n**Scope:** s\n**Blocked by:** nothing\n\n"
                "- [x] **1.1** Delete the stale directory\n"
            )
        )
        problems = validate(ledger)
        self.assertTrue(has_errors(problems))
        self.assertEqual(1, len(problems))
        self.assertEqual("error", problems[0].severity)
        self.assertIn("1.1", problems[0].message)
        self.assertIn("Verified", problems[0].message)

    def test_ticked_task_with_evidence_is_clean(self) -> None:
        ledger = parse_ledger(
            build(
                "## T1 Foundation\n\n**Scope:** s\n**Blocked by:** nothing\n\n"
                "- [x] **1.1** Delete it   **Verified:** `ls bin/` -> absent. 2026-08-27\n"
            )
        )
        self.assertEqual([], validate(ledger))

    def test_unticked_task_needs_no_evidence(self) -> None:
        ledger = parse_ledger(
            build(
                "## T1 Foundation\n\n**Scope:** s\n**Blocked by:** nothing\n\n"
                "- [ ] **1.1** Not done yet\n"
            )
        )
        self.assertEqual([], validate(ledger))

    def test_empty_evidence_after_the_marker_is_still_an_error(self) -> None:
        ledger = parse_ledger(
            build(
                "## T1 Foundation\n\n**Scope:** s\n**Blocked by:** nothing\n\n"
                "- [x] **1.1** Done   **Verified:**\n"
            )
        )
        problems = validate(ledger)
        self.assertTrue(has_errors(problems))

    def test_duplicate_task_ids_are_an_error(self) -> None:
        ledger = parse_ledger(
            build(
                "## T1 Foundation\n\n**Scope:** s\n**Blocked by:** nothing\n\n"
                "- [ ] **1.1** First\n"
                "\n## T2 Second\n\n**Scope:** s\n**Blocked by:** nothing\n\n"
                "- [ ] **1.1** Clashing\n"
            )
        )
        problems = validate(ledger)
        self.assertTrue(has_errors(problems))
        self.assertTrue(any("duplicate" in problem.message for problem in problems))

    def test_blocked_by_an_unknown_track_is_a_warning_not_an_error(self) -> None:
        ledger = parse_ledger(
            build(
                "## T1 Foundation\n\n**Scope:** s\n**Blocked by:** T9\n\n"
                "- [ ] **1.1** First\n"
            )
        )
        problems = validate(ledger)
        self.assertEqual(1, len(problems))
        self.assertEqual("warning", problems[0].severity)
        self.assertFalse(has_errors(problems))

    def test_blocked_by_nothing_produces_no_problem(self) -> None:
        ledger = parse_ledger(
            build(
                "## T1 Foundation\n\n**Scope:** s\n**Blocked by:** nothing\n\n"
                "- [ ] **1.1** First\n"
            )
        )
        self.assertEqual([], validate(ledger))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_ledger_validate -v`
Expected: FAIL with `ImportError: cannot import name 'has_errors'`

- [ ] **Step 3: Write the implementation**

Append to `scripts/trigpoint_ledger.py`:

```python
TRACK_REFERENCE = re.compile(r"\b(?P<identifier>[A-Z][A-Za-z0-9]*)\b")
NON_BLOCKING_WORDS = frozenset({"nothing", "none", "no", "not", "blocked", "by"})


@dataclass
class Problem:
    severity: str
    line_number: int
    message: str


def validate(ledger: Ledger) -> List[Problem]:
    problems: List[Problem] = []
    first_seen_at: dict = {}

    for track in ledger.tracks:
        for task in track.tasks:
            if task.done and not task.evidence:
                problems.append(
                    Problem(
                        severity="error",
                        line_number=task.line_number,
                        message=(
                            "task {0} is ticked with no **Verified:** line. "
                            "Record the command that was run and what it printed, "
                            "or untick it.".format(task.task_id)
                        ),
                    )
                )
            if task.task_id in first_seen_at:
                problems.append(
                    Problem(
                        severity="error",
                        line_number=task.line_number,
                        message="duplicate task id {0}, first seen at line {1}".format(
                            task.task_id, first_seen_at[task.task_id]
                        ),
                    )
                )
            else:
                first_seen_at[task.task_id] = task.line_number

    known_identifiers = {track.track_identifier for track in ledger.tracks}
    for track in ledger.tracks:
        for reference in _blocking_references(track.blocked_by):
            if reference not in known_identifiers:
                problems.append(
                    Problem(
                        severity="warning",
                        line_number=0,
                        message="track {0} is blocked by {1}, which is not a track "
                        "in this ledger".format(track.track_identifier, reference),
                    )
                )
    return problems


def _blocking_references(blocked_by: str) -> List[str]:
    references: List[str] = []
    for match in TRACK_REFERENCE.finditer(blocked_by):
        identifier = match.group("identifier")
        if identifier.lower() in NON_BLOCKING_WORDS:
            continue
        if identifier not in references:
            references.append(identifier)
    return references


def has_errors(problems: List[Problem]) -> bool:
    return any(problem.severity == "error" for problem in problems)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 19 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/trigpoint_ledger.py tests/test_ledger_validate.py
git commit -m "Add ledger validation

A ticked box with no recorded evidence is an error, not a warning. This is the
rule that makes automatic updating safe: an agent cannot tick a box without
recording the command it ran. An unknown blocking reference is only a warning,
since a ledger may legitimately name work outside itself."
```

---

### Task 3: The drift gate

A read-only CLI over the same parse, suitable as a CI gate.

**Files:**
- Create: `scripts/check_drift.py`
- Create: `tests/test_check_drift.py`

**Interfaces:**
- Consumes: `parse_ledger`, `validate`, `has_errors`, `Problem` from Tasks 1 and 2.
- Produces: `report(problems: List[Problem], ledger_path: str) -> str`, `main(argv: List[str]) -> int`. Exit code 0 when clean or warnings only, 1 when any error, 2 when the ledger file is missing.

- [ ] **Step 1: Write the failing test**

Create `tests/test_check_drift.py`:

```python
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import check_drift


class CheckDriftTest(unittest.TestCase):
    def write_ledger(self, body: str) -> str:
        directory = tempfile.mkdtemp()
        path = pathlib.Path(directory) / "ROADMAP.md"
        path.write_text("# Example\n\n" + body, encoding="utf-8")
        return str(path)

    def test_clean_ledger_exits_zero(self) -> None:
        path = self.write_ledger(
            "## T1 Foundation\n\n**Scope:** s\n**Blocked by:** nothing\n\n"
            "- [ ] **1.1** Not done\n"
        )
        self.assertEqual(0, check_drift.main([path]))

    def test_ticked_without_evidence_exits_one(self) -> None:
        path = self.write_ledger(
            "## T1 Foundation\n\n**Scope:** s\n**Blocked by:** nothing\n\n"
            "- [x] **1.1** Done\n"
        )
        self.assertEqual(1, check_drift.main([path]))

    def test_warnings_alone_exit_zero(self) -> None:
        path = self.write_ledger(
            "## T1 Foundation\n\n**Scope:** s\n**Blocked by:** T9\n\n"
            "- [ ] **1.1** Not done\n"
        )
        self.assertEqual(0, check_drift.main([path]))

    def test_missing_file_exits_two(self) -> None:
        self.assertEqual(2, check_drift.main(["/nonexistent/ROADMAP.md"]))

    def test_report_names_the_file_and_line(self) -> None:
        from trigpoint_ledger import Problem

        text = check_drift.report(
            [Problem("error", 42, "task 1.1 is ticked with no evidence")],
            "ROADMAP.md",
        )
        self.assertIn("ROADMAP.md:42", text)
        self.assertIn("ERROR", text)

    def test_report_is_explicit_when_clean(self) -> None:
        text = check_drift.report([], "ROADMAP.md")
        self.assertIn("no problems", text.lower())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_check_drift -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'check_drift'`

- [ ] **Step 3: Write the implementation**

Create `scripts/check_drift.py`:

```python
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
    problems = validate(parse_ledger(path.read_text(encoding="utf-8")))
    sys.stdout.write(report(problems, ledger_path) + "\n")
    return 1 if has_errors(problems) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 25 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/check_drift.py tests/test_check_drift.py
git commit -m "Add the drift gate

Read-only over the same parse, with exit codes a CI job can act on. Warnings do
not fail a build; a ticked box with no evidence does."
```

---

### Task 4: Progress table generation in place

The table that drifted in the source run. It is now written by a script, into the ledger, between markers.

**Files:**
- Create: `scripts/trigpoint_render.py`
- Create: `tests/test_progress_table.py`

**Interfaces:**
- Consumes: `Ledger`, `Track` from Task 1.
- Produces:
  - `render_progress_table(ledger: Ledger) -> str`
  - `replace_marked_region(text: str, region: str, replacement: str) -> Tuple[str, bool]` returning the new text and whether the region was found

- [ ] **Step 1: Write the failing test**

Create `tests/test_progress_table.py`:

```python
from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from trigpoint_ledger import parse_ledger
from trigpoint_render import render_progress_table, replace_marked_region

LEDGER = """# Example

## Progress at a glance

<!-- trigpoint:progress:begin -->
stale content that must be replaced
<!-- trigpoint:progress:end -->

## T1 Foundation

**Scope:** Make it boot
**Blocked by:** nothing

- [x] **1.1** One   **Verified:** `run` -> ok. 2026-08-27
- [ ] **1.2** Two

## T2 Security

**Scope:** Lock it down
**Blocked by:** T1

- [ ] **2.1** Three
"""


class ProgressTableTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = parse_ledger(LEDGER)
        self.table = render_progress_table(self.ledger)

    def test_one_row_per_track(self) -> None:
        self.assertIn("| **T1 Foundation** |", self.table)
        self.assertIn("| **T2 Security** |", self.table)

    def test_counts_are_computed_not_copied(self) -> None:
        rows = [line for line in self.table.splitlines() if line.startswith("| **T1")]
        self.assertIn("| 2 | 1 |", rows[0])

    def test_scope_and_blocked_by_are_carried_through(self) -> None:
        self.assertIn("Make it boot", self.table)
        self.assertIn("T1", self.table)

    def test_total_row_is_present(self) -> None:
        self.assertIn("| **Total** |", self.table)
        self.assertIn("| 3 | 1 |", self.table)

    def test_region_replacement_preserves_markers(self) -> None:
        replaced, found = replace_marked_region(LEDGER, "progress", self.table)
        self.assertTrue(found)
        self.assertIn("<!-- trigpoint:progress:begin -->", replaced)
        self.assertIn("<!-- trigpoint:progress:end -->", replaced)
        self.assertNotIn("stale content", replaced)

    def test_region_replacement_is_idempotent(self) -> None:
        once, _ = replace_marked_region(LEDGER, "progress", self.table)
        twice, _ = replace_marked_region(once, "progress", self.table)
        self.assertEqual(once, twice)

    def test_missing_region_reports_false_without_raising(self) -> None:
        replaced, found = replace_marked_region("# No markers here\n", "progress", "x")
        self.assertFalse(found)
        self.assertEqual("# No markers here\n", replaced)

    def test_content_outside_the_region_is_untouched(self) -> None:
        replaced, _ = replace_marked_region(LEDGER, "progress", self.table)
        self.assertIn("## T1 Foundation", replaced)
        self.assertIn("- [ ] **1.2** Two", replaced)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_progress_table -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'trigpoint_render'`

- [ ] **Step 3: Write the implementation**

Create `scripts/trigpoint_render.py`:

```python
"""Render a Trigpoint ledger.

Pure functions over strings. No filesystem access and no third-party imports.
"""

from __future__ import annotations

import re
from typing import Tuple

from trigpoint_ledger import Ledger


def marker_pair(region: str) -> Tuple[str, str]:
    return (
        "<!-- trigpoint:{0}:begin -->".format(region),
        "<!-- trigpoint:{0}:end -->".format(region),
    )


def replace_marked_region(text: str, region: str, replacement: str) -> Tuple[str, bool]:
    begin_marker, end_marker = marker_pair(region)
    pattern = re.compile(
        re.escape(begin_marker) + r".*?" + re.escape(end_marker), re.DOTALL
    )
    if not pattern.search(text):
        return text, False
    body = "{0}\n{1}\n{2}".format(begin_marker, replacement.strip("\n"), end_marker)
    return pattern.sub(lambda _: body, text, count=1), True


def render_progress_table(ledger: Ledger) -> str:
    lines = [
        "| Track | Scope | Tasks | Done | Blocked by |",
        "| --- | --- | --- | --- | --- |",
    ]
    for track in ledger.tracks:
        lines.append(
            "| **{0} {1}** | {2} | {3} | {4} | {5} |".format(
                track.track_identifier,
                track.name,
                track.scope,
                track.task_count,
                track.done_count,
                track.blocked_by or "nothing",
            )
        )
    lines.append(
        "| **Total** | | {0} | {1} | |".format(ledger.task_count, ledger.done_count)
    )
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 33 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/trigpoint_render.py tests/test_progress_table.py
git commit -m "Generate the progress table from the task lists

The table is written between markers rather than by hand, so its counts cannot
disagree with the tasks they summarise. A missing marker pair is reported, not
raised, so one absent region never discards the rest of a write."
```

---

### Task 5: Dashboard renderer

Ledger to a self-contained, theme-aware HTML page. Tests assert structure and honesty, not aesthetics.

**Files:**
- Modify: `scripts/trigpoint_render.py`
- Create: `tests/test_render.py`

**Interfaces:**
- Consumes: `Ledger` from Task 1, `render_progress_table` from Task 4.
- Produces: `render_dashboard(ledger: Ledger, title: str, headline: str, lanes_run: List[str], lanes_skipped: List[str]) -> str`

- [ ] **Step 1: Write the failing test**

Create `tests/test_render.py`:

```python
from __future__ import annotations

import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from trigpoint_ledger import parse_ledger
from trigpoint_render import render_dashboard

LEDGER = """# Example

## T1 Foundation

**Scope:** Make it boot
**Blocked by:** nothing

- [x] **1.1** One   **Verified:** `run` -> ok. 2026-08-27
- [ ] **1.2** Two & three <script>alert(1)</script>

## Definition of done

- [ ] 1. A fresh clone boots
"""


class RenderDashboardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.html = render_dashboard(
            parse_ledger(LEDGER),
            title="Example",
            headline="The two halves have never run together.",
            lanes_run=["boot", "reachability"],
            lanes_skipped=["honesty"],
        )

    def test_headline_leads_the_page(self) -> None:
        body_start = self.html.index("<body")
        self.assertLess(
            self.html.index("never run together"),
            self.html.index("T1 Foundation"),
        )
        self.assertGreater(self.html.index("never run together"), body_start)

    def test_every_task_is_listed_not_a_highlight_reel(self) -> None:
        self.assertIn("1.1", self.html)
        self.assertIn("1.2", self.html)

    def test_task_text_is_escaped(self) -> None:
        self.assertNotIn("<script>alert(1)</script>", self.html)
        self.assertIn("&lt;script&gt;", self.html)
        self.assertIn("&amp;", self.html)

    def test_lanes_run_and_skipped_are_both_stated(self) -> None:
        self.assertIn("honesty", self.html)
        self.assertIn("reachability", self.html)

    def test_definition_of_done_is_rendered(self) -> None:
        self.assertIn("A fresh clone boots", self.html)

    def test_page_is_self_contained(self) -> None:
        for forbidden in ("<script src=", 'href="http', "@import url(http"):
            self.assertNotIn(forbidden, self.html)

    def test_page_is_theme_aware(self) -> None:
        self.assertIn("prefers-color-scheme: dark", self.html)
        self.assertIn('data-theme="dark"', self.html)

    def test_counts_come_from_the_ledger(self) -> None:
        self.assertIsNotNone(re.search(r"\b1\s*/\s*2\b", self.html))

    def test_title_is_set(self) -> None:
        self.assertIn("<title>Example", self.html)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_render -v`
Expected: FAIL with `ImportError: cannot import name 'render_dashboard'`

- [ ] **Step 3: Write the implementation**

Append to `scripts/trigpoint_render.py`. Import `html as html_module` and `List` at the top of the file.

```python
DASHBOARD_STYLE = """
:root {
  --page: #f6f5f2; --ink: #1b1c1e; --muted: #6a6b70;
  --rule: #d9d7d1; --panel: #ffffff; --accent: #b4541f;
  --done: #2f6f4f; --open: #9a9893;
}
:root:not([data-theme="light"]) { }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --page: #16171a; --ink: #e9e8e4; --muted: #9a9ba0;
    --rule: #2c2e33; --panel: #1d1f23; --accent: #e0763c;
    --done: #6fbf95; --open: #5a5c62;
  }
}
:root[data-theme="dark"] {
  --page: #16171a; --ink: #e9e8e4; --muted: #9a9ba0;
  --rule: #2c2e33; --panel: #1d1f23; --accent: #e0763c;
  --done: #6fbf95; --open: #5a5c62;
}
body { background: var(--page); color: var(--ink); margin: 0;
  font: 16px/1.55 ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
.wrap { max-width: 60rem; margin: 0 auto; padding: 3rem 1.25rem 5rem; }
.headline { font-size: 1.35rem; line-height: 1.35; border-left: 3px solid var(--accent);
  padding-left: 1rem; margin: 0 0 2.5rem; }
.track { border: 1px solid var(--rule); background: var(--panel);
  border-radius: 6px; padding: 1.1rem 1.25rem; margin: 0 0 1rem; }
.track h2 { font-size: 1rem; margin: 0 0 .35rem; letter-spacing: .01em; }
.meta { color: var(--muted); font-size: .85rem; margin: 0 0 .8rem; }
.bar { height: 4px; background: var(--open); border-radius: 2px; overflow: hidden;
  margin: 0 0 .9rem; }
.bar span { display: block; height: 100%; background: var(--done); }
ul.tasks { list-style: none; margin: 0; padding: 0; }
ul.tasks li { padding: .3rem 0; border-top: 1px solid var(--rule); font-size: .92rem; }
ul.tasks li:first-child { border-top: 0; }
.state { display: inline-block; width: 1.4rem; color: var(--muted); }
.state.done { color: var(--done); }
.evidence { display: block; color: var(--muted); font-size: .8rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace; padding-left: 1.4rem; }
footer { color: var(--muted); font-size: .82rem; border-top: 1px solid var(--rule);
  margin-top: 3rem; padding-top: 1rem; }
.scroll { overflow-x: auto; }
"""


def render_dashboard(
    ledger: Ledger,
    title: str,
    headline: str,
    lanes_run: List[str],
    lanes_skipped: List[str],
) -> str:
    escape = html_module.escape
    parts = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>{0}</title>".format(escape(title)),
        "<style>{0}</style>".format(DASHBOARD_STYLE),
        "</head><body><div class=\"wrap\">",
        "<p class=\"headline\">{0}</p>".format(escape(headline)),
        "<p class=\"meta\">{0} of {1} tasks complete across {2} tracks.</p>".format(
            ledger.done_count, ledger.task_count, len(ledger.tracks)
        ),
    ]

    for track in ledger.tracks:
        percent = (
            int(round(100.0 * track.done_count / track.task_count))
            if track.task_count
            else 0
        )
        parts.append('<section class="track">')
        parts.append(
            "<h2>{0} {1}</h2>".format(
                escape(track.track_identifier), escape(track.name)
            )
        )
        parts.append(
            '<p class="meta">{0} &middot; blocked by {1} &middot; {2} / {3}</p>'.format(
                escape(track.scope),
                escape(track.blocked_by or "nothing"),
                track.done_count,
                track.task_count,
            )
        )
        parts.append('<div class="bar"><span style="width:{0}%"></span></div>'.format(percent))
        parts.append('<ul class="tasks">')
        for task in track.tasks:
            state_class = "state done" if task.done else "state"
            state_mark = "x" if task.done else "-"
            parts.append(
                '<li><span class="{0}">{1}</span>{2}'.format(
                    state_class, state_mark, escape(task.text)
                )
            )
            if task.evidence:
                parts.append(
                    '<span class="evidence">{0}</span>'.format(escape(task.evidence))
                )
            parts.append("</li>")
        parts.append("</ul></section>")

    if ledger.done_criteria:
        parts.append('<section class="track"><h2>Definition of done</h2>')
        parts.append('<ul class="tasks">')
        for criterion in ledger.done_criteria:
            state_class = "state done" if criterion.done else "state"
            state_mark = "x" if criterion.done else "-"
            parts.append(
                '<li><span class="{0}">{1}</span>{2}</li>'.format(
                    state_class, state_mark, escape(criterion.text)
                )
            )
        parts.append("</ul></section>")

    parts.append("<footer>")
    parts.append(
        "<p>Audit lanes run: {0}.</p>".format(
            escape(", ".join(lanes_run)) if lanes_run else "none recorded"
        )
    )
    parts.append(
        "<p>Audit lanes NOT run: {0}. Nothing is claimed about them.</p>".format(
            escape(", ".join(lanes_skipped)) if lanes_skipped else "none"
        )
    )
    parts.append(
        "<p>Generated from the ledger. Do not hand-edit this file.</p>"
    )
    parts.append("</footer></div></body></html>")
    return "\n".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 42 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/trigpoint_render.py tests/test_render.py
git commit -m "Render the dashboard from the ledger

Self-contained and theme-aware, with every task listed rather than a curated
subset. The footer states which audit lanes did not run, so an absent lane
never reads as a clean one."
```

---

### Task 6: The sync CLI

Wires the parser, the table and the renderer together, obeying the partial application rule.

**Files:**
- Create: `scripts/build_dashboard.py`
- Create: `tests/test_build_dashboard.py`

**Interfaces:**
- Consumes: everything from Tasks 1, 2, 4 and 5.
- Produces: `main(argv: List[str]) -> int`. Exit 0 on success, 1 when validation errors exist, 2 when the ledger is unreadable. Accepts `--ledger PATH`, `--output PATH`, `--title TEXT`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_build_dashboard.py`:

```python
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import build_dashboard

WITH_MARKERS = """# Example

**Headline:** The two halves have never run together.

## Progress at a glance

<!-- trigpoint:progress:begin -->
stale
<!-- trigpoint:progress:end -->

## T1 Foundation

**Scope:** Make it boot
**Blocked by:** nothing

- [ ] **1.1** One
"""

WITHOUT_MARKERS = """# Example

## T1 Foundation

**Scope:** Make it boot
**Blocked by:** nothing

- [ ] **1.1** One
"""

TICKED_NO_EVIDENCE = """# Example

## T1 Foundation

**Scope:** Make it boot
**Blocked by:** nothing

- [x] **1.1** One
"""


class BuildDashboardTest(unittest.TestCase):
    def make(self, body: str):
        directory = pathlib.Path(tempfile.mkdtemp())
        ledger = directory / "ROADMAP.md"
        ledger.write_text(body, encoding="utf-8")
        return ledger, directory / "dashboard.html"

    def test_progress_table_is_rewritten_in_place(self) -> None:
        ledger, output = self.make(WITH_MARKERS)
        self.assertEqual(
            0, build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        )
        text = ledger.read_text(encoding="utf-8")
        self.assertNotIn("stale", text)
        self.assertIn("| **T1 Foundation** |", text)

    def test_html_is_written(self) -> None:
        ledger, output = self.make(WITH_MARKERS)
        build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        self.assertTrue(output.is_file())
        self.assertIn("T1 Foundation", output.read_text(encoding="utf-8"))

    def test_headline_is_taken_from_the_ledger(self) -> None:
        ledger, output = self.make(WITH_MARKERS)
        build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        self.assertIn("never run together", output.read_text(encoding="utf-8"))

    def test_missing_markers_still_writes_the_html(self) -> None:
        ledger, output = self.make(WITHOUT_MARKERS)
        exit_code = build_dashboard.main(
            ["--ledger", str(ledger), "--output", str(output)]
        )
        self.assertEqual(0, exit_code)
        self.assertTrue(output.is_file())

    def test_validation_errors_fail_the_run(self) -> None:
        ledger, output = self.make(TICKED_NO_EVIDENCE)
        self.assertEqual(
            1, build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        )

    def test_validation_errors_still_leave_the_html_written(self) -> None:
        ledger, output = self.make(TICKED_NO_EVIDENCE)
        build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        self.assertTrue(output.is_file())

    def test_running_twice_is_idempotent(self) -> None:
        ledger, output = self.make(WITH_MARKERS)
        build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        once = ledger.read_text(encoding="utf-8")
        build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        self.assertEqual(once, ledger.read_text(encoding="utf-8"))

    def test_missing_ledger_exits_two(self) -> None:
        self.assertEqual(2, build_dashboard.main(["--ledger", "/nope/ROADMAP.md"]))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_build_dashboard -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'build_dashboard'`

- [ ] **Step 3: Write the implementation**

Create `scripts/build_dashboard.py`:

```python
#!/usr/bin/env python3
"""Regenerate the ledger's progress table and the dashboard HTML.

Applies what matches and writes regardless. A missing region is reported, never
a reason to discard the rest of the work. This script never commits.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from typing import List, Optional

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from trigpoint_ledger import has_errors, parse_ledger, validate
from trigpoint_render import render_dashboard, render_progress_table, replace_marked_region

HEADLINE_LINE = re.compile(r"^\*\*Headline:\*\*\s*(?P<headline>.+?)\s*$", re.MULTILINE)
LANES_RUN_LINE = re.compile(r"^\*\*Lanes run:\*\*\s*(?P<lanes>.+?)\s*$", re.MULTILINE)
LANES_SKIPPED_LINE = re.compile(
    r"^\*\*Lanes not run:\*\*\s*(?P<lanes>.+?)\s*$", re.MULTILINE
)
TITLE_LINE = re.compile(r"^#\s+(?P<title>.+?)\s*$", re.MULTILINE)


def _first(pattern: "re.Pattern[str]", text: str, group: str) -> Optional[str]:
    match = pattern.search(text)
    return match.group(group).strip() if match else None


def _split_lanes(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


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

    original_text = ledger_path.read_text(encoding="utf-8")
    ledger = parse_ledger(original_text)

    applied: List[str] = []
    failed: List[str] = []

    updated_text, region_found = replace_marked_region(
        original_text, "progress", render_progress_table(ledger)
    )
    if region_found:
        if updated_text != original_text:
            ledger_path.write_text(updated_text, encoding="utf-8")
        applied.append("progress table")
    else:
        failed.append(
            "progress table: no <!-- trigpoint:progress:begin --> region in "
            + arguments.ledger
        )

    title = arguments.title or _first(TITLE_LINE, original_text, "title") or "Roadmap"
    headline = (
        _first(HEADLINE_LINE, original_text, "headline")
        or "No headline recorded in the ledger."
    )
    html = render_dashboard(
        ledger,
        title=title,
        headline=headline,
        lanes_run=_split_lanes(_first(LANES_RUN_LINE, original_text, "lanes")),
        lanes_skipped=_split_lanes(_first(LANES_SKIPPED_LINE, original_text, "lanes")),
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 50 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_dashboard.py tests/test_build_dashboard.py
git commit -m "Add the sync CLI

Rewrites the progress table in place and writes the dashboard in one pass, so
the two cannot disagree. A missing marker region is reported and the HTML is
written anyway, rather than one absent pattern discarding the whole run."
```

---

### Task 7: The CLAUDE.md instruction block

What makes future sessions self-driving, and what makes the discipline survive without the plugin.

**Files:**
- Create: `scripts/install_block.py`
- Create: `tests/test_install_block.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `render_block(mode: str) -> str`, `upsert_block(existing_text: str, block: str) -> str`, `main(argv: List[str]) -> int` accepting `--claude-md PATH` and `--mode automatic|manual`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_install_block.py`:

```python
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import install_block


class InstallBlockTest(unittest.TestCase):
    def test_block_is_delimited(self) -> None:
        block = install_block.render_block("automatic")
        self.assertTrue(block.startswith("<!-- trigpoint:begin -->"))
        self.assertTrue(block.rstrip().endswith("<!-- trigpoint:end -->"))

    def test_block_states_the_mode(self) -> None:
        self.assertIn("Mode: automatic", install_block.render_block("automatic"))
        self.assertIn("Mode: manual", install_block.render_block("manual"))

    def test_block_carries_the_evidence_rule(self) -> None:
        block = install_block.render_block("automatic")
        self.assertIn("**Verified:**", block)
        self.assertIn("Never tick on assumption", block)

    def test_block_carries_the_discovered_work_rule(self) -> None:
        self.assertIn("ADDED", install_block.render_block("automatic"))

    def test_appends_to_an_existing_file_preserving_content(self) -> None:
        result = install_block.upsert_block(
            "# Project\n\nExisting guidance.\n", install_block.render_block("automatic")
        )
        self.assertIn("Existing guidance.", result)
        self.assertIn("<!-- trigpoint:begin -->", result)

    def test_replaces_rather_than_stacking_on_reinstall(self) -> None:
        once = install_block.upsert_block("# Project\n", install_block.render_block("automatic"))
        twice = install_block.upsert_block(once, install_block.render_block("manual"))
        self.assertEqual(1, twice.count("<!-- trigpoint:begin -->"))
        self.assertIn("Mode: manual", twice)
        self.assertNotIn("Mode: automatic", twice)

    def test_is_idempotent_for_the_same_mode(self) -> None:
        once = install_block.upsert_block("# Project\n", install_block.render_block("automatic"))
        twice = install_block.upsert_block(once, install_block.render_block("automatic"))
        self.assertEqual(once, twice)

    def test_creates_the_file_when_absent(self) -> None:
        directory = pathlib.Path(tempfile.mkdtemp())
        target = directory / "CLAUDE.md"
        self.assertEqual(
            0, install_block.main(["--claude-md", str(target), "--mode", "automatic"])
        )
        self.assertIn("<!-- trigpoint:begin -->", target.read_text(encoding="utf-8"))

    def test_rejects_an_unknown_mode(self) -> None:
        with self.assertRaises(SystemExit):
            install_block.main(["--mode", "sometimes"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_install_block -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'install_block'`

- [ ] **Step 3: Write the implementation**

Create `scripts/install_block.py`:

```python
#!/usr/bin/env python3
"""Write the Trigpoint instruction block into a repository's CLAUDE.md.

Delimited and idempotent: re-running updates the block in place rather than
stacking copies.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
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
- `python3 .trigpoint/check_drift.py` exits non-zero when a box is ticked with
  no evidence recorded.

Mode: {mode}"""


def render_block(mode: str) -> str:
    return "{0}\n{1}\n{2}\n".format(
        BEGIN_MARKER, BLOCK_BODY.format(mode=mode), END_MARKER
    )


def upsert_block(existing_text: str, block: str) -> str:
    pattern = re.compile(
        re.escape(BEGIN_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL
    )
    if pattern.search(existing_text):
        return pattern.sub(lambda _: block.rstrip("\n"), existing_text, count=1)
    separator = "" if not existing_text or existing_text.endswith("\n\n") else "\n"
    if existing_text and not existing_text.endswith("\n"):
        separator = "\n\n"
    return "{0}{1}{2}".format(existing_text, separator, block)


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Install the Trigpoint CLAUDE.md block")
    parser.add_argument("--claude-md", default="CLAUDE.md")
    parser.add_argument("--mode", choices=VALID_MODES, default="automatic")
    arguments = parser.parse_args(argv)

    target = pathlib.Path(arguments.claude_md)
    existing_text = target.read_text(encoding="utf-8") if target.is_file() else ""
    target.write_text(
        upsert_block(existing_text, render_block(arguments.mode)), encoding="utf-8"
    )
    sys.stdout.write(
        "applied: trigpoint block in {0}, mode {1}\n".format(
            arguments.claude_md, arguments.mode
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 59 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/install_block.py tests/test_install_block.py
git commit -m "Add the CLAUDE.md instruction block installer

The block is what makes a future session in any window pick up the ledger
discipline, and it is plain markdown, so a collaborator without the plugin gets
the same rules. Delimited so reinstalling updates rather than stacks."
```

---

### Task 8: Dogfood against the reference ledger

Prove the parser against the real document it was derived from, before any of it is published.

**Files:**
- Create: `tests/test_reference_ledger.py`
- Create: `tests/fixtures/reference_ledger.md` (a copy of a private reference project's `ROADMAP.md`)

**Interfaces:**
- Consumes: `parse_ledger`, `validate` from Tasks 1 and 2.
- Produces: nothing new. This task only proves the existing interfaces on real input.

- [ ] **Step 1: Copy the reference ledger into fixtures**

```bash
cp <path to the private reference project>/ROADMAP.md tests/fixtures/reference_ledger.md
```

- [ ] **Step 2: Write the characterisation test**

Create `tests/test_reference_ledger.py`:

```python
from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from trigpoint_ledger import parse_ledger

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "reference_ledger.md"


class ReferenceLedgerTest(unittest.TestCase):
    """The real ledger this format was derived from, parsed as-is.

    The reference predates the Scope and Blocked by metadata lines, so it is
    expected to yield zero tracks. That is the point: it proves the parser
    refuses to invent structure that is not there, and it is the fixture the
    migration note in the README is written against.
    """

    def setUp(self) -> None:
        self.ledger = parse_ledger(FIXTURE.read_text(encoding="utf-8"))

    def test_parsing_the_reference_does_not_raise(self) -> None:
        self.assertIsNotNone(self.ledger)

    def test_sections_without_scope_lines_are_not_tracks(self) -> None:
        self.assertEqual([], self.ledger.tracks)

    def test_definition_of_done_is_still_found(self) -> None:
        self.assertGreaterEqual(len(self.ledger.done_criteria), 10)
```

- [ ] **Step 3: Run the test**

Run: `python3 -m unittest tests.test_reference_ledger -v`
Expected: PASS.

If `test_definition_of_done_is_still_found` fails, the heading in the reference is `## Definition of done for Stage 1` and the prefix match should already cover it. Investigate the parse rather than loosening the assertion.

- [ ] **Step 4: Convert the reference into a Trigpoint ledger and rebuild it**

Add `**Scope:**` and `**Blocked by:**` lines plus the progress markers to a working copy, then:

```bash
cp tests/fixtures/reference_ledger.md /tmp/converted.md
# add the metadata lines and marker pair by hand in /tmp/converted.md
python3 scripts/build_dashboard.py --ledger /tmp/converted.md --output /tmp/converted.html
python3 scripts/check_drift.py /tmp/converted.md
```

Expected: the progress table in `/tmp/converted.md` matches the counts stated in the source document (8 tracks, 67 tasks), and `check_drift.py` reports the one ticked task, 7.1, as an error because it carries no `**Verified:**` line.

Record the actual output. If the counts disagree with the source document, the source document was wrong, which is the entire point of the tool. State which.

- [ ] **Step 5: Commit**

```bash
git add tests/test_reference_ledger.py tests/fixtures/reference_ledger.md
git commit -m "Characterise the parser against the reference ledger

The document this format was derived from carries no Scope metadata, so it
yields zero tracks. That is the correct behaviour and it is what the migration
note in the README is written against."
```

---

### Task 9: Plugin scaffold

The files that make this installable.

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`
- Create: `commands/trigpoint.md`
- Create: `commands/trigpoint-sync.md`
- Create: `tests/test_manifests.py`

**Interfaces:**
- Consumes: nothing.
- Produces: the installable plugin surface. The command files invoke the skill by name.

- [ ] **Step 1: Write the failing test**

Create `tests/test_manifests.py`:

```python
from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class ManifestTest(unittest.TestCase):
    def test_plugin_manifest_is_valid_json_with_required_fields(self) -> None:
        data = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text("utf-8"))
        for field in ("name", "description", "version"):
            self.assertIn(field, data)
        self.assertEqual("trigpoint", data["name"])

    def test_marketplace_manifest_lists_this_plugin(self) -> None:
        data = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text("utf-8")
        )
        self.assertIn("name", data)
        self.assertIn("owner", data)
        names = [plugin["name"] for plugin in data["plugins"]]
        self.assertIn("trigpoint", names)

    def test_every_command_file_exists_and_has_frontmatter(self) -> None:
        for command_name in ("trigpoint", "trigpoint-sync"):
            path = ROOT / "commands" / (command_name + ".md")
            self.assertTrue(path.is_file(), command_name)
            text = path.read_text("utf-8")
            self.assertTrue(text.startswith("---"), command_name)
            self.assertIn("description:", text)

    def test_no_forbidden_typography_in_shipped_markdown(self) -> None:
        forbidden = ["—", "–", "‘", "’", "“", "”", "…"]
        for path in list(ROOT.glob("commands/*.md")) + list(
            ROOT.glob("skills/**/*.md")
        ):
            text = path.read_text("utf-8")
            for character in forbidden:
                self.assertNotIn(character, text, "{0} in {1}".format(repr(character), path))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_manifests -v`
Expected: FAIL with `FileNotFoundError` on `.claude-plugin/plugin.json`

- [ ] **Step 3: Write the manifests**

Create `.claude-plugin/plugin.json`:

```json
{
  "name": "trigpoint",
  "description": "Audit a codebase, then produce a plan of record that cannot drift. Generates a ledger, a dashboard and a design spec, and keeps them true while the work is done.",
  "version": "0.1.0",
  "author": { "name": "Felipe Florencio" },
  "homepage": "https://github.com/felipeflorencio/trigpoint",
  "keywords": ["planning", "roadmap", "audit", "codebase", "dashboard"]
}
```

Create `.claude-plugin/marketplace.json`:

```json
{
  "name": "trigpoint",
  "description": "Trigpoint, installed directly from its own repository.",
  "owner": { "name": "Felipe Florencio" },
  "plugins": [
    {
      "name": "trigpoint",
      "description": "Audit a codebase, then produce a plan of record that cannot drift.",
      "category": "development",
      "source": "./",
      "homepage": "https://github.com/felipeflorencio/trigpoint"
    }
  ]
}
```

Create `commands/trigpoint.md`:

```markdown
---
description: Audit this codebase and build a plan of record with a generated dashboard
---

Invoke the `trigpoint` skill and run it from the beginning: the light pass and
lane selection, the audit, the premise check, the question ladder, the design
sections, then emit the ledger, the spec and the dashboard.

Arguments, if any, are the user's stated goal for the work: $ARGUMENTS
```

Create `commands/trigpoint-sync.md`:

```markdown
---
description: Regenerate the ledger progress table and the dashboard from ROADMAP.md
---

Run `python3 .trigpoint/build_dashboard.py` in the repository root.

Report what was applied and what was not, separately and verbatim. If the
script reports validation errors, list them and stop; do not tick, untick or
edit any task to make the errors go away.

If a dashboard artifact URL is recorded in the ledger header, republish to that
same URL rather than creating a new one.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 63 tests.

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin commands tests/test_manifests.py
git commit -m "Add the plugin manifests and commands

Manifests are asserted as valid JSON with the fields the working marketplaces
use, and shipped markdown is checked for the typography the style rules forbid."
```

---

### Task 10: The skill

The process itself. This is the substance of the plugin; the scripts only keep its output honest.

**Files:**
- Create: `skills/trigpoint/SKILL.md`
- Create: `skills/trigpoint/references/audit-lanes.md`
- Create: `skills/trigpoint/references/agent-brief-skeleton.md`
- Create: `skills/trigpoint/references/question-ladder.md`
- Create: `skills/trigpoint/references/evidence-rules.md`
- Create: `skills/trigpoint/references/ledger-format.md`
- Create: `skills/trigpoint/references/dashboard-design.md`
- Create: `skills/trigpoint/templates/ROADMAP.template.md`
- Create: `skills/trigpoint/templates/spec.template.md`

**Interfaces:**
- Consumes: the scripts from Tasks 1 to 7, invoked by path.
- Produces: the authoring process. No code.

- [ ] **Step 1: Read the authoring rules**

Invoke `superpowers:writing-skills` and follow it. The frontmatter `description` decides whether the skill is ever selected, so it must name the triggers: building a roadmap, planning work on an existing codebase, auditing a repository before planning.

- [ ] **Step 2: Write SKILL.md**

Content, drawn from spec sections 3, 4, 6 and 7, in this order:

1. What this produces: ledger, dashboard, spec. One paragraph.
2. Phase A: the light pass, then the single lane-selection question. **Silence runs all seven lanes.**
3. Phase B: dispatch one agent per selected lane using the brief skeleton. Reference `audit-lanes.md` and `agent-brief-skeleton.md`.
4. The verification gate. Reference `evidence-rules.md`. Findings are tagged CONFIRMED, PLAUSIBLE or REFUTED, and only CONFIRMED findings become tasks.
5. Phase C: the premise check, stated before any question is asked.
6. Phase D: the four questions, one per message, **expecting the user to reject the menu.** Reference `question-ladder.md`.
7. Phase E: design sections with approval after each, then emit.
8. Phase F: state that updates will be automatic unless the user says otherwise, then run `install_block.py` with the chosen mode and copy `build_dashboard.py`, `check_drift.py` and `trigpoint_ledger.py`, `trigpoint_render.py` into the target repository's `.trigpoint/`.
9. A red-flags table in the style of the superpowers skills: "the audit found nothing, so the repo is clean" -> absence of findings in a lane that did not run is not a clean result; "I will tick this box, the change is obvious" -> the box needs the command and its output.

- [ ] **Step 3: Write the reference files**

Each reference is the corresponding spec section rewritten as instructions rather than as description. `ledger-format.md` must contain the exact parse contract from spec section 4, including the three grammar rules and the marker pair, since an agent authoring a ledger has to produce something the parser accepts.

- [ ] **Step 4: Write the templates**

`ROADMAP.template.md` carries the full section order from spec section 4, the `<!-- trigpoint:progress:begin -->` marker pair, and the `**Headline:**`, `**Lanes run:**` and `**Lanes not run:**` lines that `build_dashboard.py` reads. Placeholders are written as `{{ }}` so an unfilled one is obvious.

- [ ] **Step 5: Verify the template round-trips**

```bash
python3 scripts/build_dashboard.py \
  --ledger skills/trigpoint/templates/ROADMAP.template.md \
  --output /tmp/template.html
```

Expected: exits 0, reports the progress table applied, writes the HTML. If the marker region is reported as not found, the template is missing it.

- [ ] **Step 6: Run the full suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS. `test_no_forbidden_typography_in_shipped_markdown` now covers the new skill files.

- [ ] **Step 7: Commit**

```bash
git add skills/
git commit -m "Add the trigpoint skill and its references

The process is the substance: audit lanes, the verification gate, the premise
check and the four questions. The scripts only keep its output honest."
```

---

### Task 11: CI gate, dogfooded

The repository runs its own drift check against its own ledger.

**Files:**
- Create: `.github/workflows/checks.yml`
- Create: `ROADMAP.md` (this repository's own ledger)

**Interfaces:**
- Consumes: `check_drift.py` from Task 3, `build_dashboard.py` from Task 6.
- Produces: a green CI run.

- [ ] **Step 1: Write this repository's own ledger**

Create `ROADMAP.md` from the template, with the tracks of this plan. Every already-completed task carries its real `**Verified:**` line with the command that was actually run.

- [ ] **Step 2: Write the workflow**

Create `.github/workflows/checks.yml`:

```yaml
name: checks

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.9"
      - name: Unit tests
        run: python3 -m unittest discover -s tests -v
      - name: Ledger drift gate
        run: python3 scripts/check_drift.py ROADMAP.md
      - name: Dashboard is up to date
        run: |
          python3 scripts/build_dashboard.py --ledger ROADMAP.md --output roadmap-dashboard.html
          git diff --exit-code ROADMAP.md roadmap-dashboard.html
```

The third step is the real gate: it regenerates and fails if the committed output differs, which is what makes drift impossible rather than merely discouraged.

- [ ] **Step 3: Verify locally before pushing**

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_drift.py ROADMAP.md
python3 scripts/build_dashboard.py --ledger ROADMAP.md --output roadmap-dashboard.html
git diff --exit-code ROADMAP.md roadmap-dashboard.html
```

Expected: all four succeed, the last printing nothing and exiting 0.

- [ ] **Step 4: Commit**

```bash
git add .github ROADMAP.md roadmap-dashboard.html
git commit -m "Run the drift gate against this repository's own ledger

Regenerating in CI and failing on any diff is what makes drift impossible
rather than merely discouraged."
```

---

### Task 12: README and cover

The page that decides whether anyone installs it.

**Files:**
- Create: `README.md`
- Create: `assets/cover.html`
- Create: `assets/cover.png`
- Create: `examples/README.md`

**Interfaces:**
- Consumes: the install path from spec section 9.
- Produces: the public face of the repository.

- [ ] **Step 1: Write the README**

Sections, in this order, per spec section 10:

1. One-line problem: plans made by an agent go stale within a week, and a stale plan is worse than none.
2. What it produces: three artefacts, with the dashboard screenshot first.
3. Install, both routes, shared marketplace first:

```
/plugin marketplace add felipeflorencio/claude-plugins
/plugin install trigpoint@felipeflorencio
```

4. Usage: `/trigpoint`, then what the seven questions are.
5. The guarantees: counts cannot drift, a box cannot be ticked without recorded evidence. Show the failing `check_drift.py` output as proof.
6. The worked example, with the real numbers from the source run: 248 findings, 15 confirmed, 67 tasks, 8 tracks.
7. Honest limits, verbatim from spec section 11, including that the source plan has never been executed and that the audit is the bulk of the token cost.

- [ ] **Step 2: Build the cover source**

Create `assets/cover.html`: a 1280x640 artboard. Subject-derived per the metaphor rule, so: a trig point, a fixed reference, marks measured against it. One claim, no feature list. Reuse the palette tokens from `DASHBOARD_STYLE` so the cover and the product agree.

- [ ] **Step 3: Render the cover to PNG**

Render `assets/cover.html` at exactly 1280x640 through the available browser tooling and save `assets/cover.png`.

- [ ] **Step 4: Look at the PNG**

Open `assets/cover.png` and view it. A written file is not a correct image. Confirm the dimensions, that no text is clipped, and that it is legible at the size GitHub renders a social preview. If it is wrong, fix the HTML and re-render rather than accepting it.

- [ ] **Step 5: Commit**

```bash
git add README.md assets examples
git commit -m "Add README and cover

Leads with the problem, shows the three artefacts, and states the limits
plainly, including that the plan this method produced has never been executed."
```

---

### Task 13: Publish and verify the install

Nothing is claimed to work until it has been installed from the published source.

**Files:**
- Create: `~/Personal/claude-plugins/.claude-plugin/marketplace.json`
- Create: `~/Personal/claude-plugins/README.md`

**Interfaces:**
- Consumes: the published `felipeflorencio/trigpoint` repository.
- Produces: a verified install path.

- [ ] **Step 1: Create and push the plugin repository**

```bash
cd ~/Personal/trigpoint
gh repo create felipeflorencio/trigpoint --public --source=. --remote=origin --push
```

Confirm the full test suite passed before this push, per the pre-push test gate.

- [ ] **Step 2: Create the shared marketplace repository**

```bash
mkdir -p ~/Personal/claude-plugins/.claude-plugin
```

Create `~/Personal/claude-plugins/.claude-plugin/marketplace.json` exactly as specified in spec section 9, then:

```bash
cd ~/Personal/claude-plugins
git init && git add -A && git commit -m "Add marketplace listing trigpoint"
gh repo create felipeflorencio/claude-plugins --public --source=. --remote=origin --push
```

- [ ] **Step 3: Verify the marketplace resolves**

```bash
python3 -c "import json,urllib.request; \
d=json.load(urllib.request.urlopen('https://raw.githubusercontent.com/felipeflorencio/claude-plugins/main/.claude-plugin/marketplace.json')); \
print(d['name'], [p['name'] for p in d['plugins']])"
```

Expected: prints the marketplace name and `['trigpoint']`. A 404 means the default branch is not `main` or the path is wrong. Fix before continuing.

- [ ] **Step 4: Install it for real**

In a Claude Code session:

```
/plugin marketplace add felipeflorencio/claude-plugins
/plugin install trigpoint@felipeflorencio
```

Then confirm `/trigpoint` and `/trigpoint-sync` appear in the command list, and that the `trigpoint` skill appears in the skill list.

**This is the step that settles whether the manifest format inferred from working examples is correct.** If the install fails, the error names the field that is wrong. Fix the manifest, push, and repeat. Do not update the README's install instructions until this has actually succeeded.

- [ ] **Step 5: Set the social preview**

Upload `assets/cover.png` as the repository social preview in GitHub settings, and confirm it renders by viewing the repository card.

- [ ] **Step 6: Record the result**

Tick the corresponding tasks in this repository's own `ROADMAP.md` with real `**Verified:**` lines, regenerate, and commit:

```bash
python3 scripts/build_dashboard.py --ledger ROADMAP.md --output roadmap-dashboard.html
git add ROADMAP.md roadmap-dashboard.html
git commit -m "Record verified install path in the ledger"
git push
```

---

## Self-Review

**Spec coverage.** Section 3 phases A to F are covered by Task 10 (the skill) and Task 7 (mode persistence). Section 4's format contract is Tasks 1, 2 and 4. Section 5's dashboard is Task 5. Section 6's living mechanism is Tasks 6, 7 and 11. Section 7's question timeline is Task 10. Section 8's layout is Tasks 9 and 10. Section 9's distribution is Task 13. Section 10's promotion is Task 12. Section 11's honest limits are written into the README in Task 12 step 1.

**One gap found and closed:** the spec says the ledger header records the dashboard artifact URL so `/trigpoint-sync` republishes to the same URL rather than spawning a new one. No script reads it, because publishing is done by the agent, not by Python. Task 9's `commands/trigpoint-sync.md` now carries that instruction explicitly.

**A second gap, deliberately left open:** Task 13 step 4 is the only verification of the manifest format, and it cannot be run from a shell. It is a human-in-the-loop step and is marked as such. Nothing downstream claims the install works until it passes.

**Type consistency.** `parse_ledger`, `validate`, `has_errors`, `Problem`, `Task`, `Track`, `DoneCriterion`, `Ledger`, `render_progress_table`, `replace_marked_region`, `render_dashboard`, `render_block`, `upsert_block` are each defined once and referenced with the same signature everywhere. `track_identifier` is used throughout; `track_id` appears nowhere.

**Placeholder scan.** No TBD, no "add error handling", no "similar to Task N". Task 10 specifies content by section rather than by finished prose, which is appropriate for skill authoring and is bounded by the round-trip check in step 5 and the typography test in Task 9.
