# Trigpoint - design

**Written:** 2026-08-26
**Status:** approved, not yet implemented
**Source material:** `BRIEF-roadmap-artifact-skill.md`, and the run it describes (a private
reference project's `ROADMAP.md`, its dashboard artifact, and
`docs/superpowers/specs/2026-08-26-reactivation-stage1-design.md`)

---

## 1. What this is

A Claude Code plugin that turns a codebase and a stated goal into three linked artefacts, then
keeps them true while the work is done:

1. **A ledger** at the repository root. The plan of record. Tracks, dependencies, every task as a
   checkbox, the hand-off contracts, and a falsifiable definition of done.
2. **A visual dashboard**, generated from the ledger, published as an artifact. Same plan, built
   for scanning and operating rather than reading.
3. **A design spec** recording why the plan is shaped the way it is.

A trig point is the fixed concrete pillar on a hilltop from which the surrounding landscape is
triangulated. A known reference that everything else is measured against. That is what the
ledger is for a project.

### The problem it solves

Plans produced by an agent go stale within a week, and a stale plan is worse than no plan,
because it is still consulted. Two mechanisms cause the rot:

- **Counts drift.** In the source run the summary table was hand-maintained. Counts were
  corrected by hand three times as agents landed and diverged from the task lists twice.
- **Discovered work never lands.** Work found mid-development lives in a chat window and dies
  with the session, so the ledger silently stops describing the project.

Trigpoint makes the first structurally impossible and makes the second an instruction that binds
every future session.

### What made the source run good, and what is being packaged

The rendering was never the hard part. Everything that mattered happened before a line of HTML
was written: an audit that established ground truth, a premise check that contradicted the
user's own framing, and four questions asked in dependency order. That is the transferable
method, and it is what this plugin is.

## 2. Non-goals

- **Not a task tracker.** No sync to Jira, Linear or GitHub Issues. The ledger is a file in the
  repository, on purpose, because files survive a context reset and messages do not.
- **Not an execution engine.** It produces a plan and keeps it honest. It does not implement it.
- **Not a linter.** The audit establishes ground truth for planning. It is not a replacement for
  static analysis, and it says so.
- **No hosted service.** Distribution is a GitHub repository. There is no backend and no account.

## 3. The run, end to end

Six phases. A through E produce the plan. F makes it live.

### Phase A - light pass and lane selection

A cheap read of the repository shape: how many deployable units, is there a frontend, a
datastore, a CI configuration, a test suite, a lockfile, how old is the last commit.

That grounds **one question**: which audit lanes to run. Lanes arrive pre-ticked, each carrying a
reason drawn from what was actually found, for example "Contract drift - ticked: two deployable
units, 41 endpoints, no shared type package."

**If the user does not answer, all seven lanes run.** Over-cover, never under-cover. A lane
skipped by silence is exactly the gap that reads as clean.

**The ledger records which lanes ran and which did not.** "The honesty lane was not run" is an
honest line in a plan of record. Silence there would imply coverage that never happened.

### Phase B - the audit

Seven lanes, run as parallel agents. Each has one job and one output file. They do not message
each other.

| Lane | Question it answers | Output |
| --- | --- | --- |
| Boot from clean | Does this start from a fresh clone and a fresh datastore? | The gap between "runs on my machine" and "runs at all" |
| Reachability | What is reachable from a real entry point? | Wired / half-wired / dead, per route, endpoint, screen |
| Contract drift | Where do the two halves disagree? | Field-by-field diff: caller expectation vs callee reality |
| Honesty | Does the UI claim things that do not happen? | Mock defaults, fake success states, controls wired to nothing |
| Secrets and authz | What is exposed? | Hardcoded credentials, unauthenticated routes, object-level gaps |
| Test and CI reality | What is actually gated? | Not "tests exist" but "what would a bad commit hit" |
| Subtraction | What can be deleted? | Every candidate carries a reachability trace to a real entry point |

The **honesty lane** has no equivalent in existing tooling and produced the source run's best
finding. A frontend defaulting to mock data reports success while connected to nothing. Linters,
type checkers and test suites all pass on it.

#### The agent brief skeleton

Every lane agent receives the same five-part brief, parameterised:

```
1. GROUND TRUTH      what is known to be true about this system, stated as fact
2. TASKS             numbered, in dependency order
3. ANTI-ASSUMPTION   what you must not infer; what counts as evidence here
4. OUTPUT            exact path, exact structure
5. STYLE             constraints on how it is written
```

Two orchestration rules, both learned in the source run:

- **Adversarial framing.** Agents told to refute a finding, and to default to the cautious verdict
  under uncertainty, outperformed agents told to confirm one.
- **Warn in-flight agents when a fact changes.** One agent was about to record a working endpoint
  as dead; a mid-flight correction caught it. This is an orchestrator duty, not an optional nicety.

#### The verification gate

Findings do not reach the question ladder unverified. The source run's numbers show why: 248
findings in, 15 confirmed, 3 sharpened, 1 refuted.

- **Tool inference is not evidence.** A knowledge graph asserted a dead-code relationship that was
  exactly inverted. Every deletion carries a reachability trace from a real entry point instead.
- **Two independent agents converging is the strongest signal available.** Two found the same dead
  configuration variable by different methods. That finding was trusted immediately.
- **Calibrate with controls before trusting any sweep.** Check one case known to be true and one
  known to be false. If the controls misbehave the sweep is meaningless and gets discarded.
- **A failed check is never an absence.** A timeout, a 429 or a refused connection is recorded as
  UNVERIFIED and reported as such, never as clean.
- **A count is never verification.** State what was checked and what was not.
- **Discard poisoned data loudly.** Exclude it and document the incident rather than quietly
  dropping it.

Findings are tagged `CONFIRMED`, `PLAUSIBLE` or `REFUTED`. Only confirmed findings become tasks.
A plausible finding becomes an investigation task, which is a different thing and says so.

Two operational guards:

- **Budget the phase.** Four parallel research agents drained the source session's web-search
  quota and the last agents silently fell back to direct page fetches. Lanes get a search budget
  or get sequenced.
- **Batch edits apply what matches.** A script that asserts every pattern before writing discards
  all edits when one fails, and a commit in the same command then records a message describing
  changes that were never applied. This happened twice in the source session. The rule: apply what
  matches, write regardless, report applied and failed separately, and never commit in the same
  breath as an edit.

### Phase C - the premise check

Before any question is asked, state where the user's own framing is contradicted by what the
audit found. This is a statement, not a question.

The source run opened by establishing that there was no cloud to migrate away from, and that the
two halves of the system had never run together. Both contradicted the request as stated, and
reporting that first changed the entire engagement.

### Phase D - the question ladder

Four questions, one per message, multiple choice where possible, recommendation first with its
reasoning attached, **and built expecting the user to reject the menu.** Two of the source run's
four answers overrode the recommendation and both overrides improved the plan.

1. **"How do you currently run the things you already have deployed?"**
   Establishes the deployment target from existing practice rather than from a survey of options.
2. **"What is this work actually aiming at?"**
   The destination question. Concrete end-states, not adjectives. The source run's answer rejected
   all four options and supplied a two-stage split that became the most load-bearing idea in the
   plan.
3. **"How should half-built areas be handled - deleted, flagged off, or finished?"**
   The subtraction question. This is what turns an audit into a plan, because it decides what
   survives. Every option is grounded in what the code actually contains.
4. **"What access do I have, and can I verify the result myself?"**
   A plan whose completion cannot be verified is not a plan. This produces the falsifiable
   definition of done.

### Phase E - design sections, then emit

The design is presented in sections, with approval after each, rather than as a finished
document. Two of the source run's sections were corrected cheaply at this stage.

Then the three artefacts are written: the ledger, the spec, and the generated dashboard.

### Phase F - mode

Stated once, at emit: the ledger will be kept updated automatically as work proceeds, unless the
user says otherwise. **Automatic is the default.** The answer is persisted into the repository,
not re-litigated each session.

## 4. The ledger format

### Authored versus derived

Every line is one or the other. Nothing is both.

| Authored - a human or agent writes it | Derived - a script writes it, always |
| --- | --- |
| Track sections, scope, blocked-by | Every count in the progress table |
| Every task line | Done totals, per track and overall |
| Contracts table | The whole dashboard HTML |
| Definition of done | The definition-of-done scoreboard |
| The reframing finding | Which tracks are unblocked right now |
| Which audit lanes ran | |

The source run's counts drifted because the progress table was authored. Here it is **generated in
place**: `build_dashboard.py` rewrites that table inside the ledger and emits the HTML in the same
pass. Two artefacts, one command, structurally incapable of disagreeing.

### The parse contract

Natural markdown, written without thinking about a schema:

```markdown
## T1 Foundation

**Scope:** Make it boot from clean
**Blocked by:** nothing

Nothing real starts until this lands. A fresh database currently fails Hibernate
validation: 17 missing columns, 2 missing tables.

- [ ] **1.1** Write `V1__reconcile_entity_drift.sql`
- [x] **1.2** Set `ddl-auto=validate` in the dev profile
      **Verified:** `./gradlew bootRun` -> started, validation passed. 2026-08-27
```

Three rules:

1. `## T<id> <name>` opens a track. `**Scope:**` and `**Blocked by:**` are its metadata.
2. `- [ ] **<id>** <text>` is a task. That is the whole grammar.
3. **A `[x]` with no `**Verified:**` line is a hard error and the build refuses.**

Rule 3 is the load-bearing one. It is evidence-before-assertions made mechanical, and it is what
makes automatic mode safe to switch on: an agent physically cannot tick a box without recording
the command it ran and what came back. It is **not configurable**. The moment it can be turned
off, someone turns it off and automatic mode becomes unsafe. The line may be short, so a trivial
task costs one line:

```markdown
- [x] **0.4** Delete stale `bin/`   **Verified:** `ls bin/` -> absent. 2026-08-27
```

### Ledger sections

Derived from the reference implementation:

- Header: title, the statement that this file is the ledger, links to companion documents and to
  the dashboard artifact URL
- The reframing finding
- Stage table, when the goal splits into stages
- Progress at a glance (**generated**)
- Dependency figure
- Track sections with tasks
- Deferred work
- Hand-off contracts, each with what enforces it
- Definition of done, falsifiable
- Companion documents
- Audit coverage: which lanes ran and which did not

## 5. The dashboard

Not a rendering of the markdown. A different instrument for a different job: the ledger is read,
the dashboard is scanned and operated.

- **Opens with the finding that reframes everything.** In the source run that was "the two halves
  have never run together", which does more work than any statistic on the page.
- **Condition on arrival, then progress.** State before motion.
- **Track cards where state is encoded in form as well as number.** Blocked, unblocked, running
  and done are distinguishable without reading a digit.
- **One figure, one claim.** The source diagram showed that only one track blocks and where the
  critical path runs. The accent colour is spent entirely on that one chain. If a second thing
  wants the accent, the figure is making two claims and needs splitting.
- **Every task listed. No highlight reel.** The point is to know all of the work.
- **A footer stating what was checked and what was not**, including which lanes ran.

### The metaphor rule

The skill does not ship a theme. It ships a **derivation step**: read what the subject actually
is, take a concrete metaphor from that subject's own world, then derive vocabulary, section names
and palette from it.

The source run's metaphor was a restoration survey of a dormant structure. That single choice
produced the condition-on-arrival framing, the subtraction track and the palette. Shipping that
same palette to every user is precisely how the output becomes a template.

Paired with the structural rule: **a structural device must encode something true.** The source
run's track codes are identifiers, not a sequence, so no `01 / 02 / 03` markers were used and the
dependency diagram carries the ordering instead. Before using a numbered list, a stepper or a
progress ring, ask what it is claiming.

Mechanics: load `artifact-design` before writing and `artifact-diagramming` when a real mechanism
needs drawing. Self-contained, theme-aware, responsive. Always written to disk as HTML first and
published second, so the file exists and is correct even where publishing is unavailable.

## 6. The living mechanism

### Two directions

- **Completion flows in.** Tasks are ticked with recorded evidence as work lands.
- **Discovered work flows in.** Work found mid-development is written into the right track at the
  time it is found, rather than living in a chat window. This is what keeps a plan alive; ticking
  boxes only keeps a number accurate.

### Where the instruction lives

In the target repository's own `CLAUDE.md`, as a delimited block written at creation:

```markdown
<!-- trigpoint:begin -->
## The ledger

`ROADMAP.md` is this repository's plan of record. Read it before starting work.

- Work only on tracks whose **Blocked by** is satisfied.
- A box is ticked ONLY after its verification has actually run. Record the command
  and its output on a `**Verified:**` line. Never tick on assumption.
- Work discovered mid-flight that is not in the ledger gets ADDED to the right
  track when found, not done silently.
- A finding that contradicts the ledger is raised, not quietly edited away.
- After any tick or addition, run `.trigpoint/build_dashboard.py`. Counts and the
  dashboard are generated. Never hand-edit them.

Mode: automatic.
<!-- trigpoint:end -->
```

### The scripts are installed into the target repository

At creation, the skill copies all four scripts - `trigpoint_ledger.py`, `trigpoint_render.py`,
`build_dashboard.py` and `check_drift.py` - into `.trigpoint/` in the target repository rather
than leaving them inside the plugin. Both CLIs import the other two modules, so copying only the
CLIs would leave a broken install. Two reasons to copy them at all, and the first is decisive:

- **CI cannot reach the plugin.** A drift-check workflow runs on a bare checkout. If the script
  lives only in the installed plugin, the gate cannot exist.
- **The repository stays self-contained.** A collaborator who clones it can regenerate the
  dashboard without installing anything.

`/trigpoint-sync` therefore invokes the copy in the repository, not its own. The plugin owns the
canonical version and reports when the installed copy is behind.

Three properties this buys:

1. **Every future session, in any window, on any machine, picks it up**, because `CLAUDE.md` is
   loaded as project instructions automatically.
2. **A collaborator who has never installed the plugin still gets the discipline.** The block is
   plain markdown and the scripts are in the repository. The plugin adds the authoring process and
   the sync command; it is not required for the rules to bind or for the dashboard to rebuild.
3. **It is idempotent.** Delimited, so re-running updates it in place rather than stacking copies.

### What the plugin adds

- **`/trigpoint`** - start a new ledger. Runs phases A through F.
- **`/trigpoint-sync`** - reparse the ledger, rewrite the progress table in place, regenerate the
  HTML, republish the dashboard to the same URL. The artifact URL is recorded in the ledger
  header, so it updates rather than spawning a new link.
- **`check_drift.py`** - the same parse with no writes. Suitable as a CI gate, so a `[x]` without
  a `**Verified:**` line fails the build rather than relying on anyone noticing.

## 7. The interaction surface

Seven touchpoints for an entire run. After the last one the skill never asks again on that
project; it reads the persisted mode and proceeds. "Blocks" means the run stops and waits: only
the user holds that fact, and guessing it would produce a plan built on an invented premise.

| # | When | What | If the user says nothing |
| --- | --- | --- | --- |
| - | Phase C | The premise check. A statement, not a question. | - |
| 1 | Phase A | Which audit lanes, pre-ticked with reasons from the repo | Runs all seven |
| 2 | Phase D | How do you run what you already have deployed? | Blocks |
| 3 | Phase D | What is this work actually aiming at? | Blocks |
| 4 | Phase D | Half-built areas: deleted, flagged off, or finished? | Blocks |
| 5 | Phase D | What access do I have, and can I verify the result myself? | Blocks |
| 6 | Phase E | Section-by-section approval of the design | Blocks |
| 7 | Phase F | Automatic updates, unless you say otherwise | Automatic |

## 8. Package layout

```
felipeflorencio/claude-plugins               public, the shared marketplace (see section 9)
  .claude-plugin/marketplace.json            lists trigpoint and every later tool
  README.md

felipeflorencio/trigpoint                    public, the plugin itself
  .claude-plugin/
    marketplace.json                         single entry, for direct install
    plugin.json
  skills/
    trigpoint/
      SKILL.md                               the process: audit -> ladder -> emit
      references/
        audit-lanes.md                       the seven lanes, parameterised
        agent-brief-skeleton.md              the five-part brief
        question-ladder.md                   the four questions, expect-rejection rule
        evidence-rules.md                    controls, convergence, unverified handling
        ledger-format.md                     the parse contract
        dashboard-design.md                  metaphor derivation, one-figure-one-claim
      templates/
        ROADMAP.template.md
        dashboard.template.html
        spec.template.md
        claude-md-block.md
  scripts/                                   canonical copies; four of the five are also
                                              installed into target repos
    trigpoint_ledger.py                      parses tracks, tasks and definition of done
    trigpoint_render.py                      renders the progress table and dashboard HTML
    build_dashboard.py                       ledger -> progress table + HTML
    check_drift.py                           the same parse, no writes, CI gate
    install_block.py                         installs the CLAUDE.md block, run from the plugin,
                                              not copied
  commands/
    trigpoint.md
    trigpoint-sync.md
  examples/
    README.md                                points at this repository's own ROADMAP.md and
                                              dashboard as the worked example
  .github/workflows/drift-check.yml          dogfooded on this repo's own ledger
  README.md
  assets/cover.png
```

### What lands in a target repository

```
<target repo>/
  ROADMAP.md                                 the ledger
  roadmap-dashboard.html                     generated, committed
  .trigpoint/
    trigpoint_ledger.py                      copied from the plugin
    trigpoint_render.py                      copied from the plugin
    build_dashboard.py                       copied from the plugin
    check_drift.py                           copied from the plugin
  CLAUDE.md                                  gains the delimited block
  docs/superpowers/specs/<date>-<topic>-design.md
  docs/trigpoint/audit/<lane>.md             one file per lane that ran
  .github/workflows/drift-check.yml          offered, not imposed
```

## 9. Distribution

Two repositories, owned by the same user, with different jobs.

### The marketplace repository - shared, and outlives this plugin

`felipeflorencio/claude-plugins` is a standalone marketplace listing every plugin this user
publishes. Trigpoint is its first entry; later tools live in their own repositories and are added
as further entries. The marketplace is not embedded in this plugin, because embedding it would
mean a second tool needs a second marketplace and users would have to add each one separately.

```jsonc
// felipeflorencio/claude-plugins/.claude-plugin/marketplace.json
{
  "name": "felipeflorencio",
  "owner": { "name": "Felipe Florencio" },
  "plugins": [
    {
      "name": "trigpoint",
      "description": "Audit a codebase, then produce a plan of record that cannot drift.",
      "category": "development",
      "source": {
        "source": "url",
        "url": "https://github.com/felipeflorencio/trigpoint.git"
      },
      "homepage": "https://github.com/felipeflorencio/trigpoint"
    }
  ]
}
```

Install, two lines, no gatekeeper:

```
/plugin marketplace add felipeflorencio/claude-plugins
/plugin install trigpoint@felipeflorencio
```

### The plugin repository

`felipeflorencio/trigpoint` holds the plugin itself, with `.claude-plugin/plugin.json` at its
root. It **also** carries its own single-entry `marketplace.json`, so someone who lands on this
repository directly can install without knowing the shared marketplace exists:

```
/plugin marketplace add felipeflorencio/trigpoint
```

The README leads with the shared marketplace and offers the direct route as a fallback.

### How the format was established

The marketplace schema URL advertised in the manifests, `anthropic.com/claude-code/marketplace.schema.json`,
returns HTML rather than JSON and could not be read. The format above is therefore taken from two
marketplaces that demonstrably work, both installed locally and inspected:

- `anthropics/claude-plugins-official`, 300+ plugins, which uses three source forms: a relative
  string for plugins inside the same repository, `git-subdir` for a plugin in a subdirectory of
  another repository, and **`url` for a plugin at another repository's root** - the form used here,
  by 151 of its entries.
- `alirezarezvani/claude-skills`, a third-party marketplace with 97 plugins, confirming that a
  non-Anthropic marketplace works with the same manifest shape.

This is empirical evidence from working examples, not an inferred schema. If a field turns out to
be wrong, `/plugin marketplace add` against the real repository is the check that settles it, and
that check happens before the README claims the install works.

## 10. Promotion

### README

- The problem in one line: plans made by an agent go stale within a week, and a stale plan is
  worse than none.
- The three artefacts shown, not described: a dashboard screenshot, a ledger fragment, the spec.
- Install: two commands.
- The worked example with real numbers from the source run: 248 findings, 15 confirmed, 67 tasks,
  8 tracks.
- What it guarantees: counts cannot drift, a box cannot be ticked without recorded evidence.
- Honest limits, stated plainly. See section 11.

### Cover

1280x640 for the GitHub social preview, plus a square crop. Built the way the dashboard is built:
an HTML artboard rendered to PNG through the browser tooling, so the source is version-controlled
rather than a binary someone has to redo. Subject-derived, one claim, not a feature list.

## 11. Honest limits

These go in the README, not just in this spec.

- **The source plan has never been executed.** Trigpoint produces a plan that reads as excellent.
  Whether such a plan survives contact with implementation is not yet known.
- **The audit is expensive.** It is the bulk of the token cost of a run. This is a deliberate
  trade: without ground truth the questions produce generic options.
- **The source run started from an unusually rich position** - 248 findings and 18 evidence
  reports already existed. Phase B exists to remove that dependency, but it has not yet been
  proven on a cold repository.
- **The audit is not static analysis** and does not replace it.

## 12. Decisions taken, with their reasons

| Decision | Reason |
| --- | --- |
| Plugin, not a bare skill | A marketplace serves plugins, and this ships scripts and templates, not only a prompt |
| Dashboard generated, never authored | The one documented failure of the source run |
| Progress table generated in place in the ledger | That table is where the drift actually happened |
| `**Verified:**` required, not configurable | An exemption clause lets an agent decide what is obvious, which is the failure being prevented |
| Automatic mode default | User decision, 2026-08-26 |
| Instruction block in the target repo's `CLAUDE.md` | Binds every future session and works without the plugin installed |
| Full seven lanes on silence | A lane skipped by silence reads as coverage that never happened |
| Metaphor derived per subject, not shipped | A shipped palette makes every output look like a template |
| Named Trigpoint | npm free, only zero-star GitHub collisions, and it fits the surveying metaphor family. No domain available on com/io/dev/app, which does not matter for a GitHub-distributed plugin. |
| Marketplace is a separate shared repository | More tools are coming in their own repositories. One marketplace the user adds once, rather than one per tool. |
