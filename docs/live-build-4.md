# Live Build 4 Queue

This file is the standing assignment queue for Build 4.

Build 4 is the Opus high-level thinking lane. It should work on architecture, capabilities, strategy, naming, review frameworks, and synthesis. It should not implement runtime code unless Codex explicitly assigns a code slice later.

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
- The Codex review check must automatically repair actionable findings in your owned files, rerun required tests if any are relevant, commit/push fixes, and report findings/fixes back in this file's heartbeat sections.
- Record Codex review requests, findings, repairs, and outcomes in the Codex Review Cadence section.
- Use local time with timezone when possible.
- Own only the files listed in the active task.
- Do not edit Build 1, Build 2, or Build 3 live queue files.
- Do not edit runtime code unless the active task explicitly allows it.
- Do not edit files owned by another active build task.
- Keep scope tight.
- Run the requested tests if the task calls for tests.
- Commit only your slice.
- Push to `origin/main`.
- Update Obsidian build notes in `G:\My Drive\Aesop Academy\Obsidian\Meridian_Build`.

## Read Checks

Append entries here when this file is checked while idle.

```text
YYYY-MM-DD HH:MM TZ - Build 4 checked queue; status: idle/running/blocked
2026-05-30 11:06 -06:00 - Build 4 checked queue; status: running; Active Task = capabilities architecture map; pulled origin/main fast-forward to d84bb0f
```

## Write/Completion Log

Append entries here when this file is modified or an active task is completed.

```text
YYYY-MM-DD HH:MM TZ - Build 4 completed <task>; commit <hash>; tests <result>
2026-05-30 11:04 -06:00 - Codex created Build 4 Opus high-level queue and assigned Meridian capabilities architecture map; commit pending; tests not required
2026-05-30 11:09 -06:00 - Build 4 completed Meridian capabilities architecture map (docs/meridian-capabilities-architecture-map.md); commit pending push; tests not required
```

## Cross-Check Activity

Append entries here when you check or act on cross-check activity.

```text
YYYY-MM-DD HH:MM TZ - Build 4 cross-check: none/finding/fix; details: <short note>
```

## Codex Review Cadence

After every three completed changes/commits by Build 4, request a Codex review check before starting another task. The review check should automatically repair actionable findings in Build 4-owned files, rerun relevant tests if any, commit/push fixes, and report the result here.

```text
YYYY-MM-DD HH:MM TZ - Build 4 Codex review requested after commits <hash1>, <hash2>, <hash3>
YYYY-MM-DD HH:MM TZ - Build 4 Codex review finding: <severity>; details: <short note>
YYYY-MM-DD HH:MM TZ - Build 4 Codex review repair: commit <hash>; tests <result>; details: <short note>
YYYY-MM-DD HH:MM TZ - Build 4 Codex review result: pass/no actionable findings/fixed; details: <short note>
```

## Active Task

Goal: create a Meridian capabilities architecture map.

Allowed files only:

- `docs/meridian-capabilities-architecture-map.md`

Task:

- Read the existing Meridian architecture/capability docs before writing:
  - `context.md`
  - `docs/meridian-capabilities.md`
  - `docs/meridian-pillars.md`
  - `docs/polaris-lessons-for-meridian.md`
  - `docs/relay-prompt-budget-integration-brief.md`
  - `docs/prompt-packet-design-brief.md`
  - `docs/prompt-packet-implementation-checklist.md`
- Create a high-level architecture map of Meridian's major capabilities.
- Focus on what makes Meridian different and marketable:
  - Prime as persistent orchestrator
  - worker sessions as harness-driven execution lanes
  - live queue / pull / poll / review loop
  - Prompt Budget / Prompt Packet / Prompt Metrics
  - Review Console and non-orchestrator surface
  - Aegis proof and gated cognition
  - Council reasoning
  - memory and effective unbounded context
  - cross-check review automation
  - future multi-user / connected Meridian possibility
- For each capability, include:
  - one-sentence definition
  - why it matters
  - current maturity: planned / domain slice / integrated / needs hardening
  - likely harness owner
  - risks or open questions
- Keep this strategic and architectural.
- Do not write runtime code.
- Do not edit FileMap yet.
- Do not edit package exports.
- Do not edit other live queues.

Tests:

- No tests required. This is docs-only.

Completion:

- Commit only this docs slice.
- Push to `origin/main`.
- Update Obsidian.
- Report commit hash in your session.
