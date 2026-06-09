# Backlog Authority Contract

Backend-owned contract for BAK3-BAK11.

## Scope

Backlog Authority owns durable backlog records, state transitions, audit history, import candidates, task-draft projection, project/initiative links, archive metadata, and query/filter fields.

It does not implement UI controls, bridge POST routes, Electron/renderer wiring, model calls, session dispatch, Prime autonomous recommendation, or Polaris writeback.

## Owned Rows

- BAK3 intake capture: create an auditable `BacklogItem` with source, source ref, creator, timestamp, project scope, priority, owner, blocked status, and initial revision.
- BAK4 modify item: preserve immutable revision history for title, summary, acceptance criteria, priority, owner, and blocked status changes.
- BAK5 approve item: move a captured/deferred item into `APPROVED` with approval evidence before task conversion.
- BAK6 deny/defer item: move an item to `REJECTED` or `DEFERRED` without deleting history.
- BAK7 convert to task: create a `BacklogTaskDraft` with owner, project, proof expectation, risk tier, and acceptance criteria; no session is dispatched.
- BAK8 link to project/initiative: attach a `BacklogScope` with project, initiative, and optional venture identifiers.
- BAK9 import candidate list: hold imported candidates with provenance and dedupe keys; `writes_back_to_source` must remain false.
- BAK10 archive backlog item: mark archived with actor, timestamp, and reason while preserving full audit/revision history.
- BAK11 search/filter backlog: filter by real backend fields: project, state, priority, owner, blocked status, archived visibility, and safe text.

## Display Safety

Serialized backlog records must not expose raw prompts, worker chat, provider responses, transcripts, credentials, tokens, API keys, secrets, or local absolute paths.

Backlog text and refs are bounded and validated at construction. Unsafe text fails closed with `BacklogValidationError`; it is not silently accepted or written.

## Persistence Boundary

`save_backlog()` and `load_backlog()` operate only on caller-supplied JSON paths. This slice does not choose the production store, mutate `docs/backlog.json` by itself, or expose bridge routes. Persistence tests use temporary paths.

## Downstream Boundaries

Goal Runtime may consume `to_goal_objective_ref()` and task drafts, but it does not rewrite backlog records.

Prime may read/query backlog records and recommend next work in a separate reviewed slice, but it does not mutate backlog state through this contract.

UI wiring remains a separate lane. UI may render reviewed backend records after a bridge/API surface exists; it must not invent mutation authority from display-only snapshots.
