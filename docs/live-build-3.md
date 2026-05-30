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
```

## Write/Completion Log

Append entries here when this file is modified or an active task is completed.

```text
YYYY-MM-DD HH:MM TZ - Build 3 completed <task>; commit <hash>; tests <result>
2026-05-30 10:33 -06:00 - Codex assigned Prompt Packet domain slice; commit pending; tests pending
2026-05-30 10:37 -06:00 - Codex strengthened polling contract; commit pending; tests not required
```

## Cross-Check Activity

Append entries here when you check or act on cross-check activity.

```text
YYYY-MM-DD HH:MM TZ - Build 3 cross-check: none/finding/fix; details: <short note>
```

## Codex Review Cadence

After every three completed changes/commits by Build 3, request a Codex review check before starting another task. The review check should automatically repair actionable findings in Build 3-owned files, rerun tests, commit/push fixes, and report the result here.

```text
YYYY-MM-DD HH:MM TZ - Build 3 Codex review requested after commits <hash1>, <hash2>, <hash3>
YYYY-MM-DD HH:MM TZ - Build 3 Codex review finding: <severity>; details: <short note>
YYYY-MM-DD HH:MM TZ - Build 3 Codex review repair: commit <hash>; tests <result>; details: <short note>
YYYY-MM-DD HH:MM TZ - Build 3 Codex review result: pass/no actionable findings/fixed; details: <short note>
```

## Active Task

Goal: create the Prompt Packet domain slice.

Allowed files only:

- `meridian_core/prompt_packet.py`
- `tests/test_prompt_packet.py`

Task:

- Add a small domain-only module that models the bounded prompt packet Relay will eventually send through the agent/model harness.
- Suggested concepts:
  - `PromptContextSource` enum or value object for allowed context sources
  - `PromptPacket` immutable dataclass containing:
    - `request`
    - `instructions`
    - `context_references`
    - `budget`
    - `estimated_tokens`
    - optional `notes` / `warnings`
  - `build_prompt_packet(...)` helper that validates the packet against a provided `PromptBudgetPlan`
- Enforce:
  - estimated tokens cannot exceed the budget's max context tokens
  - context sources must be allowed by the budget plan
  - empty request is rejected
  - packet is immutable
- Keep this domain-only.
- Do not import or edit Relay.
- Do not assemble long prompts.
- Do not call models.
- Do not add UI.
- Do not add persistence.
- Do not edit package exports or FileMap in this slice.

Tests:

```text
python -m pytest tests/test_prompt_packet.py tests/test_prompt_budget.py -q
python -m pytest -q
```

Completion:

- Commit only this slice.
- Push to `origin/main`.
- Update Obsidian.
- Report commit hash and test count in your session.
