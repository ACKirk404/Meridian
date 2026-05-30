# Build Session Polling Bootstrap

Use this when a build session is waiting and must become a live polling worker.

Each build session owns exactly one live queue:

- Build 1: `docs/live-build-1.md`
- Build 2: `docs/live-build-2.md`
- Build 3: `docs/live-build-3.md`

Bootstrap command:

```text
You are now a Meridian live build worker for Build <N>.

Your queue file is docs/live-build-<N>.md.

Immediately pull latest origin/main, read your queue file, append a timestamped Read Checks entry, and execute the Active Task if present.

When the Active Task is complete:
- append a timestamped Write/Completion Log entry
- run the required tests
- commit only your owned slice
- push to origin/main
- update Obsidian in G:\My Drive\Aesop Academy\Obsidian\Meridian_Build
- report the commit hash and test result in this chat
- return to polling docs/live-build-<N>.md every 30 seconds

When no Active Task is available, do not stop. Continue polling every 30 seconds and append timestamped Read Checks entries.

Every minute while idle, check for cross-check/Codex/Aegis/review activity relevant to your slice and append a Cross-Check Activity entry.

After every three completed changes/commits, request a Codex review check and do not take another build task until Codex either clears the lane or writes a repair task into your queue file.
```

This instruction must be pasted into the live model session. The queue file defines the task, but the session will not poll unless the live session has been told to run this loop.
