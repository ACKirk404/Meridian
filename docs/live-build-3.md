# Live Build 3 Queue

This file is the standing assignment queue for Build 3.

When idle, check this file every 30 seconds. If there is an active task below, execute it. If the task is complete, commit and push your slice, update Obsidian, then report completion in your session and return to polling this file.

Rules:

- Always pull latest `origin/main` before editing.
- Every time you check/read this file, add a timestamped entry to the Read Checks section.
- Every time you modify this file or complete a task from it, add a timestamped entry to the Write/Completion Log section.
- Every minute while idle, check for cross-check activity relevant to your slice: review notes, Codex findings, Aegis findings, failing tests, or Obsidian build log updates.
- If cross-check activity affects your task, record it in this file's Cross-Check Activity section and address it before starting unrelated work.
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
```

## Cross-Check Activity

Append entries here when you check or act on cross-check activity.

```text
YYYY-MM-DD HH:MM TZ - Build 3 cross-check: none/finding/fix; details: <short note>
```

## Active Task

Goal: create a Relay Prompt Metrics integration brief.

Allowed files only:

- `docs/relay-prompt-metrics-integration-brief.md`

Do not edit FileMap yet. Build 1 is currently touching FileMap/package API.

Task:

Write a focused future integration brief for how Relay should use Prompt Metrics.

Cover:

- Where `PromptMetricSample` should be created in the future Relay dispatch lifecycle.
- How to measure prompt construction time.
- How to record prompt token count.
- How to measure time to first token and total response time.
- How to compare against native/vendor baseline when available.
- How Prompt Metrics should interact with Prompt Budget.
- How `HEALTHY` / `WATCH` / `DEGRADED` should affect Prime decisions.
- What should appear in Review Console versus stay internal.
- What must not be inserted into worker prompts.
- Required tests before runtime integration.

No runtime code.
No FileMap edits.
No package API edits.

Tests:

- No tests required unless you change code.

Completion:

- Commit only this brief.
- Push to `origin/main`.
- Update Obsidian.
- Report commit hash in your session.
