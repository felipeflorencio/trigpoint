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


def check() -> List[str]:
    """Paths whose content differs from what this script would generate."""
    drifted = []
    for path, manifest in targets():
        expected = serialise(manifest)
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            drifted.append(str(path.relative_to(REPOSITORY_ROOT)))
    return drifted


def write() -> List[str]:
    """Apply what matches and write regardless, reporting each path."""
    written = []
    for path, manifest in targets():
        expected = serialise(manifest)
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
