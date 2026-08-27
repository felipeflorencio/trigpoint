"""Evidence is either an assertion a machine can re-run, or a record that it happened.

A gate that demands a re-runnable command for every ticked task cannot be
satisfied honestly by work that has no such command. "Published to a
marketplace" happened once, on a date, witnessed by a person. The only way to
tick it under the old rule was to invent a command that stands near the claim
without proving it -- a `curl` that shows a file still returns 200, which will
pass forever whether or not anyone ever published anything.

Manufactured evidence is precisely what this tool exists to prevent, so the
gate now accepts two kinds. `**Verified:**` carries a command, is re-run, and
can untick itself. `**Recorded:**` carries a witnessed fact, is never re-run,
and no machine may untick it.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

import trigpoint_verify as verify
from trigpoint_ledger import parse_ledger, validate


BOTH_KINDS = """# Example - Roadmap

## T1 - Foundation

**Scope:** One task of each evidence kind
**Blocked by:** nothing

- [x] **1.1** Write the ledger parser
      **Verified:** `python3 -m unittest tests.test_ledger_parse -v`. 2026-08-26
- [x] **1.2** Publish the plugin to a marketplace and install it from outside this checkout
      **Recorded:** Published to `felipeflorencio/claude-plugins`; `claude plugin update
      trigpoint` reported 0.1.0 to 0.2.0. 2026-08-27
"""

NEITHER_KIND = """# Example - Roadmap

## T1 - Foundation

**Scope:** A tick with nothing behind it
**Blocked by:** nothing

- [x] **1.1** Ticked with no evidence of any kind
"""


def task_by_id(markdown_text, task_id):
    ledger = parse_ledger(markdown_text)
    for track in ledger.tracks:
        for task in track.tasks:
            if task.task_id == task_id:
                return task
    raise AssertionError("no task {0}".format(task_id))


def errors_in(markdown_text):
    return [
        problem
        for problem in validate(parse_ledger(markdown_text))
        if problem.severity == "error"
    ]


class RecordedEvidenceParsingTests(unittest.TestCase):
    def test_a_recorded_line_is_read_as_evidence(self):
        task = task_by_id(BOTH_KINDS, "1.2")
        self.assertIsNotNone(task.evidence)
        self.assertIn("felipeflorencio/claude-plugins", task.evidence)

    def test_a_recorded_line_is_marked_as_a_record_not_an_assertion(self):
        self.assertEqual(task_by_id(BOTH_KINDS, "1.2").evidence_kind, "recorded")

    def test_a_verified_line_is_still_marked_as_an_assertion(self):
        self.assertEqual(task_by_id(BOTH_KINDS, "1.1").evidence_kind, "verified")

    def test_a_task_with_no_evidence_has_no_kind(self):
        self.assertIsNone(task_by_id(NEITHER_KIND, "1.1").evidence_kind)

    def test_the_recorded_marker_is_not_left_in_the_task_text(self):
        self.assertNotIn("Recorded:", task_by_id(BOTH_KINDS, "1.2").text)

    def test_a_description_quoting_the_marker_in_inline_code_is_not_evidence(self):
        quoted = NEITHER_KIND.replace(
            "Ticked with no evidence of any kind",
            "Explain that `**Recorded:**` means a witnessed fact",
        )
        self.assertIsNone(task_by_id(quoted, "1.1").evidence)


class RecordedEvidenceSatisfiesTheGateTests(unittest.TestCase):
    def test_a_recorded_tick_is_not_an_error(self):
        self.assertEqual(errors_in(BOTH_KINDS), [])

    def test_a_tick_with_neither_marker_is_still_an_error(self):
        problems = errors_in(NEITHER_KIND)
        self.assertEqual(len(problems), 1)
        self.assertIn("1.1", problems[0].message)

    def test_an_unfilled_placeholder_in_a_recorded_line_is_still_an_error(self):
        unfilled = BOTH_KINDS.replace(
            "Published to `felipeflorencio/claude-plugins`; `claude plugin update\n"
            "      trigpoint` reported 0.1.0 to 0.2.0.",
            "{{ what happened }}.",
        )
        self.assertEqual(len(errors_in(unfilled)), 1)


class RecordedEvidenceIsNeverReRunTests(unittest.TestCase):
    def test_only_the_verified_task_is_selected_for_re_running(self):
        selected = verify.selectable(parse_ledger(BOTH_KINDS))
        self.assertEqual([task.task_id for task, _ in selected], ["1.1"])

    def test_backticks_in_a_recorded_line_are_never_taken_as_a_command(self):
        commands = [command for _, command in verify.selectable(parse_ledger(BOTH_KINDS))]
        self.assertNotIn("felipeflorencio/claude-plugins", commands)

    def test_a_recorded_task_cannot_be_unticked_by_a_failing_outcome(self):
        outcomes = {"1.2": verify.Outcome(1, "boom", "2026-08-27", verify.FAILED)}
        text, report = verify.apply_regressions(BOTH_KINDS, outcomes)
        self.assertIn("- [x] **1.2**", text)
        self.assertNotIn(verify.REGRESSED_MARKER, text)
        self.assertIn("not found", " ".join(report))



RECORDED_ONLY = """# Example - Roadmap

## T1 - Foundation

**Scope:** One assertion, one record, one bare note
**Blocked by:** nothing

- [x] **1.1** Write the ledger parser
      **Verified:** `python3 -m unittest tests.test_ledger_parse -v`. 2026-08-26
- [x] **1.2** Publish the plugin to a marketplace
      **Recorded:** Published to `felipeflorencio/claude-plugins` and installed from
      there. 2026-08-27
- [x] **1.3** Agree the naming convention with the team
      **Verified:** agreed in review, no command to run. 2026-08-27
"""


class SessionStateCountsTests(unittest.TestCase):
    """The state an agent reads first must not overstate what is re-provable."""

    def setUp(self):
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "hooks"))
        import session_start

        self.state = session_start.build_state(RECORDED_ONLY)

    def test_only_the_assertion_counts_as_a_re_runnable_command(self):
        self.assertIn("1 carrying a re-runnable command", self.state)

    def test_the_record_is_counted_as_a_record(self):
        self.assertIn("1 recording something that happened", self.state)

    def test_the_bare_note_is_counted_separately(self):
        self.assertIn("1 resting on a written note only", self.state)


BOTH_MARKERS_IN_ONE_BLOCK = """# Example - Roadmap

## T1 - Publication

**Scope:** A task migrated from 0.2.0, keeping its old note beside a new record
**Blocked by:** nothing

- [x] **5.2** Publish the plugin to a marketplace
      **Verified:** reviewed by eye, nothing to re-run. 2026-08-27
      **Recorded:** Published to `felipeflorencio/claude-plugins`; `claude plugin update
      trigpoint` reported 0.2.0 to 0.3.0. 2026-08-27
"""

COMMAND_THEN_RECORD = """# Example - Roadmap

## T1 - Publication

**Scope:** A real assertion with a record kept beside it
**Blocked by:** nothing

- [x] **5.2** Ship the parser and publish it
      **Verified:** `python3 -m unittest tests.test_ledger_parse -v`. 2026-08-27
      **Recorded:** Published to `felipeflorencio/claude-plugins`. 2026-08-27
"""

BLANK_VERIFIED_THEN_RECORD = """# Example - Roadmap

## T1 - Publication

**Scope:** A blanked template line left above a real record
**Blocked by:** nothing

- [x] **5.2** Publish the plugin to a marketplace
      **Verified:**
      **Recorded:** Published to `felipeflorencio/claude-plugins`. 2026-08-27
"""


class EvidenceSpansStopAtTheNextMarkerTests(unittest.TestCase):
    """One marker must never swallow the next one's text.

    Evidence was sliced from its marker to the END of the task block, so a
    `**Verified:**` line holding prose absorbed the `**Recorded:**` line beneath
    it, kept the VERIFIED kind, and offered the record's first backticked span
    as a command to run. The backticks in a record quote repository and product
    names. Trigpoint selected `felipeflorencio/claude-plugins` as a shell
    command, and unticked a true task when the shell could not find it.

    That shape is not exotic: it is what a 0.2.0 ledger looks like halfway
    through migrating, and the parser's own docstring invites it.
    """

    def test_a_prose_assertion_never_borrows_a_command_from_the_record_below(self):
        selected = verify.selectable(parse_ledger(BOTH_MARKERS_IN_ONE_BLOCK))
        self.assertEqual(selected, [])

    def test_the_assertion_text_stops_where_the_record_begins(self):
        task = task_by_id(BOTH_MARKERS_IN_ONE_BLOCK, "5.2")
        self.assertNotIn("Recorded:", task.evidence)
        self.assertNotIn("felipeflorencio", task.evidence)

    def test_a_real_command_beside_a_record_still_runs_and_the_record_does_not(self):
        commands = [command for _, command in verify.selectable(parse_ledger(COMMAND_THEN_RECORD))]
        self.assertEqual(commands, ["python3 -m unittest tests.test_ledger_parse -v"])

    def test_an_empty_assertion_marker_falls_through_to_the_record(self):
        task = task_by_id(BLANK_VERIFIED_THEN_RECORD, "5.2")
        self.assertEqual(task.evidence_kind, "recorded")
        self.assertEqual(verify.selectable(parse_ledger(BLANK_VERIFIED_THEN_RECORD)), [])

    def test_a_block_carrying_both_is_still_read_as_an_assertion(self):
        self.assertEqual(task_by_id(COMMAND_THEN_RECORD, "5.2").evidence_kind, "verified")

    def test_the_task_text_is_cut_at_whichever_marker_comes_first(self):
        inline = BOTH_MARKERS_IN_ONE_BLOCK.replace(
            "- [x] **5.2** Publish the plugin to a marketplace\n"
            "      **Verified:** reviewed by eye, nothing to re-run. 2026-08-27\n",
            "- [x] **5.2** Publish it   **Recorded:** by hand `foo/bar`. 2026-08-27\n",
        )
        self.assertEqual(task_by_id(inline, "5.2").text, "Publish it")


class DashboardShowsWhichKindOfClaimTests(unittest.TestCase):
    """The dashboard is one of the three artefacts, and it flattened the difference.

    A re-proved command and a person's written word rendered as the same grey
    line. The whole point of the two kinds is that they are different strengths
    of claim, so a reader looking at the dashboard could not tell which claims a
    machine keeps honest and which rest on somebody's memory.
    """

    def rendered(self):
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
        from trigpoint_render import render_dashboard

        return render_dashboard(
            parse_ledger(BOTH_KINDS), "Example", "Two kinds of evidence", [], []
        )

    def test_an_assertion_and_a_record_are_not_rendered_identically(self):
        html = self.rendered()
        self.assertIn("evidence verified", html)
        self.assertIn("evidence recorded", html)

    def test_the_record_is_labelled_so_a_reader_knows_it_is_not_re_run(self):
        self.assertIn("not re-run", self.rendered())

    def test_both_evidence_texts_still_appear(self):
        html = self.rendered()
        self.assertIn("tests.test_ledger_parse", html)
        self.assertIn("felipeflorencio/claude-plugins", html)

THREE_MARKERS = """# Example - Roadmap

## T1 - Publication

**Scope:** A record, a blanked assertion, then another record
**Blocked by:** nothing

- [x] **1.1** Publish
      **Recorded:** marketplace entry added on 2026-08-26
      **Verified:**
      **Recorded:** published `felipeflorencio/claude-plugins` on 2026-08-27
"""

PROSE_THEN_TWO_RECORDS = """# Example - Roadmap

## T1 - Publication

**Scope:** A prose assertion followed by two records
**Blocked by:** nothing

- [x] **1.1** Publish
      **Verified:** reviewed by eye. 2026-08-26
      **Recorded:** first record, no backticks
      **Recorded:** second record naming `rm -rf /tmp/pwned`. 2026-08-27
"""

REGRESSED_BELOW_EVIDENCE = """# Example - Roadmap

## T1 - Foundation

**Scope:** A task carrying a regression note
**Blocked by:** nothing

- [x] **1.1** Build it
      **Verified:** `make test`. 2026-08-27
      **Regressed:** `make test` -> exit 1. `FAILED (failures=2)`. 2026-08-27
"""


class EveryMarkerBoundsTheSpanBeforeItTests(unittest.TestCase):
    """One occurrence of each marker is not enough to bound the spans.

    The first fix scanned for the FIRST `**Verified:**` and the FIRST
    `**Recorded:**`, so whichever came last still ran to the end of the block.
    A third marker after those two was absorbed exactly as before, and a task
    could still hand a record's backticked name to the shell. Fixing the shape
    that was reported rather than the class that produced it left the incident
    reproducible.
    """

    def test_a_third_marker_is_not_absorbed_by_the_second(self):
        self.assertEqual(verify.selectable(parse_ledger(THREE_MARKERS)), [])

    def test_that_block_is_read_as_a_record_not_an_assertion(self):
        self.assertEqual(task_by_id(THREE_MARKERS, "1.1").evidence_kind, "recorded")

    def test_no_evidence_string_ever_contains_a_marker(self):
        for ledger_text in (THREE_MARKERS, PROSE_THEN_TWO_RECORDS, BOTH_MARKERS_IN_ONE_BLOCK):
            evidence = task_by_id(ledger_text, "1.1" if "1.1" in ledger_text else "5.2").evidence
            self.assertNotIn("**Recorded:**", evidence)
            self.assertNotIn("**Verified:**", evidence)

    def test_a_prose_assertion_never_reaches_a_later_record(self):
        commands = [command for _, command in verify.selectable(parse_ledger(PROSE_THEN_TWO_RECORDS))]
        self.assertEqual(commands, [])

    def test_a_regression_note_does_not_leak_into_the_evidence_it_follows(self):
        task = task_by_id(REGRESSED_BELOW_EVIDENCE, "1.1")
        self.assertNotIn("Regressed", task.evidence)
        self.assertEqual(task.evidence, "`make test`. 2026-08-27")

    def test_the_command_is_still_read_when_a_regression_note_follows(self):
        commands = [command for _, command in verify.selectable(parse_ledger(REGRESSED_BELOW_EVIDENCE))]
        self.assertEqual(commands, ["make test"])

    def test_carriage_returns_do_not_reopen_the_hole(self):
        commands = [
            command
            for _, command in verify.selectable(parse_ledger(THREE_MARKERS.replace("\n", "\r\n")))
        ]
        self.assertEqual(commands, [])

    def test_a_marker_quoted_in_inline_code_still_bounds_nothing(self):
        quoted = REGRESSED_BELOW_EVIDENCE.replace(
            "- [x] **1.1** Build it",
            "- [x] **1.1** Explain that `**Recorded:**` is never re-run",
        )
        self.assertEqual(task_by_id(quoted, "1.1").evidence, "`make test`. 2026-08-27")


if __name__ == "__main__":
    unittest.main()
