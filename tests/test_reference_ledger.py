from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from trigpoint_ledger import parse_ledger

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "reference_ledger.md"


class ReferenceLedgerTest(unittest.TestCase):
    """A synthetic ledger in the shape of a pre-Trigpoint document, parsed as-is.

    The fixture is fictional, not a copy of any real project: it predates the
    Scope and Blocked by metadata lines Trigpoint's format requires, so it is
    expected to yield zero tracks. That is the point: it proves the parser
    refuses to invent structure that is not there, and it is the fixture the
    migration note in the README is written against.
    """

    def setUp(self) -> None:
        self.ledger = parse_ledger(FIXTURE.read_text(encoding="utf-8"))

    def test_parsing_the_reference_does_not_raise(self) -> None:
        self.assertIsNotNone(self.ledger)

    def test_sections_without_scope_lines_are_not_tracks(self) -> None:
        self.assertEqual([], self.ledger.tracks)

    def test_definition_of_done_is_still_found(self) -> None:
        self.assertGreaterEqual(len(self.ledger.done_criteria), 10)
