# The worked example

There is no sanitised copy of somebody else's project in here, because this repository is the
example. Trigpoint's rules govern Trigpoint's own plan, and its own gate runs against that plan in
CI on every push. Two files, both at the repository root.

## `../ROADMAP.md` - the ledger

The plan of record. Read it top to bottom once, then look specifically at these five things.

**The generated region.** Between `<!-- trigpoint:progress:begin -->` and
`<!-- trigpoint:progress:end -->` sits the progress table. Every number in it is derived from the
task lines further down the file. Nothing else in the document is generated. Edit a count by hand
and the next `python3 scripts/build_dashboard.py` puts it back, and CI fails the diff in between.

**A ticked task, and what it costs to tick one.** Task 1.2 is the cleanest instance: the checkbox
is followed by an indented `**Verified:**` line carrying the command that was run and what the
command printed. That line is not documentation. `check_drift.py` treats its absence as an error
and fails the build, and it treats an unfilled `{{ placeholder }}` in it the same way.

**An untouched track, stated as untouched.** In the snapshot below, T5 Publication reads "This track has not started.
Nobody has published this plugin anywhere, and nobody has installed it from outside this checkout."
A ledger that quietly omits the part nobody has done is the failure this format exists to prevent.

**The hand-off contracts table.** Four contracts, each with the specific test or CI step that
enforces it. Parallel work fails by drifting apart silently rather than by colliding, so a contract
that nothing machine-checks is a wish. Note that each row names its enforcer by file.

**The audit coverage footer.** It says "Lanes run: none" and then names all seven lanes that did
not run, with a paragraph explaining why and what that leaves unknown about this repository. An
unrun lane is an unsearched area, not a clean result, and the ledger is required to say which is
which.

## `../roadmap-dashboard.html` - the dashboard

Open it in a browser. It is generated from the same parse as the progress table, in the same pass,
so the two are structurally incapable of disagreeing.

Look at the footer first: it repeats which lanes ran and which did not, so the honesty of the
ledger cannot be lost by moving to the prettier artefact. Then note that every task is listed, each
ticked one carrying its evidence line underneath it, the two open ones visibly carrying nothing.
There is no highlight reel and no interesting-subset view, because
a dashboard that shows the interesting work is how the rest of the work goes missing.

The page this repository ships is the plain floor that `build_dashboard.py` emits with no design
work at all. A real run replaces the presentation, deriving a metaphor and a palette from the
subject of that project, and never touches the source of the numbers. That derivation step is in
`../skills/trigpoint/references/dashboard-design.md`.

## Regenerating both

From the repository root:

```
python3 scripts/build_dashboard.py --ledger ROADMAP.md --output roadmap-dashboard.html
python3 scripts/check_drift.py ROADMAP.md
```

The first rewrites the table and the dashboard. The second reads and writes nothing, exits 0 when
the ledger is clean, 1 when it holds an error, and 2 when it cannot read the ledger at all. It is
the CI gate, and it is what `.github/workflows/checks.yml` runs.
