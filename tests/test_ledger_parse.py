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

    def test_single_word_heading_yields_empty_name(self) -> None:
        ledger_text = """# Ledger

## Hygiene

**Scope:** Stay clean
**Blocked by:** nothing

- [ ] **1.1** Task one
"""
        ledger = parse_ledger(ledger_text)
        self.assertEqual(1, len(ledger.tracks))
        track = ledger.tracks[0]
        self.assertEqual("Hygiene", track.track_identifier)
        self.assertEqual("", track.name)

    def test_numbered_heading_yields_empty_name_not_a_duplicate(self) -> None:
        ledger_text = """# Ledger

## 1. Foundation

**Scope:** Boot from clean
**Blocked by:** nothing

- [ ] **1.1** Task one
"""
        ledger = parse_ledger(ledger_text)
        self.assertEqual(1, len(ledger.tracks))
        track = ledger.tracks[0]
        self.assertEqual("1. Foundation", track.track_identifier)
        self.assertEqual("", track.name)

    def test_emoji_heading_yields_empty_name_not_a_duplicate(self) -> None:
        ledger_text = """# Ledger

## \U0001F680 Launch

**Scope:** Ship it
**Blocked by:** nothing

- [ ] **1.1** Task one
"""
        ledger = parse_ledger(ledger_text)
        self.assertEqual(1, len(ledger.tracks))
        track = ledger.tracks[0]
        self.assertEqual("\U0001F680 Launch", track.track_identifier)
        self.assertEqual("", track.name)


class FencedCodeBlockTest(unittest.TestCase):
    """A fenced example is documentation, not work. It must not become a task."""

    def test_a_fenced_example_task_does_not_become_a_phantom_task(self) -> None:
        ledger = parse_ledger(
            "# Example\n\n## T1 Foundation\n\n"
            "**Scope:** s\n**Blocked by:** nothing\n\n"
            "The shape of a ticked task:\n\n"
            "```markdown\n"
            "- [x] **9.9** An illustrative example\n"
            "      **Verified:** `ls` -> listed. 2026-08-27\n"
            "```\n\n"
            "- [ ] **1.1** The only real task\n"
        )
        foundation = ledger.tracks[0]
        self.assertEqual(["1.1"], [task.task_id for task in foundation.tasks])
        self.assertEqual(1, foundation.task_count)
        self.assertEqual(0, foundation.done_count)

    def test_a_real_task_after_a_closed_fence_is_still_parsed(self) -> None:
        ledger = parse_ledger(
            "# Example\n\n## T1 Foundation\n\n"
            "**Scope:** s\n**Blocked by:** nothing\n\n"
            "- [ ] **1.1** Before the fence\n\n"
            "```\n"
            "- [x] **9.9** Fenced example\n"
            "```\n\n"
            "- [x] **1.2** After the fence   **Verified:** `ls` -> listed. 2026-08-27\n"
        )
        foundation = ledger.tracks[0]
        self.assertEqual(["1.1", "1.2"], [task.task_id for task in foundation.tasks])
        self.assertEqual(1, foundation.done_count)
        self.assertEqual(
            "`ls` -> listed. 2026-08-27", foundation.tasks[1].evidence
        )

    def test_an_unclosed_fence_swallows_the_rest_of_the_section(self) -> None:
        ledger = parse_ledger(
            "# Example\n\n## T1 Foundation\n\n"
            "**Scope:** s\n**Blocked by:** nothing\n\n"
            "- [ ] **1.1** Before the fence\n\n"
            "```\n"
            "- [x] **9.9** Never closed\n"
            "- [ ] **9.8** Still inside the fence\n"
        )
        foundation = ledger.tracks[0]
        self.assertEqual(["1.1"], [task.task_id for task in foundation.tasks])

    def test_a_fenced_checkbox_in_the_definition_of_done_is_ignored(self) -> None:
        ledger = parse_ledger(
            "# Example\n\n## Definition of done\n\n"
            "Criteria look like this:\n\n"
            "```markdown\n"
            "- [ ] 9. An illustrative criterion\n"
            "```\n\n"
            "- [ ] 1. The only real criterion\n"
        )
        self.assertEqual(
            ["1. The only real criterion"],
            [criterion.text for criterion in ledger.done_criteria],
        )

    def test_a_tilde_fenced_example_task_does_not_become_a_phantom_task(self) -> None:
        ledger = parse_ledger(
            "# Example\n\n## T1 Foundation\n\n"
            "**Scope:** s\n**Blocked by:** nothing\n\n"
            "The shape of a ticked task:\n\n"
            "~~~markdown\n"
            "- [x] **9.9** An illustrative example\n"
            "      **Verified:** `ls` -> listed. 2026-08-27\n"
            "~~~\n\n"
            "- [ ] **1.1** The only real task\n"
        )
        foundation = ledger.tracks[0]
        self.assertEqual(["1.1"], [task.task_id for task in foundation.tasks])
        self.assertEqual(1, foundation.task_count)
        self.assertEqual(0, foundation.done_count)

    def test_a_real_task_after_a_closed_tilde_fence_is_still_parsed(self) -> None:
        ledger = parse_ledger(
            "# Example\n\n## T1 Foundation\n\n"
            "**Scope:** s\n**Blocked by:** nothing\n\n"
            "- [ ] **1.1** Before the fence\n\n"
            "~~~\n"
            "- [x] **9.9** Fenced example\n"
            "~~~\n\n"
            "- [x] **1.2** After the fence   **Verified:** `ls` -> listed. 2026-08-27\n"
        )
        foundation = ledger.tracks[0]
        self.assertEqual(["1.1", "1.2"], [task.task_id for task in foundation.tasks])
        self.assertEqual(1, foundation.done_count)
        self.assertEqual(
            "`ls` -> listed. 2026-08-27", foundation.tasks[1].evidence
        )

    def test_a_backtick_fence_is_not_closed_by_a_tilde_fence(self) -> None:
        ledger = parse_ledger(
            "# Example\n\n## T1 Foundation\n\n"
            "**Scope:** s\n**Blocked by:** nothing\n\n"
            "- [ ] **1.1** Before the fence\n\n"
            "```\n"
            "~~~\n"
            "- [x] **9.9** Still fenced, the tilde line did not close it\n"
            "```\n\n"
            "- [x] **1.2** After the fence   **Verified:** `ls` -> listed. 2026-08-27\n"
        )
        foundation = ledger.tracks[0]
        self.assertEqual(["1.1", "1.2"], [task.task_id for task in foundation.tasks])


class FencedSectionHeadingTest(unittest.TestCase):
    """A heading inside a fence is an example of a heading, not a heading.

    A phantom track is worse than a phantom task: it adds a whole row to the
    generated progress table and a whole section to the dashboard, with counts
    attached to neither.
    """

    def test_a_fenced_track_heading_does_not_become_a_track(self) -> None:
        ledger = parse_ledger(
            "## T1 A\n\n"
            "**Scope:** s\n**Blocked by:** nothing\n\n"
            "```\n"
            "## T9 Phantom\n\n"
            "**Scope:** should not become a track\n"
            "**Blocked by:** nothing\n"
            "```\n\n"
            "- [ ] **1.1** Real\n"
        )
        self.assertEqual(["T1"], [track.track_identifier for track in ledger.tracks])
        self.assertEqual(1, ledger.task_count)

    def test_a_fenced_definition_of_done_does_not_open_a_second_one(self) -> None:
        ledger = parse_ledger(
            "## Definition of done\n\n"
            "The criteria are written like this:\n\n"
            "```markdown\n"
            "## Definition of done\n\n"
            "- [ ] 9. A phantom criterion\n"
            "```\n\n"
            "- [ ] 1. The only real criterion\n"
        )
        self.assertEqual(
            ["1. The only real criterion"],
            [criterion.text for criterion in ledger.done_criteria],
        )

    def test_a_real_heading_after_a_closed_fence_still_opens_its_section(self) -> None:
        ledger = parse_ledger(
            "## T1 A\n\n"
            "**Scope:** first\n**Blocked by:** nothing\n\n"
            "```\n"
            "## T9 Phantom\n"
            "```\n\n"
            "- [ ] **1.1** Real\n\n"
            "## T2 B\n\n"
            "**Scope:** second\n**Blocked by:** T1\n\n"
            "- [ ] **2.1** Also real\n"
        )
        self.assertEqual(
            ["T1", "T2"], [track.track_identifier for track in ledger.tracks]
        )
        self.assertEqual("second", ledger.tracks[1].scope)
        self.assertEqual("T1", ledger.tracks[1].blocked_by)
        self.assertEqual(2, ledger.task_count)

    def test_a_tilde_fenced_track_heading_does_not_become_a_track(self) -> None:
        ledger = parse_ledger(
            "## T1 A\n\n"
            "**Scope:** s\n**Blocked by:** nothing\n\n"
            "~~~\n"
            "## T9 Phantom\n\n"
            "**Scope:** should not become a track\n"
            "**Blocked by:** nothing\n"
            "~~~\n\n"
            "- [ ] **1.1** Real\n"
        )
        self.assertEqual(["T1"], [track.track_identifier for track in ledger.tracks])
        self.assertEqual(1, ledger.task_count)

    def test_an_unclosed_fence_swallows_every_later_section(self) -> None:
        ledger = parse_ledger(
            "## T1 A\n\n"
            "**Scope:** first\n**Blocked by:** nothing\n\n"
            "- [ ] **1.1** Real\n\n"
            "```\n"
            "## T2 B\n\n"
            "**Scope:** second\n**Blocked by:** nothing\n\n"
            "- [ ] **2.1** Never reached\n"
        )
        self.assertEqual(["T1"], [track.track_identifier for track in ledger.tracks])
        self.assertEqual(1, ledger.task_count)



class HardWrappedMetadataTest(unittest.TestCase):
    """A Scope or Blocked by line an author hard-wrapped across two physical
    source lines is one field, not a truncated one -- markdown's own rule for
    two lines with no blank line between them.
    """

    def test_a_hard_wrapped_scope_line_is_read_in_full(self) -> None:
        ledger = parse_ledger(
            "## T1 Foundation\n\n"
            "**Scope:** Make the whole system boot from a clean checkout with\n"
            "no manual setup steps required beforehand\n"
            "**Blocked by:** nothing\n\n"
            "- [ ] **1.1** Task\n"
        )
        self.assertEqual(
            "Make the whole system boot from a clean checkout with no manual "
            "setup steps required beforehand",
            ledger.tracks[0].scope,
        )

    def test_a_hard_wrapped_blocked_by_line_is_read_in_full(self) -> None:
        ledger = parse_ledger(
            "## T2 Security\n\n"
            "**Scope:** Credentials and authorization\n"
            "**Blocked by:** T1 and also every task in the foundation track that\n"
            "touches the database connection\n\n"
            "- [ ] **2.1** Task\n"
        )
        self.assertEqual(
            "T1 and also every task in the foundation track that touches the "
            "database connection",
            ledger.tracks[0].blocked_by,
        )

    def test_a_blank_line_after_scope_does_not_absorb_the_following_prose(
        self,
    ) -> None:
        ledger = parse_ledger(
            "## T1 Foundation\n\n"
            "**Scope:** short scope\n\n"
            "This paragraph must never become part of the scope text no matter\n"
            "what it says or how it is wrapped.\n\n"
            "**Blocked by:** nothing\n\n"
            "- [ ] **1.1** Task\n"
        )
        self.assertEqual("short scope", ledger.tracks[0].scope)
        self.assertEqual("nothing", ledger.tracks[0].blocked_by)

    def test_scope_immediately_followed_by_blocked_by_does_not_absorb_it(
        self,
    ) -> None:
        ledger = parse_ledger(
            "## T1 Foundation\n\n"
            "**Scope:** exactly this phrase\n"
            "**Blocked by:** T9\n\n"
            "- [ ] **1.1** Task\n"
        )
        self.assertEqual("exactly this phrase", ledger.tracks[0].scope)
        self.assertEqual("T9", ledger.tracks[0].blocked_by)

    def test_a_blank_marker_line_does_not_absorb_the_prose_after_it(self) -> None:
        # "**Scope:** " with a trailing space matches the pattern and captures
        # an empty-after-strip value. Continuation must never extend a value
        # that does not exist, so this section gets no scope at all -- which
        # means it is not recognised as a track, exactly as if the Scope line
        # were missing outright. A sibling track with a real Scope proves the
        # rest of the document still parses normally.
        ledger = parse_ledger(
            "## T1 Broken\n\n"
            "**Scope:** \n"
            "This prose has nothing to do with the scope and must never "
            "become one.\n"
            "**Blocked by:** nothing\n\n"
            "- [ ] **1.1** Task\n\n"
            "## T2 Fine\n\n"
            "**Scope:** A real scope\n"
            "**Blocked by:** nothing\n\n"
            "- [ ] **2.1** Task\n"
        )
        identifiers = [track.track_identifier for track in ledger.tracks]
        self.assertEqual(["T2"], identifiers)
        self.assertNotIn(
            "This prose has nothing to do with the scope and must never "
            "become one.",
            [track.scope for track in ledger.tracks],
        )

    def test_a_whitespace_only_marker_line_behaves_like_a_blank_one(self) -> None:
        ledger = parse_ledger(
            "## T1 Broken\n\n"
            "**Scope:**   \n"
            "Unrelated prose that must never become the scope.\n"
            "**Blocked by:** nothing\n\n"
            "- [ ] **1.1** Task\n\n"
            "## T2 Fine\n\n"
            "**Scope:** A real scope\n"
            "**Blocked by:** nothing\n\n"
            "- [ ] **2.1** Task\n"
        )
        identifiers = [track.track_identifier for track in ledger.tracks]
        self.assertEqual(["T2"], identifiers)

    def test_scope_with_content_stops_at_a_fence_and_absorbs_nothing_after(
        self,
    ) -> None:
        # Prose sits both inside the fence and right after it closes, with
        # no blank line anywhere in between. If fenced lines were simply
        # spliced out of the scan (as the section splitter used to do), the
        # post-fence prose would land immediately after the Scope line and
        # get absorbed. The fence delimiter has to stop the scan outright.
        ledger = parse_ledger(
            "## T1 Foundation\n\n"
            "**Scope:** Boot from a clean checkout\n"
            "```markdown\n"
            "some fenced content that must never be absorbed into the scope\n"
            "```\n"
            "and this trailing prose must never be absorbed either\n"
            "**Blocked by:** nothing\n\n"
            "- [ ] **1.1** Task\n"
        )
        self.assertEqual("Boot from a clean checkout", ledger.tracks[0].scope)
        self.assertEqual("nothing", ledger.tracks[0].blocked_by)
        self.assertEqual(1, ledger.tracks[0].task_count)

    def test_a_fenced_fake_scope_before_the_real_one_is_ignored(self) -> None:
        ledger = parse_ledger(
            "## T1 Foundation\n\n"
            "```markdown\n"
            "**Scope:** FAKE fenced scope that must never win\n"
            "```\n"
            "**Scope:** The real scope\n"
            "**Blocked by:** nothing\n\n"
            "- [ ] **1.1** Task\n"
        )
        self.assertEqual("The real scope", ledger.tracks[0].scope)

    def test_a_fenced_fake_blocked_by_between_two_real_fields_is_ignored(
        self,
    ) -> None:
        ledger = parse_ledger(
            "## T1 Foundation\n\n"
            "**Scope:** Real scope here\n"
            "```markdown\n"
            "**Blocked by:** FAKE blocked reason\n"
            "```\n"
            "**Blocked by:** T2\n\n"
            "- [ ] **1.1** Task\n"
        )
        self.assertEqual("Real scope here", ledger.tracks[0].scope)
        self.assertEqual("T2", ledger.tracks[0].blocked_by)

    def test_an_unclosed_fence_swallows_a_real_blocked_by_line(self) -> None:
        ledger = parse_ledger(
            "## T1 Foundation\n\n"
            "**Scope:** Real scope\n"
            "```markdown\n"
            "**Blocked by:** swallowed text that must not be returned\n"
        )
        self.assertEqual("Real scope", ledger.tracks[0].scope)
        self.assertEqual("", ledger.tracks[0].blocked_by)



class InlineCodeEvidenceTests(unittest.TestCase):
    """A task that quotes the evidence marker must not have evidence read from it.

    Found by re-running the commands this repository's own ledger records: task
    1.2 describes the rule using `**Verified:**` in backticks, and the evidence
    scan matched that occurrence rather than the real line below it. Validation
    passed throughout, because the field was non-empty - it was simply wrong.
    """

    LEDGER = """# Example - Roadmap

## T1 Parser

**Scope:** The parser
**Blocked by:** nothing

- [x] **1.1** Write validation: a ticked task with no `**Verified:**` line is an error, and
      an unknown `**Blocked by:**` reference is a warning
      **Verified:** `python3 -m unittest tests.test_ledger_validate -v` -> `OK`. 2026-08-26
"""

    def setUp(self):
        self.task = parse_ledger(self.LEDGER).tracks[0].tasks[0]

    def test_evidence_starts_at_the_real_marker(self):
        self.assertTrue(
            self.task.evidence.startswith("`python3 -m unittest"),
            "evidence was read from the quoted marker inside the description",
        )

    def test_the_description_keeps_its_quoted_marker(self):
        # text is the task's first line by design, so only the marker quoted
        # there is expected here.
        self.assertIn("`**Verified:**`", self.task.text)

    def test_the_description_stops_before_the_real_evidence(self):
        self.assertNotIn("python3 -m unittest", self.task.text)

    def test_a_quoted_marker_alone_is_not_evidence(self):
        ledger = parse_ledger(
            "# X\n\n## T1 One\n\n**Scope:** s\n**Blocked by:** nothing\n\n"
            "- [ ] **1.1** Mentions `**Verified:**` and nothing more\n"
        )
        self.assertIsNone(ledger.tracks[0].tasks[0].evidence)

if __name__ == "__main__":
    unittest.main()
