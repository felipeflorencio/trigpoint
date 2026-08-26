"""The hooks are only useful if a project actually receives them.

These guard the wiring rather than the behaviour: that the manifest registers
both hooks, that the skill copies the verifier into `.trigpoint/` alongside the
other scripts, and that the commands a user is told to run exist.
"""

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class HookManifestTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / "hooks" / "hooks.json").read_text())

    def test_registers_both_events(self):
        self.assertEqual(sorted(self.manifest["hooks"]), ["SessionStart", "Stop"])

    def test_every_registered_script_exists(self):
        for event in self.manifest["hooks"].values():
            for group in event:
                for hook in group["hooks"]:
                    name = hook["command"].split("/hooks/")[1].strip('"')
                    self.assertTrue((ROOT / "hooks" / name).exists(), name)

    def test_every_hook_has_a_timeout(self):
        for event in self.manifest["hooks"].values():
            for group in event:
                for hook in group["hooks"]:
                    self.assertIn("timeout", hook)

    def test_the_description_says_it_is_silent_by_default(self):
        self.assertIn("Silent", self.manifest["description"])


class InstallWiringTests(unittest.TestCase):
    def setUp(self):
        self.skill = (ROOT / "skills" / "trigpoint" / "SKILL.md").read_text()

    def test_the_skill_copies_the_verifier_into_the_project(self):
        self.assertIn("scripts/trigpoint_verify.py", self.skill)

    def test_the_skill_copies_every_script_the_verifier_imports(self):
        for module in ("trigpoint_ledger.py", "trigpoint_render.py",
                       "build_dashboard.py", "check_drift.py", "trigpoint_verify.py"):
            self.assertIn(module, self.skill, module)

    def test_the_skill_says_the_plugin_is_inert_until_a_project_opts_in(self):
        self.assertIn("inert", self.skill)

    def test_the_skill_says_nothing_is_ticked_automatically(self):
        self.assertIn("Nothing is ever ticked automatically", self.skill)


class CommandTests(unittest.TestCase):
    def test_the_commands_the_user_is_told_to_run_exist(self):
        for name in ("trigpoint", "trigpoint-sync", "trigpoint-verify", "trigpoint-pause"):
            self.assertTrue((ROOT / "commands" / (name + ".md")).exists(), name)

    def test_the_verify_command_refuses_bulk_approval(self):
        text = (ROOT / "commands" / "trigpoint-verify.md").read_text().lower()
        self.assertIn("never approve in bulk", text)
        self.assertIn("read-only assertions", text)

    def test_the_pause_command_says_how_to_undo_it(self):
        text = (ROOT / "commands" / "trigpoint-pause.md").read_text()
        self.assertIn("rm .trigpoint/paused", text)
