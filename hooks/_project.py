"""Decide whether Trigpoint may act in the directory a hook fired in.

Trigpoint is a per-project tool. Installing the plugin must change nothing
anywhere; a project opts in when someone runs the skill, which creates
`.trigpoint/` and a ledger. Both hooks ask this module first and exit silently
when the answer is no, so a repository that never opted in never sees Trigpoint
and never pays for it.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

HOOKS_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(HOOKS_DIRECTORY)
sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))

STATE_DIRECTORY = ".trigpoint"
LEDGER_NAME = "ROADMAP.md"
# Where a ledger may live, nearest the root first. The CLI was taught to verify
# a ledger kept in `docs/`; the hooks required one at the root, so the whole
# automatic half of the tool stayed inert for exactly the layout the CLI had
# just learned to support, and said nothing about it.
LEDGER_LOCATIONS = (LEDGER_NAME, os.path.join("docs", LEDGER_NAME))
PAUSE_FILE = "paused"
DISABLE_VARIABLE = "TRIGPOINT_DISABLE"


def initialised_root(start_directory: str, environment=None) -> Optional[str]:
    """The root of the initialised Trigpoint project containing `start_directory`.

    Returns None when Trigpoint must stay silent: the environment disables it,
    the project is paused, no ancestor directory has been initialised, or an
    initialised directory has no ledger to act on.
    """
    environment = os.environ if environment is None else environment
    if environment.get(DISABLE_VARIABLE):
        return None

    current = os.path.abspath(start_directory)
    while True:
        state = os.path.join(current, STATE_DIRECTORY)
        if os.path.isdir(state):
            if os.path.exists(os.path.join(state, PAUSE_FILE)):
                return None
            if _ledger_in(current):
                return current
            return None
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def _ledger_in(root: str) -> Optional[str]:
    for relative in LEDGER_LOCATIONS:
        candidate = os.path.join(root, relative)
        if os.path.exists(candidate):
            return candidate
    return None


def ledger_path(start_directory: str, environment=None) -> Optional[str]:
    root = initialised_root(start_directory, environment)
    return _ledger_in(root) if root else None
