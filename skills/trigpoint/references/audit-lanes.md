# The seven audit lanes

Each section below is a lane. Dispatch one agent per lane, in parallel, each writing to
`docs/trigpoint/audit/<lane>.md` and to nothing else. Wrap the lane text in the five-part brief
from `agent-brief-skeleton.md`; the text here supplies parts 2 and 3 of that brief.

Every lane obeys three rules that are not repeated in each section:

- Report the **file and line** that proves each finding. A finding without a location is not a
  finding; downgrade it or drop it.
- Try to **refute** each finding before recording it. Say what would have to be true for the
  finding to be wrong, then go check that.
- A check that fails to complete (a timeout, a refused connection, a 429, a missing credential) is
  recorded as **UNVERIFIED** with the reason. Never as clean and never as absent.

---

## Lane 1 - Boot from clean

Determine whether this system starts from a fresh clone and an empty datastore, with nothing on
the machine that a new contributor would not have.

1. Read every entry point that starts a deployable unit, and list what each requires before it
   will run: environment variables, config files, a datastore, a message broker, a seeded row.
2. For each requirement, find where a new contributor would get it. Record which ones have no
   documented source.
3. Read the schema migrations against the model or ORM definitions. Report every column and table
   the code expects that the migrations do not create, by name.
4. Report the gap between "runs on a machine that already ran it" and "runs at all", as a list of
   concrete missing steps.

Do not infer bootability from the presence of a compose file, a Dockerfile or a README section.
Those are claims. The migrations and the entry points are the evidence.

## Lane 2 - Reachability

Classify every route, endpoint and screen as **wired**, **half-wired** or **dead**, starting from
a real entry point and following the calls.

1. Enumerate the real entry points: the router, the HTTP server registration, the app's root
   component, scheduled jobs, message consumers.
2. From each, walk outward and record what is actually reachable.
3. Mark **wired** when the whole path from entry point to effect exists. Mark **half-wired** when
   the path exists but ends in something incomplete: a handler that returns a stub, a screen
   present but not routed, a consumer with no producer. Mark **dead** when nothing reaches it.
4. For every **dead** verdict, record the trace you followed and why it terminates. A dead verdict
   with no trace is downgraded to half-wired.

Never mark something dead because a search found no references. Dynamic registration, reflection,
string-keyed routing and dependency injection all defeat text search.

## Lane 3 - Contract drift

Find every place the two halves of this system disagree about the same data.

1. Build the caller's expected shape for each cross-boundary call: the request it sends, the
   response fields it reads, the types and nullability it assumes.
2. Build the callee's actual shape from the handler and the serialised model.
3. Diff them **field by field**. Report each mismatch as caller expectation on one side, callee
   reality on the other, with both file locations.
4. Report status codes and error shapes as well as success bodies. The disagreement that hurts is
   usually on the error path.

Report a mismatch even when it currently causes no failure. A field the caller ignores today is
drift already recorded.

## Lane 4 - Honesty

Find every place the interface reports success without the underlying operation having occurred.

1. Find every mock, stub, fixture or fake data module, and determine which one is the **default**
   when no configuration is present. A default of mock data means the product reports success
   while connected to nothing.
2. Find hardcoded success states: a handler that returns a fixed success, a UI that shows a
   confirmation without reading the result, a catch block that swallows a failure and continues.
3. Find controls wired to nothing: buttons, menu items, toggles and form submissions with no
   handler, or with a handler whose body is empty or a comment.
4. Find progress, counts and status indicators computed from something other than the thing they
   claim to describe.

Report each with the file and line that proves it, and with what the user would see versus what
actually happened.

This lane has no equivalent in existing tooling and produced the source run's best finding.
Linters, type checkers and test suites all pass on a frontend that defaults to mock data.

## Lane 5 - Secrets and authz

Determine what is exposed.

1. Search the working tree **and the git history** for credentials: keys, tokens, passwords,
   connection strings, private keys, service-account JSON. Report the file, the line and the
   commit. Treat anything found in history as live until rotated.
2. List every route and enumerate which authentication it requires. Report every route that
   requires none, and say whether that is intentional.
3. For every route that takes an object identifier, check whether it verifies that the caller owns
   that object. Report each place it does not: that is an object-level authorization gap.
4. Report privilege escalation paths: any route where a caller can set their own role, tier or
   permissions.

Do not test against a live system without explicit permission. Read the code.

## Lane 6 - Test and CI reality

Determine what is actually gated, not what exists.

1. Read the CI configuration and record exactly which commands run, on which events, on which
   branches, and which of them can fail the build.
2. Determine whether the test suite is run by CI at all, and whether a failure blocks a merge.
3. Separate tests that exercise real integration (real HTTP, a real datastore) from tests that
   mock the layer under test. A suite of mocked repositories gates nothing.
4. Answer the actual question: **what would a bad commit hit?** Name the specific defect classes
   this pipeline would catch, and the ones it would let through.

Coverage percentages are not an answer to that question. Do not report one as if it were.

## Lane 7 - Subtraction

Produce the list of what can be deleted, with the evidence that makes each deletion safe.

1. Propose deletion candidates: unreferenced modules, dead configuration, superseded
   implementations, vendored copies, generated output committed by hand.
2. For **every** candidate, attempt to reach it from a real entry point and record the attempt.
   The recorded trace is what makes the candidate a candidate.
3. Record the blast radius per candidate: what else imports it, what tests cover it, what
   configuration names it.
4. Rank by confidence and put the unreachable-with-a-full-trace items first.

**Tool inference is not evidence here.** A knowledge graph asserted a dead-code relationship that
was exactly inverted. Every candidate carries its own reachability trace, and a candidate whose
trace you could not complete is reported as UNVERIFIED rather than as deletable.
