<img src="assets/cover.png" alt="Trigpoint: a plan of record that cannot drift" width="100%">

# Trigpoint

**Your agent's plan was accurate the day it was written. It has not been accurate since.**

Trigpoint is a Claude Code plugin that turns a codebase into a plan of record which cannot quietly
go out of date.

---

## A week with an ordinary plan

**Monday.** You ask an agent to plan the work. It reads the repository and produces something
genuinely good: 40 tasks across 6 tracks, dependencies mapped, a summary table at the top.

**Tuesday.** You finish three tasks. Two others turn out to have been done months ago. One of them
uncovers four more that nobody knew existed.

**Friday.** The table at the top still says **0 of 40 done**. Nobody updated it, because updating
it was nobody's job. The four discovered tasks live in a chat window that has since been closed.

**Next Monday.** A fresh session opens the plan and believes the table. It schedules work that is
already finished, and it has never heard of the four tasks that turned out to matter most.

The plan did not fail because it was wrong. It failed because it **stopped being true**, and
nothing announced that it had.

---

## Why plans rot

Three causes, none of which are fixed by trying harder.

**Counts are typed by hand.** A header that reads "12 of 40" is one person's memory of the
checkboxes below it. It is correct on the day it is written and wrong soon after. The fix is not
more discipline. The fix is to stop typing it.

**"Done" is a claim, not a fact.** A ticked box asserts that something happened. It carries no
evidence that it did. An agent in a hurry ticks the box it believes is finished, and belief is not
the same as having run the command and read the output.

**Discovered work has nowhere to land.** The most valuable thing a week of implementation produces
is the work nobody predicted. It gets mentioned in conversation, and it dies when the session ends.

---

## What Trigpoint does about it

**Nobody types a number.** The summary table is regenerated from the task lists themselves. A
count cannot disagree with the tasks it counts, because it is derived from them. Continuous
integration regenerates it and fails the build on any difference, so drift is not discouraged, it
is impossible.

**A tick requires evidence.** A ticked task must carry the command that was run, or, when no
command can re-check the work, a record of what happened. There is no exemption for obvious tasks,
and no setting to turn it off, because the moment there is one an agent decides what counts as
obvious. Six months later you can see not only that
something was done, but how anyone knew.

**The rules live in your repository.** They are written into your `CLAUDE.md` as plain markdown, so
every future session picks them up automatically, and a colleague who has never installed this
plugin still gets them.

**The questions come after the evidence.** Trigpoint audits the code before it asks you anything,
so the options it offers are drawn from what is actually there. A plan built from a README is a
plan built from a claim.

---

## What you get

- **Numbers you can trust.** Generated, never typed.
- **Progress you can believe.** Every completed task carries proof.
- **A plan that survives context resets.** It lives in the repository, not in a chat window.
- **Questions grounded in your real code**, not in what the documentation claims.
- **Something to scan as well as read.** A generated dashboard alongside the markdown.

---

## When to reach for it

- **You have inherited a codebase** and need to know what is real before promising anything.
- **A project has gone dormant** and you cannot tell what still works, what half-shipped, and what
  should simply be deleted.
- **An agent wrote you a plan** and a week later you no longer trust it.
- **The work will span many sessions**, so whatever holds the plan has to outlive any one of them.
- **Several people or agents are working in parallel** and you need one place that says what is
  actually done.

It is a poor fit for a small change you can hold in your head, or for a greenfield project with no
existing code to audit. It earns its keep where there is more truth to establish than you can keep
in working memory.

---

## What a run produces

Three linked artefacts. The examples below are not mock-ups: they are this repository's own
`ROADMAP.md`, which Trigpoint's rules govern and whose gate runs against it in CI.

**1. The ledger,** `ROADMAP.md` at the repository root. Tracks, dependencies, every task as a
checkbox, the hand-off contracts, and a falsifiable definition of done. A ticked task carries the
command that was run and the date it was proven, or, for work no command can re-check, a record of
what happened:

```markdown
- [x] **1.2** Write ledger validation: a ticked task with no `**Verified:**` line is an error, a
      duplicate task id is an error, an unknown `**Blocked by:**` reference is a warning
      **Verified:** `python3 -m unittest tests.test_ledger_validate -v`. 2026-08-26

- [x] **5.2** Publish the plugin to a marketplace and verify a real install from outside this
      checkout
      **Recorded:** Published to `felipeflorencio/claude-plugins`; `claude plugin update
      trigpoint` reported 0.1.0 to 0.2.0 on a machine outside this checkout. 2026-08-27
```

`**Verified:**` names a command, is re-run at the end of every working turn, and unticks its box
when the command stops passing. `**Recorded:**` names something that happened, and is never re-run
or unticked by machine. The second exists so that nobody has to invent a command for work that has
none: a proxy that passes whether or not the claim is true is worse than an honest record.

**2. The progress table,** generated in place inside that same ledger, between a pair of markers.
Nobody types these numbers. This is the current table from this repository, verbatim:

```markdown
<!-- trigpoint:progress:begin -->
| Track | Scope | Tasks | Done | Blocked by |
| --- | --- | --- | --- | --- |
| **T1 Parser and gate** | The ledger model, its validation rules, and the read-only CI gate built on them | 6 | 6 | nothing |
| **T2 Generation** | The generated progress table, the dashboard renderer, and the sync CLI that writes both | 4 | 4 | T1 |
| **T3 Installation** | The CLAUDE.md instruction block installer | 3 | 3 | T1 |
| **T4 Packaging** | The plugin and marketplace manifests, the slash commands, and the skill with its references and templates | 4 | 4 | T1, T2, T3 |
| **T5 Publication** | The README, the cover art, the published marketplace listing, and a verified real install | 2 | 0 | T4 |
| **Total** | | 19 | 17 | |
<!-- trigpoint:progress:end -->
```

**3. The dashboard,** `roadmap-dashboard.html`, generated from the same parse in the same pass, so
it is structurally incapable of disagreeing with the table above. Plus a design spec recording why
the plan is shaped the way it is.

See [`examples/README.md`](examples/README.md) for what to look at in each.

---

## Install

Both routes below were run on 2026-08-26 and both succeeded.

The shared marketplace, which lists this plugin and any later ones:

```
/plugin marketplace add felipeflorencio/claude-plugins
/plugin install trigpoint@felipeflorencio
```

Or directly from this repository, which carries its own single-entry marketplace manifest:

```
/plugin marketplace add felipeflorencio/trigpoint
/plugin install trigpoint@trigpoint
```

Verified with the `claude plugin` CLI, which takes the same arguments as the slash commands:

```
$ claude plugin marketplace add felipeflorencio/claude-plugins
Successfully added marketplace: felipeflorencio (declared in user settings)

$ claude plugin install trigpoint@felipeflorencio
Successfully installed plugin: trigpoint@felipeflorencio (scope: user)
```

### Other agents

The skills, the scripts and the ledger format have nothing Claude-specific in them, so the same
plugin ships a manifest for several harnesses. Each is generated from
`.claude-plugin/plugin.json`, and CI fails if one drifts.

| Harness | Manifest |
| --- | --- |
| Claude Code | `.claude-plugin/plugin.json` |
| Codex | `.codex-plugin/plugin.json` |
| Cursor | `.cursor-plugin/plugin.json` |
| Gemini CLI | `gemini-extension.json`, with `AGENTS.md` as the context file |
| Anything reading `AGENTS.md` | `AGENTS.md` at the repository root |

**Only the Claude Code route has been installed and run end to end.** The others are manifests
built to each harness's published shape and are unverified until someone installs one, which is
worth knowing before you rely on them.

### Requirements

Python 3.9 or later, standard library only. Nothing to `pip install`. macOS and Linux already
have it.

On Windows the hooks run through `hooks/run-hook.cmd`, a polyglot wrapper that finds `py -3`,
`python3` or `python`. If none of them exist it exits quietly, so the session works exactly as
before, just without the ledger state and the re-run. The technique is borrowed from
[obra/superpowers](https://github.com/obra/superpowers), which uses the same trick to find bash.

---

## Usage

| Command | What it does |
| --- | --- |
| `/trigpoint` | Runs the whole thing from the beginning: light pass, audit, premise check, the question ladder, design sections, then emits the three artefacts. Any argument is your stated goal for the work. |
| `/trigpoint-sync` | Regenerates the progress table and the dashboard from the ledger. Reports what applied and what did not, separately and verbatim. |
| `/trigpoint-verify` | Re-runs the commands recorded in `**Verified:**` lines and unticks anything that stopped passing. Each distinct command is approved once before it will ever run. |
| `/trigpoint-pause` | Stops the hooks in this repository until you undo it with `rm .trigpoint/paused`. |

A whole run has **seven interaction touchpoints**, and after the last one the skill never asks
again on that project. "Blocks" means it stops and waits, because only you hold that fact and
guessing it would build the plan on an invented premise.

| # | What | If you say nothing |
| --- | --- | --- |
| - | The premise check. A statement, not a question. | - |
| 1 | Which audit lanes, pre-ticked with reasons drawn from your repo | Runs all seven |
| 2 | How do you run what you already have deployed? | Blocks |
| 3 | What is this work actually aiming at? | Blocks |
| 4 | Half-built areas: deleted, flagged off, or finished? | Blocks |
| 5 | What access do I have, and can I verify the result myself? | Blocks |
| 6 | Section-by-section approval of the design | Blocks |
| 7 | Automatic updates, unless you say otherwise | Automatic |

Silence on question 1 runs all seven audit lanes. Over-cover, never under-cover: a lane skipped by
silence is exactly the gap that later reads as clean. The ledger names which lanes ran and which
did not, so an absent lane never passes for a clean one.

---

## Watch it refuse

Both transcripts below are real output, run against this repository.

**A hand-edited count does not survive.** The `Total` row was edited by hand from `19 | 17` to
`24 | 22` on a scratch copy, then the generator was run:

```
$ grep -n "Total" ROADMAP.md
27:| **Total** | | 24 | 22 | |

$ python3 .trigpoint/build_dashboard.py --ledger ROADMAP.md --output roadmap-dashboard.html
applied: progress table
applied: dashboard html -> roadmap-dashboard.html

$ grep -n "Total" ROADMAP.md
27:| **Total** | | 19 | 17 | |
```

CI closes the loop: the workflow regenerates both files and runs `git diff --exit-code`, so a
committed count that disagrees with the tasks fails the build.

**A tick without evidence does not pass.** Two ticked tasks, one with no evidence at all and one
whose evidence is still an unfilled template:

```markdown
- [x] **1.1** Wire the export endpoint
- [x] **1.2** Add the retry budget
      **Verified:** {{ command and output }}
```

```
$ python3 .trigpoint/check_drift.py ROADMAP.md; echo "exit code: $?"
ROADMAP.md: 2 task(s) in 1 track(s) and 0 definition-of-done criteria; 2 ticked, 1 carrying evidence; 2 checkbox line(s) read, 0 not claimed as either.
ERROR  ROADMAP.md:8  task 1.1 is ticked with nothing behind it. Add a **Verified:** line naming the command that was run, or a **Recorded:** line stating what happened and when, or untick it.
ERROR  ROADMAP.md:9  task 1.2 is ticked but its evidence line still contains an unfilled {{ placeholder }}. Record the command that was actually run, or what actually happened, or untick it.
2 error(s), 0 warning(s) in ROADMAP.md
exit code: 1
```

**The gate states what it read, and refuses to pass a file it read nothing from.** Exit codes are
`0` clean, `1` at least one error, `2` the ledger or the install cannot be read, and `3` nothing
was checked. Exit 3 is the one
worth knowing about: point the gate at a ROADMAP.md that has never been converted and you get a
diagnostic rather than a green tick.

**Already have a ROADMAP.md?** The most common reason a real one parses as zero tasks is a missing
`**Scope:**` line. A section becomes a track only by carrying one directly under its heading, so a
document with correct `## T1 - Foundation` headings and correct `- [x] **0.1** text` task lines
still reads as empty without it. The gate says so specifically rather than leaving you to guess.

```
$ python3 .trigpoint/check_drift.py PLANS.md; echo "exit code: $?"
PLANS.md: 0 task(s) in 0 track(s) and 0 definition-of-done criteria; 0 ticked, 0 carrying evidence; 33 checkbox line(s) read, 33 not claimed as either.
PLANS.md: no tasks parsed although 33 checkbox line(s) are present. Either this file is not a Trigpoint ledger, or the parser has stopped recognising it. A section becomes a track by carrying a **Scope:** line, and a task line reads `- [ ] **1.1** text`. NOTHING WAS CHECKED; this is not a pass.
exit code: 3
```

---

## The worked example

The method comes from one real run against a dormant two-part codebase. The audit put **248
findings** in front of the verification gate; **15** came out CONFIRMED, 3 were sharpened and 1 was
refuted. Only a confirmed finding became a task. The plan that resulted was **67 tasks across 8
tracks**.

---

## Limits

- **It does not replace static analysis.** It establishes ground truth for planning. It is not a
  linter and it is not a type checker; run those too.
- **It is version 0.3.0.** The ledger, the drift gate and the verifier are covered by a test
  suite CI runs on every push; `python3 -m unittest discover -s tests` reports the count, which is
  why this sentence does not. A number here that nothing re-reads is exactly the decoration this
  tool stopped keeping in its own evidence lines, and it had already been wrong twice. The plan it hands you is a strong first draft to argue with, not a verdict.

---

## What is in here

| Path | What it is |
| --- | --- |
| `skills/trigpoint/SKILL.md` | The process: audit, then the question ladder, then emit |
| `skills/trigpoint/references/` | The seven audit lanes, the four questions, the evidence rules, the parse contract |
| `scripts/trigpoint_ledger.py` | Parses a ledger's tracks, tasks and definition of done. No filesystem access |
| `scripts/trigpoint_render.py` | Renders the parsed ledger into the progress table and the dashboard HTML |
| `scripts/build_dashboard.py` | Regenerates the progress table in place and writes the dashboard |
| `scripts/check_drift.py` | The read-only CI gate over the same parse |
| `scripts/trigpoint_verify.py` | Re-runs the commands the ledger records and unticks what stopped passing. Never ticks |
| `hooks/` | The session-start and end-of-turn hooks, and the guard that keeps both silent in any repository that never opted in |
| `scripts/install_block.py` | Installs the delimited block into a target repository's `CLAUDE.md` |
| `commands/` | The four slash commands: `/trigpoint`, `/trigpoint-sync`, `/trigpoint-verify`, `/trigpoint-pause` |
| `ROADMAP.md` | This repository's own ledger, kept under its own rules |
| `assets/cover.html` | The source of the cover image, version-controlled rather than a loose binary |

Run the checks locally with `python3 -m unittest discover -s tests` and
`python3 scripts/check_drift.py ROADMAP.md`.
