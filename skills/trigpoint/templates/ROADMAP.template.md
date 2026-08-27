# {{ Project name }} - Roadmap

**The top-level reference of work.** What is being built, in what order, and what is done.

This file is the ledger, and it is the plan of record. The design behind it is
`docs/superpowers/specs/{{ YYYY-MM-DD }}-{{ topic }}-design.md`. The dashboard generated from it is
`roadmap-dashboard.html`, published at {{ dashboard artifact URL, or "not yet published" }}.

Applies to: {{ repository or repositories this plan covers }}.

**Headline:** {{ The one finding that reframes the project. One sentence. Replace this placeholder; an empty headline is worse than a blunt one. }}

---

## The stages

{{ Delete this whole section if the goal does not split into stages. }}

| | Stage 1 - {{ name }} | Stage 2 - {{ name }} |
| --- | --- | --- |
| **Goal** | {{ what is true when stage 1 ends }} | {{ what stage 2 adds }} |
| **Status** | {{ in progress / not started }} | {{ outlined only, see <document> }} |
| **Rule** | {{ the boundary rule, stated so a task can be tested against it }} | {{ when stage 2 starts }} |

**The boundary is defended on purpose.** {{ State the likeliest way this plan fails, and the test
that keeps a task on the correct side of the boundary. }}

---

## Progress at a glance

Generated. Do not hand-edit anything between the markers. Run `python3 .trigpoint/build_dashboard.py`.

<!-- trigpoint:progress:begin -->
| Track | Scope | Tasks | Done | Blocked by |
| --- | --- | --- | --- | --- |
| **T1 {{ Track name }}** | {{ what this track makes true, in one short phrase }} | 3 | 0 | nothing |
| **T2 {{ Track name }}** | {{ what this track makes true }} | 2 | 0 | T1 |
| **Total** | | 5 | 0 | |
<!-- trigpoint:progress:end -->

{{ One or two sentences naming what actually blocks and where the critical path runs. }}

```
{{ The dependency figure. One claim: what blocks, and what runs in parallel from hour one. }}
```

---

## T1 {{ Track name }}

**Scope:** {{ what this track makes true, in one short phrase }}
**Blocked by:** nothing

{{ Why this track exists, with the numbers the audit found. Adjectives here mean the audit was
not read carefully enough. }}

- [ ] **1.1** {{ Task text. What is done, specifically enough that its verification is obvious. }}
- [ ] **1.2** {{ Task text }}
- [ ] **1.3** {{ Task text }}

## T2 {{ Track name }}

**Scope:** {{ what this track makes true }}
**Blocked by:** T1

{{ Why this track exists, and why it is blocked by T1. }}

- [ ] **2.1** {{ Task text }}
- [ ] **2.2** {{ Task text }}

{{ Add one section per track, following the same shape. Track identifiers are identifiers, not a
sequence: if two tracks run in parallel, say so in the dependency figure rather than implying an
order by their numbers. }}

---

## Deferred work

{{ Work that is real, is not in scope now, and would otherwise be rediscovered every session.
Each entry says what it is, roughly what it costs, and why it is not now. Delete this section only
if there genuinely is none. }}

- **{{ item }}.** {{ size }}. {{ why it is deferred }}

---

## Hand-off contracts

Parallel work fails by drifting apart silently, not by colliding. Contracts are therefore **files
in the repository, not messages between agents**: messages die with a session, files are versioned
and survive a context reset. Each contract below is machine-checked, so drift breaks a build.

| | Contract | Enforced by |
| --- | --- | --- |
| **C1** | {{ the file that holds the contract, and who updates it when }} | {{ the test or gate that fails when it drifts }} |
| **C2** | {{ contract }} | {{ enforcement }} |

**Ledger discipline.** A box above is ticked only with evidence recorded beneath it: a
`**Verified:**` line naming the command that was run, or a `**Recorded:**` line stating what
happened for work no command can re-check. Never on assumption.
`python3 .trigpoint/check_drift.py` fails the build otherwise.

The format of a ticked task, as an example rather than as a live task. The evidence line may sit
on the task line itself or indented beneath it:

```markdown
- [x] **1.3** Set `ddl-auto=validate` in the dev profile
      **Verified:** `grep -q '^spring.jpa.hibernate.ddl-auto=validate$'
      src/main/resources/application-dev.properties`. 2026-08-27

- [x] **0.4** Delete stale `bin/`   **Verified:** `test ! -e bin/`. 2026-08-27

- [x] **0.5** Migrate the production database to the new schema
      **Recorded:** Ran against production at 09:12 UTC, 4,812 rows migrated, verified by
      spot-check. 2026-08-27
```

The `**Verified:**` text records the command that was actually run, in backticks, and the date
it was proven. It does not record what the command printed: nothing re-reads that, and evidence
the tool never checks is decoration that goes stale.

Work that no command can re-check uses `**Recorded:**` instead, stating what happened and when.
It is never re-run and never unticked by machine. Use it rather than inventing a command that
would pass whether or not the claim is true. A ticked
task whose evidence is still an unfilled `{{ placeholder }}` fails the gate exactly as a missing
evidence line does, so this template ships no ticked task for anyone to copy half-filled.

---

## Definition of done

Each criterion is falsifiable on purpose: someone can look at the system and say it is false.
{{ What starts when all of them are demonstrated. }}

- [ ] 1. {{ A criterion naming an observable event, not an adjective. }}
- [ ] 2. {{ Criterion }}
- [ ] 3. {{ Criterion }}

---

## Companion documents

| Document | Contents |
| --- | --- |
| `docs/superpowers/specs/{{ YYYY-MM-DD }}-{{ topic }}-design.md` | The design this plan implements |
| `docs/trigpoint/audit/{{ lane }}.md` | {{ one row per lane that ran }} |

---

## Audit coverage

**Lanes run:** {{ comma-separated lane names, for example: boot from clean, reachability, contract drift }}
**Lanes not run:** {{ comma-separated lane names, or "none" }}

{{ For each lane that did not run, one line saying why, and what therefore has not been looked at.
An unrun lane is an unsearched area, not a clean one. }}
