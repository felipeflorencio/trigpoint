# The agent brief skeleton

Every lane agent receives the same five parts, in this order. Fill each one; do not drop a part
because it seems obvious for a particular lane. A brief missing part 3 produces an agent that
infers, and an agent that infers produces findings you then have to throw away.

```
1. GROUND TRUTH      what is known to be true about this system, stated as fact
2. TASKS             numbered, in dependency order
3. ANTI-ASSUMPTION   what you must not infer; what counts as evidence here
4. OUTPUT            exact path, exact structure
5. STYLE             constraints on how it is written
```

## How to fill each part

**1. GROUND TRUTH.** Write what the light pass established, as flat statements with numbers: the
deployable units and their languages, where the entry points are, whether there is a datastore and
which, what CI exists, the date of the last commit. State only what you verified. If something is
merely likely, either leave it out or mark it as unconfirmed in this section, because everything
here is treated by the agent as settled.

**2. TASKS.** Copy the numbered task list from that lane's section in `audit-lanes.md`, and add any
task specific to this repository. Keep them numbered and keep them in dependency order, because the
agent will work them in sequence and an out-of-order list makes it guess.

**3. ANTI-ASSUMPTION.** State what this lane must not infer and what counts as evidence in it. This
is the part that decides finding quality. Always include:

- Frame it adversarially: "Try to refute each finding before you record it. State what would have
  to be true for the finding to be wrong, then check that. Under uncertainty take the cautious
  verdict."
- "A search returning no matches is not proof of absence. Dynamic registration, reflection,
  string-keyed routing and dependency injection all defeat text search."
- "Tool output is a lead, not evidence. Confirm it by reading the code it points at."
- "A check that fails to complete is UNVERIFIED with its reason recorded, never clean and never
  absent."
- "Before trusting any sweep, calibrate it: check one case you know is true and one you know is
  false. If the controls misbehave, discard the sweep and say so."

**4. OUTPUT.** Give the exact path, `docs/trigpoint/audit/<lane>.md`, and the exact structure. Every
lane writes the same structure so the findings merge:

```markdown
# <Lane name>

**Ran:** <date>
**Scope covered:** <what was actually examined>
**Not covered:** <what was not, and why>

## Findings

### F<n> - <one-line claim>
- **Evidence:** <file>:<line>, and what it says
- **Refutation attempted:** <what would make this wrong, and what you found>
- **Confidence:** CONFIRMED | PLAUSIBLE | REFUTED | UNVERIFIED
- **Impact:** <what breaks, for whom>
```

Tell the agent it writes that file and no other file, and that it makes no edit anywhere else in
the repository.

**5. STYLE.** Constrain the writing:

- One claim per finding. Split a finding that needs the word "and" in its claim line.
- No adjectives where a number belongs. "17 missing columns", not "significant drift".
- No recommendations. This lane reports what is; the plan decides what to do.
- Plain typography: hyphens, straight quotes, three dots. No em dashes, en dashes, curly quotes or
  ellipsis characters.

## Orchestration duties that stay with you

These are not delegated. They are yours while the lanes run.

- **Warn in-flight agents when a fact changes.** When one lane establishes something that
  contradicts what another lane was told in its GROUND TRUTH, interrupt that agent and correct it
  immediately. In the source run this caught an agent one step from recording a working endpoint as
  dead. Treat it as a duty, not a courtesy.
- **Budget the phase before dispatching.** Give each lane a search budget or sequence the lanes.
  Four parallel research agents drained the source session's web-search quota, and the last agents
  fell back silently to direct page fetches. A silently degraded agent returns something that looks
  exactly like a clean result.
- **Never let an agent commit.** Lanes write their own report file and nothing else.
