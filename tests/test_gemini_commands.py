"""Gemini reads commands as TOML, and this plugin ships them as Markdown.

Roadmap item 6.8 asked for a non-Claude harness to be verified rather than
assumed. No Gemini CLI is installed on this machine, so the manifests were
checked against the vendors' published references instead. Gemini's is explicit:

    "Provide custom commands by placing TOML files in a `commands/`
    subdirectory. Gemini CLI uses the directory structure to determine the
    command name."

    prompt      required, string
    description optional, string

Trigpoint ships `commands/*.md`. On Gemini the skill loads and all four slash
commands are invisible. The TOML is generated from the Markdown rather than
hand-written, for the same reason every other manifest is: two copies of the
same fact drift, and only one of them is the one anybody edits.
"""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import sync_plugin_variants as sync


class GeminiCommandGenerationTests(unittest.TestCase):
    def test_one_toml_is_generated_for_every_markdown_command(self):
        markdown = sorted(path.stem for path in (ROOT / "commands").glob("*.md"))
        generated = sorted(path.stem for path, _ in sync.command_targets())
        self.assertEqual(generated, markdown)
        self.assertIn("trigpoint-verify", generated)

    def test_every_generated_file_is_toml_staged_outside_the_live_commands_directory(self):
        """Staged in gemini/commands/, not commands/, until 6.8 can test it.

        Claude Code names a command by "the file name without extension", which
        does not settle whether it globs `*.md` or everything in the directory.
        A `.toml` beside each `.md` could hand the one verified-working harness
        four duplicate commands whose body is TOML.
        """
        for path, _ in sync.command_targets():
            self.assertEqual(path.suffix, ".toml")
            self.assertEqual(path.parent.name, "commands")
            self.assertEqual(path.parent.parent.name, "gemini")

    def test_no_toml_is_left_in_the_live_commands_directory(self):
        self.assertEqual(list((ROOT / "commands").glob("*.toml")), [])

    def test_the_description_carries_over_from_the_frontmatter(self):
        for path, content in sync.command_targets():
            if path.stem == "trigpoint-sync":
                self.assertIn(
                    'description = "Regenerate the ledger progress table '
                    'and the dashboard from ROADMAP.md"',
                    content,
                )
                return
        self.fail("trigpoint-sync was not generated")

    def test_the_prompt_carries_the_body_and_not_the_frontmatter(self):
        for path, content in sync.command_targets():
            if path.stem == "trigpoint-sync":
                self.assertIn("prompt = \"\"\"", content)
                self.assertIn("build_dashboard.py", content)
                self.assertNotIn("---\\ndescription:", content)
                return
        self.fail("trigpoint-sync was not generated")

    def test_a_body_containing_a_quote_run_is_escaped(self):
        rendered = sync.render_command_toml("d", 'he said """hello""" loudly')
        self.assertNotIn('"""hello"""', rendered)
        self.assertIn('prompt = """', rendered)

    def test_a_backslash_in_the_body_is_escaped(self):
        self.assertIn("\\\\n", sync.render_command_toml("d", "a literal \\n here"))

    def test_the_generated_files_are_on_disk_and_current(self):
        self.assertEqual(sync.check(), [])


class ClaudeCommandsAreUnaffectedTests(unittest.TestCase):
    """Adding .toml beside .md must not change what Claude Code loads."""

    def test_every_markdown_command_still_exists(self):
        names = sorted(path.name for path in (ROOT / "commands").glob("*.md"))
        self.assertEqual(
            names,
            ["trigpoint-pause.md", "trigpoint-sync.md", "trigpoint-verify.md", "trigpoint.md"],
        )


if __name__ == "__main__":
    unittest.main()
