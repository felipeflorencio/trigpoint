# Trigpoint - Roadmap

**The top-level reference of work.** What is being built, in what order, and what is done.

This file is the ledger, and it is the plan of record. The design behind it is
`docs/superpowers/specs/2026-08-26-trigpoint-design.md`. The dashboard generated from it is
`roadmap-dashboard.html`, published at not yet published.

Applies to: this repository, `trigpoint`.

**Headline:** This repository now runs its own drift gate in CI, so a ledger that lies about its own evidence fails its own build before it fails anyone else's.

---

## Progress at a glance

Generated. Do not hand-edit anything between the markers. Run `python3 scripts/build_dashboard.py`.

<!-- trigpoint:progress:begin -->
| Track | Scope | Tasks | Done | Blocked by |
| --- | --- | --- | --- | --- |
| **T1 Parser and gate** | The ledger model, its validation rules, and the read-only CI gate built on them | 6 | 6 | nothing |
| **T2 Generation** | The generated progress table, the dashboard renderer, and the sync CLI that writes both | 4 | 4 | T1 |
| **T3 Installation** | The CLAUDE.md instruction block installer | 3 | 3 | T1 |
| **T4 Packaging** | The plugin and marketplace manifests, the slash commands, and the skill with its references and templates | 4 | 4 | T1, T2, T3 |
| **T5 Publication** | The README, the cover art, the published marketplace listing, and a verified real install | 2 | 0 | T4 |
| **T6 Continuous verification** | The hooks that state the plan at session start and re-prove it at the end of a turn, the approval gate that keeps command execution safe, and the parser fix that made the re-run trustworthy | 5 | 4 | nothing |
| **Total** | | 24 | 21 | |
<!-- trigpoint:progress:end -->

T1 is the only true blocker: nothing downstream works without a parser and a gate that trusts
its own evidence rule. T2, T3 and T4 each depend on T1 but not on each other. T6 depends on
nothing, because it re-runs what the ledger already records. What remains is T5, which is
genuinely not started, and 6.5, which needs a project other than this one.

```
T1 PARSER AND GATE (blocking)
     |
     +--> T2 GENERATION
     +--> T3 INSTALLATION
     +--> T4 PACKAGING
                |
                +--> T5 PUBLICATION (not started)
```

---

## T1 Parser and gate

**Scope:** The ledger model, its validation rules, and the read-only CI gate built on them
**Blocked by:** nothing

Everything else in this repository reads a ledger through this module or fails safe if it
cannot. The evidence rule here is the one the rest of the plugin exists to enforce: a ticked
task with no real `**Verified:**` line is an error, not a warning, because that is the rule
that makes automatic ledger updates safe to trust.

- [x] **1.1** Write the ledger parser: sections become tracks only when they carry a `**Scope:**`
      line, tasks and their evidence are read from checkbox lines and their indented
      continuations
      **Verified:** `python3 -m unittest tests.test_ledger_parse -v` -> `Ran 22 tests in 0.002s` /
      `OK`. 2026-08-26
- [x] **1.2** Write ledger validation: a ticked task with no `**Verified:**` line is an error, a
      duplicate task id is an error, an unknown `**Blocked by:**` reference is a warning
      **Verified:** `python3 -m unittest tests.test_ledger_validate -v` -> `Ran 18 tests in
      0.001s` / `OK`. 2026-08-26
- [x] **1.3** Write `scripts/check_drift.py`, the read-only CI gate over the same parse, with
      exit codes 0 (clean or warnings only), 1 (at least one error) and 2 (ledger unreadable)
      **Verified:** `python3 -m unittest tests.test_check_drift -v` -> `Ran 7 tests in 0.002s` /
      `OK`. 2026-08-26
- [x] **1.4** Characterise the parser against the reference ledger it was derived from: a
      real-world document with no `**Scope:**` lines yields zero tracks, which is correct
      behaviour rather than a defect
      **Verified:** `python3 -m unittest tests.test_reference_ledger -v` -> `Ran 3 tests in
      0.001s` / `OK`. 2026-08-26
- [x] **1.5** Harden the evidence gate: a fenced heading or fenced task is documentation, not a
      real section or task, and a genuine `{{ ... }}` span in evidence (a Go template, a shell
      brace expansion) is not mistaken for an unfilled placeholder
      **Verified:** `python3 -m unittest tests.test_ledger_parse tests.test_ledger_validate -v`
      -> `Ran 40 tests in 0.002s` / `OK`. 2026-08-26
- [x] **1.6** Dogfood: this repository gets its own ledger and a CI workflow,
      `.github/workflows/checks.yml`, that runs the unit tests, the drift gate and a
      regenerate-and-diff check against it on every push
      **Verified:** `python3 scripts/check_drift.py ROADMAP.md` -> `ROADMAP.md: no problems
      found.`; exit code 0. `python3 scripts/build_dashboard.py --ledger ROADMAP.md --output
      roadmap-dashboard.html && git diff --exit-code ROADMAP.md roadmap-dashboard.html` -> exit
      code 0, no diff. 2026-08-26

## T2 Generation

**Scope:** The generated progress table, the dashboard renderer, and the sync CLI that writes both
**Blocked by:** T1

The progress table and the dashboard are both derived from the same parse, in the same pass, so
they are structurally incapable of disagreeing with each other or with the task lines that feed
them.

- [x] **2.1** Generate the progress table between the `<!-- trigpoint:progress:begin -->` and
      `<!-- trigpoint:progress:end -->` markers from the track and task lists
      **Verified:** `python3 -m unittest tests.test_progress_table -v` -> `Ran 10 tests in
      0.001s` / `OK`. 2026-08-26
- [x] **2.2** Write `render_dashboard`: a self-contained, theme-aware HTML page listing every
      task, with a footer stating which audit lanes did not run so an absent lane never reads as
      a clean one
      **Verified:** `python3 -m unittest tests.test_render -v` -> `Ran 11 tests in 0.001s` /
      `OK`. 2026-08-26
- [x] **2.3** Write `scripts/build_dashboard.py`, the sync CLI that rewrites the progress table in
      place and writes the dashboard HTML in one pass, reporting a missing marker region rather
      than discarding the rest of the write
      **Verified:** `python3 -m unittest tests.test_build_dashboard -v` -> `Ran 11 tests in
      0.012s` / `OK`. 2026-08-26
- [x] **2.4** Fix single-word track heading duplication (a track named `Hygiene` rendered as
      `Hygiene Hygiene`) shared between the progress table and the dashboard renderer
      **Verified:** `python3 -m unittest
      tests.test_progress_table.ProgressTableTest.test_two_word_track_still_renders_correctly
      tests.test_render.RenderDashboardTest.test_two_word_track_heading_renders_correctly -v` ->
      `Ran 2 tests in 0.000s` / `OK`. 2026-08-26

## T3 Installation

**Scope:** The CLAUDE.md instruction block installer
**Blocked by:** T1

The installed block is what makes a future session in any window pick up the ledger discipline
without the plugin being loaded. It is delimited so a second install updates the block rather
than stacking a second copy, and it has to be safe to run against a file it does not control:
a symlink, an existing unmatched marker, an interrupted write.

- [x] **3.1** Write `scripts/install_block.py`: install a delimited Trigpoint block into
      `CLAUDE.md`, reinstalling updates the existing block rather than stacking a second one
      **Verified:** `python3 -m unittest tests.test_install_block -v` -> `Ran 15 tests in
      0.010s` / `OK`. 2026-08-26
- [x] **3.2** Fix a data-loss defect: an unmatched begin marker could let the replace regex span
      across real user content; write with atomic replace and preserve line endings
      **Verified:** `python3 -m unittest tests.test_install_block -v` -> `Ran 15 tests in
      0.010s` / `OK`. 2026-08-26
- [x] **3.3** Fix two regressions the atomic write introduced: file permissions reset to `0600`
      on an existing file, and a symlinked `CLAUDE.md` destroyed rather than followed
      **Verified:** `python3 -m unittest
      tests.test_install_block.InstallBlockTest.test_symlinked_claude_md_is_followed -v` -> `Ran
      1 test in 0.000s` / `OK`. 2026-08-26

## T4 Packaging

**Scope:** The plugin and marketplace manifests, the slash commands, and the skill with its references and templates
**Blocked by:** T1, T2, T3

The scripts only keep the ledger honest; the skill is what teaches an agent to run the audit
lanes, ask the four questions, and write a ledger that deserves to pass its own gate. The
manifests and commands are what let a user install any of it.

- [x] **4.1** Write `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`, and the
      two slash commands `commands/trigpoint.md` and `commands/trigpoint-sync.md`
      **Verified:** `python3 -m unittest
      tests.test_manifests.ManifestTest.test_plugin_manifest_is_valid_json_with_required_fields
      tests.test_manifests.ManifestTest.test_marketplace_manifest_lists_this_plugin
      tests.test_manifests.ManifestTest.test_every_command_file_exists_and_has_frontmatter -v` ->
      `Ran 3 tests in 0.001s` / `OK`. 2026-08-26
- [x] **4.2** Write the trigpoint skill: `skills/trigpoint/SKILL.md`, its six references
      (`agent-brief-skeleton.md`, `audit-lanes.md`, `dashboard-design.md`, `evidence-rules.md`,
      `ledger-format.md`, `question-ladder.md`) and its two templates
      (`ROADMAP.template.md`, `spec.template.md`)
      **Verified:** `ls skills/trigpoint/references | wc -l` -> `6`. `ls skills/trigpoint/templates
      | wc -l` -> `2`. 2026-08-26
- [x] **4.3** Widen the shipped-markdown typography gate to cover the repository root,
      `commands/`, `skills/` and `examples/`, excluding the reference ledger fixture, which is a
      verbatim third-party copy
      **Verified:** `python3 -m unittest
      tests.test_manifests.ManifestTest.test_no_forbidden_typography_in_shipped_markdown
      tests.test_manifests.ManifestTest.test_shipped_markdown_glob_covers_the_user_facing_surface
      -v` -> `Ran 2 tests in 0.001s` / `OK`. 2026-08-26
- [x] **4.4** Rewrite the skill's guidance so a user's request to skip the audit or the
      four questions is stated as neither consent nor an answer, under direct pressure to move
      faster
      **Verified:** `grep -n "pressure" skills/trigpoint/SKILL.md` -> line 69, "never quietly
      drop one for budget, whether the pressure comes from your own". 2026-08-26

## T5 Publication

**Scope:** The README, the cover art, the published marketplace listing, and a verified real install
**Blocked by:** T4

This track has not started. Nobody has published this plugin anywhere, and nobody has installed
it from outside this checkout.

- [ ] **5.1** Write the README and the cover art
- [ ] **5.2** Publish the plugin to a marketplace and verify a real install from outside this
      checkout

## T6 Continuous verification

**Scope:** The hooks that state the plan at session start and re-prove it at the end of a turn,
the approval gate that keeps command execution safe, and the parser fix that made the re-run
trustworthy
**Blocked by:** nothing

`check_drift.py` proves a ticked task CARRIES evidence. Nothing proved the evidence was STILL
TRUE, and that gap is the failure this plugin exists to close. Every `**Verified:**` line already
holds the command that proved the task, so re-running it needs no new ledger syntax. Nothing here
ever ticks a box: a machine can show a claim has become false, but deciding that work is finished
stays with a person.

- [x] **6.1** Write `scripts/trigpoint_verify.py`: read the command out of each ticked task's
      `**Verified:**` line, re-run only commands a human approved by hash, and untick anything
      that stopped passing with a `**Regressed:**` note that leaves the original evidence intact
      **Verified:** `python3 -m unittest tests.test_verify -v` -> `Ran 23 tests in 0.001s` /
      `OK`. 2026-08-26
- [x] **6.2** Write the two hooks and the project guard: state the ledger at session start,
      re-prove it at the end of a turn, and exit silently in any directory that has not been
      initialised with `.trigpoint/`, that is paused, or that set `TRIGPOINT_DISABLE`
      **Verified:** `python3 -m unittest tests.test_hooks -v` -> `Ran 19 tests in 0.584s` /
      `OK`. 2026-08-26
- [x] **6.3** Fix the evidence scan: a task whose own description quotes the marker in backticks
      had its evidence read from the middle of that sentence, and validation passed because the
      field was merely non-empty rather than correct. Found by re-running this repository's own
      recorded commands, which is the mechanism catching a defect in itself
      **Verified:** `python3 -m unittest tests.test_ledger_parse -v` -> `Ran 41 tests in 0.003s` /
      `OK`. 2026-08-26
- [x] **6.4** Wire it into installation: the skill copies the verifier alongside the other
      scripts, `/trigpoint-verify` reviews and approves commands one at a time, and
      `/trigpoint-pause` stops the hooks in a repository
      **Verified:** `python3 -m unittest tests.test_hook_wiring -v` -> `Ran 11 tests in 0.002s` /
      `OK`. 2026-08-26
- [ ] **6.5** Prove it against a project that is not this one. The dogfood run here unticked four
      tasks correctly when the renderer was broken, but it also showed that a repository managing
      ITSELF shares one parser between the checker and the checked, so sabotaging the parser
      silently disables the checker. That blind spot needs a real second project to characterise

---

## Deferred work

- **Nothing deferred beyond T5.** Every task this plan currently names is either done or listed
  in T5. A new deferred item belongs here the moment one is found, rather than being
  rediscovered in a future session.

---

## Hand-off contracts

Parallel work fails by drifting apart silently, not by colliding. Contracts are therefore **files
in the repository, not messages between agents**: messages die with a session, files are versioned
and survive a context reset. Each contract below is machine-checked, so drift breaks a build.

| | Contract | Enforced by |
| --- | --- | --- |
| **C1** | `scripts/trigpoint_ledger.py` is the single parser every other script imports; no script re-implements the grammar | `tests/test_ledger_parse.py`, `tests/test_ledger_validate.py` |
| **C2** | The progress table between the marker pair and `roadmap-dashboard.html` are both written by `scripts/build_dashboard.py` from the same parse, in the same pass | `.github/workflows/checks.yml` step 3: regenerate, then `git diff --exit-code` |
| **C3** | Every shipped markdown file (repository root, `commands/`, `skills/`, `examples/`) contains no em dash, en dash, curly quote or ellipsis character | `tests/test_manifests.py::test_no_forbidden_typography_in_shipped_markdown` |
| **C4** | A ticked task always carries a real `**Verified:**` line, never an unfilled `{{ placeholder }}` | `scripts/check_drift.py`, run in CI on every push |

**Ledger discipline.** A box above is ticked only with the verification command and its output
recorded on a `**Verified:**` line. Never on assumption. `python3 scripts/check_drift.py
ROADMAP.md` fails the build otherwise.

---

## Definition of done

Each criterion is falsifiable on purpose: someone can look at the system and say it is false.
Publication starts once T5 is checked off as well.

- [x] 1. A fresh clone runs `python3 -m unittest discover -s tests` and it exits 0.
      **Verified:** `python3 -m unittest discover -s tests` -> `Ran 102 tests in 0.027s` / `OK`.
      2026-08-26
- [x] 2. `python3 scripts/check_drift.py ROADMAP.md` reports no problems against this
      repository's own ledger.
      **Verified:** `python3 scripts/check_drift.py ROADMAP.md` -> `ROADMAP.md: no problems
      found.`; exit code 0. 2026-08-26
- [x] 3. Regenerating the ledger and the dashboard from `ROADMAP.md` produces byte-identical
      committed files.
      **Verified:** `python3 scripts/build_dashboard.py --ledger ROADMAP.md --output
      roadmap-dashboard.html && git diff --exit-code ROADMAP.md roadmap-dashboard.html` -> exit
      code 0, no output. 2026-08-26
- [ ] 4. `.github/workflows/checks.yml` has reached `success` on a real push to this repository's
      remote, not merely locally.
- [ ] 5. This plugin has been installed from outside this checkout, from a published marketplace
      listing, at least once.

---

## Companion documents

| Document | Contents |
| --- | --- |
| `docs/superpowers/specs/2026-08-26-trigpoint-design.md` | The design this plan implements |
| `docs/superpowers/plans/2026-08-26-trigpoint.md` | The task-by-task build plan, tasks 1 through 13 |

---

## Audit coverage

**Lanes run:** none
**Lanes not run:** boot from clean, reachability, contract drift, honesty, secrets and authz, test and CI reality, subtraction

No audit was run against this repository. Trigpoint was built from a plan, task by task, rather
than reactivated from a dormant codebase an audit was needed to understand first, so none of the
seven lanes in `skills/trigpoint/references/audit-lanes.md` were dispatched here. That means
nothing has independently checked this repository for reachability gaps, contract drift between
the scripts and their tests, hardcoded success states, exposed secrets, or dead code beyond what
the unit tests happen to exercise. A future session auditing this repository starts from zero,
not from a completed pass.
