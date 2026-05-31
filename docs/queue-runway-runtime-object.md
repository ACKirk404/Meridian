# V2 Queue Runway Runtime Object Contract

**Date:** 2026-05-31
**Owner:** Build 1
**Status:** Contract — design-only, no runtime code yet
**Supersedes:** the markdown-only `docs/live-build-N.md` polling model
**Related:** `docs/prime-queue-runway-policy.md` (the invariant this object enforces)

## Purpose

The queue runway runtime object is the canonical, machine-readable representation
of one build lane's queue state. It replaces today's markdown-only
`docs/live-build-N.md` polling files as the source of truth for coordinator
decisions while leaving the markdown file in place as a human-readable mirror.

The runtime object exists so Prime (and any coordinator surface) can:

- promote Next → Active deterministically instead of by free-text rewrite,
- detect stale Active Task bodies (work already in Completed Slices),
- compute cadence and review-gate state without text parsing,
- escalate stalled lanes without a human reading every queue file.

This contract defines the object's shape. It does not yet implement persistence,
transport, or a Bifrost surface. Subsequent slices will wire those in.

## Object: `QueueRunway`

One `QueueRunway` instance exists per build lane. Identity is the lane id.

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `lane_id` | string | yes | Lane identifier (e.g. `"build-1"`, `"build-5"`, `"codex-reviews-b"`). Unique across the Meridian repo. |
| `worktree_path` | string | yes | Absolute filesystem path to the unique worktree owning this lane's current session. Empty when no session is attached. |
| `queue_file_path` | string | yes | Repo-relative path to the markdown mirror (e.g. `"docs/live-build-1.md"`). |
| `active_task` | `TaskEntry \| null` | yes | The one executable task this lane is running or ready to run. `null` only during a clean idle window (no work, no stale body). |
| `next_candidate` | `TaskEntry \| null` | yes | The one task staged behind `active_task`. Required to satisfy the runway invariant unless the lane is officially drained. |
| `cadence` | `CadenceState` | yes | Three-commit cadence status (see below). |
| `review_gate` | `ReviewGateState` | yes | Codex review lane gating status (see below). |
| `last_read_at` | timestamp (RFC 3339, UTC) | yes | When this lane last appended a Read Check entry. Heartbeats older than the polling-interval threshold are stale. |
| `last_write_at` | timestamp (RFC 3339, UTC) | yes | When this lane last appended a Write/Completion Log entry (a real task-changing commit, not a heartbeat). |
| `escalation` | `EscalationState` | yes | Whether the lane needs coordinator/human attention (see below). |
| `policy_version` | string | yes | Version of `docs/prime-queue-runway-policy.md` this runway is compliant with (e.g. `"1.0"`). |

### Nested types

#### `TaskEntry`

| Field | Type | Required | Description |
|---|---|---|---|
| `goal` | string | yes | One-sentence summary of the task. |
| `allowed_files` | string list | yes | Repo-relative paths the lane may edit for this task. Empty list means docs-only with no file edits expected; `null` is not allowed. |
| `task_body` | string | yes | The full task description (the same text humans read in the markdown mirror). |
| `tests` | string list | yes | Test commands to run, in order. Empty list means no tests required. |
| `completion_criteria` | string | yes | What "done" looks like (e.g. "commit slice, push, update Obsidian, mark Ready for Codex Review"). |
| `assigned_at` | timestamp | yes | When this task was promoted into this slot. |
| `commit_hash` | string \| null | yes | If complete, the commit that landed it. Coordinator uses this to detect stale Active Task bodies whose work is already in Completed Slices. |

A task is **stale** when its `task_body` describes work that already appears in
the lane's Completed Slices with the matching `commit_hash` — the runtime object
exposes this so the lane refuses to re-execute it.

#### `CadenceState`

| Field | Type | Description |
|---|---|---|
| `window_index` | int (1..3) | Position within the current three-commit window. |
| `window_commits` | string list (length 0..3) | Hashes of task-changing commits in this window. Heartbeats are not counted. |
| `status` | enum: `running` \| `paused-for-review` \| `cleared` | `paused-for-review` when `len(window_commits) == 3` and Codex Reviews has not yet cleared the window. |
| `last_review_clear_at` | timestamp \| null | When the Codex Reviews lane last cleared this lane's cadence. |

#### `ReviewGateState`

| Field | Type | Description |
|---|---|---|
| `pending_reviews` | string list | Commit hashes marked "Ready for Codex Review" but not yet reviewed. |
| `pending_repairs` | `TaskEntry` list | Repair tasks routed from a Codex Reviews lane that must complete before unrelated work. |
| `last_review_round` | string \| null | Identifier of the most recent Codex Reviews round that touched this lane (e.g. `"Round B14"`). |

#### `EscalationState`

| Field | Type | Description |
|---|---|---|
| `level` | enum: `none` \| `stale-active` \| `stalled` \| `boundary-cross` \| `worktree-collision` | The kind of attention needed. |
| `reason` | string | Free-text explanation of the escalation (e.g. `"Active Task body refilled with completed slice b5bbab8"`). |
| `since` | timestamp \| null | When the lane first entered this escalation. |
| `acknowledged_by` | string \| null | Lane or session id that acknowledged the escalation, if any. |

`level` semantics:

- `none` — runway invariant holds, lane is healthy.
- `stale-active` — `active_task` describes work already in Completed Slices; the lane is heartbeating idle while the body still names done work.
- `stalled` — `last_write_at` is older than a configured threshold and no `next_candidate` is staged.
- `boundary-cross` — a recent commit by this lane touched files outside the active task's `allowed_files` (the existing self-reported boundary-cross pattern in cross-check activity).
- `worktree-collision` — multiple sessions are operating on the same worktree path, violating the unique-worktree rule from the runway policy.

## Invariants

The runtime object enforces the runway policy's invariant in machine-checkable
form. At all times for a healthy lane:

1. `active_task` is non-null **or** `escalation.level` is `none` and the lane is
   in a coordinator-approved drained state.
2. `next_candidate` is non-null **or** the lane is officially drained.
3. `cadence.status == "paused-for-review"` implies the lane refuses new Active
   Task promotions until the Codex Reviews lane records a clear.
4. `len(review_gate.pending_repairs) > 0` implies the lane's `active_task` is
   one of those repair tasks until they all clear.
5. `escalation.level != "none"` implies a coordinator (Prime or human) must
   either resolve the cause or move the lane to a drained state.
6. For any task with `commit_hash != null`, that hash must appear in the lane's
   Completed Slices list before the task can be considered safely complete.

## Lifecycle

The runtime object is updated by three actors:

| Actor | What they write |
|---|---|
| Build lane session | `last_read_at` on every poll; `last_write_at` and `cadence.window_commits` on real task-changing commits; `escalation` self-reports |
| Coordinator (Prime) | `active_task`, `next_candidate` (promotion, supersession); cross-lane escalation `level` and `reason` |
| Codex Reviews lane | `review_gate.pending_reviews`, `review_gate.pending_repairs`, `cadence.last_review_clear_at`, `cadence.status` transitions out of `paused-for-review` |

A build lane MUST NOT directly write `active_task` or `next_candidate`; promotion
is coordinator-owned. The lane requests promotion by marking its current slice
"Ready for Codex Review" and waiting.

## Mapping to today's markdown polling

Until the runtime object exists, the markdown queue file remains the source of
truth and the runtime object derives from it:

| Runtime field | Derived from in `docs/live-build-N.md` |
|---|---|
| `lane_id` | filename (`live-build-1.md` → `build-1`) |
| `active_task` | `## Active Task` section (or `## Coordinator Override - Active Now` when present) |
| `next_candidate` | `## Next Candidate Task` section |
| `cadence.window_commits` | hashes in `Ready for Codex Review` block, after the most recent cadence clear |
| `review_gate` | `## Codex Review Cadence` block plus `## Ready for Codex Review` block |
| `last_read_at` | most recent `Read Checks` timestamp |
| `last_write_at` | most recent `Write/Completion Log` timestamp |
| `escalation` | `## Cross-Check Activity` block plus heuristic stale-task detection against Completed Slices |

Once the runtime object lands, the markdown file becomes a generated human
mirror — Prime writes the object, then re-renders the markdown for review.

## Out of scope for this contract

This contract intentionally does NOT specify:

- the storage format (JSON, SQLite, Bifrost-backed, etc.)
- the transport (filesystem watch, MCP tool, HTTP, etc.)
- the Bifrost cockpit surface that would render runway state
- the migration plan from markdown to runtime object
- the schema version negotiation between coordinator and lanes

Those belong to follow-up slices once the contract is reviewed.

## Open questions

1. Should `escalation` be a list rather than a single value, to allow a lane to
   be both `stale-active` and `boundary-cross` simultaneously?
2. Should `cadence.window_commits` count repair commits separately from task
   commits, or treat them as the same cadence unit?
3. Where does `pending_reviews` clear from — does the build lane delete entries
   on review-pass, or does the Codex Reviews lane own that mutation exclusively?
4. How is `worktree_path` reconciled when a session exits without cleanup? Is
   there a TTL on `last_read_at` after which `worktree_path` clears?

These questions are deferred to the next slice; the contract as written here
is sufficient to start scoping that work.
