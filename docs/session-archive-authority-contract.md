# Session Archive Authority Contract

Session Archive Authority owns backend-only archive catalog records, reload
plans, run-again plans, and authorized transcript access handles for V2 archive
rows. It consumes reviewed Session Lifecycle close/write-through results and
never wires UI controls, bridge routes, provider calls, filesystem writes, or
live session execution.

## Authority

- `ArchivedSessionRecord` records display-safe archive metadata from a
  successful `SessionCloseWriteThroughResult`.
- `ArchiveCatalogEntry` exposes catalog posture for reload/run-again visibility.
- `ArchiveReloadPlan` and `ArchiveRunAgainPlan` are typed plans only. They may
  report readiness, but `execution_authorized` remains `False`.
- `TranscriptAccessHandle` exposes metadata or an authorized handle. It never
  carries raw transcript text.

## Guardrails

- No raw transcript, raw prompt, worker chat, provider response, credential,
  token, local path, or path-shaped safe URI payload may serialize.
- Transcript text may be accepted only to derive hash and length metadata.
- Reload/run-again planning does not start sessions, dispatch models, mutate UI,
  or write archive storage.
- Obsidian proof refs are metadata only in this slice.
