"""A checker that parsed nothing must never report a pass.

`check_drift.py` answered "no problems found", exit 0, for a file it had
understood as containing zero tasks. Success and silence were the same output,
so the gate was indistinguishable from a gate that was not running. The live
case is not a sabotaged parser: it is a user pointing the gate at a ROADMAP.md
they have not converted yet, getting a green light over a document nothing
read. `tests/fixtures/reference_ledger.md` is exactly that document, and it is
the regression test.
"""

import contextlib
import io
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_drift
from trigpoint_ledger import count_checkbox_lines

EMPTY = "# Nothing here\n\nNo tasks at all.\n"

HEALTHY = """# Example - Roadmap

## T1 - Foundation

**Scope:** One proven task
**Blocked by:** nothing

- [x] **1.1** Write the ledger parser
      **Verified:** `python3 -m unittest tests.test_ledger_parse -v`. 2026-08-26
"""


def run_gate(markdown_text):
    handle = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
    handle.write(markdown_text)
    handle.close()
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = check_drift.main([handle.name])
    return code, out.getvalue(), err.getvalue()


class NothingCheckedTests(unittest.TestCase):
    def test_a_file_with_no_tasks_does_not_report_success(self):
        _, out, _ = run_gate(EMPTY)
        self.assertNotIn("no problems found", out)

    def test_a_file_with_no_tasks_exits_with_its_own_code(self):
        code, _, _ = run_gate(EMPTY)
        self.assertEqual(code, check_drift.NOTHING_CHECKED)

    def test_the_nothing_checked_code_is_not_the_clean_code_nor_the_error_code(self):
        self.assertNotIn(check_drift.NOTHING_CHECKED, (0, 1, 2))

    def test_an_unconverted_document_full_of_checkboxes_is_not_reported_clean(self):
        reference = (ROOT / "tests/fixtures/reference_ledger.md").read_text(encoding="utf-8")
        code, out, _ = run_gate(reference)
        self.assertEqual(code, check_drift.NOTHING_CHECKED)
        self.assertNotIn("no problems found", out)

    def test_the_message_names_how_many_checkbox_lines_it_could_see(self):
        reference = (ROOT / "tests/fixtures/reference_ledger.md").read_text(encoding="utf-8")
        _, _, err = run_gate(reference)
        self.assertIn("33", err)

    def test_a_healthy_ledger_still_exits_zero_and_still_says_no_problems_found(self):
        code, out, _ = run_gate(HEALTHY)
        self.assertEqual(code, 0)
        self.assertIn("no problems found", out)

    def test_a_healthy_ledger_states_what_was_checked(self):
        _, out, _ = run_gate(HEALTHY)
        self.assertIn("1 task", out)
        self.assertIn("1 track", out)


class CheckboxCountingTests(unittest.TestCase):
    def test_it_counts_every_checkbox_line(self):
        self.assertEqual(count_checkbox_lines("- [ ] a\n- [x] b\n- [X] c\n"), 3)

    def test_it_ignores_checkboxes_inside_a_fenced_block(self):
        self.assertEqual(
            count_checkbox_lines("- [ ] real\n\n```\n- [ ] an example\n```\n"), 1)

    def test_it_ignores_checkboxes_inside_a_tilde_fence(self):
        self.assertEqual(
            count_checkbox_lines("- [ ] real\n\n~~~\n- [ ] an example\n~~~\n"), 1)

    def test_it_accepts_bullets_the_task_grammar_would_reject(self):
        self.assertEqual(count_checkbox_lines("* [ ] a\n+ [x] b\n- [ ]\n"), 3)

    def test_it_never_sees_less_than_the_grammar_claims(self):
        for name in ("ROADMAP.md", "skills/trigpoint/templates/ROADMAP.template.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            from trigpoint_ledger import parse_ledger
            ledger = parse_ledger(text)
            claimed = ledger.task_count + len(ledger.done_criteria)
            self.assertGreaterEqual(count_checkbox_lines(text), claimed, name)



sys.path.insert(0, str(ROOT / "hooks"))


class HooksSpeakUpWhenNothingParsedTests(unittest.TestCase):
    """The end of a turn is the worst moment for the tool to be quiet.

    Silence there reads as "all good" at precisely the moment an agent is about
    to claim it finished.
    """

    def test_session_start_warns_rather_than_stating_a_confident_zero(self):
        import session_start

        state = session_start.build_state(EMPTY)
        self.assertIn("WARNING", state)
        self.assertNotIn("0 of 0 tasks done", state)

    def test_session_start_names_the_checkbox_lines_it_could_see(self):
        import session_start

        reference = (ROOT / "tests/fixtures/reference_ledger.md").read_text(encoding="utf-8")
        self.assertIn("33", session_start.build_state(reference))

    def test_session_start_is_unchanged_for_a_healthy_ledger(self):
        import session_start

        state = session_start.build_state(HEALTHY)
        self.assertIn("1 of 1 tasks done", state)
        self.assertNotIn("WARNING", state)

    def test_the_stop_hook_reports_that_nothing_was_re_proved(self):
        import stop

        self.assertIn("zero tasks", stop.nothing_parsed_message(33))


class StopHookActuallySpeaksTests(unittest.TestCase):
    """The Stop hook must RUN its guard, not merely be able to phrase it.

    A test that calls the message helper proves the sentence exists. It does
    not prove the hook ever reaches it, and the hook is the half that matters:
    silence at the end of a turn is read as a clean ledger. Deleting the guard
    from `stop.main()` once left the whole suite green.
    """

    def run_stop_hook_on(self, markdown_text):
        directory = tempfile.mkdtemp(prefix="trigpoint-stop-")
        self.addCleanup(shutil.rmtree, directory, True)
        os.makedirs(os.path.join(directory, ".trigpoint"))
        with open(os.path.join(directory, "ROADMAP.md"), "w", encoding="utf-8") as handle:
            handle.write(markdown_text)
        return subprocess.run(
            [sys.executable, str(ROOT / "hooks" / "stop.py")],
            cwd=directory, capture_output=True, text=True, env=dict(os.environ),
        )

    def test_it_says_nothing_was_re_proved_when_the_ledger_parses_as_zero_tasks(self):
        finished = self.run_stop_hook_on(EMPTY)
        self.assertIn("zero tasks", finished.stdout)
        self.assertIn("NOTHING", finished.stdout)

    def test_it_names_the_checkbox_lines_it_could_see(self):
        reference = (ROOT / "tests/fixtures/reference_ledger.md").read_text(encoding="utf-8")
        self.assertIn("33", self.run_stop_hook_on(reference).stdout)

    def test_it_does_not_cry_zero_tasks_at_a_healthy_ledger(self):
        finished = self.run_stop_hook_on(HEALTHY)
        self.assertNotIn("zero tasks", finished.stdout)
        self.assertIn("never been approved", finished.stdout)


TRACK_WITHOUT_TASKS = """# Example - Roadmap

## T1 - Foundation

**Scope:** A track written before its tasks were broken out
**Blocked by:** nothing

## Definition of done

- [ ] 1. The suite passes.
"""


class TheDiagnosisMustBeTrueTests(unittest.TestCase):
    """Refusing to pass is right. Asserting a false reason for it is not.

    A ledger whose tracks parsed but whose tasks are not written yet was told
    "either this file is not a Trigpoint ledger, or the parser has stopped
    recognising it". Both alternatives are false, and stdout contradicted
    stderr one line apart: one track found, file may not be a ledger. The tool
    already holds the track count; it can tell the two cases apart.
    """

    def test_a_recognised_track_with_no_tasks_is_not_called_unrecognisable(self):
        _, _, err = run_gate(TRACK_WITHOUT_TASKS)
        self.assertNotIn("not a Trigpoint ledger", err)
        self.assertNotIn("stopped recognising", err)

    def test_it_says_instead_that_the_tracks_carry_no_tasks_yet(self):
        _, _, err = run_gate(TRACK_WITHOUT_TASKS)
        self.assertIn("no tasks", err)
        self.assertIn("1 track", err)

    def test_it_still_refuses_to_report_a_pass(self):
        code, out, _ = run_gate(TRACK_WITHOUT_TASKS)
        self.assertEqual(code, check_drift.NOTHING_CHECKED)
        self.assertNotIn("no problems found", out)

    def test_a_file_with_nothing_ledger_shaped_gets_the_unconverted_diagnosis(self):
        _, _, err = run_gate(PLAIN_CHECKLIST)
        self.assertIn("not a Trigpoint ledger", err)


class BrokenInstallIsDiagnosedTests(unittest.TestCase):
    """A half-updated `.trigpoint/` must not look like a failing ledger.

    The vendored copies are refreshed by hand. Copy the new `check_drift.py`
    beside a stale `trigpoint_ledger.py` and the import blows up with a raw
    traceback and exit 1 -- the code that means "your ledger has errors", so CI
    reports a broken install as a broken plan. Exit 2 already means "cannot
    read the ledger", which is what this is.
    """

    def run_against_stale_module(self):
        directory = tempfile.mkdtemp(prefix="trigpoint-stale-")
        self.addCleanup(shutil.rmtree, directory, True)
        shutil.copy(ROOT / "scripts/check_drift.py", directory)
        with open(os.path.join(directory, "trigpoint_ledger.py"), "w", encoding="utf-8") as handle:
            handle.write("# a 0.2.0 copy: no count_checkbox_lines here\n")
        with open(os.path.join(directory, "ROADMAP.md"), "w", encoding="utf-8") as handle:
            handle.write(HEALTHY)
        return subprocess.run(
            [sys.executable, os.path.join(directory, "check_drift.py"), "ROADMAP.md"],
            cwd=directory, capture_output=True, text=True,
        )

    def test_it_does_not_report_the_ledger_as_having_errors(self):
        self.assertNotEqual(self.run_against_stale_module().returncode, 1)

    def test_it_reports_an_unreadable_install_instead(self):
        self.assertEqual(self.run_against_stale_module().returncode, 2)

    def test_it_names_the_stale_copies_rather_than_printing_a_traceback(self):
        finished = self.run_against_stale_module()
        self.assertNotIn("Traceback", finished.stderr)
        self.assertIn(".trigpoint", finished.stderr)

PLAIN_CHECKLIST = """# Just a checklist

Some notes about the work.

- [ ] buy milk
- [x] feed the cat
- [ ] renew the domain
"""

TRACKS_WITHOUT_SCOPE = """# Achieve Grow - Roadmap

**The top-level reference of work.**

## T1 - Foundation

**Solved.** A fresh database used to fail Hibernate validation.

- [x] **0.1** Replace the initial schema with a curated baseline
- [x] **0.2** Set `ddl-auto=validate` in the dev profile

## T2 - Security

- [x] **1.1** Unify the Stripe property names
"""


class TheDiagnosisNamesTheActualMistakeTests(unittest.TestCase):
    """Say what is wrong with THIS file, not what the format is in general.

    Found by running the gate against real ledgers in other repositories on
    this machine, which is what roadmap item 6.5b asks for. Every one of them
    that came close used `## T1 - Foundation` headings and `- [x] **0.1**` task
    lines -- the correct visible shape -- and carried no `**Scope:**` line, so
    the grammar saw no tracks and therefore no tasks. One real file had 83
    checkbox lines and parsed as zero.

    Refusing to pass is right. Telling that author their file might not be a
    ledger, when it is one in every visible respect and is wrong by a single
    missing line, wastes the refusal.
    """

    def test_it_counts_the_lines_that_are_already_task_shaped(self):
        _, _, err = run_gate(TRACKS_WITHOUT_SCOPE)
        self.assertIn("3", err)
        self.assertIn("task-shaped", err)

    def test_it_names_the_missing_scope_line(self):
        _, _, err = run_gate(TRACKS_WITHOUT_SCOPE)
        self.assertIn("**Scope:**", err)

    def test_it_does_not_suggest_the_file_might_not_be_a_ledger(self):
        _, _, err = run_gate(TRACKS_WITHOUT_SCOPE)
        self.assertNotIn("not a Trigpoint ledger", err)

    def test_it_still_refuses_to_pass(self):
        code, out, _ = run_gate(TRACKS_WITHOUT_SCOPE)
        self.assertEqual(code, check_drift.NOTHING_CHECKED)
        self.assertNotIn("no problems found", out)

    def test_a_document_with_no_task_shaped_lines_keeps_the_general_diagnosis(self):
        _, _, err = run_gate(PLAIN_CHECKLIST)
        self.assertIn("not a Trigpoint ledger", err)
        self.assertNotIn("task-shaped", err)

    def test_the_pre_trigpoint_fixture_gets_the_specific_diagnosis(self):
        """23 of its 33 checkboxes are already task-shaped, so it is one line away."""
        reference = (ROOT / "tests/fixtures/reference_ledger.md").read_text(encoding="utf-8")
        _, _, err = run_gate(reference)
        self.assertIn("task-shaped", err)
        self.assertIn("**Scope:**", err)


DEEPER_HEADING = """# Example - Roadmap

### T1 - Foundation

**Scope:** written correctly, but under a level-three heading
**Blocked by:** nothing

- [x] **1.1** Ship it
      **Verified:** `true`. 2026-08-27
"""

HALF_CONVERTED = """# Example - Roadmap

## T1 - Foundation

**Scope:** a real track whose tasks are not written yet
**Blocked by:** nothing

## Backlog

- [ ] **2.1** Something not in any track
- [ ] **2.2** Another one
"""


class TheDiagnosisNamesTheRightMistakeTests(unittest.TestCase):
    """Telling an author to add a line they already added is worse than silence.

    A track heading must be exactly `##`. Someone using `###` writes a correct
    `**Scope:**` line, gets no tracks, and is told to add a `**Scope:**` line.
    Separately, once ANY track parses, the task-shaped count was computed and
    then thrown away, so a half-converted ledger heard nothing about the tasks
    sitting outside its tracks.
    """

    def test_a_deeper_heading_is_not_blamed_on_a_missing_scope_line(self):
        _, _, err = run_gate(DEEPER_HEADING)
        self.assertNotIn("Add that line to each track heading", err)

    def test_it_names_the_heading_level_instead(self):
        _, _, err = run_gate(DEEPER_HEADING)
        self.assertIn("##", err)
        self.assertIn("heading", err.lower())

    def test_a_half_converted_ledger_still_hears_about_its_loose_tasks(self):
        _, _, err = run_gate(HALF_CONVERTED)
        self.assertIn("2", err)
        self.assertIn("task-shaped", err)

    def test_both_still_refuse_to_pass(self):
        for markdown in (DEEPER_HEADING, HALF_CONVERTED):
            code, out, _ = run_gate(markdown)
            self.assertEqual(code, check_drift.NOTHING_CHECKED)
            self.assertNotIn("no problems found", out)


if __name__ == "__main__":
    unittest.main()
