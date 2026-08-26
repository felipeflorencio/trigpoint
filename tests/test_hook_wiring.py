"""The hooks are only useful if a project actually receives them.

These guard the wiring rather than the behaviour: that the manifest registers
both hooks, that the skill copies the verifier into `.trigpoint/` alongside the
other scripts, and that the commands a user is told to run exist.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class HookManifestTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / "hooks" / "hooks.json").read_text())

    def test_registers_both_events(self):
        self.assertEqual(sorted(self.manifest["hooks"]), ["SessionStart", "Stop"])

    def test_every_registered_script_exists(self):
        # A command reads: "<plugin root>/hooks/run-hook.cmd" script_name.py
        for event in self.manifest["hooks"].values():
            for group in event:
                for hook in group["hooks"]:
                    wrapper, _, script = hook["command"].partition('" ')
                    wrapper_name = wrapper.split("/hooks/")[1].strip('"')
                    self.assertTrue((ROOT / "hooks" / wrapper_name).exists(), wrapper_name)
                    self.assertTrue((ROOT / "hooks" / script.strip()).exists(), script)

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


class WindowsWrapperTests(unittest.TestCase):
    """The wrapper is what makes the hooks work where python3 does not exist."""

    def setUp(self):
        self.path = ROOT / "hooks" / "run-hook.cmd"
        self.text = self.path.read_text()

    def test_the_wrapper_exists_and_is_executable(self):
        self.assertTrue(self.path.exists())
        self.assertTrue(os.access(self.path, os.X_OK), "run-hook.cmd must be executable")

    def test_it_looks_for_every_windows_python_name(self):
        for launcher in ("py -3", "python3", "python"):
            self.assertIn(launcher, self.text, launcher)

    def test_a_machine_with_no_python_is_a_silent_no_op(self):
        self.assertIn("exit /b 0", self.text, "Windows half must exit cleanly")
        self.assertIn("exit 0", self.text, "Unix half must exit cleanly")

    def test_both_hooks_are_invoked_through_the_wrapper(self):
        manifest = json.loads((ROOT / "hooks" / "hooks.json").read_text())
        for event in manifest["hooks"].values():
            for group in event:
                for hook in group["hooks"]:
                    self.assertIn("run-hook.cmd", hook["command"])

    def test_the_wrapper_actually_runs_a_hook(self):
        directory = tempfile.mkdtemp(prefix="trigpoint-wrapper-")
        try:
            os.makedirs(os.path.join(directory, ".trigpoint"))
            pathlib.Path(directory, "ROADMAP.md").write_text(
                "# X\n\n## T1 One\n\n**Scope:** s\n**Blocked by:** nothing\n\n"
                "- [ ] **1.1** Something\n"
            )
            result = subprocess.run(
                ["bash", str(self.path), "session_start.py"],
                cwd=directory, capture_output=True, text=True,
            )
            payload = json.loads(result.stdout)
            self.assertIn("TRIGPOINT LEDGER",
                          payload["hookSpecificOutput"]["additionalContext"])
        finally:
            shutil.rmtree(directory, ignore_errors=True)


class GeneratedManifestTests(unittest.TestCase):
    """Every harness manifest is generated, so none of them can drift."""

    def test_no_generated_manifest_is_out_of_date(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "sync_plugin_variants.py"), "--check"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_every_harness_has_a_manifest(self):
        for relative in (".claude-plugin/plugin.json", ".claude-plugin/marketplace.json",
                         ".codex-plugin/plugin.json", ".cursor-plugin/plugin.json",
                         "gemini-extension.json"):
            self.assertTrue((ROOT / relative).exists(), relative)

    def test_every_manifest_states_the_same_version(self):
        source = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
        for relative in (".codex-plugin/plugin.json", ".cursor-plugin/plugin.json",
                         "gemini-extension.json"):
            other = json.loads((ROOT / relative).read_text())
            self.assertEqual(other["version"], source["version"], relative)

    def test_the_context_file_gemini_names_exists(self):
        extension = json.loads((ROOT / "gemini-extension.json").read_text())
        self.assertTrue((ROOT / extension["contextFileName"]).exists())
