# Example - Roadmap

**The ledger.**

## Progress at a glance

<!-- trigpoint:progress:begin -->
<!-- trigpoint:progress:end -->

## T1 Foundation

**Scope:** Make it boot from clean
**Blocked by:** nothing

Prose about the track that must not be parsed as a task.

- [ ] **1.1** Write the migration
- [x] **1.2** Set validate mode
      **Verified:** `./run boot` -> started clean. 2026-08-27

## T2 Security

**Scope:** Credentials and authorization
**Blocked by:** T1

- [x] **2.1** Rotate the keys   **Verified:** `./check secrets` -> 0 found. 2026-08-27

## Hand-off contracts

Prose only. This section has no Scope line and is not a track.

- [ ] **X.1** A task-shaped line outside a track, which must be ignored

## Definition of done

- [ ] 1. A fresh clone boots with no manual intervention
- [x] 2. The health endpoint returns 200
