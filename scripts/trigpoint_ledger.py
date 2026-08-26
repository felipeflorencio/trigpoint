"""Parse a Trigpoint ledger.

Pure functions over strings. No filesystem access and no third-party imports,
because this module is copied into arbitrary repositories and must run on a
bare CI checkout.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Iterator, List, Optional, Tuple

SECTION_HEADING = re.compile(r"^##\s+(?P<heading>\S.*?)\s*$")
SCOPE_LINE = re.compile(r"^\*\*Scope:\*\*\s*(?P<scope>.+?)\s*$")
BLOCKED_LINE = re.compile(r"^\*\*Blocked by:\*\*\s*(?P<blocked_by>.+?)\s*$")
TASK_LINE = re.compile(
    r"^\s*-\s+\[(?P<mark>[ xX])\]\s+\*\*(?P<task_id>[^*]+?)\*\*\s*(?P<text>.*)$"
)
CRITERION_LINE = re.compile(r"^\s*-\s+\[(?P<mark>[ xX])\]\s+(?P<text>\S.*?)\s*$")
HEADING_PARTS = re.compile(r"^(?P<identifier>[A-Za-z][A-Za-z0-9]*)(?:\s+(?P<name>.+))?$")

# Any bold "**Key:**" marker line, used to recognise where one metadata field's
# continuation must stop because a different field has begun.
METADATA_LINE = re.compile(r"^\*\*[^*]+:\*\*")
HEADING_LINE = re.compile(r"^#")

EVIDENCE_MARKER = "**Verified:**"
DONE_HEADING_PREFIX = "definition of done"
PLACEHOLDER_OPEN = "{{"
PLACEHOLDER_CLOSE = "}}"
PLACEHOLDER_BODY = re.compile(r"^[A-Za-z -]+$")
FENCE_MARKER = "```"
TILDE_FENCE_MARKER = "~~~"


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
        scope = _read_metadata_field(numbered_lines, SCOPE_LINE, "scope")
        if scope is not None:
            blocked_by = (
                _read_metadata_field(numbered_lines, BLOCKED_LINE, "blocked_by") or ""
            )
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


def _is_fence_delimiter(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith(FENCE_MARKER) or stripped.startswith(TILDE_FENCE_MARKER)


def _fence_marker(line: str) -> Optional[str]:
    """Return which fence marker a delimiter line opens or closes, or None."""
    stripped = line.strip()
    if stripped.startswith(FENCE_MARKER):
        return FENCE_MARKER
    if stripped.startswith(TILDE_FENCE_MARKER):
        return TILDE_FENCE_MARKER
    return None


def _lines_outside_fences(
    numbered_lines: Iterable[NumberedLine],
) -> Iterator[NumberedLine]:
    """Yield only the lines that are not inside a fenced code block.

    The single implementation of fence state. Every scanner in this module goes
    through it, so a heading, a task and a criterion can never disagree about
    whether a line is documentation or work.

    Fenced content is documentation: an example of a heading is not a heading,
    an example of a task is not a task, and a fenced **Verified:** line is not
    evidence for the task above the fence. A fence that is opened and never
    closed leaves the remainder fenced, which is what a markdown renderer does.

    Both a triple-backtick fence and a triple-tilde fence open and close a
    block. A fence tracks which marker opened it, so a backtick fence is only
    closed by another backtick fence and a tilde fence is only closed by
    another tilde fence -- a stray fence of the other kind while one is
    already open is just more fenced content, exactly as a markdown renderer
    treats it.
    """
    open_marker: Optional[str] = None
    for line_number, line in numbered_lines:
        marker = _fence_marker(line)
        if marker is not None:
            if open_marker is None:
                open_marker = marker
            elif marker == open_marker:
                open_marker = None
            continue
        if open_marker is not None:
            continue
        yield line_number, line


def _split_sections(markdown_text: str) -> List[Tuple[str, List[NumberedLine]]]:
    """Split the document into (heading, lines) sections.

    A section's collected lines are the RAW lines in its range, fence
    delimiters and fenced content included, not the fence-filtered stream.
    Heading detection still goes through `_lines_outside_fences` -- reused
    rather than re-implemented -- so a fenced "##" line never opens a section
    and an unclosed fence still swallows every heading after it, exactly as
    before. Keeping the raw lines in `collected` is what lets a downstream
    scanner choose its own relationship with fences: `_extract_tasks` and
    `_extract_criteria` filter fenced content back out themselves, and
    `_read_metadata_field` needs to see the fence delimiter as a stop signal
    rather than have it silently removed.
    """
    all_lines: List[NumberedLine] = list(
        enumerate(markdown_text.splitlines(), start=1)
    )
    unfenced_line_numbers = {
        line_number for line_number, _ in _lines_outside_fences(all_lines)
    }

    sections: List[Tuple[str, List[NumberedLine]]] = []
    heading: Optional[str] = None
    collected: List[NumberedLine] = []
    for index, line in all_lines:
        if index in unfenced_line_numbers:
            match = SECTION_HEADING.match(line)
            if match:
                if heading is not None:
                    sections.append((heading, collected))
                heading = match.group("heading")
                collected = []
                continue
        if heading is not None:
            collected.append((index, line))
    if heading is not None:
        sections.append((heading, collected))
    return sections


def _read_metadata_field(
    numbered_lines: List[NumberedLine], pattern: "re.Pattern[str]", group: str
) -> Optional[str]:
    """Read a one-line metadata field plus any hard-wrapped continuation.

    Markdown treats two lines with no blank line between them as one paragraph,
    so a `**Scope:**` or `**Blocked by:**` line that an author wrapped across
    two physical source lines is one field, not a truncated one. A non-blank
    line immediately following the field's own line is absorbed and joined with
    a single space. Absorption stops at the first line that is blank, that
    opens a different metadata field, that is a task line, that is a
    definition-of-done criterion line, that is fenced, or that is a heading --
    each of those marks the end of the field's paragraph.

    Continuation only ever EXTENDS a value that already exists. A marker line
    whose own text is empty or whitespace-only carries no value to extend, so
    the field is empty and the lines after it are never even inspected --
    otherwise unrelated prose sitting right after a blank `**Scope:**` would
    become the scope, which is the same failure this function exists to close,
    just aimed at the marker line instead of the continuation.

    `numbered_lines` is a section's RAW lines: fenced content is present, not
    pre-stripped, so `_split_sections` can hand every scanner the same raw
    stream and let each decide its own relationship with fences. Fence state
    is therefore computed exactly once here, via `_lines_outside_fences` --
    the module's single fence-toggle implementation, not a second copy of it
    -- into a set of line numbers that are NOT inside a fence. Both the
    initial marker scan and the continuation scan consult that same set: a
    marker line inside a fence is invisible to the scan that looks for the
    field (a fenced example `**Scope:**` never wins over a real one further
    down), and a continuation line that has become fenced ends the field
    exactly like a blank line does.
    """
    lines = list(numbered_lines)
    unfenced_line_numbers = {
        line_number for line_number, _ in _lines_outside_fences(lines)
    }
    for index, (line_number, line) in enumerate(lines):
        if line_number not in unfenced_line_numbers:
            continue
        match = pattern.match(line)
        if not match:
            continue
        own_value = match.group(group).strip()
        if not own_value:
            return None
        parts = [own_value]
        for continuation_number, continuation in lines[index + 1 :]:
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


def _split_heading(heading: str) -> Tuple[str, str]:
    match = HEADING_PARTS.match(heading.strip())
    if not match:
        return heading.strip(), ""
    identifier = match.group("identifier")
    name = match.group("name")
    return identifier, (name.strip() if name else "")


def _extract_tasks(numbered_lines: List[NumberedLine]) -> List[Task]:
    tasks: List[Task] = []
    pending_task: Optional[Task] = None
    pending_block: List[str] = []

    for line_number, line in _lines_outside_fences(numbered_lines):
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


def _marker_outside_inline_code(text: str, marker: str) -> int:
    """Index of the first `marker` that is not inside an inline code span, or -1.

    A task whose own description quotes the evidence marker -- writing
    `**Verified:**` in backticks while describing the rule -- must not have its
    evidence read from the middle of that sentence. This is the same principle
    the module already applies to fenced blocks, one level down: an example of
    evidence is documentation, not evidence.

    Backtick runs open and close a span, and a span is closed only by a run of
    the same length, which is how markdown lets `` ` `` appear inside code.
    """
    index = 0
    length = len(text)
    open_run = 0
    while index < length:
        if text[index] == "`":
            run = 0
            while index + run < length and text[index + run] == "`":
                run += 1
            if open_run == 0:
                open_run = run
            elif run == open_run:
                open_run = 0
            index += run
            continue
        if open_run == 0 and text.startswith(marker, index):
            return index
        index += 1
    return -1


def _apply_evidence(task: Task, block_lines: List[str]) -> Task:
    block = "\n".join(block_lines)
    position = _marker_outside_inline_code(block, EVIDENCE_MARKER)
    if position != -1:
        evidence = block[position + len(EVIDENCE_MARKER) :]
        task.evidence = " ".join(evidence.split()) or None
    first_line = block_lines[0] if block_lines else ""
    first_line_marker = _marker_outside_inline_code(first_line, EVIDENCE_MARKER)
    if first_line_marker != -1:
        first_line = first_line[:first_line_marker]
    task.text = " ".join(first_line.split())
    return task


def _extract_criteria(numbered_lines: List[NumberedLine]) -> List[DoneCriterion]:
    criteria: List[DoneCriterion] = []
    for line_number, line in _lines_outside_fences(numbered_lines):
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
            elif task.done and is_unfilled_placeholder(task.evidence):
                problems.append(
                    Problem(
                        severity="error",
                        line_number=task.line_number,
                        message=(
                            "task {0} is ticked but its **Verified:** line still "
                            "contains an unfilled {{{{ placeholder }}}}. Record the "
                            "command that was actually run and what it printed, "
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


def is_unfilled_placeholder(evidence: Optional[str]) -> bool:
    """True when an evidence string is still template text rather than a record.

    The gate that makes automatic mode safe checks that a ticked task carries
    the command that was run. Template text of the form {{ ... }} satisfies a
    presence check while recording nothing, so it is rejected here as firmly as
    a missing line.

    The test is deliberately narrow. A brace pair only counts when the text
    between the braces is prose: letters, spaces and hyphens and nothing else.
    Real evidence is full of brace pairs that are not placeholders at all, and
    accusing a truthful author of faking evidence is worse than the hole this
    closes. `{{.Name}}` is a Go template, `{{a,b},{c,d}}` is shell brace
    expansion, `{{$VARIABLE}}` is an environment substitution; none is prose and
    none is rejected.
    """
    if not evidence:
        return False
    search_position = 0
    while True:
        opening_position = evidence.find(PLACEHOLDER_OPEN, search_position)
        if opening_position == -1:
            return False
        body_start = opening_position + len(PLACEHOLDER_OPEN)
        closing_position = evidence.find(PLACEHOLDER_CLOSE, body_start)
        if closing_position == -1:
            return False
        body = evidence[body_start:closing_position].strip()
        if body and PLACEHOLDER_BODY.match(body):
            return True
        search_position = closing_position + len(PLACEHOLDER_CLOSE)


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
