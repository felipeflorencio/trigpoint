from __future__ import annotations

import os
import pathlib
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import install_block


class InstallBlockTest(unittest.TestCase):
    def test_block_is_delimited(self) -> None:
        block = install_block.render_block("automatic")
        self.assertTrue(block.startswith("<!-- trigpoint:begin -->"))
        self.assertTrue(block.rstrip().endswith("<!-- trigpoint:end -->"))

    def test_block_states_the_mode(self) -> None:
        self.assertIn("Mode: automatic", install_block.render_block("automatic"))
        self.assertIn("Mode: manual", install_block.render_block("manual"))

    def test_block_carries_the_evidence_rule(self) -> None:
        block = install_block.render_block("automatic")
        self.assertIn("**Verified:**", block)
        self.assertIn("Never tick on assumption", block)

    def test_block_carries_both_evidence_kinds(self) -> None:
        """The block is the rule an agent reads inside the user's own repo.

        It once stated two incompatible rules at the same time: an older bullet
        demanding the command and its output, and a newer one describing the
        two kinds. Deleting either left the suite green.
        """
        block = install_block.render_block("automatic")
        self.assertIn("**Recorded:**", block)
        self.assertIn("re-run", block)
        self.assertNotIn("and its output", block)

    def test_block_never_demands_the_output_of_a_command(self) -> None:
        block = install_block.render_block("automatic")
        self.assertNotIn("what it printed", block)

    def test_block_carries_the_discovered_work_rule(self) -> None:
        self.assertIn("ADDED", install_block.render_block("automatic"))

    def test_appends_to_an_existing_file_preserving_content(self) -> None:
        result = install_block.upsert_block(
            "# Project\n\nExisting guidance.\n", install_block.render_block("automatic")
        )
        self.assertIn("Existing guidance.", result)
        self.assertIn("<!-- trigpoint:begin -->", result)

    def test_replaces_rather_than_stacking_on_reinstall(self) -> None:
        once = install_block.upsert_block("# Project\n", install_block.render_block("automatic"))
        twice = install_block.upsert_block(once, install_block.render_block("manual"))
        self.assertEqual(1, twice.count("<!-- trigpoint:begin -->"))
        self.assertIn("Mode: manual", twice)
        self.assertNotIn("Mode: automatic", twice)

    def test_is_idempotent_for_the_same_mode(self) -> None:
        once = install_block.upsert_block("# Project\n", install_block.render_block("automatic"))
        twice = install_block.upsert_block(once, install_block.render_block("automatic"))
        self.assertEqual(once, twice)

    def test_creates_the_file_when_absent(self) -> None:
        directory = pathlib.Path(tempfile.mkdtemp())
        target = directory / "CLAUDE.md"
        self.assertEqual(
            0, install_block.main(["--claude-md", str(target), "--mode", "automatic"])
        )
        self.assertIn("<!-- trigpoint:begin -->", target.read_text(encoding="utf-8"))

    def test_rejects_an_unknown_mode(self) -> None:
        with self.assertRaises(SystemExit):
            install_block.main(["--mode", "sometimes"])

    def test_orphan_begin_marker_with_user_content_survives_two_runs(self) -> None:
        directory = pathlib.Path(tempfile.mkdtemp())
        target = directory / "CLAUDE.md"
        distinctive_content = "DISTINCTIVE_USER_CONTENT_MARKER"
        orphan_initial = "<!-- trigpoint:begin -->\n" + distinctive_content + "\n"
        target.write_text(orphan_initial, encoding="utf-8")
        install_block.main(["--claude-md", str(target), "--mode", "automatic"])
        after_first = target.read_text(encoding="utf-8")
        self.assertIn(distinctive_content, after_first)
        install_block.main(["--claude-md", str(target), "--mode", "automatic"])
        after_second = target.read_text(encoding="utf-8")
        self.assertIn(distinctive_content, after_second)

    def test_crlf_file_preserves_line_endings(self) -> None:
        directory = pathlib.Path(tempfile.mkdtemp())
        target = directory / "CLAUDE.md"
        existing_crlf = "# Project\r\n\r\nExisting content.\r\n"
        with open(target, "w", encoding="utf-8", newline="") as file:
            file.write(existing_crlf)
        install_block.main(["--claude-md", str(target), "--mode", "automatic"])
        with open(target, "r", encoding="utf-8", newline="") as file:
            result = file.read()
        self.assertIn("\r\n", result)
        self.assertIn("Existing content.", result)
        lf_count = result.count("\n")
        crlf_count = result.count("\r\n")
        self.assertEqual(lf_count, crlf_count)

    def test_crlf_file_idempotent_for_the_same_mode(self) -> None:
        directory = pathlib.Path(tempfile.mkdtemp())
        target = directory / "CLAUDE.md"
        existing_crlf = "# Project\r\n\r\nExisting content.\r\n"
        with open(target, "w", encoding="utf-8", newline="") as file:
            file.write(existing_crlf)
        install_block.main(["--claude-md", str(target), "--mode", "automatic"])
        with open(target, "r", encoding="utf-8", newline="") as file:
            first_run = file.read()
        install_block.main(["--claude-md", str(target), "--mode", "automatic"])
        with open(target, "r", encoding="utf-8", newline="") as file:
            second_run = file.read()
        self.assertEqual(first_run, second_run)

    def test_file_permissions_are_preserved(self) -> None:
        directory = pathlib.Path(tempfile.mkdtemp())
        target = directory / "CLAUDE.md"
        target.write_text("# Project\n", encoding="utf-8")
        os.chmod(target, 0o644)
        mode_before = stat.S_IMODE(os.stat(target).st_mode)
        install_block.main(["--claude-md", str(target), "--mode", "automatic"])
        mode_after = stat.S_IMODE(os.stat(target).st_mode)
        self.assertEqual(0o644, mode_before)
        self.assertEqual(0o644, mode_after)

    def test_symlinked_claude_md_is_followed(self) -> None:
        directory = pathlib.Path(tempfile.mkdtemp())
        real_file = directory / "CLAUDE_real.md"
        symlink_path = directory / "CLAUDE.md"
        real_file.write_text("# Project\n", encoding="utf-8")
        os.symlink(real_file, symlink_path)
        install_block.main(["--claude-md", str(symlink_path), "--mode", "automatic"])
        self.assertTrue(os.path.islink(symlink_path))
        result_text = real_file.read_text(encoding="utf-8")
        self.assertIn("<!-- trigpoint:begin -->", result_text)

    def test_brand_new_file_creation_still_works(self) -> None:
        directory = pathlib.Path(tempfile.mkdtemp())
        target = directory / "CLAUDE.md"
        self.assertFalse(target.exists())
        install_block.main(["--claude-md", str(target), "--mode", "automatic"])
        self.assertTrue(target.exists())
        content = target.read_text(encoding="utf-8")
        self.assertIn("<!-- trigpoint:begin -->", content)


if __name__ == "__main__":
    unittest.main()
