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


class TheGeneratedTomlActuallyParsesTests(unittest.TestCase):
    """Nothing in this repository ever parsed the TOML it generates.

    The whole feature rested on asserting that certain substrings appeared in
    the output. Three mutations of the escaper survived the entire suite:
    swapping the two replace() calls, which injects literal backslashes into
    every prompt; removing the quote escaping, which produces a file no parser
    accepts; and substituting the wrong quote run.

    CI pins Python 3.9, which has no `tomllib`, so a skipUnless would leave the
    generated files unchecked exactly where it matters. The reader below is a
    deliberately small parser for the one shape this generator emits, and the
    real `tomllib` is used as well wherever it exists.
    """

    @staticmethod
    def read_generated(content):
        """Parse `description = "..."` and `prompt = \"\"\"...\"\"\"`, unescaping as TOML does."""
        description = None
        lines = content.split("\n")
        index = 0
        if lines[index].startswith("description = "):
            raw = lines[index][len('description = '):]
            assert raw.startswith('"') and raw.endswith('"'), raw
            inner = raw[1:-1]
            # A TOML basic string may not contain a bare quote or a bare
            # backslash. Accepting them made this reader tolerate output no real
            # parser would, so removing the escaping entirely left it green.
            position = 0
            while position < len(inner):
                if inner[position] == "\\":
                    assert position + 1 < len(inner), "trailing backslash: " + raw
                    position += 2
                    continue
                assert inner[position] != '"', "unescaped quote in: " + raw
                position += 1
            description = inner.replace('\\"', '"').replace("\\\\", "\\")
            index += 1
        assert lines[index] == 'prompt = """', lines[index]
        closing = len(lines) - 1
        while lines[closing] != '"""':
            closing -= 1
        body = "\n".join(lines[index + 1:closing])
        body = body.replace('\\"\\"\\"', '"""').replace("\\\\", "\\")
        return description, body

    def test_every_generated_file_round_trips_to_its_source_body(self):
        for path, content in sync.command_targets():
            markdown = ROOT / "commands" / (path.stem + ".md")
            expected_description, expected_body = sync._split_frontmatter(
                markdown.read_text(encoding="utf-8"))
            description, body = self.read_generated(content)
            self.assertEqual(description, expected_description or None, path.name)
            self.assertEqual(body, expected_body, path.name)

    def test_awkward_bodies_round_trip(self):
        for body in [
            "ends with a backslash \\",
            'ends with a quote "',
            'has """ three quotes inside',
            'has """""" six quotes',
            "has a literal \\n and a \\u escape",
            "plain",
        ]:
            with self.subTest(body=body):
                _, parsed = self.read_generated(sync.render_command_toml("d", body))
                self.assertEqual(parsed, body)

    def test_awkward_descriptions_round_trip(self):
        """No shipped description contains a quote, so nothing exercised this.

        Removing the description escaping entirely left the whole suite green:
        a real defect hidden by the fact that today's inputs happen to be tame.
        """
        for description in [
            'has a " quote',
            "ends with a backslash \\",
            'both \\ and "',
            "plain",
        ]:
            with self.subTest(description=description):
                parsed, _ = self.read_generated(sync.render_command_toml(description, "body"))
                self.assertEqual(parsed, description)

    def test_the_real_toml_library_accepts_every_generated_file(self):
        try:
            import tomllib
        except ImportError:
            self.skipTest("tomllib needs Python 3.11; the reader above covers 3.9")
        for path, content in sync.command_targets():
            parsed = tomllib.loads(content)
            self.assertIn("prompt", parsed, path.name)
            markdown = ROOT / "commands" / (path.stem + ".md")
            _, expected_body = sync._split_frontmatter(markdown.read_text(encoding="utf-8"))
            self.assertEqual(parsed["prompt"].strip(), expected_body, path.name)


if __name__ == "__main__":
    unittest.main()
