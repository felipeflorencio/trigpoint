# Meridian Notes - Roadmap

**The top-level reference of work.** What we are building, in what order, and what is done.

This file is a synthetic ledger, in the shape of a pre-Trigpoint document, written for a
fictional note-taking product called Meridian Notes. It predates the Scope and Blocked by
metadata lines that Trigpoint's format requires, and it exists to prove the parser refuses to
invent structure that is not present.

---

## The two phases

| | Phase 1 - Make it true | Phase 2 - Finish the product |
| --- | --- | --- |
| **Goal** | Everything that exists is connected, correct and honest. | New capability: sharing, search, paid plans. |
| **Status** | In progress | Outlined only |
| **Rule** | No new product capability. Only make existing capability true. | Starts when Phase 1's definition of done is fully ticked. |

---

## Progress at a glance

| Track | Tasks | Done |
| --- | --- | --- |
| **T1 Foundation** | 4 | 0 |
| **T2 Security** | 5 | 0 |
| **T3 Sync correctness** | 6 | 0 |
| **T4 Editor** | 5 | 0 |
| **Hygiene** | 3 | 1 |

---

## T1 - Foundation

Nothing real starts until this lands. A fresh install currently fails schema validation.

- [ ] **0.1** Write the reconciliation migration for the notes table
- [ ] **0.2** Set schema validation to strict in the development profile
- [ ] **0.3** Make startup failures visible rather than swallowed by the logger
- [ ] **0.4** Delete the stale build directory and fix `.gitignore`

## T2 - Security

- [ ] **1.1** Add ownership checks to the notebook endpoints
- [ ] **1.2** Audit every endpoint that takes a notebook id for the same flaw
- [ ] **1.3** Stop logging the session token at debug level
- [ ] **1.4** Implement rate limiting on the sync endpoint
- [ ] **1.5** Clear the client cache on sign out

## T3 - Sync correctness

- [ ] **2.1** Fix the conflict-resolution merge for offline edits
- [ ] **2.2** Fix the sort-order contract between client and server
- [ ] **2.3** Fix the token refresh response contract
- [ ] **2.4** Fix the tag rename fan-out across existing notes
- [ ] **2.5** Fix timestamp handling across time zones
- [ ] **2.6** Delete the stub sync client returning canned responses

## T4 - Editor

The editor defaults to a local-only mode and is roughly a year behind the sync backend.

- [ ] **3.1** Repair the attachment upload path
- [ ] **3.2** Gate the offline fixture data and flip the default to the real API
- [ ] **3.3** Fix the seven broken editor commands
- [ ] **3.4** Make the discard-draft control reachable
- [ ] **3.5** Mount the notification toast or remove it

## Hygiene

- [x] **7.1** Settle on one product name. **DECIDED: the product is Meridian Notes.**
- [ ] **7.2** Rewrite the README against the verified setup steps
- [ ] **7.3** Keep the dependency list current

---

## Hand-off contracts

| | Contract | Enforced by |
| --- | --- | --- |
| **C1** | Environment variable list plus an example file. Any track adding, renaming or removing a variable updates it in the same commit. | Test: every variable read by the app has an example entry |
| **C2** | Published API snapshot, consumed by the editor track | Test: every editor call path exists in the snapshot |

**Ledger discipline.** A box above is ticked only with the verification command and its output
recorded. Never on assumption.

---

## Definition of done for Phase 1

Each is falsifiable on purpose. Phase 2 starts when all these are demonstrated.

- [ ] 1. A fresh clone against an empty database boots with no manual intervention
- [ ] 2. Listing notes returns 200 with real persisted data
- [ ] 3. Authorization tests pass: user A cannot read, edit or delete user B's notebook
- [ ] 4. A session survives access-token expiry without forcing a sign out
- [ ] 5. The editor default is the real API, and no fixture module is present in the built bundle
- [ ] 6. Every command reaches a working action or has been removed
- [ ] 7. Both test suites pass in CI, integration tests included
- [ ] 8. A push to the main branch produces a deploy that reaches a healthy state, verified by
      probing the live health endpoint
- [ ] 9. No credential exists in the repository; all secrets are rotated and injected at deploy
      time
- [ ] 10. A new user can register through the UI, receive and click a real verification email,
      then sign in with no manual database change, and can create a note, sync it and see it on
      a second device

---

## Companion documents

| Document | Contents |
| --- | --- |
| `docs/reactivation/BACKLOG.md` | The manual: full detail per task |
| `docs/reactivation/AUDIT.md` | The findings and their verification status |
| `docs/reactivation/DEPLOYMENT-DESIGN.md` | Hosting design, Dockerfiles, pipeline |
| `docs/ARCHITECTURE.md` | Backend architecture |
