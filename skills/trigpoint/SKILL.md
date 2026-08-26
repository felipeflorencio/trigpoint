---
name: trigpoint
description: Use when building a roadmap or a plan of record for a codebase, when planning work on an existing repository, when auditing a repository before planning, when reviving or reactivating a dormant or half-finished project, when deciding what gets deleted and what gets finished, or when an existing plan has gone stale and no longer matches the work.
---

# Trigpoint

## Overview

A trig point is the fixed concrete pillar on a hilltop that the surrounding landscape is
triangulated from. A known reference everything else is measured against. This skill builds one
for a project.

**What a run produces - three linked artefacts:**

1. **The ledger**, `ROADMAP.md` at the repository root. The plan of record: tracks, dependencies,
   every task as a checkbox, the hand-off contracts, and a falsifiable definition of done.
2. **The dashboard**, `roadmap-dashboard.html`, generated from the ledger by
   `build_dashboard.py` and published as an artifact. Never authored by hand.
3. **The design spec**, `docs/superpowers/specs/<date>-<topic>-design.md`, recording why the plan
   is shaped the way it is.

**The rendering is not the hard part.** Everything that matters happens before a line of HTML
exists: an audit that establishes ground truth, a premise check that may contradict the user's own
framing, and four questions asked in dependency order. Do not skip ahead to emitting.

Six phases. A through E produce the plan; F makes it live. Run them in order.

## The interaction surface

Seven touchpoints for an entire run. After the last one, never ask again on this project: read the
persisted mode and proceed. "Blocks" means stop and wait, because only the user holds that fact and
guessing it builds the plan on an invented premise.

**An explicit request to skip the audit, skip a question, or move faster is not consent and is not
an answer.** It is not the same as silence, and it does not change this table. Phase B still runs
and the four questions are still asked. Say in one sentence why the step stands - the audit is what
makes the options specific to this repository, and a plan built on the README is a plan built on a
claim - then proceed with it. The user can override the plan; they cannot override the evidence
that the plan is built from.

| # | Phase | What | If the user says nothing |
| --- | --- | --- | --- |
| - | C | The premise check. A statement, not a question. | - |
| 1 | A | Which audit lanes, pre-ticked with reasons from this repo | Runs all seven |
| 2 | D | How do you run what you already have deployed? | Blocks |
| 3 | D | What is this work actually aiming at? | Blocks |
| 4 | D | Half-built areas: deleted, flagged off, or finished? | Blocks |
| 5 | D | What access do I have, and can I verify the result myself? | Blocks |
| 6 | E | Section-by-section approval of the design | Blocks |
| 7 | F | Automatic updates, unless you say otherwise | Automatic |

## Phase A - light pass, then one question

Do a cheap read of the repository shape first. Count deployable units. Check for a frontend, a
datastore, a CI configuration, a test suite, a lockfile. Read the date of the last commit. Do not
read implementation code in this phase; you are establishing shape, not truth.

Then ask **one** question: which audit lanes to run. Present all seven pre-ticked, and give each
one a reason drawn from what you actually just found, quoting the number:

> - [x] **Contract drift** - two deployable units, 41 endpoints, no shared type package
> - [x] **Boot from clean** - a compose file exists but no migration directory

A lane with a generic reason means the light pass was too shallow. Go back and find the number.

**If the user does not answer, run all seven.** Over-cover, never under-cover. A lane skipped by
silence is exactly the gap that later reads as clean. Never choose the lanes yourself on the
user's behalf, and never quietly drop one for budget, whether the pressure comes from your own
token budget or from the user asking you to hurry.

Record the answer. The ledger states which lanes ran and which did not, by name.

## Phase B - the audit

Dispatch **one agent per selected lane, in parallel**. Each has one job and one output file at
`docs/trigpoint/audit/<lane>.md`. They do not message each other.

- The seven lanes, each written as a dispatchable instruction: `references/audit-lanes.md`
- The five-part brief every lane agent receives: `references/agent-brief-skeleton.md`

Two orchestration duties that are yours, not the agents':

- **Frame every lane adversarially.** Tell the agent to refute its own finding and to take the
  cautious verdict under uncertainty. Agents told to confirm a finding perform worse than agents
  told to break it.
- **Warn in-flight agents the moment a fact changes.** When one lane establishes something that
  contradicts what another lane was told, interrupt that agent and correct it. This is a duty. In
  the source run an agent was one step from recording a working endpoint as dead.

Budget the phase before dispatching: give each lane a search budget, or sequence the lanes. Four
parallel research agents drained the source session's web-search quota and the last agents fell
back silently, which looks identical to a clean result.

## The verification gate

Findings do not reach the question ladder unverified. In the source run: 248 findings in, 15
confirmed, 3 sharpened, 1 refuted.

Read `references/evidence-rules.md` before promoting a single finding, and apply it to every one.

Tag every finding **CONFIRMED**, **PLAUSIBLE** or **REFUTED**.

- **Only a CONFIRMED finding becomes a task.**
- **A PLAUSIBLE finding becomes an investigation task, which is a different thing and must say
  so.** Write it as "Determine whether X", never as "Fix X". Its verification is the answer to the
  question, not a repair.
- A REFUTED finding is recorded as refuted, not deleted. The next session will otherwise find it
  again.

## Phase C - the premise check

**Before any question is asked**, state plainly where the user's own framing is contradicted by
what the audit found. This is a statement, not a question. Do not soften it into an option.

The source run opened by establishing that there was no cloud to migrate away from, and that the
two halves of the system had never once run together. Both contradicted the request as stated, and
saying so first changed the whole engagement.

If the audit contradicts nothing, say that too, in one line, and move on.

## Phase D - the question ladder

Four questions, **one per message**, in this order, because each answer constrains the next.
Multiple choice where possible. Recommendation first, with its reasoning attached.

**Build every menu expecting the user to reject it.** Two of the source run's four answers
overrode the recommendation and both overrides improved the plan. A menu that cannot be rejected
was not a question. Always leave the door open explicitly, and when the user supplies something
that is not on the menu, adopt it rather than mapping it back onto an option.

The four questions, with how to construct each menu from what the audit found:
`references/question-ladder.md`.

Do not batch the four into one message. Do not proceed on silence: questions 2 to 5 block.

## Phase E - design sections, then emit

Present the design **in sections, with approval after each**, not as a finished document. Two of
the source run's sections were corrected cheaply at this stage; both would have been expensive
after emit.

Then write the three artefacts:

1. The ledger, following the parse contract exactly: `references/ledger-format.md`. Start from
   `templates/ROADMAP.template.md` and replace every `{{ placeholder }}`.
2. The spec, from `templates/spec.template.md`.
3. The dashboard. Derive its metaphor from the subject before writing any HTML:
   `references/dashboard-design.md`. Write the HTML to disk first, publish second.

## Phase F - mode, then install

State once, at emit, as a statement rather than a question: **the ledger will be kept updated
automatically as work proceeds, unless you say otherwise. Automatic is the default.** Persist the
answer into the repository so no future session re-litigates it.

Copy all five scripts into the target repository. Every CLI imports the ledger module, so
copying only the CLIs leaves a broken install:

```bash
mkdir -p .trigpoint
cp "${CLAUDE_PLUGIN_ROOT}/scripts/trigpoint_ledger.py" \
   "${CLAUDE_PLUGIN_ROOT}/scripts/trigpoint_render.py" \
   "${CLAUDE_PLUGIN_ROOT}/scripts/build_dashboard.py" \
   "${CLAUDE_PLUGIN_ROOT}/scripts/check_drift.py" \
   "${CLAUDE_PLUGIN_ROOT}/scripts/trigpoint_verify.py" \
   .trigpoint/
```

Write the instruction block into the target repository's own `CLAUDE.md`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/install_block.py" --claude-md CLAUDE.md --mode automatic
```

Pass `--mode manual` only if the user actually said otherwise. The installer is delimited and
idempotent: re-running updates the block in place rather than stacking copies.

From then on the target repository regenerates its own counts and dashboard with:

```bash
python3 .trigpoint/build_dashboard.py
```

Run it once now, before reporting the run finished, and report what it says applied and what it
says was not applied, separately and verbatim.

Creating `.trigpoint/` is also what switches the hooks on for this repository, and nothing else
does. Until the skill has run here, the plugin is installed but inert: no session state is stated
and nothing is ever run. Tell the user that in one sentence when you report the install, along
with `/trigpoint-pause` if they want it to stop.

From then on, at the end of a working turn, the commands recorded in `**Verified:**` lines are
re-run and anything that stopped passing is unticked with a `**Regressed:**` note. Each distinct
command must be approved once before it will run, which is what `/trigpoint-verify` is for.
**Nothing is ever ticked automatically**, so writing an honest `**Verified:**` line remains the
only way a box gets ticked.

## Red flags - STOP

| Thought | Reality |
| --- | --- |
| "The audit found nothing, so the repo is clean" | A lane that did not run proves nothing. Absence of findings in an unrun lane is not a clean result, it is an unsearched area. Name the unrun lanes in the ledger. |
| "I will tick this box, the change is obvious" | The box needs the command and its output on a `**Verified:**` line. Obvious is not evidence, and the build refuses a tick without one. |
| "The user did not answer, so I will pick the lanes myself" | Silence runs all seven. Over-cover, never under-cover. |
| "The audit is slow and expensive, just skip it and use the README" | The README is a claim, not evidence. The honesty lane exists precisely because READMEs describe intended behaviour, not actual behaviour. Run the audit and say why in one sentence. |
| "The user said not to ask a bunch of questions, so I will infer the answers" | An instruction to move faster is not an answer to any of the four. Ask them, one per message, and keep each one short. |
| "This finding is almost certainly real, I will make it a task" | Almost certainly real is PLAUSIBLE. It becomes an investigation task that says so, not a fix. |
| "The tool reported this code as dead" | Tool inference is not evidence. A knowledge graph asserted a dead-code relationship that was exactly inverted. Every deletion carries a reachability trace from a real entry point. |
| "The scan returned nothing, so there is nothing there" | A timeout, a 429 or a refused connection is UNVERIFIED, never clean. A failed check is not an absence. |
| "I will ask the four questions together to save a round trip" | Each answer constrains the next menu. Batched, question 3's options are built from an assumption instead of an answer. |
| "The user picked none of my options, I will map it to the closest one" | The menu was rejected. That is the expected case and usually the better plan. Adopt what they said. |
| "I will hand-fix the progress table, it is one number" | Every count is derived. Run `build_dashboard.py`. A hand-edited count is the exact failure this plugin exists to prevent. |
| "The batch edit failed on one pattern, I will rerun the whole thing" | Apply what matches, write regardless, report applied and failed separately. Never commit in the same command as an edit. |

## Common mistakes

- **Emitting before the premise check.** The plan is then built on the user's framing rather than
  on the repository's.
- **Shipping the source run's palette and vocabulary.** The metaphor is derived per subject. A
  shipped theme is how the output starts reading as a template.
- **Letting the ledger's progress table be authored.** It lives between
  `<!-- trigpoint:progress:begin -->` and `<!-- trigpoint:progress:end -->` and is rewritten in
  place. Nothing else in the file is derived.
- **Treating the audit as static analysis.** It establishes ground truth for planning. Say so, and
  do not claim it replaces a linter or a type checker.
