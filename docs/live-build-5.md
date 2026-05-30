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
- After every three completed changes/commits from this build session, stop normal build work and request a Codex review check before taking another task.
- The Codex review check must automatically repair actionable findings in your owned files, rerun relevant tests if any, commit/push fixes, and report findings/fixes back in this file's heartbeat sections.
- Record Codex review requests, findings, repairs, and outcomes in the Codex Review Cadence section.
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

## Read Checks

Append entries here when this file is checked while idle.

```text
YYYY-MM-DD HH:MM TZ - Build 5 checked queue; status: idle/running/blocked
2026-05-30 11:33 -06:00 - Build 5 checked queue; status: running; Active Task = create docs/bifrost-session-queue-activation-brief.md; origin/main up to date
2026-05-30 11:35 -06:00 - Build 5 checked queue; status: idle; Active Task = bifrost-session-queue-activation-brief (already complete at 3b5435f in Write/Completion Log; awaiting orchestrator reassignment); origin/main at ecc9fdf
2026-05-30 11:37 -06:00 - Build 5 checked queue; status: idle; Active Task = bifrost-session-queue-activation-brief (still stale; complete at 3b5435f); Cross-Check Activity: none; origin/main at 7792243
2026-05-30 11:39 -06:00 - Build 5 checked queue; status: running; Active Task = design Bifrost cockpit queue status surface at docs/bifrost-cockpit-queue-status-brief.md; Cross-Check Activity: none; origin/main at 7792243
```

## Write/Completion Log

Append entries here when this file is modified or an active task is completed.

```text
YYYY-MM-DD HH:MM TZ - Build 5 completed <task>; commit <hash>; tests <result>
2026-05-30 11:30 -06:00 - Codex created Build 5 Bifrost/session-harness queue and assigned queue activation brief; commit pending; tests not required
2026-05-30 11:33 -06:00 - Build 5 completed Bifrost session queue activation brief at docs/bifrost-session-queue-activation-brief.md; commit pending; tests not required
2026-05-30 11:37 -06:00 - Codex assigned Bifrost cockpit queue status brief; commit pending; tests not required
2026-05-30 11:39 -06:00 - Build 5 completed Bifrost cockpit queue status surface brief at docs/bifrost-cockpit-queue-status-brief.md; commit pending; tests not required
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

Goal: design the Bifrost cockpit queue status surface.

Allowed files only:

- `docs/bifrost-cockpit-queue-status-brief.md`

Task:

- Write a concise product/architecture brief for how the Meridian cockpit should show queue-driven worker activity without recreating the Polaris worker-card wall.
- Cover:
  - global queue activation state
  - per-lane state for Build 1 through Build 5
  - statuses: idle, polling, running, blocked, needs review, needs human gate, stale
  - how Prime should decide what appears in the Orchestrator Queue versus the Review Console
  - what a user can click or command from the cockpit
  - what should be hidden until there is a problem
  - how Beacon supplies liveness/staleness signals
  - how Aegis/cross-check results surface without hijacking the main conversation
  - what Polaris taught us about too many visible worker cards
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
- Report commit hash in your session.
