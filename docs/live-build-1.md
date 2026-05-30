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
2026-05-30 ~23:10 CDT - Build 1 checked queue; status: running (Prompt Packet domain model task)
2026-05-30 ~23:12 CDT - Build 1 checked queue; status: idle (awaiting next assignment)
2026-05-30 ~23:20 CDT - Build 1 checked queue; status: running (PromptPacket validation hardening task)
2026-05-30 ~23:22 CDT - Build 1 checked queue; status: idle (awaiting next assignment)
2026-05-31 ~00:05 CDT - Build 1 checked queue; status: running (PromptPacket model-dispatch boundary task)
2026-05-31 ~00:08 CDT - Build 1 checked queue; status: idle (awaiting next assignment)
2026-05-31 ~00:20 CDT - Build 1 checked queue; status: idle (no new active task)
2026-05-31 ~00:30 CDT - Build 1 checked queue; status: idle (no new active task)
2026-05-31 ~00:40 CDT - Build 1 checked queue; status: running (Codex review pass on PromptPacket slice)
2026-05-31 ~00:45 CDT - Build 1 checked queue; status: idle (review complete, awaiting next assignment)
2026-05-31 ~01:00 CDT - Build 1 checked queue; status: running (Relay PromptPacket integration plan task)
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
2026-05-30 10:54 -06:00 - Codex review cleared PromptBudgetPlan immutability hardening and assigned Prompt Packet domain model; commit pending; tests pending
2026-05-30 ~23:10 CDT - Build 1 completed Prompt Packet domain model; commit b453e2e; tests 669 passed
2026-05-30 11:00 -06:00 - Codex review found PromptPacket direct-construction validation bypass and assigned repair; commit pending; tests pending
2026-05-30 ~23:20 CDT - Build 1 completed PromptPacket validation hardening; commit 0ce0cf9; tests 675 passed
2026-05-31 ~00:05 CDT - Build 1 completed PromptPacket model_payload() dispatch boundary; commit 111a975; tests 685 passed; Obsidian updated
2026-05-31 ~00:40 CDT - Build 1 Codex review repair: commit 9389563; tests 688 passed; whitespace prompt + empty packet_id validation added; Obsidian updated
```

## Cross-Check Activity

Append entries here when you check or act on cross-check activity.

```text
YYYY-MM-DD HH:MM TZ - Build 1 cross-check: none/finding/fix; details: <short note>
2026-05-30 10:39 -06:00 - Build 1 cross-check finding: PromptBudgetPlan is frozen but allowed_sources is mutable list; repair before Prompt Packet runtime work.
2026-05-30 10:54 -06:00 - Build 1 cross-check: no blocking findings in commit 305b8d4; targeted tests 239 passed.
2026-05-30 11:00 -06:00 - Build 1 cross-check finding: PromptPacket validates through build_prompt_packet(), but direct PromptPacket(...) construction can bypass validation.
```

## Codex Review Cadence

After every three completed changes/commits by Build 1, request a Codex review check before starting another task. The review check should automatically repair actionable findings in Build 1-owned files, rerun tests, commit/push fixes, and report the result here.

```text
YYYY-MM-DD HH:MM TZ - Build 1 Codex review requested after commits <hash1>, <hash2>, <hash3>
YYYY-MM-DD HH:MM TZ - Build 1 Codex review finding: <severity>; details: <short note>
YYYY-MM-DD HH:MM TZ - Build 1 Codex review repair: commit <hash>; tests <result>; details: <short note>
YYYY-MM-DD HH:MM TZ - Build 1 Codex review result: pass/no actionable findings/fixed; details: <short note>
2026-05-31 ~00:40 CDT - Build 1 Codex review requested after commits b453e2e, 0ce0cf9, 111a975
2026-05-31 ~00:40 CDT - Build 1 Codex review finding: MEDIUM; whitespace-only prompt passes validation (truthy but blank)
2026-05-31 ~00:40 CDT - Build 1 Codex review finding: MEDIUM; empty packet_id passes without error
2026-05-31 ~00:40 CDT - Build 1 Codex review repair: commit 9389563; tests 688 passed; strip() check + packet_id validation added
2026-05-31 ~00:40 CDT - Build 1 Codex review result: fixed; all other checks clear (no aliasing, no leakage, no budget gaps)
```

## Active Task

Goal: create the Relay PromptPacket integration plan.

Allowed files only:

- `docs/relay-prompt-packet-integration-plan.md`

Task:

- Build 1 completed PromptPacket domain, validation, dispatch boundary, and Codex review repair.
- Before editing Relay runtime, write a short implementation plan for how Relay should build/use PromptPacket.
- Cover:
  - what Relay should pass into `build_prompt_packet(...)`
  - where prompt token counting belongs
  - how source lineage should be calculated
  - how `model_payload()` should be the only model-facing string
  - how Prompt Metrics should observe packet construction without bloating worker prompts
  - what tests should be written before runtime integration
  - what must not happen yet
- Keep it practical and build-ready.
- Do not edit runtime code.
- Do not edit package exports; Build 2 owns package API.
- Do not edit FileMap; Build 3 owns FileMap.
- No UI.
- No persistence.
- No model calls.

Tests:

- No tests required. This is docs-only.

Completion:

- Commit only this slice.
- Push to `origin/main`.
- Update Obsidian.
- Report commit hash and test count in your session.
