# {{ Topic }} - design

**Written:** {{ YYYY-MM-DD }}
**Status:** {{ approved, not yet implemented }}
**Ledger:** `ROADMAP.md`
**Audit:** `docs/trigpoint/audit/`

---

## 1. What this is

{{ Two or three sentences: what the work produces, and what changes for whom when it lands. }}

### The problem it solves

{{ The problem, stated with the numbers the audit found. Name the mechanism that causes it, not
the symptom. }}

## 2. Non-goals

{{ What this work deliberately does not do. Each with the reason, because a non-goal without a
reason gets re-litigated. }}

- **Not {{ x }}.** {{ why }}

## 3. Condition on arrival

What the audit established, before any plan. State it as fact.

| Area | What was found | Evidence |
| --- | --- | --- |
| {{ area }} | {{ finding }} | `docs/trigpoint/audit/{{ lane }}.md` |

**Where this contradicts the original framing:** {{ the premise check, restated. If the audit
contradicted nothing, say that in one line. }}

## 4. The shape of the plan

{{ Why the tracks are the tracks. What blocks what, and why the critical path is where it is. This
is the section that explains the ledger rather than repeating it. }}

## 5. Decisions taken, with their reasons

| Decision | Reason |
| --- | --- |
| {{ decision }} | {{ reason, including whose call it was and when if the user made it }} |

## 6. What was asked, and what was answered

{{ The four questions and the answers, including the ones that rejected the menu. An override that
changed the plan is the most valuable line in this document; record it verbatim. }}

| Question | Answer |
| --- | --- |
| How do you run what you already have deployed? | {{ answer }} |
| What is this work actually aiming at? | {{ answer }} |
| Half-built areas: deleted, flagged off, or finished? | {{ answer }} |
| What access is there, and can the result be verified? | {{ answer }} |

## 7. Honest limits

{{ What this plan does not know. Which lanes did not run and what that leaves unsearched. Which
findings are PLAUSIBLE rather than CONFIRMED and are therefore investigation tasks. What would
falsify the plan's central assumption. }}

- **{{ limit }}.** {{ what it means for the plan }}
