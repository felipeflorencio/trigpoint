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


if __name__ == "__main__":
    unittest.main()


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
