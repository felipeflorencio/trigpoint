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

    def test_placeholder_evidence_is_an_error(self) -> None:
        ledger = parse_ledger(
            build(
                "## T1 Foundation\n\n**Scope:** s\n**Blocked by:** nothing\n\n"
                "- [x] **1.1** Done\n"
                "      **Verified:** {{ the command that was run }} -> "
                "{{ what it printed }}. {{ YYYY-MM-DD }}\n"
            )
        )
        problems = validate(ledger)
        self.assertTrue(has_errors(problems))
        self.assertEqual(1, len(problems))
        self.assertEqual("error", problems[0].severity)
        self.assertIn("1.1", problems[0].message)
        self.assertIn("placeholder", problems[0].message)

    def test_real_evidence_containing_no_placeholder_still_passes(self) -> None:
        ledger = parse_ledger(
            build(
                "## T1 Foundation\n\n**Scope:** s\n**Blocked by:** nothing\n\n"
                "- [x] **1.1** Done\n"
                "      **Verified:** `./gradlew bootRun` -> started, validation "
                "passed. 2026-08-27\n"
            )
        )
        self.assertEqual([], validate(ledger))

    def test_a_lone_brace_pair_in_evidence_is_not_treated_as_a_placeholder(self) -> None:
        ledger = parse_ledger(
            build(
                "## T1 Foundation\n\n**Scope:** s\n**Blocked by:** nothing\n\n"
                "- [x] **1.1** Done   **Verified:** `jq .` -> printed {} and "
                "exited 0. 2026-08-27\n"
            )
        )
        self.assertEqual([], validate(ledger))

    def ticked_task_with_evidence(self, evidence: str) -> list:
        return validate(
            parse_ledger(
                build(
                    "## T1 Foundation\n\n**Scope:** s\n**Blocked by:** nothing\n\n"
                    "- [x] **1.1** Done   **Verified:** " + evidence + "\n"
                )
            )
        )

    def test_placeholder_of_letters_and_spaces_is_rejected(self) -> None:
        problems = self.ticked_task_with_evidence("{{ the command that was run }}")
        self.assertTrue(has_errors(problems))
        self.assertIn("placeholder", problems[0].message)

    def test_placeholder_of_a_short_phrase_is_rejected(self) -> None:
        problems = self.ticked_task_with_evidence("{{ what it printed }}")
        self.assertTrue(has_errors(problems))

    def test_placeholder_of_letters_and_hyphens_is_rejected(self) -> None:
        problems = self.ticked_task_with_evidence("{{ YYYY-MM-DD }}")
        self.assertTrue(has_errors(problems))

    def test_a_go_template_expression_in_evidence_is_accepted(self) -> None:
        self.assertEqual(
            [],
            self.ticked_task_with_evidence(
                "`go run main.go` -> template rendered `{{.Name}}` correctly. 2026-08-27"
            ),
        )

    def test_shell_brace_expansion_in_evidence_is_accepted(self) -> None:
        self.assertEqual(
            [],
            self.ticked_task_with_evidence(
                "`mkdir -p dir{{a,b},{c,d}}` -> created. 2026-08-27"
            ),
        )

    def test_a_dollar_variable_in_braces_is_accepted(self) -> None:
        self.assertEqual(
            [],
            self.ticked_task_with_evidence(
                "`envsubst` -> expanded `{{$VARIABLE}}`. 2026-08-27"
            ),
        )

    def test_a_placeholder_anywhere_in_the_evidence_is_rejected(self) -> None:
        problems = self.ticked_task_with_evidence(
            "`go run main.go` -> rendered `{{.Name}}`. {{ YYYY-MM-DD }}"
        )
        self.assertTrue(has_errors(problems))

    def test_a_fenced_example_carrying_placeholder_evidence_raises_no_error(self) -> None:
        ledger = parse_ledger(
            build(
                "## T1 Foundation\n\n**Scope:** s\n**Blocked by:** nothing\n\n"
                "The shape of a ticked task:\n\n"
                "```markdown\n"
                "- [x] **9.9** Example\n"
                "      **Verified:** {{ the command that was run }}. {{ YYYY-MM-DD }}\n"
                "```\n\n"
                "- [ ] **1.1** The only real task\n"
            )
        )
        self.assertEqual([], validate(ledger))

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
