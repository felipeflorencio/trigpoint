---
description: Stop Trigpoint's hooks in this project until you resume them
---

```bash
mkdir -p .trigpoint && touch .trigpoint/paused
```

While that file exists both hooks exit immediately: no ledger state is stated at session start,
and nothing is re-run or unticked at the end of a turn. The ledger is left exactly as it is.

This stops everything that writes: both hooks fall silent, and `/trigpoint-verify` refuses
to re-run anything rather than editing a ledger whose owner asked it to stop.

Tell the user how to undo it: `rm .trigpoint/paused`.

For a single session instead, `TRIGPOINT_DISABLE=1` in the environment does the same without
touching the repository.
