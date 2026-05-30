# Live Build 1 Queue

This file is the standing assignment queue for Build 1.

When idle, check this file every 30 seconds. If there is an active task below, execute it. If the task is complete, commit and push your slice, update Obsidian, then report completion in your session and return to polling this file.

Rules:

- This session must behave as a live worker, not a one-shot handoff. After completing a task, return to this file and keep polling every 30 seconds.
- If there is no Active Task, do not stop. Append a Read Checks entry, wait 30 seconds, pull latest, and check again.
- Always pull latest `origin/main` before editing.
- Every time you check/read this file, add a timestamped entry to the Read Checks section.
- Every time you modify this file or complete a task from it, add a timestamped entry to the Write/Completion Log section.
- Every minute while idle, check for cross-check activity relevant to your slice: review notes, Codex findings, Aegis findings, failing tests, or Obsidian build log updates.
- If cross-check activity affects your task, record it in this file's Cross-Check Activity section and address it before starting unrelated work.
- After every three completed changes/commits from this build session, stop normal build work and request a Codex review check before taking another build task.
- The Codex review check must automatically repair actionable findings in your owned files, rerun required tests, commit/push the repair slice, and report findings/fixes back in this file's heartbeat sections.
- Record Codex review requests, findings, repairs, and outcomes in the Codex Review Cadence section.
- Use local time with timezone when possible.
- Own only the files listed in the active task.
- Do not edit Build 2 or Build 3 live queue files.
- Do not edit files owned by another active build task.
- Keep scope tight.
- Run the requested tests.
- Commit only your slice.
- Push to `origin/main`.
- Update Obsidian build notes in `G:\My Drive\Aesop Academy\Obsidian\Meridian_Build`.

## Read Checks

Append entries here when this file is checked while idle.

```text
YYYY-MM-DD HH:MM TZ - Build 1 checked queue; status: idle/running/blocked
2026-05-30 ~22:30 CDT - Build 1 checked queue; status: running (active task found)
2026-05-30 ~22:45 CDT - Build 1 checked queue; status: running (relay prompt budget integration task)
2026-05-30 ~23:00 CDT - Build 1 checked queue; status: running (PromptBudgetPlan immutability hardening task)
2026-05-30 ~23:02 CDT - Build 1 checked queue; status: idle (task complete, awaiting next assignment)
```

## Write/Completion Log

Append entries here when this file is modified or an active task is completed.

```text
YYYY-MM-DD HH:MM TZ - Build 1 completed <task>; commit <hash>; tests <result>
2026-05-30 ~22:30 CDT - Build 1 completed Prompt Budget package API + FileMap; commit d18d651; tests 604 passed
2026-05-30 10:33 -06:00 - Codex assigned Relay Prompt Budget integration into RelayRoute; commit pending; tests pending
2026-05-30 10:37 -06:00 - Codex strengthened polling contract; commit pending; tests not required
2026-05-30 ~22:45 CDT - Build 1 completed Relay Prompt Budget integration into RelayRoute; commit 95bb942; tests 626 passed
2026-05-30 10:39 -06:00 - Codex review cleared RelayRoute integration and assigned PromptBudgetPlan immutability repair; commit pending; tests pending
2026-05-30 ~23:00 CDT - Build 1 completed PromptBudgetPlan immutability hardening; commit 305b8d4; tests 627 passed
```

## Cross-Check Activity

Append entries here when you check or act on cross-check activity.

```text
YYYY-MM-DD HH:MM TZ - Build 1 cross-check: none/finding/fix; details: <short note>
2026-05-30 10:39 -06:00 - Build 1 cross-check finding: PromptBudgetPlan is frozen but allowed_sources is mutable list; repair before Prompt Packet runtime work.
```

## Codex Review Cadence

After every three completed changes/commits by Build 1, request a Codex review check before starting another task. The review check should automatically repair actionable findings in Build 1-owned files, rerun tests, commit/push fixes, and report the result here.

```text
YYYY-MM-DD HH:MM TZ - Build 1 Codex review requested after commits <hash1>, <hash2>, <hash3>
YYYY-MM-DD HH:MM TZ - Build 1 Codex review finding: <severity>; details: <short note>
YYYY-MM-DD HH:MM TZ - Build 1 Codex review repair: commit <hash>; tests <result>; details: <short note>
YYYY-MM-DD HH:MM TZ - Build 1 Codex review result: pass/no actionable findings/fixed; details: <short note>
```

## Active Task

Goal: harden PromptBudgetPlan immutability.

Allowed files only:

- `meridian_core/prompt_budget.py`
- `tests/test_prompt_budget.py`
- `tests/test_relay.py`

Task:

- Codex review cleared Build 1 commit `95bb942` for RelayRoute integration.
- One follow-up finding remains in the Prompt Budget domain:
  - `PromptBudgetPlan` is declared `frozen=True`, but `allowed_sources` is a mutable `list[str]`.
  - Current tests prove independent copies, but they also show mutation is possible.
- Change `allowed_sources` to an immutable collection, preferably `tuple[str, ...]`.
- Preserve ergonomic construction from lists.
- Preserve existing tier mappings and Relay behavior.
- Update tests that currently append to `allowed_sources` so they assert true immutability instead.
- Keep the backward-compatible `PromptBudget` alias.
- No UI.
- No persistence.
- No model calls.

Tests:

```text
python -m pytest tests/test_relay.py tests/test_prompt_budget.py -q
python -m pytest -q
```

Completion:

- Commit only this slice.
- Push to `origin/main`.
- Update Obsidian.
- Report commit hash and test count in your session.
