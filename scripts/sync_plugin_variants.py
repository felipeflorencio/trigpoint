#!/usr/bin/env python3
"""Generate every harness's plugin manifest from the one in .claude-plugin.

Trigpoint exists because hand-maintained copies of the same facts drift apart.
Shipping six manifests that each restate the name, version and description by
hand would be that failure, in this repository, about itself. So one manifest
is the source and the rest are generated, and CI fails when a generated file
does not match what this script would write.

Source of truth: `.claude-plugin/plugin.json`.

Generated:
  .claude-plugin/marketplace.json   version only, the rest is hand-written
  .codex-plugin/plugin.json         Codex
  .cursor-plugin/plugin.json        Cursor
  gemini-extension.json             Gemini CLI

Run `python3 scripts/sync_plugin_variants.py` to write them, or with `--check`
to report drift without writing, which is what CI does.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from typing import Dict, List, Tuple

REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = REPOSITORY_ROOT / ".claude-plugin" / "plugin.json"

SHORT_DESCRIPTION = "A plan of record that cannot drift, kept true while the work is done"
LONG_DESCRIPTION = (
    "Trigpoint audits a codebase, runs a question ladder to produce a ledger, a "
    "dashboard and a design spec, then keeps them true. Counts are generated rather "
    "than typed. A ticked task must carry the command that proved it, and those "
    "commands are re-run as work proceeds, so a task that stopped being true unticks "
    "itself instead of quietly staying green."
)


def read_source() -> Dict:
    with SOURCE.open(encoding="utf-8") as handle:
        return json.load(handle)


def codex_manifest(source: Dict) -> Dict:
    return {
        "name": source["name"],
        "version": source["version"],
        "description": source["description"],
        "author": source["author"],
        "homepage": source["homepage"],
        "repository": source["homepage"],
        "license": "MIT",
        "keywords": source["keywords"],
        "skills": "./skills/",
        "interface": {
            "displayName": "Trigpoint",
            "shortDescription": SHORT_DESCRIPTION,
            "longDescription": LONG_DESCRIPTION,
            "developerName": source["author"]["name"],
            "category": "Developer Tools",
        },
    }


def cursor_manifest(source: Dict) -> Dict:
    return {
        "name": source["name"],
        "displayName": "Trigpoint",
        "version": source["version"],
        "description": source["description"],
        "author": source["author"],
        "homepage": source["homepage"],
        "repository": source["homepage"],
        "license": "MIT",
        "keywords": source["keywords"],
        "skills": "./skills/",
        "hooks": "./hooks/hooks-cursor.json",
    }


def gemini_extension(source: Dict) -> Dict:
    return {
        "name": source["name"],
        "version": source["version"],
        "description": source["description"],
        "contextFileName": "AGENTS.md",
    }


def marketplace_manifest(source: Dict) -> Dict:
    """The marketplace entry is hand-written except for the version it pins."""
    path = REPOSITORY_ROOT / ".claude-plugin" / "marketplace.json"
    with path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    for plugin in manifest.get("plugins", []):
        if plugin.get("name") == source["name"]:
            plugin["version"] = source["version"]
    return manifest


def targets() -> List[Tuple[pathlib.Path, Dict]]:
    source = read_source()
    return [
        (REPOSITORY_ROOT / ".codex-plugin" / "plugin.json", codex_manifest(source)),
        (REPOSITORY_ROOT / ".cursor-plugin" / "plugin.json", cursor_manifest(source)),
        (REPOSITORY_ROOT / "gemini-extension.json", gemini_extension(source)),
        (REPOSITORY_ROOT / ".claude-plugin" / "marketplace.json", marketplace_manifest(source)),
    ]


def serialise(manifest: Dict) -> str:
    return json.dumps(manifest, indent=2) + "\n"


# ------------------------------------------------------- gemini slash commands


def _split_frontmatter(markdown_text: str) -> Tuple[str, str]:
    """The `description:` from a command file's frontmatter, and its body."""
    description = ""
    body = markdown_text
    if markdown_text.startswith("---"):
        end = markdown_text.find("\n---", 3)
        if end != -1:
            frontmatter = markdown_text[3:end]
            body = markdown_text[end + 4 :]
            for line in frontmatter.splitlines():
                if line.strip().lower().startswith("description:"):
                    description = line.split(":", 1)[1].strip()
                    break
    return description, body.strip()


def _toml_basic_string(value: str) -> str:
    return '"{0}"'.format(value.replace("\\", "\\\\").replace('"', '\\"'))


def render_command_toml(description: str, body: str) -> str:
    """One Gemini command file.

    Gemini's reference gives `prompt` as required and `description` as
    optional. The body goes in a multi-line basic string, so a backslash has to
    be escaped or TOML reads it as an escape sequence, and a run of three
    quotes has to be broken or it closes the string early.
    """
    escaped = body.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    # TOML forbids raw control characters in a string. A body carrying an ESC
    # from a coloured example, or a lone carriage return, produced a file no
    # parser would accept. Tab and newline are the two that are legal as-is.
    escaped = "".join(
        character if character in "\t\n" or ord(character) >= 0x20
        else "\\u{0:04X}".format(ord(character))
        for character in escaped
        if character != "\r"
    )
    lines = []
    if description:
        lines.append("description = {0}".format(_toml_basic_string(description)))
    lines.append('prompt = """')
    lines.append(escaped)
    lines.append('"""')
    return "\n".join(lines) + "\n"


def command_targets() -> List[Tuple[pathlib.Path, str]]:
    """A Gemini `.toml` beside every Claude/Cursor `.md` command.

    Gemini reads TOML only, so without these its users get the skill and none
    of the slash commands. Generated rather than hand-written: a second copy of
    the same instruction drifts from the first, and the Markdown is the one
    anybody actually edits.

    They are written to `gemini/commands/` and NOT to `commands/`, where Gemini
    would actually look. Claude Code's reference gives a command's name as "the
    file name without extension", which does not say whether it globs `*.md` or
    everything in the directory, and no Gemini CLI is installed here to test
    the other side. Dropping a `.toml` beside each `.md` could therefore give
    Claude Code four duplicate commands whose body is TOML, in exchange for
    fixing a harness nobody here can run. Staging them keeps the generator
    honest and the working harness untouched; moving the directory is a
    one-line change the moment 6.8 can actually be tested.
    """
    generated = []
    for markdown in sorted((REPOSITORY_ROOT / "commands").glob("*.md")):
        description, body = _split_frontmatter(markdown.read_text(encoding="utf-8"))
        target = REPOSITORY_ROOT / "gemini" / "commands" / (markdown.stem + ".toml")
        generated.append((target, render_command_toml(description, body)))
    return generated


def context_file_targets() -> List[Tuple[pathlib.Path, str]]:
    """`GEMINI.md`, generated from `AGENTS.md`.

    The two were byte-identical, hand-maintained copies of the same rules, which
    is the drift this module exists to prevent. Gemini's manifest names its own
    context file, so the content has to appear twice on disk; nothing says it
    has to be typed twice.
    """
    source = REPOSITORY_ROOT / "AGENTS.md"
    return [(REPOSITORY_ROOT / "GEMINI.md", source.read_text(encoding="utf-8"))]


PROGRESS_BEGIN = "<!-- trigpoint:progress:begin -->"
PROGRESS_END = "<!-- trigpoint:progress:end -->"


def readme_targets() -> List[Tuple[pathlib.Path, str]]:
    """The README's copy of the ledger's progress table.

    The README calls it "the current table from this repository, verbatim" and
    it had drifted to five tracks while the ledger showed six. Retyping it
    correctly once only resets the clock: this is a tool whose whole argument is
    that a hand-copied number drifts, making that argument on a page carrying a
    hand-copied number. So it is copied by the same script that copies
    everything else.
    """
    ledger = (REPOSITORY_ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    start = ledger.index(PROGRESS_BEGIN)
    finish = ledger.index(PROGRESS_END, start) + len(PROGRESS_END)
    region = ledger[start:finish]

    readme_path = REPOSITORY_ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    start = readme.index(PROGRESS_BEGIN)
    finish = readme.index(PROGRESS_END, start) + len(PROGRESS_END)
    return [(readme_path, readme[:start] + region + readme[finish:])]


def _everything() -> List[Tuple[pathlib.Path, str]]:
    """Every generated file: manifests, Gemini commands, then GEMINI.md."""
    return ([(path, serialise(manifest)) for path, manifest in targets()]
            + command_targets() + context_file_targets() + readme_targets())


def check() -> List[str]:
    """Paths whose content differs from what this script would generate."""
    drifted = []
    for path, expected in _everything():
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            drifted.append(str(path.relative_to(REPOSITORY_ROOT)))
    return drifted


def write() -> List[str]:
    """Apply what matches and write regardless, reporting each path."""
    written = []
    for path, expected in _everything():
        if path.exists() and path.read_text(encoding="utf-8") == expected:
            continue
        os.makedirs(path.parent, exist_ok=True)
        path.write_text(expected, encoding="utf-8")
        written.append(str(path.relative_to(REPOSITORY_ROOT)))
    return written


def main(argv: List[str]) -> int:
    if "--check" in argv:
        drifted = check()
        for path in drifted:
            print("out of date: {0}".format(path))
        if drifted:
            print("run: python3 scripts/sync_plugin_variants.py")
            return 1
        print("every generated manifest matches .claude-plugin/plugin.json")
        return 0

    written = write()
    for path in written:
        print("applied: {0}".format(path))
    if not written:
        print("nothing to apply: every generated manifest was already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
