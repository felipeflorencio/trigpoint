import subprocess
import unittest
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

import trigpoint_verify as verify
from trigpoint_ledger import parse_ledger, validate


TICKED = """# Example - Roadmap

## T1 - Foundation

**Scope:** The parser and its gate
**Blocked by:** nothing

- [x] **1.1** Write the ledger parser
      **Verified:** `python3 -m unittest tests.test_ledger_parse -v` -> `Ran 22 tests` /
      `OK`. 2026-08-26
- [x] **1.2** Write ledger validation
      **Verified:** `python3 -m unittest tests.test_ledger_validate` -> `OK`. 2026-08-26
"""

NO_EVIDENCE = """# Example - Roadmap

## T1 - Foundation

**Scope:** Work with nothing recorded
**Blocked by:** nothing

- [ ] **1.1** Not done yet
"""


class Result:
    """Stands in for a completed process."""

    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def runner_returning(code, output=""):
    return lambda *args, **kwargs: Result(code, output)


class RecordedCommandTests(unittest.TestCase):
    def test_reads_the_first_backticked_span_of_an_evidence_line(self):
        evidence = "`python3 -m unittest tests.test_ledger_parse -v` -> `Ran 22 tests` / `OK`. 2026-08-26"
        self.assertEqual(
            verify.recorded_command(evidence),
            "python3 -m unittest tests.test_ledger_parse -v",
        )

    def test_evidence_with_no_backticks_yields_no_command(self):
        self.assertIsNone(verify.recorded_command("I checked it by hand on Tuesday"))

    def test_missing_evidence_yields_no_command(self):
        self.assertIsNone(verify.recorded_command(None))

    def test_a_wrapped_evidence_line_still_yields_the_whole_command(self):
        ledger = parse_ledger(TICKED)
        task = ledger.tracks[0].tasks[0]
        self.assertEqual(
            verify.recorded_command(task.evidence),
            "python3 -m unittest tests.test_ledger_parse -v",
        )


class ApprovalTests(unittest.TestCase):
    def test_an_unseen_command_is_not_approved(self):
        self.assertFalse(verify.is_approved("rm -rf /", {}))

    def test_approval_is_remembered_by_hash_and_is_specific(self):
        approvals = verify.approve("python3 -m unittest tests.test_x", {})
        self.assertTrue(verify.is_approved("python3 -m unittest tests.test_x", approvals))
        self.assertFalse(verify.is_approved("python3 -m unittest tests.test_y", approvals))

    def test_approval_ignores_surrounding_whitespace_only(self):
        approvals = verify.approve("  make test  ", {})
        self.assertTrue(verify.is_approved("make test", approvals))


class RunTests(unittest.TestCase):
    def test_a_passing_command_reports_exit_zero(self):
        outcome = verify.run_command("true", ".", runner=runner_returning(0, "fine"))
        self.assertEqual(outcome.exit_code, 0)
        self.assertIn("fine", outcome.tail)

    def test_output_is_truncated_and_flattened_to_one_line(self):
        outcome = verify.run_command("true", ".", runner=runner_returning(0, "a\nb\n" + "x" * 900))
        self.assertLessEqual(len(outcome.tail), verify.TAIL_LIMIT)
        self.assertNotIn("\n", outcome.tail)

    def test_the_note_keeps_the_summary_rather_than_a_truncated_traceback(self):
        output = "Traceback...\n  File x\n    assert False\nRan 12 tests in 0.004s\nFAILED (failures=2)"
        outcome = verify.run_command("true", ".", runner=runner_returning(1, output))
        self.assertIn("FAILED (failures=2)", outcome.tail)
        self.assertIn("Ran 12 tests", outcome.tail)
        self.assertNotIn("Traceback", outcome.tail)

    def test_empty_output_is_not_a_crash(self):
        self.assertEqual(verify.run_command("true", ".", runner=runner_returning(1, "")).tail, "")

    def test_backticks_are_stripped_so_the_note_stays_readable(self):
        outcome = verify.run_command("true", ".", runner=runner_returning(1, "saw `weird` output"))
        self.assertNotIn("`", outcome.tail)

    def test_a_missing_shell_is_a_failure_rather_than_a_crash(self):
        def explode(*args, **kwargs):
            raise OSError("no shell here")

        outcome = verify.run_command("true", ".", runner=explode)
        self.assertNotEqual(outcome.exit_code, 0)


class RegressionTests(unittest.TestCase):
    def test_a_still_passing_check_changes_nothing(self):
        outcomes = {"1.1": verify.Outcome(0, "OK", "2026-08-27")}
        text, report = verify.apply_regressions(TICKED, outcomes)
        self.assertEqual(text, TICKED)
        self.assertIn("1.1 still passing", " ".join(report))

    def test_a_failing_check_unticks_the_box(self):
        outcomes = {"1.1": verify.Outcome(1, "2 tests failed", "2026-08-27")}
        text, _ = verify.apply_regressions(TICKED, outcomes)
        self.assertIn("- [ ] **1.1**", text)
        self.assertIn("- [x] **1.2**", text)

    def test_a_failing_check_records_why_without_erasing_the_original_evidence(self):
        outcomes = {"1.1": verify.Outcome(1, "2 tests failed", "2026-08-27")}
        text, _ = verify.apply_regressions(TICKED, outcomes)
        self.assertIn("**Regressed:**", text)
        self.assertIn("2 tests failed", text)
        self.assertIn("**Verified:**", text, "the original proof is history, not a lie")

    def test_the_regressed_note_matches_the_evidence_indentation(self):
        outcomes = {"1.1": verify.Outcome(1, "boom", "2026-08-27")}
        text, _ = verify.apply_regressions(TICKED, outcomes)
        line = [row for row in text.split("\n") if "**Regressed:**" in row][0]
        self.assertTrue(line.startswith("      "), "should sit in the task's own block")

    def test_the_result_still_parses_and_still_validates(self):
        outcomes = {"1.1": verify.Outcome(1, "boom", "2026-08-27")}
        text, _ = verify.apply_regressions(TICKED, outcomes)
        ledger = parse_ledger(text)
        task = ledger.tracks[0].tasks[0]
        self.assertFalse(task.done)
        errors = [p for p in validate(ledger) if p.severity == "error"]
        self.assertEqual(errors, [])

    def test_an_unknown_task_id_is_reported_and_the_rest_still_apply(self):
        outcomes = {
            "1.1": verify.Outcome(1, "boom", "2026-08-27"),
            "9.9": verify.Outcome(1, "boom", "2026-08-27"),
        }
        text, report = verify.apply_regressions(TICKED, outcomes)
        self.assertIn("- [ ] **1.1**", text)
        self.assertIn("9.9", " ".join(report))
        self.assertIn("not found", " ".join(report))

    def test_regressing_twice_does_not_stack_notes(self):
        outcomes = {"1.1": verify.Outcome(1, "boom", "2026-08-27")}
        once, _ = verify.apply_regressions(TICKED, outcomes)
        twice, _ = verify.apply_regressions(once, outcomes)
        self.assertEqual(once.count("**Regressed:**"), 1)
        self.assertEqual(twice.count("**Regressed:**"), 1)


class SelectionTests(unittest.TestCase):
    def test_only_ticked_tasks_carrying_a_command_are_selected(self):
        selected = verify.selectable(parse_ledger(TICKED))
        self.assertEqual(sorted(task.task_id for task, _ in selected), ["1.1", "1.2"])

    def test_a_task_with_no_evidence_is_not_selected(self):
        self.assertEqual(verify.selectable(parse_ledger(NO_EVIDENCE)), [])

    def test_an_unticked_task_is_never_re_run(self):
        unticked = TICKED.replace("- [x] **1.1**", "- [ ] **1.1**")
        selected = verify.selectable(parse_ledger(unticked))
        self.assertEqual([task.task_id for task, _ in selected], ["1.2"])


class CouldNotRunTests(unittest.TestCase):
    """A command Trigpoint failed to RUN says nothing about whether the claim is true.

    The tool only ever unticks, so a wrong untick corrupts the plan of record
    while a missed one merely delays a catch. That asymmetry means anything
    ambiguous must resolve to "leave it alone and say so".
    """

    def test_a_command_that_could_not_be_started_is_not_a_failure(self):
        def explode(*args, **kwargs):
            raise OSError("no shell here")

        outcome = verify.run_command("true", ".", runner=explode)
        self.assertEqual(outcome.status, verify.COULD_NOT_RUN)

    def test_a_timeout_is_not_a_failure(self):
        def hang(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="true", timeout=120)

        outcome = verify.run_command("true", ".", runner=hang)
        self.assertEqual(outcome.status, verify.COULD_NOT_RUN)

    def test_a_passing_command_is_passed(self):
        outcome = verify.run_command("true", ".", runner=runner_returning(0, "OK"))
        self.assertEqual(outcome.status, verify.PASSED)

    def test_a_non_zero_exit_is_a_failure(self):
        outcome = verify.run_command("true", ".", runner=runner_returning(1, "FAILED"))
        self.assertEqual(outcome.status, verify.FAILED)

    def test_a_command_that_could_not_run_leaves_the_box_ticked(self):
        outcomes = {"1.1": verify.Outcome(127, "no shell", "2026-08-27", verify.COULD_NOT_RUN)}
        text, _ = verify.apply_regressions(TICKED, outcomes)
        self.assertEqual(text, TICKED)

    def test_a_command_that_could_not_run_writes_no_regressed_note(self):
        outcomes = {"1.1": verify.Outcome(124, "timed out", "2026-08-27", verify.COULD_NOT_RUN)}
        text, _ = verify.apply_regressions(TICKED, outcomes)
        self.assertNotIn(verify.REGRESSED_MARKER, text)

    def test_a_command_that_could_not_run_is_reported_rather_than_passed_over(self):
        outcomes = {"1.1": verify.Outcome(127, "no shell", "2026-08-27", verify.COULD_NOT_RUN)}
        _, report = verify.apply_regressions(TICKED, outcomes)
        joined = " ".join(report)
        self.assertIn("1.1", joined)
        self.assertIn("could not be run", joined)
        self.assertNotIn("still passing", joined)

    def test_a_genuine_failure_alongside_one_that_could_not_run_still_unticks(self):
        outcomes = {
            "1.1": verify.Outcome(1, "2 tests failed", "2026-08-27", verify.FAILED),
            "1.2": verify.Outcome(127, "no shell", "2026-08-27", verify.COULD_NOT_RUN),
        }
        text, _ = verify.apply_regressions(TICKED, outcomes)
        self.assertIn("- [ ] **1.1**", text)
        self.assertIn("- [x] **1.2**", text)

    def test_an_outcome_built_without_a_status_still_reads_from_its_exit_code(self):
        self.assertEqual(verify.Outcome(0, "", "2026-08-27").status, verify.PASSED)
        self.assertEqual(verify.Outcome(1, "", "2026-08-27").status, verify.FAILED)


class EvidenceWithoutOutputTests(unittest.TestCase):
    """Evidence records the command, not what the command printed.

    Recorded output was never checked -- verification consults the exit code
    only -- so a ledger that displayed it was displaying a number nothing
    stood behind. `Ran 102 tests` sat in this repository's own gate long after
    the suite had grown past 200. The convention is now the command and the
    date, and these tests keep the shorter form first-class so nothing
    reintroduces a requirement to print output.
    """

    COMMAND_ONLY = """# Example - Roadmap

## T1 - Foundation

**Scope:** Evidence in the current convention
**Blocked by:** nothing

- [x] **1.1** Write the ledger parser
      **Verified:** `python3 -m unittest tests.test_ledger_parse -v`. 2026-08-26
"""

    def test_a_command_only_evidence_line_yields_the_command(self):
        evidence = "`python3 -m unittest tests.test_ledger_parse -v`. 2026-08-26"
        self.assertEqual(
            verify.recorded_command(evidence),
            "python3 -m unittest tests.test_ledger_parse -v",
        )

    def test_a_command_only_ledger_still_validates(self):
        ledger = parse_ledger(self.COMMAND_ONLY)
        errors = [problem for problem in validate(ledger) if problem.severity == "error"]
        self.assertEqual(errors, [])

    def test_a_command_only_task_is_still_selected_for_re_running(self):
        selected = verify.selectable(parse_ledger(self.COMMAND_ONLY))
        self.assertEqual(
            [command for _, command in selected],
            ["python3 -m unittest tests.test_ledger_parse -v"],
        )

    def test_the_older_arrow_form_is_still_read_correctly(self):
        ledger = parse_ledger(TICKED)
        errors = [problem for problem in validate(ledger) if problem.severity == "error"]
        self.assertEqual(errors, [])
        self.assertEqual(len(verify.selectable(ledger)), 2)
