---
description: Re-run the commands the ledger records, and review any that have never been approved to run here
---

Re-prove the ledger rather than trusting it.

```bash
python3 .trigpoint/trigpoint_verify.py ROADMAP.md
```

It re-runs the command inside each ticked task's `**Verified:**` line. A task whose command no
longer exits zero is unticked and given a `**Regressed:**` line recording the exit code and what
it printed. The original `**Verified:**` line stays: it was true the day it was written, and that
history is worth keeping.

**Nothing is ever ticked by this.** A machine can show a claim has become false. Deciding that
work is finished stays with a person.

## Approving commands

A command the project has not run before is reported as `awaiting approval` and is skipped.
Show the user each one **in full** and ask whether to approve it. Only on an explicit yes:

```bash
python3 .trigpoint/trigpoint_verify.py --approve '<the exact command>'
```

Never approve in bulk, and never approve a command that writes, deploys, deletes or rotates.
Verify commands are read-only assertions. This gate exists because cloning a repository that
contains a ledger would otherwise run its author's commands on this machine.

Report unticked tasks, regressions and skipped commands separately and verbatim. If something
regressed, say so plainly rather than burying it, and do not re-tick it to make the report tidy.
