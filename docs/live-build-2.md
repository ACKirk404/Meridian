# Live Build 2 Queue

This file is the standing assignment queue for Build 2.

When idle, check this file every 30 seconds. If there is an active task below, execute it. If the task is complete, commit and push your slice, update Obsidian, then report completion in your session and return to polling this file.

Rules:

- Always pull latest `origin/main` before editing.
- Every time you check/read this file, add a timestamped entry to the Read Checks section.
- Every time you modify this file or complete a task from it, add a timestamped entry to the Write/Completion Log section.
- Every minute while idle, check for cross-check activity relevant to your slice: review notes, Codex findings, Aegis findings, failing tests, or Obsidian build log updates.
- If cross-check activity affects your task, record it in this file's Cross-Check Activity section and address it before starting unrelated work.
- Use local time with timezone when possible.
- Own only the files listed in the active task.
- Do not edit Build 1 or Build 3 live queue files.
- Do not edit files owned by another active build task.
- Keep scope tight.
- Run the requested tests.
- Commit only your slice.
- Push to `origin/main`.
- Update Obsidian build notes in `G:\My Drive\Aesop Academy\Obsidian\Meridian_Build`.

## Read Checks

Append entries here when this file is checked while idle.

```text
YYYY-MM-DD HH:MM TZ - Build 2 checked queue; status: idle/running/blocked
```

## Write/Completion Log

Append entries here when this file is modified or an active task is completed.

```text
YYYY-MM-DD HH:MM TZ - Build 2 completed <task>; commit <hash>; tests <result>
```

## Cross-Check Activity

Append entries here when you check or act on cross-check activity.

```text
YYYY-MM-DD HH:MM TZ - Build 2 cross-check: none/finding/fix; details: <short note>
```

## Active Task

Goal: review and harden Prompt Metrics domain slice.

Commit to review:

- `abff252`

Allowed files only:

- `meridian_core/prompt_metrics.py`
- `tests/test_prompt_metrics.py`

Review questions:

- Should negative prompt timings or token counts be rejected?
- Should native baseline greater than total response time produce a negative delta, or should overhead floor at zero?
- Are `HEALTHY` / `WATCH` / `DEGRADED` thresholds reasonable?
- Should prompt token count influence status, or only timing?
- Is the empty sample list error clear enough?
- Are immutable dataclasses the right choice?

Task:

- If the current slice is good, write an Obsidian review note and do not change code.
- If changes are needed, make them only in the allowed files.
- Keep this domain-only.
- No UI.
- No persistence.
- No model calls.

Tests:

```text
python -m pytest tests/test_prompt_metrics.py -q
python -m pytest -q
```

Completion:

- If changes were made, commit only this slice.
- Push to `origin/main` if a commit was made.
- Update Obsidian.
- Report whether `abff252` was accepted as-is or changed, plus test count and commit hash if applicable.
