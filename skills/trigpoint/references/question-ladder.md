# The question ladder

Four questions. Ask them **one per message**, in this order. Each answer constrains the menu of the
next, so batching them means building question 3's options from an assumption rather than from an
answer.

## The three rules that apply to all four

**Recommendation first, with its reasoning attached.** Open with what you would do and why, then
give the alternatives. A menu with no recommendation makes the user do the synthesis you were
supposed to do.

**Ground every option in what the audit found.** An option that could have been written before
reading the repository is a generic option, and generic options are what the audit exists to
prevent. Attach the finding to the option: "Delete it - lane 7 traced no path to it from any entry
point, and nothing imports it."

**Build the menu expecting the user to reject it.** Two of the source run's four answers overrode
the recommendation and both overrides improved the plan. End every question with an explicit
opening, in your own words, for an answer that is not on the list. When the user supplies one,
adopt it. Do not map it back onto the closest option, and do not re-ask the question with the same
menu reworded.

**These four questions block.** If the user does not answer, wait. Only the user holds these facts
and a guess produces a plan built on an invented premise.

---

## Question 1 - "How do you currently run the things you already have deployed?"

Establishes the deployment target from **existing practice**, not from a survey of options.

Build the menu from what you found: the CI configuration, the container files, any deploy scripts,
any host referenced in configuration. Offer what the repository already implies, and ask whether
that is still how it works.

Do not present a comparison of hosting providers. The answer you need is what this user already
operates and is willing to keep operating, and a provider survey buries that.

What it constrains: everything infrastructure, and whether the definition of done can name a live
system to probe.

## Question 2 - "What is this work actually aiming at?"

The destination question. Offer **concrete end-states**, not adjectives.

A concrete end-state is a sentence someone could later confirm or deny: "a user can register
through the UI, click a real verification email and log in, against the deployed instance". An
adjective is "production ready", "solid", "modern", "clean". If an option contains an adjective,
rewrite it until it names an observable event.

Expect this one to be rejected hardest. The source run's answer rejected all four options and
supplied a two-stage split that became the most load-bearing idea in the whole plan. When the user
supplies a structure rather than picking an end-state, take the structure: it is worth more than
the menu was.

What it constrains: the track list, and what belongs to this plan versus a later one.

## Question 3 - "How should half-built areas be handled - deleted, flagged off, or finished?"

The subtraction question. This is what turns an audit into a plan, because it decides what
survives.

Do not ask it in the abstract. List the half-built areas lane 2 and lane 7 actually found, and ask
per area, or per group of areas that share a fate. Each option carries its evidence: how much of it
exists, what reaches it, what depends on it, what deleting it would cost.

Offer the three fates plainly:

- **Delete** - it goes, and the deletion carries the reachability trace that makes it safe.
- **Flag off** - it stays in the tree, unreachable behind a flag, with the flag named and the
  removal condition written down.
- **Finish** - it becomes tasks, with the remaining work sized from what the audit found.

An area with no decision defaults to nothing, which is the worst of the three. Get a fate for every
area.

What it constrains: the subtraction track, and the size of the plan.

## Question 4 - "What access do I have, and can I verify the result myself?"

A plan whose completion cannot be verified is not a plan. This question produces the falsifiable
definition of done.

Ask concretely: can you run the test suite, reach the datastore, hit the deployed instance, read
the CI logs, use a real account. For each thing you cannot reach, the definition of done needs a
criterion the **user** can demonstrate instead, and the ledger says who demonstrates it.

Then write the definition of done from the answers, and check every criterion against one test:
could someone look at the system and say this is false? "The frontend no longer uses mock data" is
falsifiable only if it names how you would tell, so write "no mock module is present in the built
artifact, verified by inspecting the build output rather than by grepping source".

What it constrains: the definition of done, and therefore whether the plan can ever be called
finished.
