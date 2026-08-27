"""The project root is where `.trigpoint/` is, not wherever the ledger sits.

`verify_ledger` took the repository root to be the ledger file's own directory.
That is true only because this repository keeps ROADMAP.md at its root, so
nothing in here could ever surface it. Anyone who keeps their ledger in `docs/`
got two failures at once:

- approvals were looked for in `docs/.trigpoint/`, which does not exist, so no
  command was ever approved and the verifier was silently inert forever while
  appearing to work;
- and once approved, every recorded command ran with `docs/` as its working
  directory, so a command that resolves from the repository root failed and
  unticked a TRUE task with a `**Regressed:**` note.

The second is a false untick, which is the one failure this design exists to
prevent. Found by running Trigpoint against a layout this repository does not
have, which is what roadmap item 6.5b is for.
"""

import os
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import trigpoint_verify as verify
from trigpoint_ledger import parse_ledger

NESTED = """# Nested - Roadmap

## T1 - Foundation

**Scope:** A ledger kept in docs/, not at the repository root
**Blocked by:** nothing

- [x] **1.1** Ship the thing
      **Verified:** `cat marker-at-repo-root.txt`. 2026-08-27
"""


class Project:
    """A repository whose ledger is in docs/ and whose state is at the root."""

    def __init__(self, ledger_subdirectory):
        self.root = tempfile.mkdtemp(prefix="trigpoint-layout-")
        os.makedirs(os.path.join(self.root, ".trigpoint"))
        directory = os.path.join(self.root, ledger_subdirectory) if ledger_subdirectory else self.root
        os.makedirs(directory, exist_ok=True)
        self.path = os.path.join(directory, "ROADMAP.md")
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(NESTED)
        with open(os.path.join(self.root, "marker-at-repo-root.txt"), "w", encoding="utf-8") as handle:
            handle.write("this file lives at the repository root\n")
        approvals = {}
        for _, command in verify.selectable(parse_ledger(NESTED)):
            approvals = verify.approve(command, approvals)
        verify.save_approvals(self.root, approvals)

    def read(self):
        with open(self.path, encoding="utf-8") as handle:
            return handle.read()

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


class LedgerInASubdirectoryTests(unittest.TestCase):
    def setUp(self):
        self.project = Project("docs")
        self.addCleanup(self.project.cleanup)

    def test_approvals_are_found_at_the_project_root(self):
        _, awaiting = verify.verify_ledger(self.project.path)
        self.assertEqual(awaiting, [])

    def test_commands_run_from_the_project_root_not_the_ledgers_directory(self):
        report, _ = verify.verify_ledger(self.project.path)
        self.assertIn("still passing", " ".join(report))

    def test_a_true_task_is_not_unticked_by_the_layout_alone(self):
        verify.verify_ledger(self.project.path)
        self.assertIn("- [x] **1.1**", self.project.read())
        self.assertNotIn(verify.REGRESSED_MARKER, self.project.read())


class LedgerAtTheRootStillWorksTests(unittest.TestCase):
    def setUp(self):
        self.project = Project("")
        self.addCleanup(self.project.cleanup)

    def test_approvals_are_still_found(self):
        _, awaiting = verify.verify_ledger(self.project.path)
        self.assertEqual(awaiting, [])

    def test_commands_still_run_from_the_root(self):
        report, _ = verify.verify_ledger(self.project.path)
        self.assertIn("still passing", " ".join(report))


class NoStateDirectoryAnywhereTests(unittest.TestCase):
    """Without `.trigpoint/` the ledger's own directory is the only sane guess."""

    def test_it_falls_back_to_the_ledgers_directory(self):
        directory = tempfile.mkdtemp(prefix="trigpoint-bare-")
        self.addCleanup(shutil.rmtree, directory, True)
        path = os.path.join(directory, "ROADMAP.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(NESTED)
        self.assertEqual(verify.project_root_for(path), directory)


if __name__ == "__main__":
    unittest.main()
