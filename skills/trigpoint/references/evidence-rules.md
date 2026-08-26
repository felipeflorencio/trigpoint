# Evidence rules

Apply these to every finding before it reaches the question ladder, and to every box before it is
ticked. In the source run 248 findings went in and 15 came out confirmed, 3 sharpened, 1 refuted.
A gate that lets most findings through is not doing its job.

## Tag every finding

| Tag | What it means | What it becomes |
| --- | --- | --- |
| `CONFIRMED` | You read the evidence yourself and your refutation attempt failed | A task |
| `PLAUSIBLE` | Consistent with what you saw, but the proving check did not happen | An **investigation task**, worded as "Determine whether X" |
| `REFUTED` | You checked and it is not true | A recorded line saying so, kept, not deleted |
| `UNVERIFIED` | The check did not complete | Reported as unverified, with the reason. Never as clean |

Only `CONFIRMED` becomes a task to do. Never promote a `PLAUSIBLE` finding by re-reading it
harder; promote it by running the check that was missing.

Keep `REFUTED` findings in the audit file. Delete them and the next session rediscovers them and
spends the same tokens.

## The rules

**Tool inference is not evidence.** A knowledge graph asserted a dead-code relationship that was
exactly inverted. Static analysis, graph queries, search results and other agents' summaries are
leads. Confirm each by reading the code it points at. Every deletion in particular carries a
reachability trace from a real entry point, walked by you.

**Two independent agents converging is the strongest signal available.** Two lanes found the same
dead configuration variable by different methods, and that finding was trusted immediately. When
two lanes reach the same conclusion from different directions, say so explicitly in the finding.
Two agents given the same method are one agent and converge on nothing.

**Calibrate with controls before trusting any sweep.** Before believing a search, a script or a
scan across many files, check one case you know is true and one you know is false. If the positive
control does not come back positive, or the negative control comes back positive, the sweep is
meaningless. Discard it and say you discarded it.

**A failed check is never an absence.** A timeout, a 429, a refused connection, a missing
credential, a permission error: each is `UNVERIFIED` with the reason recorded. Rate limiting and a
genuine empty result are indistinguishable if you only look at whether data came back, so look at
the status.

**A count is never verification.** "41 endpoints checked" says nothing about whether the right ones
were checked or whether the checks were sound. State what was checked and, in the same breath,
what was not.

**Discard poisoned data loudly.** When a source turns out to be unreliable, exclude it and document
the incident in the audit file. Quietly dropping it leaves a coverage hole that later reads as a
clean area.

## Ticking a box is the same gate

A ticked task is a finding of the same kind: a claim that something is now true. It carries the
same evidence requirement, and here the requirement is mechanical.

```markdown
- [x] **1.2** Set `ddl-auto=validate` in the dev profile
      **Verified:** `./gradlew bootRun` -> started, validation passed. 2026-08-27
```

**A `[x]` with no `**Verified:**` line is a hard error and the build refuses.**
This is not
configurable. The moment it can be turned off, someone turns it off, and automatic mode stops being
safe.

The line records **the command that was actually run and what came back**. Not a description of the
change, not "confirmed working", not the intent. If you did not run a command, the box is not
ticked. The line may be short, so a trivial task costs one line:

```markdown
- [x] **0.4** Delete stale `bin/`   **Verified:** `ls bin/` -> absent. 2026-08-27
```

## Two operational guards

**Budget the phase.** Parallel agents share a quota. When it runs out, agents fall back silently
and return something that looks like a clean result. Give each lane a search budget, or sequence
the lanes.

**Batch edits apply what matches.** A script that asserts every pattern before writing discards all
edits when one fails, and a commit in the same command then records a message describing changes
that were never applied. This happened twice in the source session. The rule: apply what matches,
write regardless, report applied and failed separately, and **never commit in the same breath as an
edit**.
