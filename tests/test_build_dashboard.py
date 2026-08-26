from __future__ import annotations

import os
import pathlib
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import build_dashboard

WITH_MARKERS = """# Example

**Headline:** The two halves have never run together.

## Progress at a glance

<!-- trigpoint:progress:begin -->
stale
<!-- trigpoint:progress:end -->

## T1 Foundation

**Scope:** Make it boot
**Blocked by:** nothing

- [ ] **1.1** One
"""

WITHOUT_MARKERS = """# Example

## T1 Foundation

**Scope:** Make it boot
**Blocked by:** nothing

- [ ] **1.1** One
"""

TICKED_NO_EVIDENCE = """# Example

## T1 Foundation

**Scope:** Make it boot
**Blocked by:** nothing

- [x] **1.1** One
"""

EMPTY_HEADLINE = """# Example

**Headline:**

## T1 Foundation

**Scope:** Make it boot
**Blocked by:** nothing

- [ ] **1.1** One
"""

EMPTY_LANES_RUN = """# Example

**Headline:** Something happened.

**Lanes run:**

## T1 Foundation

**Scope:** Make it boot
**Blocked by:** nothing

- [ ] **1.1** One
"""

HARD_WRAPPED_HEADLINE = """# Example

**Headline:** The two halves of this system have never actually run together in
its entire recorded history.

## T1 Foundation

**Scope:** Make it boot
**Blocked by:** nothing

- [ ] **1.1** One
"""

HARD_WRAPPED_LANES_NOT_RUN = """# Example

**Headline:** Something happened.

**Lanes not run:** boot from clean, reachability, contract drift, honesty, secrets and authz,
test and CI reality, subtraction

## T1 Foundation

**Scope:** Make it boot
**Blocked by:** nothing

- [ ] **1.1** One
"""

BLANK_HEADLINE_WITH_PROSE = """# Example

**Headline:** 
This prose must never become the headline no matter what it says.

## T1 Foundation

**Scope:** Make it boot
**Blocked by:** nothing

- [ ] **1.1** One
"""

HEADLINE_THEN_FENCE = """# Example

**Headline:** The two halves of this system actually work together now.
```markdown
some fenced example text that must never leak into the rendered headline
```

## T1 Foundation

**Scope:** Make it boot
**Blocked by:** nothing

- [ ] **1.1** One
"""

FENCED_FAKE_HEADLINE_BEFORE_REAL = """# Example

```markdown
**Headline:** FAKE fenced headline that must never win
```
**Headline:** The real headline.

## T1 Foundation

**Scope:** Make it boot
**Blocked by:** nothing

- [ ] **1.1** One
"""

FENCED_FAKE_LANES_NOT_RUN = """# Example

**Headline:** Something happened.

```markdown
**Lanes not run:** fenced fake lane, another fenced fake lane
```
**Lanes not run:** boot from clean, reachability

## T1 Foundation

**Scope:** Make it boot
**Blocked by:** nothing

- [ ] **1.1** One
"""


class BuildDashboardTest(unittest.TestCase):
    def make(self, body: str):
        directory = pathlib.Path(tempfile.mkdtemp())
        ledger = directory / "ROADMAP.md"
        ledger.write_text(body, encoding="utf-8")
        return ledger, directory / "dashboard.html"

    def test_progress_table_is_rewritten_in_place(self) -> None:
        ledger, output = self.make(WITH_MARKERS)
        self.assertEqual(
            0, build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        )
        text = ledger.read_text(encoding="utf-8")
        self.assertNotIn("stale", text)
        self.assertIn("| **T1 Foundation** |", text)

    def test_html_is_written(self) -> None:
        ledger, output = self.make(WITH_MARKERS)
        build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        self.assertTrue(output.is_file())
        self.assertIn("T1 Foundation", output.read_text(encoding="utf-8"))

    def test_headline_is_taken_from_the_ledger(self) -> None:
        ledger, output = self.make(WITH_MARKERS)
        build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        self.assertIn("never run together", output.read_text(encoding="utf-8"))

    def test_missing_markers_still_writes_the_html(self) -> None:
        ledger, output = self.make(WITHOUT_MARKERS)
        exit_code = build_dashboard.main(
            ["--ledger", str(ledger), "--output", str(output)]
        )
        self.assertEqual(0, exit_code)
        self.assertTrue(output.is_file())

    def test_validation_errors_fail_the_run(self) -> None:
        ledger, output = self.make(TICKED_NO_EVIDENCE)
        self.assertEqual(
            1, build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        )

    def test_validation_errors_still_leave_the_html_written(self) -> None:
        ledger, output = self.make(TICKED_NO_EVIDENCE)
        build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        self.assertTrue(output.is_file())

    def test_running_twice_is_idempotent(self) -> None:
        ledger, output = self.make(WITH_MARKERS)
        build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        once = ledger.read_text(encoding="utf-8")
        build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        self.assertEqual(once, ledger.read_text(encoding="utf-8"))

    def test_missing_ledger_exits_two(self) -> None:
        self.assertEqual(2, build_dashboard.main(["--ledger", "/nope/ROADMAP.md"]))

    def test_empty_headline_line_falls_back_instead_of_swallowing_the_heading(
        self,
    ) -> None:
        ledger, output = self.make(EMPTY_HEADLINE)
        build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        text = output.read_text(encoding="utf-8")
        self.assertIn(
            '<p class="headline">No headline recorded in the ledger.</p>', text
        )
        self.assertNotIn("## T1 Foundation", text)

    def test_empty_lanes_run_line_claims_no_lanes(self) -> None:
        ledger, output = self.make(EMPTY_LANES_RUN)
        build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        text = output.read_text(encoding="utf-8")
        self.assertIn("Audit lanes run: none recorded.", text)

    def test_populated_headline_still_works(self) -> None:
        ledger, output = self.make(WITH_MARKERS)
        build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        text = output.read_text(encoding="utf-8")
        self.assertIn(
            '<p class="headline">The two halves have never run together.</p>', text
        )

    def test_a_hard_wrapped_headline_renders_in_full(self) -> None:
        ledger, output = self.make(HARD_WRAPPED_HEADLINE)
        build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        text = output.read_text(encoding="utf-8")
        self.assertIn(
            "The two halves of this system have never actually run together "
            "in its entire recorded history.",
            text,
        )

    def test_a_hard_wrapped_lanes_not_run_line_yields_every_lane(self) -> None:
        ledger, output = self.make(HARD_WRAPPED_LANES_NOT_RUN)
        build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        text = output.read_text(encoding="utf-8")
        self.assertIn(
            "boot from clean, reachability, contract drift, honesty, secrets "
            "and authz, test and CI reality, subtraction",
            text,
        )

    def test_a_blank_headline_line_does_not_absorb_the_prose_after_it(self) -> None:
        ledger, output = self.make(BLANK_HEADLINE_WITH_PROSE)
        build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        text = output.read_text(encoding="utf-8")
        self.assertIn(
            '<p class="headline">No headline recorded in the ledger.</p>', text
        )
        self.assertNotIn("This prose must never become the headline", text)

    def test_a_headline_stops_at_a_fence_with_no_backticks_in_the_output(
        self,
    ) -> None:
        ledger, output = self.make(HEADLINE_THEN_FENCE)
        build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        text = output.read_text(encoding="utf-8")
        self.assertIn(
            '<p class="headline">The two halves of this system actually work '
            'together now.</p>',
            text,
        )
        self.assertNotIn("`", text)

    def test_a_fenced_fake_headline_before_the_real_one_is_ignored(self) -> None:
        ledger, output = self.make(FENCED_FAKE_HEADLINE_BEFORE_REAL)
        build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        text = output.read_text(encoding="utf-8")
        self.assertIn(
            '<p class="headline">The real headline.</p>', text
        )
        self.assertNotIn("FAKE fenced headline", text)

    def test_a_fenced_fake_lanes_not_run_line_is_ignored(self) -> None:
        ledger, output = self.make(FENCED_FAKE_LANES_NOT_RUN)
        build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        text = output.read_text(encoding="utf-8")
        self.assertIn("boot from clean, reachability", text)
        self.assertNotIn("fenced fake lane", text)

    def test_writing_roadmap_at_mode_0644_leaves_it_at_0644(self) -> None:
        ledger, output = self.make(WITH_MARKERS)
        os.chmod(ledger, 0o644)
        mode_before = stat.S_IMODE(os.stat(ledger).st_mode)
        self.assertEqual(0o644, mode_before)
        build_dashboard.main(["--ledger", str(ledger), "--output", str(output)])
        mode_after = stat.S_IMODE(os.stat(ledger).st_mode)
        self.assertEqual(0o644, mode_after)
        # The write only replaces the file when the progress table actually
        # changed, so confirm the rewrite really happened rather than the
        # mode simply having never been touched.
        self.assertIn("| **T1 Foundation** |", ledger.read_text(encoding="utf-8"))

    def test_writing_through_a_symlinked_roadmap_keeps_the_symlink_intact(
        self,
    ) -> None:
        directory = pathlib.Path(tempfile.mkdtemp())
        real_file = directory / "ROADMAP_real.md"
        symlink_path = directory / "ROADMAP.md"
        real_file.write_text(WITH_MARKERS, encoding="utf-8")
        os.symlink(real_file, symlink_path)
        output = directory / "dashboard.html"

        exit_code = build_dashboard.main(
            ["--ledger", str(symlink_path), "--output", str(output)]
        )

        self.assertEqual(0, exit_code)
        self.assertTrue(os.path.islink(symlink_path))
        self.assertEqual(real_file.resolve(), symlink_path.resolve())
        real_text = real_file.read_text(encoding="utf-8")
        self.assertNotIn("stale", real_text)
        self.assertIn("| **T1 Foundation** |", real_text)


if __name__ == "__main__":
    unittest.main()
