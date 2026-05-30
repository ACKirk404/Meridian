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
- After completing a task, mark the slice `Ready for Codex Review` with commit hash, files changed, and tests run.
- Do not perform your own Codex review. A separate Codex Reviews lane owns independent review, findings, and repair routing.
- If the Codex Reviews lane writes a repair task into this file, complete that repair before taking unrelated work.
- After every three completed task-changing commits, pause normal build work until the Codex Reviews lane records a cadence review result.
- Use local time with timezone when possible.
- Own only the files listed in the active task.
- Do not edit Build 1 or Build 2 live queue files.
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
YYYY-MM-DD HH:MM TZ - Build 3 checked queue; status: idle/running/blocked
2026-05-30 10:54 -06:00 - Build 3 checked queue; status: active task found (Prompt Packet implementation checklist); starting work
2026-05-30 11:10 -06:00 - Build 3 checked queue; status: awaiting Codex review (3 commits completed, review requested)
2026-05-30 11:13 -06:00 - Build 3 checked queue; status: awaiting Codex review (no findings yet, polling)
2026-05-30 11:16 -06:00 - Build 3 checked queue; status: active task found (Prompt Packet Codex review checklist); starting work
2026-05-30 11:25 -06:00 - Build 3 checked queue; status: active task found (FileMap update for prompt_packet.py and capabilities map); starting work
2026-05-30 11:45 -06:00 - Build 3 checked queue; status: idle; FileMap task already complete (73c9628); no new Active Task assigned
2026-05-30 12:00 -06:00 - Build 3 checked queue; status: idle; no new Active Task assigned; polling
2026-05-30 12:15 -06:00 - Build 3 checked queue; status: idle; Active Task section stale (FileMap done at 73c9628); awaiting new task assignment
2026-05-30 12:30 -06:00 - Build 3 checked queue; status: active task found (live queue hygiene note); starting work
2026-05-30 12:35 -06:00 - Build 3 checked queue; status: active task found (queue hygiene repair — add live-build-5.md); starting work
2026-05-30 12:50 -06:00 - Build 3 checked queue; status: idle; Active Task section stale (repair done at ecc9fdf); awaiting new task assignment
2026-05-30 13:05 -06:00 - Build 3 checked queue; status: active task found (FileMap refresh for 7 new artifacts); starting work
2026-05-30 13:20 -06:00 - Build 3 checked queue; status: idle; Active Task section stale (FileMap refresh done at 7ec16ac); awaiting new task assignment
2026-05-30 13:35 -06:00 - Build 3 checked queue; status: idle; Active Task still stale; awaiting new task assignment
2026-05-30 13:50 -06:00 - Build 3 checked queue; status: idle; Active Task still stale; awaiting new task assignment
2026-05-30 14:05 -06:00 - Build 3 checked queue; status: active task found (repair stale FileMap Relay maturity claims); starting work
2026-05-30 14:35 -06:00 - Build 3 checked queue; status: idle; Active Task stale (Relay maturity repair done at ef934b1); awaiting Codex review result and new task
2026-05-30 14:50 -06:00 - Build 3 checked queue; status: idle; Active Task still stale; awaiting Codex review result and new task
2026-05-30 15:05 -06:00 - Build 3 checked queue; status: idle; Active Task still stale; awaiting Codex review result and new task
2026-05-30 15:20 -06:00 - Build 3 checked queue; status: idle; Active Task still stale; awaiting Codex review result and new task
2026-05-30 15:35 -06:00 - Build 3 checked queue; status: idle; Active Task still stale; awaiting Codex review result and new task
2026-05-30 15:50 -06:00 - Build 3 checked queue; status: idle; Active Task still stale; awaiting Codex review result and new task
2026-05-30 16:05 -06:00 - Build 3 checked queue; status: idle; Active Task still stale; awaiting Codex review result and new task
2026-05-30 16:20 -06:00 - Build 3 checked queue; status: idle; Active Task still stale; awaiting Codex review result and new task
2026-05-30 16:35 -06:00 - Build 3 checked queue; status: idle; Active Task still stale; awaiting Codex review result and new task
2026-05-30 16:50 -06:00 - Build 3 checked queue; status: idle; Active Task still stale; awaiting Codex review result and new task
2026-05-30 17:05 -06:00 - Build 3 checked queue; status: active task found (FileMap refresh for relay_dispatch, live-codex-reviews, prime-orchestration prototype, diagrams); starting work
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
2026-05-30 12:32 -06:00 - Build 3 completed live queue hygiene note; commit 26dc597; tests not required (docs-only); Obsidian updated; 3 commits completed (d84bb0f, 73c9628, 26dc597) — Codex review required before next task
2026-05-30 12:37 -06:00 - Build 3 completed queue hygiene repair (add live-build-5.md to lane set); commit ecc9fdf; tests not required (docs-only); Obsidian updated; polling resumed
2026-05-30 11:37 -06:00 - Codex assigned FileMap refresh for new Relay/Bifrost/queue artifacts; commit pending; tests pending
2026-05-30 13:08 -06:00 - Build 3 completed FileMap refresh (7 new artifacts); commit 7ec16ac; tests 46/46 filemap, 725 full suite; Obsidian updated; polling resumed
2026-05-30 14:20 -06:00 - Build 3 completed FileMap Relay maturity repair; commit ef934b1; tests 46/46 filemap, 748 full suite; Obsidian updated; Ready for Codex Review — files: docs/FileMap.md, meridian_core/filemap.py, tests/test_filemap.py
2026-05-30 17:20 -06:00 - Build 3 completed FileMap refresh (relay_dispatch, live-codex-reviews, prime-orchestration prototype); commit 4075ef4; tests 46/46 filemap, 785 full suite; Obsidian updated; Ready for Codex Review — files: docs/FileMap.md, meridian_core/filemap.py, tests/test_filemap.py
```

## Cross-Check Activity

Append entries here when you check or act on cross-check activity.

```text
YYYY-MM-DD HH:MM TZ - Build 3 cross-check: none/finding/fix; details: <short note>
2026-05-30 10:51 -06:00 - Build 3 cross-check: no blocking findings in commit 34792fb; brief is acceptable as design planning.
2026-05-30 12:32 -06:00 - Build 3 cross-check: Codex review finding LOW — lane set in queue hygiene note omitted live-build-5.md; repaired in ecc9fdf
2026-05-30 12:32 -06:00 - Build 3 cross-check: Codex review finding LOW — PromptPacketError should be PromptPacketValidationError in implementation-checklist and codex-review-checklist; deferred (not in this task's allowed files)
2026-05-30 12:32 -06:00 - Build 3 cross-check: Codex review finding LOW — test count 13 vs 14 in codex-review-checklist; deferred (not in this task's allowed files)
```

## Codex Review Cadence

After every three completed changes/commits by Build 3, request a Codex review check before starting another task. The review check should automatically repair actionable findings in Build 3-owned files, rerun tests, commit/push fixes, and report the result here.

```text
YYYY-MM-DD HH:MM TZ - Build 3 Codex review requested after commits <hash1>, <hash2>, <hash3>
YYYY-MM-DD HH:MM TZ - Build 3 Codex review finding: <severity>; details: <short note>
YYYY-MM-DD HH:MM TZ - Build 3 Codex review repair: commit <hash>; tests <result>; details: <short note>
YYYY-MM-DD HH:MM TZ - Build 3 Codex review result: pass/no actionable findings/fixed; details: <short note>
2026-05-30 11:10 -06:00 - Build 3 Codex review requested after commits 34792fb, 7b67c41, a996abc
2026-05-30 12:32 -06:00 - Build 3 Codex review requested after commits d84bb0f, 73c9628, 26dc597
2026-05-30 12:32 -06:00 - Build 3 Codex review finding: LOW; details: lane set omitted live-build-5.md in queue hygiene note Summary
2026-05-30 12:32 -06:00 - Build 3 Codex review finding: LOW; details: PromptPacketError → PromptPacketValidationError mismatch in implementation-checklist.md and codex-review-checklist.md (deferred — not in task scope)
2026-05-30 12:32 -06:00 - Build 3 Codex review finding: LOW; details: test count stated as 13, enumerated as 14 in codex-review-checklist.md (deferred — not in task scope)
2026-05-30 12:37 -06:00 - Build 3 Codex review repair: commit ecc9fdf; tests not required; details: added live-build-5.md to lane set in queue hygiene note
2026-05-30 12:37 -06:00 - Build 3 Codex review result: fixed (lane set); 2 LOW findings deferred pending future task assignment to allowed files
```

## Active Task

Current Active Task (supersedes any stale text below):

Goal: refresh FileMap for RelayDispatchPlan and Codex Reviews queue.

Allowed files only:

- `docs/FileMap.md`
- `meridian_core/filemap.py`
- `tests/test_filemap.py`

Task:

- Codex Reviews Round 1 observed that Build 1 introduced `meridian_core/relay_dispatch.py` after the last FileMap refresh.
- Add FileMap coverage for:
  - `meridian_core/relay_dispatch.py`
  - `tests/test_relay_dispatch.py`
  - `docs/live-codex-reviews.md`
  - `docs/prime-orchestration-harness-prototype.md`
  - the new Meridian engineering diagrams in `docs/assets/diagrams/02-*.png` through `06-*.png` if the human FileMap should mention canonical visual assets
- Keep entries concise and memory-injection useful.
- Update required-path coverage only for truly core source/process files.
- Do not edit runtime code.
- Do not edit package exports.
- Do not edit other live queues.

Tests:

```text
python -m pytest tests/test_filemap.py -q
python -m pytest -q
```

Completion:

- Commit only this FileMap slice.
- Push to `origin/main`.
- Update Obsidian.
- Mark this slice `Ready for Codex Review` with commit hash, files changed, and test count.

Stale prior text:

Goal: repair stale FileMap Relay maturity claims.

Allowed files only:

- `docs/FileMap.md`
- `meridian_core/filemap.py`
- `tests/test_filemap.py`

Task:

- Codex reviewed Build 3 commit `7ec16ac`.
- Repair stale FileMap claims:
  - `docs/FileMap.md` currently says PromptBudget has no Relay integration and RelayRoute will carry PromptBudgetPlan in the future.
  - Current `meridian_core/relay.py` already carries `prompt_budget: PromptBudgetPlan`.
  - Current Build 1 also added `meridian_core/relay_packet.py`.
- Update both the human FileMap and `make_default_map()` so memory injection does not teach stale architecture.
- Add `meridian_core/relay_packet.py` and `tests/test_relay_packet.py` to FileMap if missing.
- Add `docs/bifrost-cockpit-queue-status-brief.md` to the human FileMap if missing.
- Update required-path coverage if you add a core source file that should be guaranteed present.
- Do not edit runtime code.
- Do not edit package exports.
- Do not edit other live queues.

Tests:

```text
python -m pytest tests/test_filemap.py -q
python -m pytest -q
```

Completion:

- Commit only this FileMap slice.
- Push to `origin/main`.
- Update Obsidian.
- Mark this slice `Ready for Codex Review` with commit hash, files changed, and test count.
