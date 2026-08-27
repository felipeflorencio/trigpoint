# Trigpoint

A plan of record that cannot drift.

Trigpoint turns a codebase into a `ROADMAP.md` ledger, a dashboard generated from it, and a
design spec explaining why the plan is shaped that way. Then it keeps them true while the work is
done.

## What it enforces

- **Counts are generated, never typed.** The progress table and the dashboard are rewritten from
  the ledger between markers. Nothing derived has a hand-written copy to disagree with.
- **A ticked task must carry its proof.** A `**Verified:**` line records the command that was run
  and is re-run later; a `**Recorded:**` line states what happened, for work no command can
  re-check, and is never re-run. A tick with neither is an error, not a warning. Never invent a
  command to satisfy the gate.
- **Proofs are re-run.** At the end of a working turn the recorded commands run again, and a task
  whose command stopped passing unticks itself with a `**Regressed:**` note. An optimistic tick
  does not survive contact with the next turn.
- **Nothing is ticked automatically.** A machine can show a claim has become false. Deciding that
  work is finished stays with a person.

## Using it

Read `skills/trigpoint/SKILL.md`. It carries the whole method: the audit lanes, the question
ladder, the evidence rules, and the ledger format.

The commands are `/trigpoint` to build a plan, `/trigpoint-sync` to regenerate the table and the
dashboard, `/trigpoint-verify` to re-prove the ledger and approve commands, and
`/trigpoint-pause` to stop the hooks in a repository.

## Requirements

Python 3.9 or later, standard library only. No packages to install. On Windows the hooks run
through `hooks/run-hook.cmd`, which finds `py -3`, `python3` or `python`, and stays silent if
none of them exist.

Trigpoint does nothing in a repository until someone runs the skill there, which is what creates
`.trigpoint/`. Installing it changes no project.
