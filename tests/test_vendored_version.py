"""The vendored scripts and the plugin must not drift apart in silence.

The hooks always run the plugin's own copy of the code. Everything the user is
told to run -- the block written into their CLAUDE.md, `/trigpoint-sync`,
`/trigpoint-verify`, a CI gate -- runs the copies vendored into `.trigpoint/`,
which are refreshed by hand.

So after `claude plugin update trigpoint`, the session-start hook can be
instructing the agent to write `**Recorded:**` lines while the vendored gate it
also instructs the agent to run rejects every one of them as a hard error. The
two halves disagree, both are confident, and nothing says which is stale. A
version stamp beside the copies makes the mismatch visible.
"""

import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks"))
sys.path.insert(0, str(ROOT / "scripts"))

import session_start

HEALTHY = """# Example - Roadmap

## T1 - Foundation

**Scope:** One proven task
**Blocked by:** nothing

- [x] **1.1** Write the ledger parser
      **Verified:** `python3 -m unittest tests.test_ledger_parse -v`. 2026-08-26
"""


class PluginVersionTests(unittest.TestCase):
    def test_it_reads_the_version_the_plugin_actually_ships(self):
        manifest = json.loads(
            (ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(session_start.plugin_version(), manifest["version"])


class VendoredVersionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="trigpoint-vendored-")
        self.addCleanup(shutil.rmtree, self.directory, True)
        self.state = os.path.join(self.directory, ".trigpoint")
        os.makedirs(self.state)
        with open(os.path.join(self.directory, "ROADMAP.md"), "w", encoding="utf-8") as handle:
            handle.write(HEALTHY)

    def stamp(self, version):
        with open(os.path.join(self.state, "version"), "w", encoding="utf-8") as handle:
            handle.write(version + "\n")

    def test_a_matching_stamp_produces_no_warning(self):
        self.stamp(session_start.plugin_version())
        self.assertEqual(session_start.vendored_version_warning(self.directory), "")

    def test_an_older_stamp_is_reported_with_both_versions(self):
        self.stamp("0.2.0")
        warning = session_start.vendored_version_warning(self.directory)
        self.assertIn("0.2.0", warning)
        self.assertIn(session_start.plugin_version(), warning)

    def test_an_older_stamp_says_how_to_fix_it(self):
        self.stamp("0.2.0")
        self.assertIn(".trigpoint", session_start.vendored_version_warning(self.directory))

    def test_no_stamp_at_all_is_treated_as_stale_rather_than_fine(self):
        self.assertNotEqual(session_start.vendored_version_warning(self.directory), "")

    def test_a_project_that_never_initialised_is_not_nagged(self):
        plain = tempfile.mkdtemp(prefix="trigpoint-plain-")
        self.addCleanup(shutil.rmtree, plain, True)
        self.assertEqual(session_start.vendored_version_warning(plain), "")

    def test_a_paused_project_is_not_nagged_either(self):
        self.stamp("0.2.0")
        open(os.path.join(self.state, "paused"), "w").close()
        self.assertEqual(session_start.vendored_version_warning(self.directory), "")

    def test_the_warning_reaches_the_state_an_agent_reads(self):
        self.stamp("0.2.0")
        state = session_start.build_state(HEALTHY, self.directory)
        self.assertIn("0.2.0", state)

    def test_a_matching_stamp_leaves_the_state_unchanged(self):
        self.stamp(session_start.plugin_version())
        self.assertEqual(
            session_start.build_state(HEALTHY, self.directory),
            session_start.build_state(HEALTHY),
        )


    def test_an_unreadable_stamp_does_not_kill_the_hook(self):
        """`except OSError` does not catch UnicodeDecodeError, which is a ValueError.

        `plugin_version()` one function above already catches both. A version
        file with non-UTF-8 bytes took the whole SessionStart hook down with a
        traceback, which is a worse outcome than any staleness it was reporting.
        """
        with open(os.path.join(self.state, "version"), "wb") as handle:
            handle.write(b"\xff\xfe not utf-8 at all")
        warning = session_start.vendored_version_warning(self.directory)
        self.assertIn("unrecorded", warning)

    def test_a_stamp_that_is_a_directory_does_not_kill_the_hook(self):
        os.makedirs(os.path.join(self.state, "version"))
        self.assertIn("unrecorded", session_start.vendored_version_warning(self.directory))


if __name__ == "__main__":
    unittest.main()
