#!/usr/bin/env python3
"""Re-run the ledger's own recorded proofs when a working turn ends.

`check_drift.py` proves that a ticked task carries evidence. This proves the
evidence is still true. Only commands already written in the ledger run, and
only after a human approved that exact command once.

Nothing is ever ticked here. A machine can show a claim has become false;
deciding that work is finished stays with a person.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _project import ledger_path  # noqa: E402

import trigpoint_verify  # noqa: E402


def summarise(report, awaiting) -> str:
    parts = [line for line in report if "unticked" in line or "not found" in line]
    if awaiting:
        parts.append(
            "{0} recorded command(s) have never been approved to run here, so they "
            "were skipped. Run /trigpoint-verify to review and approve them.".format(
                len(awaiting)
            )
        )
    return "Trigpoint: " + "; ".join(parts) if parts else ""


def main() -> int:
    path = ledger_path(os.getcwd())
    if path is None:
        return 0

    report, awaiting = trigpoint_verify.verify_ledger(path)
    message = summarise(report, awaiting)
    if message:
        print(json.dumps({"systemMessage": message}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
