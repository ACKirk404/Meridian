# Live Build 3 Queue

This file is the standing assignment queue for Build 3.

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
- Do not edit Build 1 or Build 2 live queue files.
- Do not edit files owned by another active build task.
- Keep scope tight.
- Run the requested tests.
- Commit only your slice.
- Push to `origin/main`.
- Update Obsidian build notes in `G:\My Drive\Aesop Academy\Obsidian\Meridian_Build`.

## Read Checks

Append entries here when this file is checked while idle.

```text
YYYY-MM-DD HH:MM TZ - Build 3 checked queue; status: idle/running/blocked
2026-05-30 10:54 -06:00 - Build 3 checked queue; status: active task found (Prompt Packet implementation checklist); starting work
2026-05-30 11:10 -06:00 - Build 3 checked queue; status: awaiting Codex review (3 commits completed, review requested)
2026-05-30 11:13 -06:00 - Build 3 checked queue; status: awaiting Codex review (no findings yet, polling)
2026-05-30 11:16 -06:00 - Build 3 checked queue; status: active task found (Prompt Packet Codex review checklist); starting work
2026-05-30 11:25 -06:00 - Build 3 checked queue; status: active task found (FileMap update for prompt_packet.py and capabilities map); starting work
2026-05-30 11:45 -06:00 - Build 3 checked queue; status: idle; FileMap task already complete (73c9628); no new Active Task assigned
2026-05-30 12:00 -06:00 - Build 3 checked queue; status: idle; no new Active Task assigned; polling
2026-05-30 12:15 -06:00 - Build 3 checked queue; status: idle; Active Task section stale (FileMap done at 73c9628); awaiting new task assignment
```

## Write/Completion Log

Append entries here when this file is modified or an active task is completed.

```text
YYYY-MM-DD HH:MM TZ - Build 3 completed <task>; commit <hash>; tests <result>
2026-05-30 10:33 -06:00 - Codex assigned Prompt Packet domain slice; commit pending; tests pending
2026-05-30 10:37 -06:00 - Codex strengthened polling contract; commit pending; tests not required
2026-05-30 10:39 -06:00 - Codex reassigned Build 3 to Haiku-sized Prompt Packet design brief; commit pending; tests not required
2026-05-30 10:48 -06:00 - Build 3 completed Prompt Packet design brief; commit 34792fb; tests 627 passing; Obsidian updated; polling resumed
2026-05-30 10:51 -06:00 - Codex review cleared Prompt Packet design brief and assigned Haiku-sized implementation checklist; commit pending; tests not required
2026-05-30 10:57 -06:00 - Build 3 completed Prompt Packet implementation checklist; commit a996abc; tests 644 passing; Obsidian updated; 3 commits completed (34792fb, 7b67c41, a996abc) — Codex review required before next task
2026-05-30 11:10 -06:00 - Build 3 Codex review requested; awaiting automated review and findings for owned files
2026-05-30 11:18 -06:00 - Build 3 completed Prompt Packet Codex review checklist; commit d84bb0f; tests 644 passing; Obsidian updated; polling resumed
2026-05-30 11:28 -06:00 - Build 3 completed FileMap update (prompt_packet.py + capabilities architecture map); commit 73c9628; tests 46 passing (test_filemap.py); Obsidian updated; polling resumed
```

## Cross-Check Activity

Append entries here when you check or act on cross-check activity.

```text
YYYY-MM-DD HH:MM TZ - Build 3 cross-check: none/finding/fix; details: <short note>
2026-05-30 10:51 -06:00 - Build 3 cross-check: no blocking findings in commit 34792fb; brief is acceptable as design planning.
```

## Codex Review Cadence

After every three completed changes/commits by Build 3, request a Codex review check before starting another task. The review check should automatically repair actionable findings in Build 3-owned files, rerun tests, commit/push fixes, and report the result here.

```text
YYYY-MM-DD HH:MM TZ - Build 3 Codex review requested after commits <hash1>, <hash2>, <hash3>
YYYY-MM-DD HH:MM TZ - Build 3 Codex review finding: <severity>; details: <short note>
YYYY-MM-DD HH:MM TZ - Build 3 Codex review repair: commit <hash>; tests <result>; details: <short note>
YYYY-MM-DD HH:MM TZ - Build 3 Codex review result: pass/no actionable findings/fixed; details: <short note>
2026-05-30 11:10 -06:00 - Build 3 Codex review requested after commits 34792fb, 7b67c41, a996abc
```

## Active Task

Goal: create a live queue hygiene note.

Allowed files only:

- `docs/live-build-queue-hygiene.md`

Task:

- Write a short operational note for live build queue hygiene based on what we learned from Q polling.
- Cover:
  - why completed Active Tasks must be replaced or explicitly marked complete
  - how stale Active Task sections cause repeated queue checks
  - why Read Checks, Write/Completion Log, Cross-Check Activity, and Codex Review Cadence should remain separate
  - how allowed-file ownership prevents lane collisions
  - how queue files should eventually map to a real Meridian session-harness queue state
  - what Prime should do when a lane is idle
- Keep it simple and concrete.
- Do not edit other live queue files.
- Do not edit runtime code.
- Do not edit FileMap.
- Do not edit package exports.

Tests:

- No tests required. This is docs-only.

Completion:

- Commit only this docs slice.
- Push to `origin/main`.
- Update Obsidian.
- Report commit hash in your session.
