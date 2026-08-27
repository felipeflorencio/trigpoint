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
import pathlib
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


if __name__ == "__main__":
    unittest.main()


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
