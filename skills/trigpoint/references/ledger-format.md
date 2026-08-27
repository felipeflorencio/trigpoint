# The ledger format

Write the ledger to `ROADMAP.md` at the repository root. Start from
`../templates/ROADMAP.template.md` and replace every `{{ placeholder }}`.

## Authored versus derived

Every line is one or the other. Write nothing that is both.

| Authored - you write it | Derived - a script writes it, always |
| --- | --- |
| Track sections, scope, blocked-by | Every count in the progress table |
| Every task line | Done totals, per track and overall |
| Contracts table | The whole dashboard HTML |
| Definition of done | The definition-of-done scoreboard |
| The reframing finding | Which tracks are unblocked right now |
| Which audit lanes ran | |

The derived region is delimited. Write the markers and leave the space between them for the script:

```markdown
<!-- trigpoint:progress:begin -->
<!-- trigpoint:progress:end -->
```

`build_dashboard.py` rewrites that region inside the ledger and emits the HTML in the same pass, so
the two artefacts are structurally incapable of disagreeing. **Never hand-edit a count.** If a
number looks wrong, run the script; if it still looks wrong, the task lines are wrong and that is
where you fix it.

## The parse contract

Write natural markdown. There are three rules and no schema beyond them.

```markdown
## T1 Foundation

**Scope:** Make it boot from clean
**Blocked by:** nothing

Nothing real starts until this lands. A fresh database currently fails Hibernate
validation: 17 missing columns, 2 missing tables.

- [ ] **1.1** Write `V1__reconcile_entity_drift.sql`
- [x] **1.2** Set `ddl-auto=validate` in the dev profile
      **Verified:** `grep -q '^spring.jpa.hibernate.ddl-auto=validate$'
      src/main/resources/application-dev.properties`. 2026-08-27
```

**Rule 1.** `## T<id> <name>` opens a track. The `**Scope:**` and `**Blocked by:**` lines are its
metadata and both are required. A `##` section is treated as a track **if and only if** it contains
a `**Scope:**` line, so never put that line in a section that is not a track.

**Rule 2.** `- [ ] **<id>** <text>` is a task. That is the whole grammar. The identifier goes in
bold immediately after the checkbox. Task identifiers are unique across the whole ledger; a
duplicate is an error.

**Rule 3.** A `[x]` with no evidence line is a hard error and the build refuses. It is not
configurable.

Evidence is one of two markers, and the text of either may sit on the task line itself or on an
indented continuation line beneath it. A marker owns the text up to the next marker, not to the
end of the block.

- `**Verified:** \`command\`. DATE` asserts something. The command is re-run at the end of a
  working turn and the box unticks itself when it stops passing. The command is the first
  backticked span; ledgers written before 0.3.0 carry a `-> output` tail after it and still read
  correctly.
- `**Recorded:** what happened. DATE` records something. Nothing re-runs it and no machine unticks
  it. Its backticks quote names, not commands, and are never executed.

A block carrying both is read as verified, unless the `**Verified:**` marker is empty, in which
case it falls through to the record. Never invent a command to satisfy the gate: a proxy that
passes whether or not the claim is true is worse than an honest record.

Two further mechanics worth knowing while writing:

- An indented line under a task belongs to that task. An unindented line ends it.
- Anything inside a fenced code block is documentation, not work. A fenced `- [x]` example
  is not parsed as a task and its `**Verified:**` line is not read as evidence, so worked
  examples of the format can be written into the ledger safely.
- `**Blocked by:**` is read for track identifiers, so write `T1` or `T3` where you mean a track.
  Write `nothing` when a track is blocked by nothing. A named identifier that is not a track in
  this ledger produces a warning.
- The `## Definition of done` section is read for `- [ ]` criteria. Those are not tasks and do not
  need identifiers, but they do need to be falsifiable.

## Section order

Write the ledger in this order:

1. **Header.** Title as `# <name>`, the statement that this file is the ledger, links to the
   companion documents and to the dashboard artifact URL.
2. **The reframing finding**, on a `**Headline:**` line. This is the one sentence that changes how
   the reader sees the project. The dashboard reads this line, so it must not be left empty.
3. **Stage table**, when the goal splits into stages, with the boundary rule stated.
4. **Progress at a glance**, the marker pair and nothing else between it.
5. **Dependency figure.** One claim: what blocks, and where the critical path runs.
6. **Track sections with tasks.**
7. **Deferred work.**
8. **Hand-off contracts**, each with what enforces it.
9. **Definition of done**, falsifiable.
10. **Companion documents.**
11. **Audit coverage**, on `**Lanes run:**` and `**Lanes not run:**` lines. The dashboard reads
    both. "The honesty lane was not run" is an honest line in a plan of record; silence there
    implies coverage that never happened.

## Lines the dashboard reads

These four are read by `build_dashboard.py` directly and must appear literally as shown:

| Line | Used for |
| --- | --- |
| `# <title>` | The dashboard title |
| `**Headline:** <one sentence>` | The reframing finding at the top of the dashboard |
| `**Lanes run:** <comma-separated>` | The footer's coverage statement |
| `**Lanes not run:** <comma-separated>` | The footer's coverage statement |

## Verify before you hand it over

```bash
python3 .trigpoint/build_dashboard.py
python3 .trigpoint/check_drift.py ROADMAP.md
```

The first must report the progress table applied. If it reports the marker region not found, the
marker pair is missing or misspelled. The second must report no errors; warnings are readable
information, not a failure.
