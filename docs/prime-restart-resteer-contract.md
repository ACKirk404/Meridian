# Prime Restart/Resteer Contract

**Status:** V2 contract baseline; runtime not implemented.
**Owner:** Prime + Session Lifecycle Harness.
**Related:** `docs/prime-restart-resteer-logic.md`, `docs/workflow-subagent-harness-contract.md`, `docs/prime-autonomy-v2-contract.md`.
**Purpose:** Define the typed contract Prime uses to detect stalled, misrouted, quota-blocked, or contaminated work and decide whether to restart, resteer, pause, or escalate.

This contract exists because Meridian cannot depend on Scott noticing that a lane is idle, polling the wrong file, running under the wrong model, sharing a worktree, or trapped behind a launch popup. Prime must make those calls continuously and visibly.

## Prime Principle

Prime treats coordination health as live state, not as a memory of the last instruction.

Prime must know:

- what every lane is supposed to be doing
- which worktree that lane owns
- whether the lane is actually active
- whether the lane is using the correct queue
- whether the lane is blocked by review, proof, quota, launch failure, or local drift
- whether the correct next action is restart, resteer, pause, review, or escalation

## Restart vs. Resteer

**Restart** restores the operating frame.

Use restart when the lane's frame is broken: stale polling, wrong queue, missing worktree, bad launch, lost session, uncommitted drift, or a worker that forgot its role.

**Resteer** changes the next move.

Use resteer when the frame is valid but the current task is wrong: priority changed, review finding landed, proof failed, cadence gate opened, quota changed, or a stronger/weaker lane should own the next slice.

Prime may do both in order: restart the lane into a valid frame, then resteer it to the next correct task.

## Domain Objects

### `LaneOperatingFrame`

The state Prime expects a lane to maintain.

- `lane_id` - stable lane name, e.g. `build-1`, `codex-reviews-b`.
- `lane_role` - `BUILD`, `REVIEW`, `COORDINATOR`, `PROOF`, or `OBSERVER`.
- `assigned_queue_path` - repo-relative queue file the lane must poll.
- `worktree_path` - absolute path to the lane's unique worktree.
- `branch_name` - current branch if known.
- `allowed_paths` - tuple of repo-relative path prefixes this lane may edit.
- `active_task_id` - current task identifier, or empty when idle.
- `next_candidate_id` - queued next task identifier, or empty when none exists.
- `review_gate_id` - active review gate, if normal build work is paused.
- `cadence_counter` - task-changing commits since last review clearance.
- `last_read_at` - last time the lane read its queue.
- `last_write_at` - last time the lane wrote output or completion state.
- `last_commit` - last commit hash attributed to this lane.
- `model_family` - the active model family, e.g. Haiku, Opus, Codex.
- `quota_state` - `AVAILABLE`, `LIMITED`, `BLOCKED`, or `UNKNOWN`.

### `PrimeHealthFinding`

A typed detection that something may need Prime action.

- `finding_id`
- `lane_id`
- `kind`
- `severity`
- `summary`
- `evidence`
- `detected_at`
- `recommended_action`

`kind` values:

- `EMPTY_QUEUE`
- `STALE_ACTIVE_TASK`
- `POLLING_BUT_NOT_EXECUTING`
- `EXECUTING_BUT_NOT_COMMITTING`
- `WRONG_QUEUE`
- `REVIEW_LANE_READING_BUILD_QUEUE`
- `BUILD_LANE_READING_REVIEW_QUEUE`
- `SHARED_WORKTREE`
- `MAIN_WORKTREE_VIOLATION`
- `BRANCH_MOVEMENT_ATTEMPT`
- `UNCOMMITTED_DRIFT`
- `CROSS_LANE_CONTAMINATION`
- `QUOTA_BLOCKED`
- `MODEL_MISMATCH`
- `LAUNCH_POPUP`
- `ELECTRON_START_FAILURE`
- `PUSH_FAILURE`
- `PROOF_BLOCKED`
- `REVIEW_BACKLOG`
- `OBSIDIAN_DIVERGENCE`

### `RestartDirective`

Prime's instruction to restore a lane frame.

- `directive_id`
- `lane_id`
- `reason_finding_ids`
- `restart_kind`
- `target_queue_path`
- `target_worktree_path`
- `frame_message`
- `must_pull_before_work`
- `must_report_worktree`
- `allowed_paths`
- `created_at`

`restart_kind` values:

- `REANCHOR_QUEUE`
- `REQUIRE_UNIQUE_WORKTREE`
- `CLEAR_STALE_TASK`
- `REISSUE_ACTIVE_TASK`
- `RELAUNCH_APP`
- `REOPEN_SESSION`
- `PULL_AND_RECHECK`
- `COMMIT_OR_REPORT_DRIFT`

### `ResteerDirective`

Prime's instruction to change what a valid lane should do next.

- `directive_id`
- `lane_id`
- `reason_finding_ids`
- `new_task_id`
- `new_task_summary`
- `risk_tier`
- `required_review_gate`
- `required_proof`
- `allowed_paths`
- `completion_proof`
- `created_at`

`completion_proof` must name the expected proof: tests, docs-only verification, audit output, FileMap registration, or screenshot/render check.

### `EscalationGate`

The Review Console item Prime creates when restart/resteer is not safe.

- `gate_id`
- `lane_id`
- `reason`
- `evidence`
- `options`
- `default_recommendation`

Escalate instead of acting when the lane has unknown uncommitted work, a shared worktree risk, branch movement ambiguity, repeated push failure, repeated popup failure, or a tier-4 decision.

## Detection Rules

Prime runs these checks before assigning work and during every heartbeat.

| Check | Trigger | Action |
|---|---|---|
| Empty build queue | no active task and no next candidate | Resteer with a new next task; never leave build lane empty |
| Stale active task | active task references a committed slice | Restart by clearing stale task, then resteer |
| Wrong queue | lane polls a queue outside its role | Restart with `REANCHOR_QUEUE` |
| Review misroute | review lane reads build queue as executable source | Restart review lane to review queue |
| Shared worktree | two lanes report same `worktree_path` | Escalate unless Prime can assign a fresh worktree safely |
| Main worktree use | worker lane reports repo root as worktree | Block lane; require unique worktree |
| Cadence reached | lane has three task-changing commits since review | Resteer to review gate |
| Quota blocked | model/account limit message detected | Resteer to lower-cost lane, pause, or switch model family |
| Launch popup | app launch error or missing executable path popup | Restart app path; if repeated, escalate |
| Push failure | commit exists locally but not origin | Restart with pull/rebase/push check; escalate after repeated failure |
| Proof blocked | Aegis blocks the task | Resteer to proof repair before new work |
| Obsidian divergence | important slice lacks Obsidian note | Resteer to memory repair |

## Decision Order

Prime must resolve conditions in this order:

1. Safety: shared worktree, main worktree, branch movement, destructive operation risk.
2. Proof: Aegis blocking proof or required human gate.
3. Review: cadence gates and review findings.
4. Frame: wrong queue, stale task, missing worktree, launch error.
5. Throughput: empty queue, idle lane, review backlog, quota limitation.
6. Memory: Obsidian divergence, FileMap registration, tracker update.

Safety beats throughput. Proof beats new work. Review gates beat queue runway.

## Queue Runway Rule

Every build lane should have:

- one active executable task
- one next candidate task
- a clear review gate state
- a unique worktree requirement
- explicit allowed files
- expected proof

Read-check-only commits are liveness evidence, not work. They do not satisfy an empty queue.

## Quota and Model Limit Handling

When a lane reports a model limit:

1. Prime records `QUOTA_BLOCKED` with the reset time if present.
2. Prime stops assigning that model family.
3. Prime routes small deterministic/docs tasks to cheaper lanes if available.
4. Prime routes review/proof tasks to Codex where appropriate.
5. Prime creates a Review Console status item only if the block changes the plan Scott expects.

Prime must not keep reissuing the same instruction into a quota-blocked lane.

## Worktree Permission Rule

Every worker lane must operate in its own unique worktree.

Only Scott or Prime may direct branch movement. A worker may report that branch movement is needed, but it may not decide to move branches independently.

If Prime cannot verify the worktree, the lane receives no new write task.

## Bifrost Visibility

Bifrost should render restart/resteer state as Prime action, not raw logs:

- lane status
- current finding
- Prime directive
- countdown or stale age
- review/proof gate
- next candidate task
- escalation gate if human judgment is needed

The cockpit should make it obvious whether Prime is driving, waiting, or blocked.

## First Runtime Slice

Build a deterministic module, suggested `meridian_core/restart_resteer.py`, with:

- frozen dataclasses for `LaneOperatingFrame`, `PrimeHealthFinding`, `RestartDirective`, `ResteerDirective`, and `EscalationGate`
- enum coverage for finding kinds and directive kinds
- `evaluate_lane_frame(frame) -> tuple[PrimeHealthFinding, ...]`
- `choose_recovery_action(frame, findings) -> RestartDirective | ResteerDirective | EscalationGate`

First tests:

- empty queue produces a resteer directive
- shared worktree produces escalation
- wrong queue produces restart
- cadence counter at three produces review gate resteer
- quota blocked does not reissue same model-family work
- proof blocked beats new work
- safety findings outrank throughput findings

No model calls, no live process control, no destructive operations in the first runtime slice.
