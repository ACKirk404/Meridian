# Live Build 5 Queue

This file is the standing assignment queue for Build 5.

Build 5 is the Bifrost / session-harness product lane. It should work on UI behavior briefs, session queue activation, cockpit interaction contracts, and user-facing workflow design. It should not implement runtime code unless Codex explicitly assigns a code slice later.

When idle, check this file every 30 seconds. If there is an active task below, execute it. If the task is complete, commit and push your slice, update Obsidian, then report completion in your session and return to polling this file.

Rules:

- This session must behave as a live worker, not a one-shot handoff. After completing a task, return to this file and keep polling every 30 seconds.
- If there is no Active Task, do not stop. Append a Read Checks entry, wait 30 seconds, pull latest, and check again.
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
- Do not edit Build 1, Build 2, Build 3, or Build 4 live queue files.
- Do not edit runtime code unless the active task explicitly allows it.
- Do not edit files owned by another active build task.
- Keep scope tight.
- Run requested tests if the task calls for tests.
- Commit only your slice.
- Push to `origin/main`.
- Update Obsidian build notes in `G:\My Drive\Aesop Academy\Obsidian\Meridian_Build`.
- Mark completed slices `Ready for Codex Review` in this file. Include commit hash, files changed, and tests run so `docs/live-codex-reviews.md` can clear or route repairs.

## Read Checks

Append entries here when this file is checked while idle.

```text
YYYY-MM-DD HH:MM TZ - Build 5 checked queue; status: idle/running/blocked
2026-05-30 11:33 -06:00 - Build 5 checked queue; status: running; Active Task = create docs/bifrost-session-queue-activation-brief.md; origin/main up to date
2026-05-30 11:35 -06:00 - Build 5 checked queue; status: idle; Active Task = bifrost-session-queue-activation-brief (already complete at 3b5435f in Write/Completion Log; awaiting orchestrator reassignment); origin/main at ecc9fdf
2026-05-30 11:37 -06:00 - Build 5 checked queue; status: idle; Active Task = bifrost-session-queue-activation-brief (still stale; complete at 3b5435f); Cross-Check Activity: none; origin/main at 7792243
2026-05-30 11:39 -06:00 - Build 5 checked queue; status: running; Active Task = design Bifrost cockpit queue status surface at docs/bifrost-cockpit-queue-status-brief.md; Cross-Check Activity: none; origin/main at 7792243
2026-05-30 11:43 -06:00 - Build 5 checked queue; status: idle; Active Task = bifrost-cockpit-queue-status-brief (already complete at 818bb31 in Write/Completion Log; awaiting orchestrator reassignment); Cross-Check Activity: none; origin/main at d1d5619
2026-05-30 11:44 -06:00 - Build 5 checked queue; status: idle; Active Task = bifrost-cockpit-queue-status-brief (still stale; complete at 818bb31); Cross-Check Activity: none; origin/main at ac0a5d3
2026-05-30 11:46 -06:00 - Build 5 checked queue; status: running; rules 18-21 updated by orchestrator (no self-Codex review; Codex Reviews lane owns review/findings/repairs; pause after 3 task-changing commits); new Active Task = design V0 cockpit layout at docs/bifrost-v0-cockpit-layout-brief.md; Cross-Check Activity: none; origin/main at a37b3cb
2026-05-30 11:50 -06:00 - Build 5 checked queue; status: paused (cadence); V0 cockpit layout brief committed at d1d32af = 3rd task-changing commit; pausing normal build work per rule 21 until Codex Reviews lane records cadence review result; will continue polling for repair tasks; Cross-Check Activity: none; origin/main at c3e3245
2026-05-30 11:54 -06:00 - Build 5 checked queue; status: paused (cadence); Codex Reviews Round 1 scope declared (Build 5 range 818bb31..d1d32af) but no review result/finding/repair routed for Build 5 yet; Active Task still names completed V0 cockpit layout brief; Cross-Check Activity: none; origin/main at 8a29011
```

## Write/Completion Log

Append entries here when this file is modified or an active task is completed.

```text
YYYY-MM-DD HH:MM TZ - Build 5 completed <task>; commit <hash>; tests <result>
2026-05-30 11:30 -06:00 - Codex created Build 5 Bifrost/session-harness queue and assigned queue activation brief; commit pending; tests not required
2026-05-30 11:33 -06:00 - Build 5 completed Bifrost session queue activation brief at docs/bifrost-session-queue-activation-brief.md; commit pending; tests not required
2026-05-30 11:37 -06:00 - Codex assigned Bifrost cockpit queue status brief; commit pending; tests not required
2026-05-30 11:39 -06:00 - Build 5 completed Bifrost cockpit queue status surface brief at docs/bifrost-cockpit-queue-status-brief.md; commit pending; tests not required
2026-05-30 11:46 -06:00 - Build 5 completed Bifrost V0 cockpit layout brief at docs/bifrost-v0-cockpit-layout-brief.md; commit pending; tests not required
```

## Ready for Codex Review

Append entries here when a completed slice is ready for the Codex Reviews lane to inspect. Format: commit hash, files changed, tests run.

```text
2026-05-30 11:33 -06:00 - Build 5 slice Ready for Codex Review; commit 3b5435f; files: docs/bifrost-session-queue-activation-brief.md, docs/live-build-5.md; tests: none (docs-only)
2026-05-30 11:39 -06:00 - Build 5 slice Ready for Codex Review; commit 818bb31; files: docs/bifrost-cockpit-queue-status-brief.md, docs/live-build-5.md; tests: none (docs-only)
2026-05-30 11:46 -06:00 - Build 5 slice Ready for Codex Review; commit d1d32af; files: docs/bifrost-v0-cockpit-layout-brief.md; tests: none (docs-only); note: 3rd task-changing commit triggers cadence pause per rule 21 — Build 5 pauses normal build work until Codex Reviews lane records cadence review result
```

## Cross-Check Activity

Append entries here when you check or act on cross-check activity.

```text
YYYY-MM-DD HH:MM TZ - Build 5 cross-check: none/finding/fix; details: <short note>
```

## Codex Review Cadence

After every three completed changes/commits by Build 5, request a Codex review check before starting another task. The review check should automatically repair actionable findings in Build 5-owned files, rerun relevant tests if any, commit/push fixes, and report the result here.

```text
YYYY-MM-DD HH:MM TZ - Build 5 Codex review requested after commits <hash1>, <hash2>, <hash3>
YYYY-MM-DD HH:MM TZ - Build 5 Codex review finding: <severity>; details: <short note>
YYYY-MM-DD HH:MM TZ - Build 5 Codex review repair: commit <hash>; tests <result>; details: <short note>
YYYY-MM-DD HH:MM TZ - Build 5 Codex review result: pass/no actionable findings/fixed; details: <short note>
```

## Active Task

Goal: design the V0 cockpit layout around Prime and the Review Console.

Allowed files only:

- `docs/bifrost-v0-cockpit-layout-brief.md`

Task:

- Write a concise product/architecture brief for the V0 cockpit layout.
- Cover:
  - Prime as the dominant top/center relationship surface
  - Orchestrator Queue and Review Console as tabbed prompt surfaces
  - bottom or side instrumentation for Beacon, Relay, Aegis, Compass, Bifrost, queue state
  - where the Harness button belongs and what it opens
  - how much worker/session detail is visible by default
  - how Mission Objectives can be called up on demand
  - how the NASA-style Go sequence should appear visually without becoming noise
  - how the layout scales from 3 lanes to 25 lanes
  - what V0 should intentionally leave out
- Keep it design-only.
- Do not edit runtime code.
- Do not edit FileMap; Build 3 owns FileMap.
- Do not edit package exports; Build 2 owns package API.
- Do not edit other live queues.

Tests:

- No tests required. This is docs-only.

Completion:

- Commit only this docs slice.
- Push to `origin/main`.
- Update Obsidian.
- Mark this slice `Ready for Codex Review` with commit hash, files changed, and tests run.
