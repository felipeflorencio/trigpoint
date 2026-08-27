"""An example command must be true exactly when its claim is true.

Two shapes shipped in the reference doc and the ledger template, and both are
worse than no example, because a person following a shipped instruction has
every reason to trust it.

    - [x] **0.4** Delete stale `bin/`   **Verified:** `ls bin/`

`ls bin/` exits 0 only while `bin/` still exists, which is only while the task
is FALSE, and exits 1 the moment the work is actually done. Doing the work
correctly makes the tool untick the box and write a `**Regressed:**` note.

    - [x] **1.3** Set `ddl-auto=validate`   **Verified:** `./gradlew bootRun`

`bootRun` starts a server and never exits, so re-running it can only ever hit
the timeout. It also contradicts the module's own contract that verify commands
are read-only assertions.

The class is not those two lines. It is an example whose exit status is not
tied to the truth of its claim: inverted, unbounded, or passing regardless.
This test scans the shipped surface so a new one cannot be added quietly.
"""

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent

SHIPPED = [
    "README.md",
    "AGENTS.md",
    "GEMINI.md",
    "skills/trigpoint/SKILL.md",
    "skills/trigpoint/references/evidence-rules.md",
    "skills/trigpoint/references/ledger-format.md",
    "skills/trigpoint/templates/ROADMAP.template.md",
]

EVIDENCE = re.compile(r"\*\*Verified:\*\*\s*`([^`]+)`")

# Commands that cannot be a proof of anything, whatever claim they sit under.
FORBIDDEN = [
    (re.compile(r"\bbootRun\b|\brunserver\b|\bnpm (run )?start\b|\bserve\b"),
     "never exits, so re-running it can only time out"),
    (re.compile(r"^\s*ls\b"),
     "listing something proves it is PRESENT, which is the wrong way round for "
     "any task about removing it, and proves nothing about content otherwise"),
    (re.compile(r"^\s*(cat|head|tail|echo)\b"),
     "prints something and exits 0 regardless of whether the claim holds"),
]


def shipped_evidence():
    for name in SHIPPED:
        path = ROOT / name
        if not path.exists():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for command in EVIDENCE.findall(line):
                yield name, number, command


class ShippedEvidenceExamplesTests(unittest.TestCase):
    def test_no_shipped_example_uses_a_command_that_cannot_prove_anything(self):
        offenders = []
        for name, number, command in shipped_evidence():
            for pattern, why in FORBIDDEN:
                if pattern.search(command):
                    offenders.append("{0}:{1} `{2}` -- {3}".format(name, number, command, why))
        self.assertEqual(offenders, [], "\n" + "\n".join(offenders))

    def test_the_shipped_surface_actually_contains_examples_to_check(self):
        """Guards the guard: a scanner that finds nothing proves nothing."""
        self.assertGreater(len(list(shipped_evidence())), 3)

    def test_the_scanner_catches_a_known_bad_example(self):
        for pattern, _ in FORBIDDEN:
            if pattern.search("ls bin/"):
                return
        self.fail("the scanner would not catch `ls bin/`")


if __name__ == "__main__":
    unittest.main()
