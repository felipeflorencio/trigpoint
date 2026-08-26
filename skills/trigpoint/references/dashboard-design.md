# Designing the dashboard

The dashboard is not a rendering of the markdown. It is a different instrument for a different job:
the ledger is **read**, the dashboard is **scanned and operated**. Build it accordingly.

Load `artifact-design` before writing any HTML, and `artifact-diagramming` when a real mechanism
needs drawing.

## Derive the metaphor before you write anything

This skill ships no theme. It ships a derivation step, and you perform it every time:

1. Read what the subject actually is. Not the tech stack: the thing the project does, and the state
   it is in.
2. Take a concrete metaphor from **that subject's own world**. The source run's subject was a
   dormant codebase being brought back, so the metaphor was a restoration survey of a dormant
   structure.
3. Derive the vocabulary, the section names and the palette from that metaphor. The source run's
   metaphor produced "condition on arrival", the subtraction track, and its colours.

Do not reuse the source run's metaphor, vocabulary or palette. Shipping the same palette to every
project is precisely how the output starts looking like a template.

## The rules the page must satisfy

**Open with the finding that reframes everything.** Put the `**Headline:**` line at the top, in the
largest type on the page. In the source run that was "the two halves have never run together",
which does more work than any statistic on the page.

**Condition on arrival, then progress. State before motion.** The reader needs to know what shape
the thing is in before they can read a percentage.

**Track cards where state is encoded in form as well as number.** Blocked, unblocked, running and
done must be distinguishable without reading a digit: border, fill, position, weight. A page where
every card looks the same until you read it is a list, not a dashboard.

**One figure, one claim.** Draw the dependency structure once, and spend the accent colour entirely
on the one chain it is claiming. If a second thing wants the accent, the figure is making two
claims and needs splitting into two figures.

**Every task listed. No highlight reel.** The point is to know all of the work. A dashboard showing
the interesting subset is how work goes missing.

**A footer stating what was checked and what was not**, including which lanes ran and which did
not, by name.

## The structural rule

**A structural device must encode something true.** Before using a numbered list, a stepper, a
progress ring or a timeline, ask what it is claiming.

The source run's track codes are identifiers, not a sequence, so no `01 / 02 / 03` markers were
used and the dependency diagram carried the ordering instead. A stepper across tracks that run in
parallel is a false claim rendered in CSS.

## Mechanics

- Self-contained: inline the CSS, embed any asset as a data URI. No external hosts.
- Theme-aware: define the full light palette on bare `:root`, redefine the tokens under
  `@media (prefers-color-scheme: dark)` guarded as `:root:not([data-theme="light"])`, and again
  under `:root[data-theme="dark"]`. Give `body` an explicit background token.
- Responsive: wide tables and diagrams scroll inside their own `overflow-x: auto` container. The
  page body never scrolls horizontally.
- **Write the HTML to disk first, publish second**, so the file exists and is correct even where
  publishing is unavailable.
- Record the published artifact URL in the ledger header, so `/trigpoint-sync` republishes to the
  same URL instead of spawning a new link.

## What generates it

`build_dashboard.py` emits a correct, plain dashboard from the ledger with no design work at all,
and it is what every later regeneration runs. Treat its output as the floor: the structure is
already right and the counts are already true. The design work above replaces the presentation, not
the source of the numbers, and nothing on the page is ever typed in by hand.
