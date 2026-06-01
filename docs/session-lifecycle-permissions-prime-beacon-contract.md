# Session Lifecycle Permissions and Prime/Beacon Binding Contract

## Purpose

This contract defines how Session Lifecycle state integrates with branch/worktree permissions, Beacon heartbeat observations, Prime autonomy directives, and restart/resteer findings without adding live process control into the harness itself.

## Owner

- Session Lifecycle Harness
- Supervising intelligence: Prime, Beacon, Aegis
- Permission gate: Branch/worktree operations require explicit named approval
- Proof requirement: All bindings must be auditable via typed state

## PermissionContext

`PermissionContext` is embedded in `SessionLifecycleState` to capture approval scope and escalation state:

Required fields:

- `approved_by`: Who approved the current branch/worktree operation (Scott, Prime, Orchestrator, or Aegis)
- `approval_scope`: What operations are approved (branch_move, worktree_create, archive, restart, resteer, recover_from_limit)
- `escalation_gate`: Whether Aegis review is required for high-risk operations (bool)
- `escalation_reason`: Human-readable reason Aegis approval is pending (str, nullable)
- `branch_permission_state`: current branch lock (locked_by_default, unlocked_temporary, unlocked_permanent)
- `last_permission_change`: when permission state was last updated (datetime)

## Beacon Integration Points

Beacon observes session staleness and heartbeat health without executing commands:

- `Session.last_queue_read_at`: Beacon records each queue read timestamp
- `Session.last_queue_write_at`: Beacon records each task completion timestamp
- `Session.last_prompt_sent_at`: Beacon tracks when the session last sent a prompt (Prime/worker activity)
- `Session.health_state`: Beacon updates this to stale/degraded/healthy based on heartbeat age
- `Session.blocker_summary`: Beacon fills this when queues or approvals are blocking progress

**Constraint:** Beacon does NOT execute restart/resteer/recover commands. It only sets health_state and blocker_summary as evidence for Prime or human review.

## Restart / Resteer Findings

When a session is stale or blocked, Beacon generates a restart/resteer finding:

- **Restart finding**: Session is idle and its queue has not changed (heartbeat > threshold). Recommend restart with same worktree and permissions.
- **Resteer finding**: Session is blocked on an approval or external queue event. Recommend resteer to a different task or queue.

**Proof requirement:**

- Findings must include evidence: the stale heartbeat age, the last queue read timestamp, the blocker summary.
- Findings are advisory only. Prime or human approval is required to execute.
- Findings must reference the session identity and current state snapshot.

## Prime Autonomy Recommendations

Prime selects next actions by consulting session state and making high-level recommendations:

- Prime reads `SessionLifecycleState` to understand each session's current task, health, and queue position.
- Prime generates `SessionCommandPlan` objects proposing spawn, watch, poll_queue, steer, stop_request, transfer, archive, restart, resteer, recover_from_limit, or request_human_gate.
- Prime includes evidence refs, expected state transitions, and Aegis/cadence gate requirements in the plan.
- Prime does NOT execute commands directly. Plans must be staged, approved, and executed by the coordinator or Aegis gate.

**Command-Prime bindings:**

- `spawn`: Prime recommends spawn; Aegis approves; Session Lifecycle creates new state + worktree.
- `watch`: Prime recommends watching a session; no special permission needed; Session Lifecycle records watch directive.
- `poll_queue`: Prime recommends queue check frequency; Session Lifecycle increments `last_queue_read_at`.
- `steer`: Prime recommends task reassignment or queue change; requires human or Aegis approval; Session Lifecycle updates `current_task_id`.
- `stop_request`: Prime recommends stopping; Aegis approves; Session Lifecycle sets status to stopped.
- `transfer`: Prime recommends session hand-off to another lane/model; requires human approval; Session Lifecycle updates session ownership.
- `archive`: Prime recommends archival after completion; requires human approval; Session Lifecycle finalizes state.
- `restart`: Prime recommends restarting after stale detection; uses existing worktree if recovery fails; Session Lifecycle re-stamps heartbeat.
- `resteer`: Prime recommends redirect to different queue; uses existing worktree; Session Lifecycle updates queue assignment.
- `recover_from_limit`: Prime recommends recovery from capacity limit; Session Lifecycle resumes polling after limit window closes.
- `request_human_gate`: Prime escalates to human; Aegis or Scott must approve before execution proceeds.

## Branch Permission Bindings

Session Lifecycle branches are owned by the session and protected by permission gates:

- **Default state**: All branches are locked by default. Branch movement requires explicit named approval.
- **Temporary unlock**: Prime or human requests unlock for a specific task (e.g., merge to stage). Unlock is timestamp-bound and task-scoped.
- **Permanent unlock**: Only used for sandbox/test sessions; requires Aegis and Scott approval together.

**Worktree isolation invariant:**

- Every worker session must run in a unique worktree.
- Every review session must run in a unique worktree.
- Session Lifecycle records worktree_path and maintains the isolation constraint.
- Branch movement must not cross worktree boundaries without explicit transfer command.

**Permission checking:**

- Before any branch operation, Session Lifecycle checks `PermissionContext.approved_by` and `approval_scope`.
- If approval is missing or expired, Session Lifecycle sets status to blocked and escalates to Aegis.
- Aegis or human must issue a new approval before the operation proceeds.

## Proof and Safety

Every Prime/Beacon/Permission binding must be auditable:

- **Session state**: `SessionLifecycleState` snapshot shows all current bindings and heartbeat values.
- **Command plan**: `SessionCommandPlan` shows intended action, reason, evidence refs, and expected transition.
- **Permission context**: `PermissionContext` shows who approved what and when.
- **Beacon findings**: Heartbeat/staleness/blocker observations are recorded with timestamps and evidence.
- **Prime recommendations**: Prime's selection logic is logged separately (not in Session Lifecycle state).

All bindings are **serializable** and **deterministic**. No hidden account automation or side-channel execution.

## Out of Scope for This Contract

- Live Polaris or Electron automation (handled by runtime integration slice later).
- Destructive branch reset or forced push (reserved for human or Aegis + Scott approval only).
- Automatic branch switching without explicit SessionCommandPlan.
- Vendor account automation (reserved for service-layer integration).
- Live process restart or signal-based recovery (out of scope until V3 harness maturity).

This contract defines the typed interface. Runtime bindings (Beacon heartbeat loop, Prime autonomy selection, Aegis approval gate) are implemented in later slices.
