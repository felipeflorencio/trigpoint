from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import check_drift


class CheckDriftTest(unittest.TestCase):
    def write_ledger(self, body: str) -> str:
        directory = tempfile.mkdtemp()
        path = pathlib.Path(directory) / "ROADMAP.md"
        path.write_text("# Example\n\n" + body, encoding="utf-8")
        return str(path)

    def test_clean_ledger_exits_zero(self) -> None:
        path = self.write_ledger(
            "## T1 Foundation\n\n**Scope:** s\n**Blocked by:** nothing\n\n"
            "- [ ] **1.1** Not done\n"
        )
        self.assertEqual(0, check_drift.main([path]))

    def test_ticked_without_evidence_exits_one(self) -> None:
        path = self.write_ledger(
            "## T1 Foundation\n\n**Scope:** s\n**Blocked by:** nothing\n\n"
            "- [x] **1.1** Done\n"
        )
        self.assertEqual(1, check_drift.main([path]))

    def test_warnings_alone_exit_zero(self) -> None:
        path = self.write_ledger(
            "## T1 Foundation\n\n**Scope:** s\n**Blocked by:** T9\n\n"
            "- [ ] **1.1** Not done\n"
        )
        self.assertEqual(0, check_drift.main([path]))

    def test_missing_file_exits_two(self) -> None:
        self.assertEqual(2, check_drift.main(["/nonexistent/ROADMAP.md"]))

    def test_unreadable_file_with_invalid_encoding_exits_two(self) -> None:
        directory = tempfile.mkdtemp()
        path = pathlib.Path(directory) / "ROADMAP.md"
        path.write_bytes(b"\xff\xfe\x00invalid")
        self.assertEqual(2, check_drift.main([str(path)]))

    def test_report_names_the_file_and_line(self) -> None:
        from trigpoint_ledger import Problem

        text = check_drift.report(
            [Problem("error", 42, "task 1.1 is ticked with no evidence")],
            "ROADMAP.md",
        )
        self.assertIn("ROADMAP.md:42", text)
        self.assertIn("ERROR", text)

    def test_report_is_explicit_when_clean(self) -> None:
        text = check_drift.report([], "ROADMAP.md")
        self.assertIn("no problems", text.lower())


if __name__ == "__main__":
    unittest.main()
