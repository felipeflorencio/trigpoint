import json
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

import _project
import session_start
import trigpoint_verify


LEDGER = """# Example - Roadmap

## T1 Foundation

**Scope:** The parser and its gate
**Blocked by:** nothing

- [x] **1.1** Write the ledger parser
      **Verified:** `test -f marker` -> `exit 0`. 2026-08-26
- [ ] **1.2** Write the renderer

## T2 Dashboard

**Scope:** The generated page
**Blocked by:** T1

- [ ] **2.1** Build the dashboard
"""


def run_hook(name, cwd, environment=None):
    env = dict(os.environ)
    env.update(environment or {})
    return subprocess.run(
        [sys.executable, str(ROOT / "hooks" / name)],
        cwd=cwd, capture_output=True, text=True, env=env,
    )


class ProjectGuardTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="trigpoint-guard-")

    def tearDown(self):
        shutil.rmtree(self.directory, ignore_errors=True)

    def initialise(self):
        os.makedirs(os.path.join(self.directory, ".trigpoint"), exist_ok=True)
        pathlib.Path(self.directory, "ROADMAP.md").write_text(LEDGER)

    def test_an_uninitialised_directory_is_never_acted_on(self):
        pathlib.Path(self.directory, "ROADMAP.md").write_text(LEDGER)
        self.assertIsNone(_project.initialised_root(self.directory, {}))

    def test_an_initialised_directory_without_a_ledger_is_not_acted_on(self):
        os.makedirs(os.path.join(self.directory, ".trigpoint"))
        self.assertIsNone(_project.initialised_root(self.directory, {}))

    def test_an_initialised_project_with_a_ledger_is_acted_on(self):
        self.initialise()
        self.assertEqual(_project.initialised_root(self.directory, {}),
                         os.path.abspath(self.directory))

    def test_a_subdirectory_finds_the_project_root(self):
        self.initialise()
        nested = os.path.join(self.directory, "src", "deep")
        os.makedirs(nested)
        self.assertEqual(_project.initialised_root(nested, {}),
                         os.path.abspath(self.directory))

    def test_a_paused_project_is_not_acted_on(self):
        self.initialise()
        pathlib.Path(self.directory, ".trigpoint", "paused").write_text("")
        self.assertIsNone(_project.initialised_root(self.directory, {}))

    def test_the_environment_can_disable_it_for_one_session(self):
        self.initialise()
        self.assertIsNone(
            _project.initialised_root(self.directory, {"TRIGPOINT_DISABLE": "1"}))


class SessionStateTests(unittest.TestCase):
    def setUp(self):
        self.state = session_start.build_state(LEDGER)

    def test_states_how_much_is_done(self):
        self.assertIn("1 of 3 tasks done", self.state)

    def test_separates_re_runnable_proof_from_a_written_note(self):
        self.assertIn("1 carrying a re-runnable command", self.state)

    def test_lists_open_tracks_with_what_blocks_them(self):
        self.assertIn("T1 Foundation", self.state)
        self.assertIn("blocked by T1", self.state)

    def test_names_the_next_unblocked_work(self):
        self.assertIn("Next unblocked: 1.2", self.state)

    def test_restates_the_ticking_rule_and_the_re_run(self):
        self.assertIn("Never on assumption", self.state)
        self.assertIn("unticked again", self.state)


class HookProcessTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="trigpoint-hook-")
        os.makedirs(os.path.join(self.directory, ".trigpoint"))
        pathlib.Path(self.directory, "ROADMAP.md").write_text(LEDGER)
        pathlib.Path(self.directory, "marker").write_text("")

    def tearDown(self):
        shutil.rmtree(self.directory, ignore_errors=True)

    def ledger_text(self):
        return pathlib.Path(self.directory, "ROADMAP.md").read_text()

    def approve_recorded(self):
        approvals = trigpoint_verify.approve("test -f marker", {})
        trigpoint_verify.save_approvals(self.directory, approvals)

    def test_session_start_emits_the_state_as_additional_context(self):
        result = run_hook("session_start.py", self.directory)
        payload = json.loads(result.stdout)
        self.assertIn("TRIGPOINT LEDGER",
                      payload["hookSpecificOutput"]["additionalContext"])

    def test_session_start_says_nothing_in_an_uninitialised_directory(self):
        plain = tempfile.mkdtemp(prefix="trigpoint-plain-")
        try:
            result = run_hook("session_start.py", plain)
            self.assertEqual(result.stdout.strip(), "")
            self.assertEqual(result.returncode, 0)
        finally:
            shutil.rmtree(plain, ignore_errors=True)

    def test_stop_runs_nothing_until_the_command_is_approved(self):
        os.remove(os.path.join(self.directory, "marker"))
        run_hook("stop.py", self.directory)
        self.assertIn("- [x] **1.1**", self.ledger_text(),
                      "an unapproved command must not be able to untick anything")

    def test_stop_unticks_a_task_whose_approved_command_now_fails(self):
        self.approve_recorded()
        os.remove(os.path.join(self.directory, "marker"))
        run_hook("stop.py", self.directory)
        text = self.ledger_text()
        self.assertIn("- [ ] **1.1**", text)
        self.assertIn("**Regressed:**", text)

    def test_stop_leaves_a_still_passing_task_alone(self):
        self.approve_recorded()
        before = self.ledger_text()
        run_hook("stop.py", self.directory)
        self.assertEqual(self.ledger_text(), before)

    def test_stop_never_ticks_anything(self):
        self.approve_recorded()
        run_hook("stop.py", self.directory)
        text = self.ledger_text()
        self.assertIn("- [ ] **1.2**", text)
        self.assertIn("- [ ] **2.1**", text)

    def test_stop_says_nothing_in_an_uninitialised_directory(self):
        plain = tempfile.mkdtemp(prefix="trigpoint-plain-")
        try:
            self.assertEqual(run_hook("stop.py", plain).stdout.strip(), "")
        finally:
            shutil.rmtree(plain, ignore_errors=True)

    def test_a_paused_project_is_left_alone(self):
        self.approve_recorded()
        pathlib.Path(self.directory, ".trigpoint", "paused").write_text("")
        os.remove(os.path.join(self.directory, "marker"))
        run_hook("stop.py", self.directory)
        self.assertIn("- [x] **1.1**", self.ledger_text())
