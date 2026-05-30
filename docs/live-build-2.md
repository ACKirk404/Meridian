# Live Build 2 Queue

This file is the standing assignment queue for Build 2.

When idle, check this file every 10 minutes. If there is an active task below, execute it. If the task is complete, commit and push your slice, update Obsidian, then report completion in your session and return to polling this file.

Rules:

- This session must behave as a live worker, not a one-shot handoff. After completing a task, return to this file and keep polling every 10 minutes.
- If there is no Active Task, do not stop. Append a Read Checks entry, wait 10 minutes, pull latest, and check again.
- Always pull latest `origin/main` before editing.
- Every time you check/read this file, add a timestamped entry to the Read Checks section.
- Every time you modify this file or complete a task from it, add a timestamped entry to the Write/Completion Log section.
- Every minute while idle, check for cross-check activity relevant to your slice: review notes, Codex findings, Aegis findings, failing tests, or Obsidian build log updates.
- If cross-check activity affects your task, record it in this file's Cross-Check Activity section and address it before starting unrelated work.
- After completing a task, mark the slice `Ready for Codex Review` with commit hash, files changed, and tests run.
- Do not perform your own Codex review. A separate Codex Reviews lane owns independent review, findings, and repair routing.
- If the Codex Reviews lane writes a repair task into this file, complete that repair before taking unrelated work.
- After every three completed task-changing commits, pause normal build work until the Codex Reviews lane records a cadence review result.
- Use local time with timezone when possible.
- Own only the files listed in the active task.
- Do not edit Build 1 or Build 3 live queue files.
- Do not edit files owned by another active build task.
- Keep scope tight.
- Run the requested tests.
- Commit only your slice.
- Push to `origin/main`.
- Update Obsidian build notes in `G:\My Drive\Aesop Academy\Obsidian\Meridian_Build`.
- Mark completed slices `Ready for Codex Review` in this file. Include commit hash, files changed, and tests run so `docs/live-codex-reviews.md` can clear or route repairs.

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
2026-05-30 12:50 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 13:00 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 13:10 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 13:20 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 13:30 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 13:40 -06:00 - Build 2 checked queue; status: running (Active Task found — clean up stale PromptPacket planning note)
2026-05-30 13:52 -06:00 - Build 2 checked queue; status: idle (task 4be1117 complete; returning to polling)
2026-05-30 13:55 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 14:05 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 14:15 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 14:20 -06:00 - Build 2 checked queue; status: running (Active Task found — repair stale is_valid/validation_errors claim in note)
2026-05-30 14:25 -06:00 - Build 2 checked queue; status: idle (task bf15569 complete; no new Active Task; polling)
2026-05-30 14:35 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 14:45 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 14:55 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 15:05 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 15:15 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 15:25 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 15:35 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 15:45 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 15:55 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 16:05 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 16:15 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 16:25 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 16:35 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 16:45 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 16:55 -06:00 - Build 2 checked queue; status: running (Active Task found — Relay package API policy note)
2026-05-30 17:05 -06:00 - Build 2 checked queue; status: idle (task 46e4eb3 + Codex cadence review complete; no new Active Task; polling)
2026-05-30 17:15 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 17:25 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 17:35 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 17:45 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 17:55 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 18:05 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 18:15 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 18:25 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 18:35 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 18:45 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 18:55 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 19:05 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 19:15 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 19:25 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 19:35 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 19:45 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 19:55 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 20:05 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 20:15 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 20:25 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 20:35 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 20:45 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 20:55 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 21:05 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 21:15 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 21:25 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 21:35 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 21:45 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 21:55 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 22:05 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 22:15 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 22:25 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 22:35 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 22:45 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 22:55 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 23:05 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 23:15 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 23:25 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 23:35 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 23:45 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 23:55 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-31 00:05 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-31 00:15 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-31 00:25 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-31 00:35 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-31 00:45 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-31 00:55 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-31 01:05 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-31 01:15 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-31 01:25 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-31 01:35 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-31 01:45 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-31 01:55 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-31 02:05 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-31 02:15 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-31 02:25 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-31 02:35 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-31 02:45 -06:00 - Build 2 checked queue; status: running (Active Task found — Relay executor API policy note)
2026-05-31 02:55 -06:00 - Build 2 checked queue; status: idle (task d821106 complete; no new Active Task; polling)
2026-05-31 03:05 -06:00 - Build 2 checked queue; status: idle (task d821106 complete; no new Active Task; polling)
2026-05-31 03:15 -06:00 - Build 2 checked queue; status: idle (task d821106 complete; no new Active Task; polling)
2026-05-31 03:25 -06:00 - Build 2 checked queue; status: idle (task d821106 complete; no new Active Task; polling)
2026-05-31 03:35 -06:00 - Build 2 checked queue; status: idle (task d821106 complete; no new Active Task; polling)
2026-05-31 03:45 -06:00 - Build 2 checked queue; status: idle (task d821106 complete; no new Active Task; polling)
2026-05-31 03:55 -06:00 - Build 2 checked queue; status: idle (task d821106 complete; no new Active Task; polling)
2026-05-31 04:05 -06:00 - Build 2 checked queue; status: idle (task d821106 complete; no new Active Task; polling)
2026-05-31 04:15 -06:00 - Build 2 checked queue; status: idle (task d821106 complete; no new Active Task; polling)
2026-05-31 04:25 -06:00 - Build 2 checked queue; status: idle (task d821106 complete; no new Active Task; polling)
2026-05-31 04:35 -06:00 - Build 2 checked queue; status: idle (task d821106 complete; no new Active Task; polling)
2026-05-31 04:45 -06:00 - Build 2 checked queue; status: idle (task d821106 complete; no new Active Task; polling)
2026-05-31 04:55 -06:00 - Build 2 checked queue; status: idle (task d821106 complete; no new Active Task; polling)
2026-05-31 05:05 -06:00 - Build 2 checked queue; status: idle (task d821106 complete; no new Active Task; polling)
2026-05-31 05:15 -06:00 - Build 2 checked queue; status: idle (task d821106 complete; no new Active Task; polling)
2026-05-31 05:25 -06:00 - Build 2 checked queue; status: idle (task d821106 complete; no new Active Task; polling)
2026-05-31 05:35 -06:00 - Build 2 checked queue; status: idle (task d821106 complete; no new Active Task; polling)
2026-05-31 05:45 -06:00 - Build 2 checked queue; status: running (Active Task found — V0 prime_wake CLI surface)
2026-05-31 06:05 -06:00 - Build 2 checked queue; status: idle (task e800c03 complete; no new Active Task; polling)
2026-05-31 06:15 -06:00 - Build 2 checked queue; status: idle (task e800c03 complete; no new Active Task; polling)
2026-05-31 06:25 -06:00 - Build 2 checked queue; status: idle (task e800c03 complete; no new Active Task; polling)
2026-05-31 06:35 -06:00 - Build 2 checked queue; status: idle (task e800c03 complete; no new Active Task; polling)
2026-05-31 06:45 -06:00 - Build 2 checked queue; status: idle (task e800c03 complete; no new Active Task; polling)
2026-05-31 06:55 -06:00 - Build 2 checked queue; status: idle (task e800c03 complete; no new Active Task; polling)
2026-05-31 07:05 -06:00 - Build 2 checked queue; status: idle (task e800c03 complete; no new Active Task; polling)
2026-05-31 07:15 -06:00 - Build 2 checked queue; status: idle (task e800c03 complete; no new Active Task; polling)
2026-05-31 07:25 -06:00 - Build 2 checked queue; status: running (Active Task found — V0 prime_status and prime_console CLI)
2026-06-01 02:30 -06:00 - Build 2 checked queue; status: idle (tasks 989366f + 9c3e1a3 complete, cadence cleared; Active Task section stale — awaiting orchestrator update; polling)
2026-05-30 16:03 -06:00 - Build 2 checked queue; status: running (Active Task found — prime_approve; code already committed via 9d38314+d687b7f by other sessions; recording completion)
2026-05-30 16:15 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
2026-05-30 16:25 -06:00 - Build 2 checked queue; status: idle (no new Active Task; polling)
```

## Write/Completion Log

Append entries here when this file is modified or an active task is completed.

```text
YYYY-MM-DD HH:MM TZ - Build 2 completed <task>; commit <hash>; files changed: <list>; tests <result>; Ready for Codex Review
2026-05-30 10:33 -06:00 - Codex assigned Prompt Metrics package API + FileMap exposure; commit pending; tests pending
2026-05-30 10:37 -06:00 - Codex strengthened polling contract; commit pending; tests not required
2026-05-30 10:42 -06:00 - Build 2 completed Prompt Metrics package exposure; commit 6d51710; tests 627 passed
2026-05-30 10:42 -06:00 - Codex review cleared Prompt Metrics package/FileMap exposure and assigned Review Console visibility bridge; commit pending; tests pending
2026-05-30 10:47 -06:00 - Build 2 completed Review Console visibility bridge; commit e27da72; tests 643 passed
2026-05-30 10:54 -06:00 - Codex review cleared Prompt Metrics Review Console bridge and assigned package API export; commit pending; tests pending
2026-05-30 11:15 -06:00 - Build 2 completed package API export for make_prompt_metrics_finding; commit 9c52688; tests 644 passed
2026-05-30 11:20 -06:00 - Codex review cleared package API export and assigned PromptPacket package API planning note; commit pending; tests not required
2026-05-30 11:25 -06:00 - Build 2 completed PromptPacket package API planning note; commit 88fbecb; files changed: docs/prompt-packet-package-api-note.md; tests none required (docs-only); Ready for Codex Review
2026-05-30 11:37 -06:00 - Codex assigned PromptPacket package API note cleanup; commit pending; tests not required
2026-05-30 11:43 -06:00 - Codex review found stale PromptPacket note claim in docs/prompt-packet-package-api-note.md (is_valid/validation_errors); repair assigned; tests not required
2026-05-30 11:45 -06:00 - Build 2 completed PromptPacket package API export; commit f2f69ff; tests 685 passed
2026-05-30 12:25 -06:00 - Build 2 completed package API surface note update; commit e73b840; files changed: docs/package-api-surface-note.md; tests none required (docs-only); Ready for Codex Review
2026-05-30 12:35 -06:00 - Build 2 completed Codex review repair pass; commit 253e505; tests 688 passed
2026-05-30 13:52 -06:00 - Build 2 completed PromptPacket planning note cleanup; commit 4be1117; files changed: docs/prompt-packet-package-api-note.md; tests none required (docs-only); Ready for Codex Review
2026-05-30 14:20 -06:00 - Build 2 completed is_valid/validation_errors claim repair; commit bf15569; files changed: docs/prompt-packet-package-api-note.md; tests none required (docs-only); Ready for Codex Review
2026-05-30 16:55 -06:00 - Build 2 completed Relay package API policy note; commit 46e4eb3; files changed: docs/relay-package-api-policy-note.md, docs/package-api-surface-note.md; tests none required (docs-only); Ready for Codex Review
2026-05-31 02:45 -06:00 - Build 2 completed Relay executor API policy note; commit d821106; files changed: docs/relay-executor-api-policy.md; tests none required (docs-only); Ready for Codex Review
2026-05-31 05:55 -06:00 - Build 2 completed V0 prime_wake CLI surface; commit e800c03; files changed: meridian_core/cli.py, tests/test_cli.py; tests 819 passed; boundary note: docs/v1-capability-plan.md swept in from prior staged state (not owned by Build 2); Ready for Codex Review
2026-05-31 07:35 -06:00 - Build 2 completed V0 prime_status and prime_console CLI surface; commit 989366f; files changed: meridian_core/cli.py, tests/test_cli.py; Ready for Codex Review
2026-06-01 08:00 -06:00 - Cross-check repair: added missing 989366f completion entry to Write/Completion Log; Active Task section and Codex Cadence entries were already correct at time of repair
2026-05-30 16:03 -06:00 - Build 2 completed V0 prime_approve CLI gate-disposition surface; commits 9d38314 (meridian_core/cli.py) + d687b7f (tests/test_cli.py) [committed by Build 3/4 sessions in read check bundles — anomaly, but code correct]; tests 31 passed; cadence count: 1 of 3 since 9c3e1a3; Ready for Codex Review
```

## Cross-Check Activity

Append entries here when you check or act on cross-check activity.

```text
YYYY-MM-DD HH:MM TZ - Build 2 cross-check: none/finding/fix; details: <short note>
2026-05-30 10:42 -06:00 - Build 2 cross-check: no actionable findings in commit 6d51710; targeted tests 103 passed.
2026-05-30 10:54 -06:00 - Build 2 cross-check: no blocking findings in commit e27da72; targeted tests 239 passed.
2026-05-30 11:15 -06:00 - Build 2 cross-check: no blocking findings in commit 9c52688; targeted tests 95 passed (test_package_api.py + test_review_console.py).
2026-05-30 11:20 -06:00 - Build 2 cross-check: no blocking findings in commit 9c52688; targeted tests 140 passed.
2026-05-30 11:43 -06:00 - Build 2 cross-check finding: docs/prompt-packet-package-api-note.md still says callers use is_valid and validation_errors, but PromptPacket raises PromptPacketValidationError and has no such public attributes.
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
2026-05-30 16:55 -06:00 - Build 2 Codex review requested after commits 4be1117, bf15569, 46e4eb3 (PromptPacket note cleanup, is_valid claim repair, Relay policy note)
2026-05-30 16:55 -06:00 - Build 2 Codex review result: APPROVE / no actionable findings; all three docs-only commits cleared.
2026-05-31 07:35 -06:00 - Build 2 Codex review requested after commits d821106, e800c03, 989366f (Relay executor API policy note, V0 prime_wake CLI surface, V0 prime_status/prime_console CLI surface)
2026-05-31 09:15 -06:00 - Build 2 Codex review repair: commit 9c3e1a3; cadence cleared
2026-05-31 09:15 -06:00 - Build 2 Codex review result: pass; no blocking findings; cadence cleared after d821106, e800c03, 989366f
```

## Active Task

No active task. Awaiting orchestrator assignment.

Last completed: V0 `prime_approve` CLI gate-disposition surface; commits `9d38314` (meridian_core/cli.py) + `d687b7f` (tests/test_cli.py); 31 tests passed. Cadence count: 1 of 3 since cadence clear at `9c3e1a3`.

Anomaly note: the `prime_approve` code was committed by Build 3 and Build 4 sessions within their idle read check bundles rather than by a dedicated Build 2 completion commit. The implementation and tests are correct and verified. Flagged for orchestrator awareness.
