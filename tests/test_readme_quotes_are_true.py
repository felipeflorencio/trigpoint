"""The README quotes this repository's own table and calls it verbatim.

It said "This is the current table from this repository, verbatim" above a
table reading 5 tracks and 19 tasks, while the ledger's real one read 6 tracks
and 36. A tool whose entire thesis is that hand-copied numbers drift was
shipping hand-copied numbers that had drifted, on the page where it makes that
argument.

Copying it correctly once is not the fix, because it will drift again the next
time a task is added. This test is the fix: the claim is now checked.
"""

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
BEGIN = "<!-- trigpoint:progress:begin -->"
END = "<!-- trigpoint:progress:end -->"


def region_of(path):
    text = (ROOT / path).read_text(encoding="utf-8")
    start = text.index(BEGIN)
    finish = text.index(END, start) + len(END)
    return text[start:finish].strip()


class ReadmeQuotesTheRealTableTests(unittest.TestCase):
    def test_the_table_the_readme_calls_verbatim_is_verbatim(self):
        self.assertEqual(region_of("README.md"), region_of("ROADMAP.md"))

    def test_the_readme_still_makes_the_claim_this_test_checks(self):
        """Guards the guard: if the sentence goes, so should this test."""
        self.assertIn("verbatim", (ROOT / "README.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
