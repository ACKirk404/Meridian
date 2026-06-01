# Session Lifecycle Permissions Implementation Checklist

## Purpose

This checklist converts `docs/session-lifecycle-permissions-prime-beacon-contract.md` into a code-ready specification for the eventual runtime implementation of Session Lifecycle permissions binding, Beacon heartbeat integration, and Prime autonomy recommendation inputs.

Do not implement until this checklist is reviewed and approved.

## Domain Objects

### PermissionContext (Frozen Dataclass)

Required fields:

- `approved_by: str` — who approved the operation (Scott, Prime, Orchestrator, Aegis)
- `approval_scope: set[str]` — approved operation types (branch_move, worktree_create, archive, restart, resteer, recover_from_limit)
- `escalation_gate: bool` — whether Aegis review is pending
- `escalation_reason: Optional[str]` — why Aegis approval is required
- `branch_permission_state: str` — current state (locked_by_default, unlocked_temporary, unlocked_permanent)
- `last_permission_change: datetime` — when permission state last changed

### SessionLifecycleState Extension

Embed `PermissionContext` in `SessionLifecycleState`:

- `permission_context: PermissionContext` — current permission/approval state

Update existing fields:

- `status` enum: add `blocked` state for when approval is pending
- `blocker_summary: Optional[str]` — what is blocking progress (approval, queue change, external event)
- `last_queue_read_at: datetime` — Beacon uses this for heartbeat staleness
- `last_queue_write_at: datetime` — Beacon uses this for activity staleness
- `last_prompt_sent_at: datetime` — Beacon uses this for session staleness

### RestartResteerFinding (Frozen Dataclass)

Advisory structure for stale/blocked sessions:

- `session_id: str` — which session
- `finding_type: str` — restart or resteer
- `reason: str` — why this finding
- `evidence: dict` — heartbeat ages, last read timestamp, blocker summary
- `recommended_action: str` — what Prime/human should do
- `timestamp: datetime` — when finding was generated

### PrimeAutonomyInput (Frozen Dataclass)

What Prime receives when selecting next action:

- `current_sessions: list[SessionLifecycleState]` — all active sessions with heartbeat/blocker state
- `queues_by_harness: dict[str, list[str]]` — queue assignment map
- `approval_backlog: list[PendingApprovalRequest]` — what's waiting for Aegis/human gate
- `restart_resteer_findings: list[RestartResteerFinding]` — stale/blocked session recommendations
- `recent_completions: list[str]` — recently completed task hashes
- `timestamp: datetime` — when this input was gathered

## Enum Types

### PermissionState (Enum)

Values:

- `locked_by_default` — branch movement requires explicit approval
- `unlocked_temporary` — temporary unlock for specific task (timestamp-bounded)
- `unlocked_permanent` — permanent unlock (Aegis + Scott approval only)

### OperationScope (Enum)

Values:

- `branch_move` — branch checkout/merge operations
- `worktree_create` — new worktree creation
- `archive` — session archival
- `restart` — session restart after staleness
- `resteer` — session task reassignment
- `recover_from_limit` — capacity limit recovery

### FindingType (Enum)

Values:

- `restart` — session is idle and should be restarted
- `resteer` — session is blocked and should be redirected

## Helper Methods

### SessionLifecycleState Methods

- `is_permission_locked() -> bool` — check if branch is currently locked
- `requires_approval_for_operation(operation: str) -> bool` — check if operation needs approval
- `can_accept_work(with_approval: bool) -> bool` — update logic to check permission state
- `heartbeat_stale(threshold_seconds: int) -> bool` — check if last_prompt_sent_at exceeds threshold
- `health_from_heartbeat() -> str` — map heartbeat to health_state (stale/degraded/healthy)
- `to_permission_context() -> PermissionContext` — serialize permission state
- `approve_operation(by: str, scope: list[str]) -> SessionLifecycleState` — return new state with updated permissions

### Beacon Helper Methods

- `generate_restart_finding(session: SessionLifecycleState, threshold: int) -> Optional[RestartResteerFinding]` — create restart recommendation if stale
- `generate_resteer_finding(session: SessionLifecycleState, blocker: str) -> Optional[RestartResteerFinding]` — create redirect recommendation if blocked
- `gather_prime_autonomy_input(sessions: list[SessionLifecycleState], ...) -> PrimeAutonomyInput` — collect all inputs Prime needs

## Tests to Write (Not Implemented Yet)

Unit tests for PermissionContext:

- [ ] immutability: PermissionContext is frozen
- [ ] locked_by_default: new contexts are locked
- [ ] unlock_temporary: permission can be set to unlocked_temporary with timestamp
- [ ] unlock_expire: temporary unlock expires after duration
- [ ] unlock_permanent: only Aegis + Scott together can set permanent
- [ ] approval_scope: approve_operation only sets approved scopes
- [ ] escalation_gate: setting escalation_gate requires reason

Unit tests for heartbeat staleness:

- [ ] fresh_heartbeat: recent last_prompt_sent_at is not stale
- [ ] stale_heartbeat: old last_prompt_sent_at is stale
- [ ] health_mapping: stale heartbeat maps to degraded/stale health_state
- [ ] blocker_propagation: blocked status updates blocker_summary

Unit tests for restart/resteer findings:

- [ ] restart_finding: generate_restart_finding returns finding when stale
- [ ] resteer_finding: generate_resteer_finding returns finding when blocked
- [ ] finding_evidence: findings include heartbeat ages and timestamp

Unit tests for Prime autonomy input:

- [ ] gather_input: gather_prime_autonomy_input collects all sessions/queues/approvals
- [ ] input_completeness: returned input has all required fields populated

Integration tests:

- [ ] session_with_locked_branch: can_accept_work returns False when locked
- [ ] session_with_temporary_unlock: can_accept_work returns True while unlock is active
- [ ] session_with_expired_unlock: can_accept_work returns False after unlock expires
- [ ] approval_for_branch_move: requires_approval_for_operation returns True for branch_move
- [ ] heartbeat_to_health: full workflow from stale heartbeat to degraded health to finding generation

## Legality Matrix

Extend existing `SessionLifecycleState.verify_state_transition_legal()` to check:

Valid permission-state transitions:

- `locked_by_default` → `unlocked_temporary` (via approve_operation with time bound)
- `unlocked_temporary` → `locked_by_default` (via unlock expiry)
- `locked_by_default` → `unlocked_permanent` (Aegis + Scott only)
- `unlocked_permanent` → `locked_by_default` (Aegis + Scott only)

Invalid transitions (must be blocked):

- `unlocked_temporary` → `unlocked_permanent` (cannot escalate from temporary to permanent without re-approving)
- `unlocked_permanent` → `unlocked_temporary` (cannot downgrade permanent to temporary)

## Proof Requirements

Every permission change must be auditable:

- `PermissionContext.approved_by` must match permission request originator
- `PermissionContext.last_permission_change` must match commit timestamp
- `SessionLifecycleState` snapshot must show all current permissions
- `RestartResteerFinding` must include evidence snapshot (heartbeat ages, blocker text)
- `PrimeAutonomyInput` must be timestamped and deterministic

## Invariants

- Every session must start with `permission_state = locked_by_default`
- Temporary unlock must have explicit expiry time (cannot be open-ended)
- Permanent unlock requires Aegis approval AND Scott approval (two independent signers)
- Branch movement without required approval must result in blocked status, not silent failure
- Beacon findings are advisory only; Prime cannot execute without separate command plan
- Permission state is immutable; updates return new SessionLifecycleState

## Out of Scope for This Checklist

- Live Beacon heartbeat loop implementation (later harness slice)
- Prime autonomy selection logic (later harness slice)
- Aegis approval gate execution (later infrastructure)
- Actual branch/worktree operations (delegated to git/filesystem)
- Account/session persistence (delegated to Prime Autonomy harness)

This checklist defines the typed interface and invariants. Runtime bindings and workflow orchestration are implemented in later slices.

---

**Review Checklist Before Implementation:**

- [ ] PermissionContext fields match contract definition
- [ ] SessionLifecycleState embeds PermissionContext correctly
- [ ] Enum types cover all documented values
- [ ] Helper methods implement documented logic
- [ ] Test cases match helper method semantics
- [ ] Legality matrix covers all valid/invalid transitions
- [ ] Proof requirements are testable via state snapshots
- [ ] Invariants are enforceable in __post_init__ / frozen class
- [ ] Out-of-scope items are clearly marked
- [ ] No runtime implementation, file I/O, or live process control
