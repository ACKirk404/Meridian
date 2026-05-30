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
2026-05-30 11:55 -06:00 - Build 2 checked queue; status: idle (task f2f69ff already complete; no new Active Task)
2026-05-30 12:05 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 12:15 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 12:25 -06:00 - Build 2 checked queue; status: running (Active Task found — update package API surface note for PromptPacket)
2026-05-30 12:40 -06:00 - Build 2 checked queue; status: idle (Codex review repair complete; no new Active Task)
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
2026-05-30 12:25 -06:00 - Build 2 completed package API surface note update; commit e73b840; tests none required (docs-only)
2026-05-30 12:35 -06:00 - Build 2 completed Codex review repair pass; commit 253e505; tests 688 passed
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
2026-05-30 12:35 -06:00 - Build 2 cross-check: Codex found 3 MEDIUM findings in 88fbecb/f2f69ff/e73b840; repaired 2 (test __all__ membership, stale candidates text); 1 deferred (prompt-packet-package-api-note.md not in allowed files); commit 253e505; tests 688 passed.
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
2026-05-30 12:25 -06:00 - Build 2 Codex review requested after commits 88fbecb, f2f69ff, e73b840 (PromptPacket planning note, PromptPacket export, surface note update)
2026-05-30 12:35 -06:00 - Build 2 Codex review finding: MEDIUM (3 findings — see Cross-Check Activity)
2026-05-30 12:35 -06:00 - Build 2 Codex review repair: commit 253e505; tests 688 passed; repaired 2/3 findings; 1 deferred (out of scope)
2026-05-30 12:35 -06:00 - Build 2 Codex review result: fixed (2 repaired, 1 deferred — no blocking findings remain in allowed files)
```

## Active Task

Goal: run Build 2 Codex review pass for package API surface.

Allowed files only:

- `meridian_core/__init__.py`
- `tests/test_package_api.py`
- `docs/package-api-surface-note.md`

Task:

- Build 2 has completed three package/API docs commits since the last review:
  - `88fbecb` PromptPacket package API planning note
  - `f2f69ff` PromptPacket package-root exports
  - `e73b840` package API surface note update
- Per the live queue cadence, stop normal build work and perform a Codex-style review pass on the Build 2-owned package API surface.
- Review only the allowed files.
- Check:
  - exported names are intentional and present in `__all__`
  - package API smoke tests cover PromptPacket exports
  - private helpers are not exported
  - package API note matches current root exports
  - no root export has been added without a clear public-contract reason
- Automatically repair actionable findings in the allowed files.
- If there are no actionable findings, record that result in this queue and return to polling.
- Do not edit FileMap; Build 3 owns FileMap.
- Do not edit PromptPacket runtime code; Build 1 owns PromptPacket.

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
