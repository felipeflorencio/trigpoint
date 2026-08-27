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
RECORD_MARKER = "**Recorded:**"

VERIFIED = "verified"
RECORDED = "recorded"

EVIDENCE_MARKERS = ((EVIDENCE_MARKER, VERIFIED), (RECORD_MARKER, RECORDED))

# A regression note follows the evidence it contradicts and carries backticks of
# its own, so it ends the span before it without ever starting one.
REGRESSED_MARKER = "**Regressed:**"
SPAN_BOUNDARIES = EVIDENCE_MARKERS + ((REGRESSED_MARKER, None),)

FENCE_MARKER = "```"
TILDE_FENCE_MARKER = "~~~"

# A deliberately weaker second reader, used only to answer one question the
# grammar cannot answer about itself: how much of this document did the grammar
# fail to claim? It is broader than TASK_LINE on purpose -- any bullet, any
# case, no trailing text required -- so the count can never fall below what the
# grammar claimed, and it keeps its own fence handling rather than sharing
# `_lines_outside_fences`, because a fence bug that hides tasks from the parser
# must not hide the same tasks from the counter as well.
SHALLOW_CHECKBOX = re.compile(r"^\s*[-*+]\s+\[[ xX]\](\s|$)")


def count_task_shaped_lines(markdown_text: str) -> int:
    """Lines already in task shape, whatever section they happen to sit in.

    A section becomes a track only by carrying a `**Scope:**` line, so a
    document written with correct `- [x] **0.1** text` lines under plain
    `## T1 - Foundation` headings parses as nothing at all. Counting these
    separately is what lets the gate tell that author the one line they are
    missing, instead of suggesting their file might not be a ledger.
    """
    total = 0
    for _, line in _lines_outside_fences(list(enumerate(markdown_text.splitlines(), start=1))):
        if TASK_LINE.match(line):
            total += 1
    return total


def count_checkbox_lines(markdown_text: str) -> int:
    """Every checkbox-looking line outside a fenced block."""
    total = 0
    open_marker = None
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if stripped.startswith(FENCE_MARKER):
            marker = FENCE_MARKER
        elif stripped.startswith(TILDE_FENCE_MARKER):
            marker = TILDE_FENCE_MARKER
        else:
            marker = None
        if marker is not None:
            if open_marker is None:
                open_marker = marker
            elif marker == open_marker:
                open_marker = None
            continue
        if open_marker is None and SHALLOW_CHECKBOX.match(line):
            total += 1
    return total
DONE_HEADING_PREFIX = "definition of done"
PLACEHOLDER_OPEN = "{{"
PLACEHOLDER_CLOSE = "}}"
PLACEHOLDER_BODY = re.compile(r"^[A-Za-z -]+$")


@dataclass
class Task:
    """One planned unit of work and whatever stands behind its tick.

    `evidence_kind` separates the two honest ways a box earns its tick.
    VERIFIED evidence names a command: a machine re-runs it, and a machine may
    untick the box when it stops passing. RECORDED evidence names something
    that happened and was witnessed -- a release published, a migration run, an
    install performed. Re-running it is not possible, so nothing re-runs it and
    no machine ever unticks it.

    The distinction exists because demanding a command for work that has none
    does not produce evidence, it produces a proxy that stands near the claim
    without proving it and passes forever either way.
    """

    task_id: str
    text: str
    done: bool
    evidence: Optional[str]
    line_number: int
    evidence_kind: Optional[str] = None


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


def _boundary_positions(text, markers):
    """Every occurrence of any marker outside an inline code span, in order.

    One scan for all markers, rather than one scan per marker. Scanning per
    marker can only ever report each one's first occurrence, and a span needs
    the next boundary of ANY kind, whichever that turns out to be.
    """
    found = []
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
        if open_run == 0:
            for marker, kind in markers:
                if text.startswith(marker, index):
                    found.append((index, len(marker), kind))
                    break
        index += 1
    return found


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


def _evidence_spans(block: str) -> List[Tuple[str, str]]:
    """Each evidence marker's own text, ending where the NEXT marker begins.

    A marker owns the text up to the next marker, never to the end of the
    block. Slicing to the end let a `**Verified:**` line holding prose absorb
    the `**Recorded:**` line beneath it, keep the VERIFIED kind, and offer the
    record's first backticked span as a command to run. The backticks in a
    record quote repository and product names, so that turned
    `felipeflorencio/claude-plugins` into something the shell was asked to
    execute, and unticked a true task when the shell could not find it.

    Every OCCURRENCE bounds the span before it, not merely the first of each
    marker. Bounding only the first left the same hole open one marker further
    along: a record, a blanked assertion and a second record put the last span
    back on a run to the end of the block. Fixing the shape that was reported
    rather than the class that produced it left the incident reproducible.
    """
    found = _boundary_positions(block, SPAN_BOUNDARIES)

    spans: List[Tuple[str, str]] = []
    for index, entry in enumerate(found):
        position, marker_length, kind = entry
        if kind is None:
            continue
        end = found[index + 1][0] if index + 1 < len(found) else len(block)
        spans.append((kind, block[position + marker_length : end]))
    return spans


def _apply_evidence(task: Task, block_lines: List[str]) -> Task:
    """Attach whichever evidence the task block carries, and its kind.

    A block carrying both is read as VERIFIED: a command that can be re-run is
    the stronger claim, and the record beside it loses nothing by being kept as
    prose. A `**Verified:**` marker with nothing behind it is not a claim at
    all, so it falls through to the record rather than standing in its way.
    """
    block = "\n".join(block_lines)
    by_kind: dict = {}
    for kind, span in _evidence_spans(block):
        cleaned = " ".join(span.split())
        if cleaned and kind not in by_kind:
            by_kind[kind] = cleaned
    for _, kind in EVIDENCE_MARKERS:
        evidence = by_kind.get(kind)
        if evidence:
            task.evidence = evidence
            task.evidence_kind = kind
            break

    first_line = block_lines[0] if block_lines else ""
    boundaries = _boundary_positions(first_line, SPAN_BOUNDARIES)
    if boundaries:
        first_line = first_line[: boundaries[0][0]]
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
                            "task {0} is ticked with nothing behind it. Add a "
                            "**Verified:** line naming the command that was "
                            "run, or a **Recorded:** line stating what "
                            "happened and when, or untick it.".format(task.task_id)
                        ),
                    )
                )
            elif task.done and is_unfilled_placeholder(task.evidence):
                problems.append(
                    Problem(
                        severity="error",
                        line_number=task.line_number,
                        message=(
                            "task {0} is ticked but its evidence line still "
                            "contains an unfilled {{{{ placeholder }}}}. Record the "
                            "command that was actually run, or what actually "
                            "happened, or untick it.".format(task.task_id)
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
