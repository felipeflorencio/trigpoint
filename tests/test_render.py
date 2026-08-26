from __future__ import annotations

import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from trigpoint_ledger import parse_ledger
from trigpoint_render import render_dashboard

LEDGER = """# Example

## T1 Foundation

**Scope:** Make it boot
**Blocked by:** nothing

- [x] **1.1** One   **Verified:** `run` -> ok. 2026-08-27
- [ ] **1.2** Two & three <script>alert(1)</script>

## Definition of done

- [ ] 1. A fresh clone boots
"""


class RenderDashboardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.html = render_dashboard(
            parse_ledger(LEDGER),
            title="Example",
            headline="The two halves have never run together.",
            lanes_run=["boot", "reachability"],
            lanes_skipped=["honesty"],
        )

    def test_headline_leads_the_page(self) -> None:
        body_start = self.html.index("<body")
        self.assertLess(
            self.html.index("never run together"),
            self.html.index("T1 Foundation"),
        )
        self.assertGreater(self.html.index("never run together"), body_start)

    def test_every_task_is_listed_not_a_highlight_reel(self) -> None:
        self.assertIn('<span class="task-id">1.1</span>', self.html)
        self.assertIn('<span class="task-id">1.2</span>', self.html)
        body_after_style = self.html.split("</style>", 1)[1]
        self.assertIn('<span class="task-id">1.1</span>', body_after_style)
        self.assertIn('<span class="task-id">1.2</span>', body_after_style)

    def test_task_text_is_escaped(self) -> None:
        self.assertNotIn("<script>alert(1)</script>", self.html)
        self.assertIn("&lt;script&gt;", self.html)
        self.assertIn("&amp;", self.html)

    def test_lanes_run_and_skipped_are_both_stated(self) -> None:
        self.assertIn("honesty", self.html)
        self.assertIn("reachability", self.html)

    def test_definition_of_done_is_rendered(self) -> None:
        self.assertIn("A fresh clone boots", self.html)

    def test_page_is_self_contained(self) -> None:
        for forbidden in ("<script src=", 'href="http', "@import url(http"):
            self.assertNotIn(forbidden, self.html)

    def test_page_is_theme_aware(self) -> None:
        self.assertIn("prefers-color-scheme: dark", self.html)
        self.assertIn('data-theme="dark"', self.html)

    def test_counts_come_from_the_ledger(self) -> None:
        self.assertIsNotNone(re.search(r"\b1\s*/\s*2\b", self.html))

    def test_title_is_set(self) -> None:
        self.assertIn("<title>Example", self.html)

    def test_single_word_track_heading_renders_once(self) -> None:
        single_word_ledger = """# Example

## Hygiene

**Scope:** Stay clean
**Blocked by:** nothing

- [x] **1.1** Task one   **Verified:** ok. 2026-08-27
"""
        html = render_dashboard(
            parse_ledger(single_word_ledger),
            title="Example",
            headline="Test",
            lanes_run=[],
            lanes_skipped=[],
        )
        heading_match = re.search(r"<h2>([^<]*Hygiene[^<]*)</h2>", html)
        self.assertIsNotNone(heading_match)
        heading_text = heading_match.group(1)
        self.assertEqual(1, heading_text.count("Hygiene"))

    def test_two_word_track_heading_renders_correctly(self) -> None:
        heading_match = re.search(r"<h2>([^<]*T1[^<]*Foundation[^<]*)</h2>", self.html)
        self.assertIsNotNone(heading_match)
        heading_text = heading_match.group(1)
        self.assertIn("T1", heading_text)
        self.assertIn("Foundation", heading_text)
        self.assertEqual(1, heading_text.count("T1"))

    def test_numbered_heading_renders_once_in_the_h2(self) -> None:
        numbered_ledger = """# Example

## 1. Foundation

**Scope:** Boot from clean
**Blocked by:** nothing

- [x] **1.1** Task one   **Verified:** ok. 2026-08-27
"""
        html = render_dashboard(
            parse_ledger(numbered_ledger),
            title="Example",
            headline="Test",
            lanes_run=[],
            lanes_skipped=[],
        )
        heading_match = re.search(r"<h2>([^<]*)</h2>", html)
        self.assertIsNotNone(heading_match)
        heading_text = heading_match.group(1)
        self.assertEqual("1. Foundation", heading_text)
        self.assertEqual(1, heading_text.count("Foundation"))

    def test_emoji_heading_renders_once_in_the_h2(self) -> None:
        emoji_ledger = """# Example

## \U0001F680 Launch

**Scope:** Ship it
**Blocked by:** nothing

- [x] **1.1** Task one   **Verified:** ok. 2026-08-27
"""
        html = render_dashboard(
            parse_ledger(emoji_ledger),
            title="Example",
            headline="Test",
            lanes_run=[],
            lanes_skipped=[],
        )
        heading_match = re.search(r"<h2>([^<]*)</h2>", html)
        self.assertIsNotNone(heading_match)
        heading_text = heading_match.group(1)
        self.assertEqual("\U0001F680 Launch", heading_text)
        self.assertEqual(1, heading_text.count("Launch"))


if __name__ == "__main__":
    unittest.main()
