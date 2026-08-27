"""Lines must be counted and addressed by the SAME rule.

The parser numbers lines with `splitlines()`. `apply_regressions` addressed
them with `split("\\n")`. Those disagree on nine characters, so one of them
anywhere above a task shifted every line number after it and the wrong box got
edited: a genuinely failing task stayed ticked while a passing one was unticked
and stamped with a `**Regressed:**` note naming somebody else's command.

The trigger is ordinary. Pasted terminal output carries a bare `\\r`; text
copied out of many editors carries U+2028.

This is not "the carriage-return bug". Reading the ledger with `newline=""` was
added to stop CRLF being rewritten as LF, and it is what let the whole class
through, because the universal-newline read it replaced had been normalising
every one of these to `\\n` before the parser ever saw them. Fixing the
character that was reported rather than the rule that was broken is what turned
a cosmetic bug into a wrong untick.
"""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import trigpoint_verify as verify

# Every character `splitlines()` breaks on and `split("\n")` does not.
DIVERGENT = ["\r", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", " ", " "]


def ledger_with(character):
    return (
        "# R - Roadmap\n"
        "\n"
        "## T1 - Foundation\n"
        "\n"
        "**Scope:** one task carrying an odd character, then two real ones\n"
        "**Blocked by:** nothing\n"
        "\n"
        "- [x] **1.0** Import the catalogue\n"
        "      **Recorded:** the importer printed 8723/8723{0}done. 2026-08-01\n"
        "- [x] **1.1** Ship the parser\n"
        "      **Verified:** `false`. 2026-08-01\n"
        "- [x] **1.2** A completely true task\n"
        "      **Verified:** `true`. 2026-08-01\n"
    ).format(character)


class Failed:
    returncode = 1
    stdout = ""
    stderr = "boom"


class TheRightTaskIsUntickedTests(unittest.TestCase):
    def outcome_for(self, character):
        text = ledger_with(character)
        outcomes = {"1.1": verify.Outcome(1, "boom", "2026-08-27", verify.FAILED)}
        return verify.apply_regressions(text, outcomes)[0]

    def test_the_failing_task_is_the_one_unticked_whatever_the_line_break(self):
        for character in DIVERGENT:
            with self.subTest(character=repr(character)):
                updated = self.outcome_for(character)
                self.assertIn("- [ ] **1.1**", updated)

    def test_a_passing_task_is_never_unticked_by_a_line_break_elsewhere(self):
        for character in DIVERGENT:
            with self.subTest(character=repr(character)):
                updated = self.outcome_for(character)
                self.assertIn("- [x] **1.2**", updated)

    def test_the_regression_note_lands_under_the_task_it_belongs_to(self):
        for character in DIVERGENT:
            with self.subTest(character=repr(character)):
                updated = self.outcome_for(character)
                after_11 = updated.split("**1.1**", 1)[1].split("**1.2**", 1)[0]
                self.assertIn(verify.REGRESSED_MARKER, after_11)

    def test_every_other_byte_of_the_ledger_survives_untouched(self):
        for character in DIVERGENT:
            with self.subTest(character=repr(character)):
                original = ledger_with(character)
                updated = self.outcome_for(character)
                self.assertIn(character, updated)
                self.assertEqual(
                    original.count("\n"), updated.count("\n") - 1,
                    "only the inserted note should add a newline",
                )

    def test_windows_line_endings_are_still_preserved(self):
        original = ledger_with("\r").replace("\n", "\r\n")
        outcomes = {"1.1": verify.Outcome(1, "boom", "2026-08-27", verify.FAILED)}
        updated = verify.apply_regressions(original, outcomes)[0]
        self.assertIn("- [ ] **1.1**", updated)
        self.assertIn("- [x] **1.2**", updated)
        self.assertGreater(updated.count("\r\n"), 5)


if __name__ == "__main__":
    unittest.main()
