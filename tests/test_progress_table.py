from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from trigpoint_ledger import parse_ledger
from trigpoint_render import render_progress_table, replace_marked_region

LEDGER = """# Example

## Progress at a glance

<!-- trigpoint:progress:begin -->
stale content that must be replaced
<!-- trigpoint:progress:end -->

## T1 Foundation

**Scope:** Make it boot
**Blocked by:** nothing

- [x] **1.1** One   **Verified:** `run` -> ok. 2026-08-27
- [ ] **1.2** Two

## T2 Security

**Scope:** Lock it down
**Blocked by:** T1

- [ ] **2.1** Three
"""


class ProgressTableTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = parse_ledger(LEDGER)
        self.table = render_progress_table(self.ledger)

    def test_one_row_per_track(self) -> None:
        self.assertIn("| **T1 Foundation** |", self.table)
        self.assertIn("| **T2 Security** |", self.table)

    def test_counts_are_computed_not_copied(self) -> None:
        rows = [line for line in self.table.splitlines() if line.startswith("| **T1")]
        self.assertIn("| 2 | 1 |", rows[0])

    def test_scope_and_blocked_by_are_carried_through(self) -> None:
        self.assertIn("Make it boot", self.table)
        self.assertIn("T1", self.table)

    def test_total_row_is_present(self) -> None:
        self.assertIn("| **Total** |", self.table)
        self.assertIn("| 3 | 1 |", self.table)

    def test_region_replacement_preserves_markers(self) -> None:
        replaced, found = replace_marked_region(LEDGER, "progress", self.table)
        self.assertTrue(found)
        self.assertIn("<!-- trigpoint:progress:begin -->", replaced)
        self.assertIn("<!-- trigpoint:progress:end -->", replaced)
        self.assertNotIn("stale content", replaced)

    def test_region_replacement_is_idempotent(self) -> None:
        once, _ = replace_marked_region(LEDGER, "progress", self.table)
        twice, _ = replace_marked_region(once, "progress", self.table)
        self.assertEqual(once, twice)

    def test_missing_region_reports_false_without_raising(self) -> None:
        replaced, found = replace_marked_region("# No markers here\n", "progress", "x")
        self.assertFalse(found)
        self.assertEqual("# No markers here\n", replaced)

    def test_content_outside_the_region_is_untouched(self) -> None:
        replaced, _ = replace_marked_region(LEDGER, "progress", self.table)
        self.assertIn("## T1 Foundation", replaced)
        self.assertIn("- [ ] **1.2** Two", replaced)

    def test_single_word_track_renders_without_duplication(self) -> None:
        single_word_ledger = """# Example

## Hygiene

**Scope:** Stay clean
**Blocked by:** nothing

- [x] **1.1** Task one   **Verified:** ok. 2026-08-27
"""
        ledger = parse_ledger(single_word_ledger)
        table = render_progress_table(ledger)
        self.assertIn("| **Hygiene** |", table)
        self.assertNotIn("| **Hygiene Hygiene** |", table)

    def test_two_word_track_still_renders_correctly(self) -> None:
        self.assertIn("| **T1 Foundation** |", self.table)
        self.assertNotIn("| **T1 T1** |", self.table)

    def test_numbered_heading_renders_without_duplication(self) -> None:
        numbered_ledger = """# Example

## 1. Foundation

**Scope:** Boot from clean
**Blocked by:** nothing

- [x] **1.1** Task one   **Verified:** ok. 2026-08-27
"""
        ledger = parse_ledger(numbered_ledger)
        table = render_progress_table(ledger)
        self.assertIn("| **1. Foundation** |", table)
        self.assertNotIn("| **1. Foundation 1. Foundation** |", table)

    def test_emoji_heading_renders_without_duplication(self) -> None:
        emoji_ledger = """# Example

## \U0001F680 Launch

**Scope:** Ship it
**Blocked by:** nothing

- [x] **1.1** Task one   **Verified:** ok. 2026-08-27
"""
        ledger = parse_ledger(emoji_ledger)
        table = render_progress_table(ledger)
        self.assertIn("| **\U0001F680 Launch** |", table)
        self.assertNotIn(
            "| **\U0001F680 Launch \U0001F680 Launch** |", table
        )


if __name__ == "__main__":
    unittest.main()
