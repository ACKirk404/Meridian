# Live Build 2 Queue

This file is the standing assignment queue for Build 2.

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
2026-05-30 10:38 -06:00 - Build 2 checked queue; status: running (Active Task found — Prompt Metrics package exposure)
2026-05-30 10:44 -06:00 - Build 2 checked queue; status: running (Active Task found — Review Console visibility bridge)
2026-05-30 10:57 -06:00 - Build 2 checked queue; status: running (Active Task found — package API export for make_prompt_metrics_finding)
2026-05-30 11:15 -06:00 - Build 2 checked queue; status: idle (Active Task completed — returning to polling)
2026-05-30 11:25 -06:00 - Build 2 checked queue; status: running (Active Task found — PromptPacket package API planning note)
2026-05-30 11:30 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 11:35 -06:00 - Build 2 checked queue; status: idle (Active Task section not yet updated; polling)
2026-05-30 11:45 -06:00 - Build 2 checked queue; status: running (Active Task found — PromptPacket package API export)
```

## Write/Completion Log

Append entries here when this file is modified or an active task is completed.

```text
YYYY-MM-DD HH:MM TZ - Build 2 completed <task>; commit <hash>; tests <result>
2026-05-30 10:33 -06:00 - Codex assigned Prompt Metrics package API + FileMap exposure; commit pending; tests pending
2026-05-30 10:37 -06:00 - Codex strengthened polling contract; commit pending; tests not required
2026-05-30 10:42 -06:00 - Build 2 completed Prompt Metrics package exposure; commit 6d51710; tests 627 passed
2026-05-30 10:42 -06:00 - Codex review cleared Prompt Metrics package/FileMap exposure and assigned Review Console visibility bridge; commit pending; tests pending
2026-05-30 10:47 -06:00 - Build 2 completed Review Console visibility bridge; commit e27da72; tests 643 passed
2026-05-30 10:54 -06:00 - Codex review cleared Prompt Metrics Review Console bridge and assigned package API export; commit pending; tests pending
2026-05-30 11:15 -06:00 - Build 2 completed package API export for make_prompt_metrics_finding; commit 9c52688; tests 644 passed
2026-05-30 11:20 -06:00 - Codex review cleared package API export and assigned PromptPacket package API planning note; commit pending; tests not required
2026-05-30 11:25 -06:00 - Build 2 completed PromptPacket package API planning note; commit 88fbecb; tests none required (docs-only)
2026-05-30 11:45 -06:00 - Build 2 completed PromptPacket package API export; commit f2f69ff; tests 685 passed
```

## Cross-Check Activity

Append entries here when you check or act on cross-check activity.

```text
YYYY-MM-DD HH:MM TZ - Build 2 cross-check: none/finding/fix; details: <short note>
2026-05-30 10:42 -06:00 - Build 2 cross-check: no actionable findings in commit 6d51710; targeted tests 103 passed.
2026-05-30 10:54 -06:00 - Build 2 cross-check: no blocking findings in commit e27da72; targeted tests 239 passed.
2026-05-30 11:15 -06:00 - Build 2 cross-check: no blocking findings in commit 9c52688; targeted tests 95 passed (test_package_api.py + test_review_console.py).
2026-05-30 11:20 -06:00 - Build 2 cross-check: no blocking findings in commit 9c52688; targeted tests 140 passed.
2026-05-30 11:45 -06:00 - Build 2 cross-check: no blocking findings in commit f2f69ff; targeted tests 11 passed (test_package_api.py).
```

## Codex Review Cadence

After every three completed changes/commits by Build 2, request a Codex review check before starting another task. The review check should automatically repair actionable findings in Build 2-owned files, rerun tests, commit/push fixes, and report the result here.

```text
YYYY-MM-DD HH:MM TZ - Build 2 Codex review requested after commits <hash1>, <hash2>, <hash3>
YYYY-MM-DD HH:MM TZ - Build 2 Codex review finding: <severity>; details: <short note>
YYYY-MM-DD HH:MM TZ - Build 2 Codex review repair: commit <hash>; tests <result>; details: <short note>
YYYY-MM-DD HH:MM TZ - Build 2 Codex review result: pass/no actionable findings/fixed; details: <short note>
2026-05-30 11:15 -06:00 - Build 2 Codex review requested after commits 6d51710, e27da72, 9c52688 (Prompt Metrics package exposure, Review Console bridge, package API export)
2026-05-30 11:20 -06:00 - Build 2 Codex review result: pass/no actionable findings; package API export cleared.
```

## Active Task

Goal: export PromptPacket package API after validation hardening.

Allowed files only:

- `meridian_core/__init__.py`
- `tests/test_package_api.py`

Task:

- Build 1 completed PromptPacket validation hardening in commit `0ce0cf9`.
- The package-root API can now expose the PromptPacket domain safely.
- Add root exports for:
  - `PromptPacket`
  - `PromptPacketValidationError`
  - `build_prompt_packet`
- Add package API smoke tests proving those names import from `meridian_core`.
- Do not export private helpers.
- Do not edit PromptPacket implementation; Build 1 owns PromptPacket runtime behavior.
- Do not edit FileMap; Build 3 owns FileMap.
- Do not edit docs other than this live queue if needed.
- Keep this package-boundary only.

Tests:

```text
python -m pytest tests/test_package_api.py -q
python -m pytest -q
```

Completion:

- Commit only this slice.
- Push to `origin/main`.
- Update Obsidian.
- Report commit hash and test count in your session.
