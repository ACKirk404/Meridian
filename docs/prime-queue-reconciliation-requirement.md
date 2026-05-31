# Prime Queue Reconciliation Requirement

**Status:** Architecture requirement
**Owner:** Prime / Session Lifecycle Harness / Beacon Harness
**Source:** Live V1/V2 queue experiment

Prime must reconcile queue state before assigning, repeating, restarting, or resteering work.

## Problem

Live queue text can become stale. A lane can still show an Active Task even after the slice has landed, tests have passed, the progress tracker has moved forward, or the review lane has cleared the work.

The V1 cockpit build exposed this failure mode clearly: Build 5 completed the Electron cockpit app shell, but stale Active Task prose still described older Bifrost work. If Prime trusts the prose alone, it can reissue completed work, waste model time, confuse review lanes, or regress the build plan.

## Requirement

Before Prime assigns or repeats work, it must reconcile the queue against completion evidence.

Prime must inspect:

- Active Task text
- Write/Completion Log entries
- `Ready for Codex Review` markers
- git commit history and changed files
- files that exist on disk
- progress tracker state
- Codex Review checkpoint ledgers
- Obsidian build notes when available

If completion evidence proves the task is already done, Prime must treat the Active Task as stale even if the queue still calls it active.

## Required Prime Behavior

When a stale-complete task is detected, Prime must:

1. Mark the task as stale-complete in orchestration state.
2. Avoid reissuing the old task.
3. Route any missing review, FileMap, package API, or tracker follow-up.
4. Assign only the next non-overlapping task.
5. Preserve proof explaining why duplicate assignment was prevented.

## Native Object Needed

V2 Session Lifecycle should introduce a queue reconciliation object with fields like:

- lane id
- queue path
- visible active task summary
- completion evidence found
- commit evidence
- file existence evidence
- tracker evidence
- review evidence
- reconciliation result: active, stale-complete, blocked, ready-for-review, ready-for-next-task
- next action

## Guardrail

Active Task prose is never the sole source of truth. It is an input to Prime's state model, not the state model itself.
