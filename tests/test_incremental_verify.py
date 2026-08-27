"""A pass that is cut short must keep what it already established.

`verify_ledger` collected every outcome into a dict and wrote the ledger once,
at the end. The Stop hook that calls it has a 180-second budget (hooks.json).
A pass that ran past the budget was killed with the dict still in memory: every
regression it had already detected was discarded, nothing was written, and
nothing was printed. Silence at the end of a turn reads as a clean ledger, so
the one place the tool actively said "your plan is fine" while holding proof
that it was not, was a pass that took too long.

This is not a speed problem. Sub-second commands here hide it; `npm test`
across sixty tasks in someone else's repository does not.
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

TWO_FAILING = """# Example - Roadmap

## T1 - Foundation

**Scope:** Two independent proofs
**Blocked by:** nothing

- [x] **1.1** First task
      **Verified:** `first-command`. 2026-08-26
- [x] **1.2** Second task
      **Verified:** `second-command`. 2026-08-26
"""

SAME_COMMAND_TWICE = """# Example - Roadmap

## T1 - Foundation

**Scope:** One command standing behind two tasks
**Blocked by:** nothing

- [x] **1.1** First task
      **Verified:** `the-only-command`. 2026-08-26
- [x] **1.2** Second task
      **Verified:** `the-only-command`. 2026-08-26
"""


class Failed:
    returncode = 1
    stdout = ""
    stderr = "no"


class LedgerOnDisk:
    def __init__(self, markdown_text):
        self.directory = tempfile.mkdtemp(prefix="trigpoint-incremental-")
        self.path = os.path.join(self.directory, "ROADMAP.md")
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(markdown_text)
        approvals = {}
        for _, command in verify.selectable(parse_ledger(markdown_text)):
            approvals = verify.approve(command, approvals)
        verify.save_approvals(self.directory, approvals)

    def read(self):
        with open(self.path, encoding="utf-8") as handle:
            return handle.read()

    def cleanup(self):
        shutil.rmtree(self.directory, ignore_errors=True)


class IncrementalWriteTests(unittest.TestCase):
    def setUp(self):
        self.ledger = LedgerOnDisk(TWO_FAILING)
        self.addCleanup(self.ledger.cleanup)

    def test_the_first_regression_is_on_disk_before_the_second_command_runs(self):
        seen = []

        def runner(command, **kwargs):
            seen.append(self.ledger.read())
            return Failed()

        verify.verify_ledger(self.ledger.path, runner=runner)
        self.assertEqual(len(seen), 2)
        self.assertIn("- [ ] **1.1**", seen[1])

    def test_a_pass_killed_after_the_first_command_still_recorded_it(self):
        class Killed(Exception):
            pass

        calls = []

        def runner(command, **kwargs):
            calls.append(command)
            if len(calls) > 1:
                raise Killed()
            return Failed()

        with self.assertRaises(Killed):
            verify.verify_ledger(self.ledger.path, runner=runner)

        surviving = self.ledger.read()
        self.assertIn("- [ ] **1.1**", surviving)
        self.assertIn(verify.REGRESSED_MARKER, surviving)

    def test_both_regressions_land_when_the_pass_completes(self):
        verify.verify_ledger(self.ledger.path, runner=lambda *a, **k: Failed())
        finished = self.ledger.read()
        self.assertIn("- [ ] **1.1**", finished)
        self.assertIn("- [ ] **1.2**", finished)

    def test_a_passing_pass_leaves_the_ledger_untouched(self):
        class Passed:
            returncode = 0
            stdout = "OK"
            stderr = ""

        before = self.ledger.read()
        verify.verify_ledger(self.ledger.path, runner=lambda *a, **k: Passed())
        self.assertEqual(self.ledger.read(), before)


class DeduplicationTests(unittest.TestCase):
    def setUp(self):
        self.ledger = LedgerOnDisk(SAME_COMMAND_TWICE)
        self.addCleanup(self.ledger.cleanup)

    def test_one_command_behind_two_tasks_runs_once(self):
        calls = []

        def runner(command, **kwargs):
            calls.append(command)
            return Failed()

        verify.verify_ledger(self.ledger.path, runner=runner)
        self.assertEqual(calls, ["the-only-command"])

    def test_its_outcome_still_reaches_every_task_that_recorded_it(self):
        verify.verify_ledger(self.ledger.path, runner=lambda *a, **k: Failed())
        finished = self.ledger.read()
        self.assertIn("- [ ] **1.1**", finished)
        self.assertIn("- [ ] **1.2**", finished)



class AtomicWriteTests(unittest.TestCase):
    """A plan of record must never be left half-written.

    Writing with `open(path, "w")` truncates before a byte is written. Applying
    each regression as it is found multiplies how often the process sits inside
    that window, and it does so on precisely the path the Stop hook's
    180-second budget kills. A crash, a full disk or a read-only checkout
    landing there leaves the user with a ledger cut in half, which is a worse
    outcome than the silent discard this change removed.

    `scripts/install_block.py` already writes through a temporary file and
    `os.replace`. So does this now.
    """

    def setUp(self):
        self.ledger = LedgerOnDisk(TWO_FAILING)
        self.addCleanup(self.ledger.cleanup)

    def test_a_write_that_fails_leaves_the_previous_ledger_intact(self):
        import builtins

        before = self.ledger.read()
        real_open = builtins.open

        def explode_on_write(*args, **kwargs):
            mode = kwargs.get("mode", args[1] if len(args) > 1 else "r")
            if "w" in mode:
                raise OSError("No space left on device")
            return real_open(*args, **kwargs)

        original_named = verify.tempfile.NamedTemporaryFile

        def failing_named(*args, **kwargs):
            raise OSError("No space left on device")

        verify.tempfile.NamedTemporaryFile = failing_named
        self.addCleanup(setattr, verify.tempfile, "NamedTemporaryFile", original_named)

        with self.assertRaises(OSError):
            verify.verify_ledger(self.ledger.path, runner=lambda *a, **k: Failed())

        self.assertEqual(self.ledger.read(), before)

    def test_no_temporary_file_is_left_behind_after_a_successful_pass(self):
        verify.verify_ledger(self.ledger.path, runner=lambda *a, **k: Failed())
        leftovers = [
            name
            for name in os.listdir(self.ledger.directory)
            if name != "ROADMAP.md" and name != ".trigpoint"
        ]
        self.assertEqual(leftovers, [])

    def test_the_ledger_is_never_observed_empty_while_being_rewritten(self):
        sizes = []

        def runner(command, **kwargs):
            sizes.append(os.path.getsize(self.ledger.path))
            return Failed()

        verify.verify_ledger(self.ledger.path, runner=runner)
        self.assertTrue(all(size > 0 for size in sizes), sizes)


class TheWritePreservesWhatItFoundTests(unittest.TestCase):
    """Writing atomically is not enough; it must write the same file, the same way.

    `scripts/build_dashboard.py` and `scripts/install_block.py` both resolve the
    target through a symlink and carry the existing permission bits over before
    replacing. The first attempt here copied neither, so a symlinked ROADMAP.md
    was replaced by a regular file and the regression never reached the real
    ledger, and a 0644 ledger silently became 0600. `open(path, "w")`, the thing
    it replaced, got both of those right.
    """

    def setUp(self):
        self.ledger = LedgerOnDisk(TWO_FAILING)
        self.addCleanup(self.ledger.cleanup)

    def test_a_symlinked_ledger_is_written_through_not_replaced(self):
        real = os.path.join(self.ledger.directory, "real-roadmap.md")
        os.rename(self.ledger.path, real)
        os.symlink(real, self.ledger.path)

        verify.verify_ledger(self.ledger.path, runner=lambda *a, **k: Failed())

        self.assertTrue(os.path.islink(self.ledger.path), "the symlink was replaced")
        with open(real, encoding="utf-8") as handle:
            self.assertIn("- [ ] **1.1**", handle.read())

    def test_the_ledgers_permissions_survive_a_regression(self):
        os.chmod(self.ledger.path, 0o644)
        verify.verify_ledger(self.ledger.path, runner=lambda *a, **k: Failed())
        self.assertEqual(os.stat(self.ledger.path).st_mode & 0o777, 0o644)

    def test_carriage_returns_are_not_silently_converted(self):
        with open(self.ledger.path, "r", encoding="utf-8", newline="") as handle:
            original = handle.read()
        with open(self.ledger.path, "w", encoding="utf-8", newline="") as handle:
            handle.write(original.replace("\n", "\r\n"))

        verify.verify_ledger(self.ledger.path, runner=lambda *a, **k: Failed())

        with open(self.ledger.path, "r", encoding="utf-8", newline="") as handle:
            after = handle.read()
        self.assertGreater(after.count("\r\n"), 0, "CRLF endings were rewritten as LF")


if __name__ == "__main__":
    unittest.main()
