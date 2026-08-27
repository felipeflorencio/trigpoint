from __future__ import annotations

import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

SHIPPED_MARKDOWN_PATTERNS = (
    "*.md",
    "commands/**/*.md",
    "skills/**/*.md",
    "examples/**/*.md",
)

# A verbatim copy of a third-party document. It must stay faithful to its source,
# so the typography rules that bind everything this plugin writes do not bind it.
EXCLUDED_MARKDOWN = frozenset({"tests/fixtures/reference_ledger.md"})


def shipped_markdown_paths() -> list:
    """Every markdown file this plugin ships to a user.

    The repository root plus commands/, skills/ and examples/. Deliberately not
    docs/ or .superpowers/, which are working notes rather than shipped output,
    and not tests/, whose fixtures are inputs rather than prose.
    """
    collected = {}
    for pattern in SHIPPED_MARKDOWN_PATTERNS:
        for candidate in ROOT.glob(pattern):
            relative_name = candidate.relative_to(ROOT).as_posix()
            if relative_name in EXCLUDED_MARKDOWN:
                continue
            collected[relative_name] = candidate
    return [collected[name] for name in sorted(collected)]


class TestFileLayoutTest(unittest.TestCase):
    """No test class may be defined below `unittest.main()`.

    `unittest discover` imports the module and collects everything, so CI stays
    green while `python3 tests/test_x.py` silently runs a subset. Three files
    drifted into that shape, and the hidden classes were the evidence for the
    very findings they had been written to close.
    """

    GUARD = re.compile(r"^if __name__ == .__main__.:", re.MULTILINE)
    CLASS = re.compile(r"^class ", re.MULTILINE)

    def test_no_test_class_is_defined_after_the_main_guard(self):
        root = pathlib.Path(__file__).resolve().parent
        offenders = []
        for path in sorted(root.glob("test_*.py")):
            source = path.read_text(encoding="utf-8")
            guard = self.GUARD.search(source)
            if guard and self.CLASS.search(source, guard.end()):
                offenders.append(path.name)
        self.assertEqual(offenders, [])


class ManifestTest(unittest.TestCase):
    def test_plugin_manifest_is_valid_json_with_required_fields(self) -> None:
        data = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text("utf-8"))
        for field in ("name", "description", "version"):
            self.assertIn(field, data)
        self.assertEqual("trigpoint", data["name"])

    def test_marketplace_manifest_lists_this_plugin(self) -> None:
        data = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text("utf-8")
        )
        self.assertIn("name", data)
        self.assertIn("owner", data)
        names = [plugin["name"] for plugin in data["plugins"]]
        self.assertIn("trigpoint", names)

    def test_every_command_file_exists_and_has_frontmatter(self) -> None:
        for command_name in ("trigpoint", "trigpoint-sync"):
            path = ROOT / "commands" / (command_name + ".md")
            self.assertTrue(path.is_file(), command_name)
            text = path.read_text("utf-8")
            self.assertTrue(text.startswith("---"), command_name)
            self.assertIn("description:", text)

    def test_no_forbidden_typography_in_shipped_markdown(self) -> None:
        forbidden = ["—", "–", "‘", "’", "“", "”", "…"]
        for markdown_path in shipped_markdown_paths():
            text = markdown_path.read_text("utf-8")
            for character in forbidden:
                self.assertNotIn(
                    character,
                    text,
                    "{0} in {1}".format(repr(character), markdown_path),
                )

    def test_shipped_markdown_glob_covers_the_user_facing_surface(self) -> None:
        covered = {
            path.relative_to(ROOT).as_posix() for path in shipped_markdown_paths()
        }
        self.assertIn("commands/trigpoint.md", covered)
        self.assertIn("skills/trigpoint/SKILL.md", covered)
        for excluded in ("tests/fixtures/reference_ledger.md",):
            self.assertNotIn(excluded, covered)
        for prefix in ("docs/", ".superpowers/", "tests/"):
            self.assertFalse(
                [name for name in covered if name.startswith(prefix)],
                "{0} must not be treated as shipped markdown".format(prefix),
            )


if __name__ == "__main__":
    unittest.main()
