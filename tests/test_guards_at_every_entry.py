"""Every entry point must locate the project the same way and honour the same guards.

Each of these is the same mistake in a different place: a rule enforced where
it was first needed rather than at the boundary it protects.

- `--approve` hardcoded the root as ".", so approving from a subdirectory wrote
  a stray `.trigpoint/` there. The approval landed where nothing reads it, and
  worse, the hooks stop at the FIRST ancestor holding `.trigpoint/`, find no
  ledger, and go permanently silent for that whole subtree. Silence is
  indistinguishable from a clean ledger.
- The hooks required ROADMAP.md at the state root, so the `docs/` layout the
  CLI was taught to support left the automatic half of the tool inert.
- `TRIGPOINT_DISABLE` was documented as equivalent to pause and read only by
  the hooks, so it did not stop the CLI that writes.
- Pause stopped the verifier but not `build_dashboard.py`, which is exactly
  what `/trigpoint-sync` and the installed CLAUDE.md block tell people to run.
- `build_dashboard.py` reported success for a ledger it read as zero tasks --
  the same fail-open closed in the other two CLIs and left open in the third.
- The Stop hook filtered its summary by matching words in prose, so
  could-not-run lines were dropped and the end-of-turn path said nothing.
"""

import contextlib
import io
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "hooks"))

import build_dashboard
import trigpoint_verify as verify
import _project

LEDGER = """# R - Roadmap

## T1 - Foundation

**Scope:** one proven task
**Blocked by:** nothing

- [x] **1.1** Ship it
      **Verified:** `true`. 2026-08-27
"""


class Project:
    def __init__(self, ledger_subdirectory=""):
        self.root = tempfile.mkdtemp(prefix="trigpoint-guards-")
        os.makedirs(os.path.join(self.root, ".trigpoint"))
        directory = os.path.join(self.root, ledger_subdirectory) if ledger_subdirectory else self.root
        os.makedirs(directory, exist_ok=True)
        self.path = os.path.join(directory, "ROADMAP.md")
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(LEDGER)

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


class ApproveFindsTheProjectRootTests(unittest.TestCase):
    def setUp(self):
        self.project = Project()
        self.addCleanup(self.project.cleanup)
        self.subdirectory = os.path.join(self.project.root, "src", "deep")
        os.makedirs(self.subdirectory)

    def test_approving_from_a_subdirectory_writes_no_stray_state_directory(self):
        cwd = os.getcwd()
        os.chdir(self.subdirectory)
        self.addCleanup(os.chdir, cwd)
        with contextlib.redirect_stdout(io.StringIO()):
            verify.main(["trigpoint_verify.py", "--approve", "true"])
        self.assertFalse(os.path.exists(os.path.join(self.subdirectory, ".trigpoint")))

    def test_the_approval_lands_where_the_verifier_reads_it(self):
        cwd = os.getcwd()
        os.chdir(self.subdirectory)
        self.addCleanup(os.chdir, cwd)
        with contextlib.redirect_stdout(io.StringIO()):
            verify.main(["trigpoint_verify.py", "--approve", "true"])
        os.chdir(cwd)
        _, awaiting = verify.verify_ledger(self.project.path)
        self.assertEqual(awaiting, [])


class HooksSeeTheSameLedgerAsTheCliTests(unittest.TestCase):
    def setUp(self):
        self.project = Project("docs")
        self.addCleanup(self.project.cleanup)

    def test_the_hooks_find_a_ledger_the_cli_can_verify(self):
        self.assertIsNotNone(_project.ledger_path(self.project.root))

    def test_they_agree_on_which_file_it_is(self):
        self.assertEqual(
            os.path.realpath(_project.ledger_path(self.project.root)),
            os.path.realpath(self.project.path),
        )

    def test_a_root_ledger_is_still_found(self):
        plain = Project()
        self.addCleanup(plain.cleanup)
        self.assertEqual(
            os.path.realpath(_project.ledger_path(plain.root)),
            os.path.realpath(plain.path),
        )


class DisableStopsEverythingThatWritesTests(unittest.TestCase):
    def setUp(self):
        self.project = Project()
        self.addCleanup(self.project.cleanup)

    def test_the_verifier_refuses_when_trigpoint_disable_is_set(self):
        os.environ["TRIGPOINT_DISABLE"] = "1"
        self.addCleanup(os.environ.pop, "TRIGPOINT_DISABLE", None)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = verify.main(["trigpoint_verify.py", self.project.path])
        self.assertEqual(code, 0)
        self.assertIn("TRIGPOINT_DISABLE", out.getvalue())


class PauseStopsTheDashboardTooTests(unittest.TestCase):
    def setUp(self):
        self.project = Project()
        self.addCleanup(self.project.cleanup)
        open(os.path.join(self.project.root, ".trigpoint", "paused"), "w").close()

    def test_the_dashboard_refuses_to_rewrite_a_paused_ledger(self):
        with open(self.project.path, encoding="utf-8") as handle:
            before = handle.read()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            build_dashboard.main(["--ledger", self.project.path,
                                  "--output", os.path.join(self.project.root, "d.html")])
        with open(self.project.path, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), before)
        self.assertIn("paused", out.getvalue().lower())


class DashboardFailsClosedTests(unittest.TestCase):
    def test_a_ledger_it_read_as_zero_tasks_is_not_reported_as_built(self):
        directory = tempfile.mkdtemp(prefix="trigpoint-empty-")
        self.addCleanup(shutil.rmtree, directory, True)
        path = os.path.join(directory, "ROADMAP.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("# Just notes\n\n- [ ] buy milk\n- [x] feed the cat\n- [ ] renew\n")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = build_dashboard.main(["--ledger", path,
                                         "--output", os.path.join(directory, "d.html")])
        self.assertNotEqual(code, 0)
        self.assertIn("no tasks", (out.getvalue() + err.getvalue()).lower())


class StopHookReportsEveryOutcomeTests(unittest.TestCase):
    def test_a_command_that_could_not_run_is_not_filtered_out_of_the_summary(self):
        import stop

        report = ["1.1 could not be run, so it was left alone: no such file"]
        self.assertIn("could not be run", stop.summarise(report, []))


class OneNotionOfWhereTheLedgerIsTests(unittest.TestCase):
    """`project_root_for` resolved with abspath; `write_atomically` with realpath.

    A symlinked ledger therefore ran its commands and read its approvals in the
    link's tree while the write landed in the target's. Two answers to "which
    directory is this" is the same defect as two answers to "which line is this".
    """

    def test_a_symlinked_ledger_resolves_to_the_same_place_it_is_written(self):
        outer = tempfile.mkdtemp(prefix="trigpoint-link-")
        self.addCleanup(shutil.rmtree, outer, True)
        real_root = os.path.join(outer, "real")
        os.makedirs(os.path.join(real_root, ".trigpoint"))
        real_ledger = os.path.join(real_root, "ROADMAP.md")
        with open(real_ledger, "w", encoding="utf-8") as handle:
            handle.write(LEDGER)
        link_root = os.path.join(outer, "link")
        os.symlink(real_root, link_root)

        self.assertEqual(
            os.path.realpath(verify.project_root_for(os.path.join(link_root, "ROADMAP.md"))),
            os.path.realpath(real_root),
        )


class RegressionNotesStayReadableTests(unittest.TestCase):
    def test_a_command_with_no_output_leaves_no_empty_backtick_pair(self):
        outcome = verify.Outcome(1, "", "2026-08-27", verify.FAILED)
        note = verify._regressed_note("      ", "false", outcome)
        self.assertNotIn("``", note)
        self.assertIn("`false`", note)

    def test_a_command_with_output_still_shows_it(self):
        outcome = verify.Outcome(1, "2 tests failed", "2026-08-27", verify.FAILED)
        self.assertIn("`2 tests failed`", verify._regressed_note("", "x", outcome))


if __name__ == "__main__":
    unittest.main()
