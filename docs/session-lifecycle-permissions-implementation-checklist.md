# Session Lifecycle Permissions Implementation Checklist

## Purpose

This checklist converts `docs/session-lifecycle-permissions-prime-beacon-contract.md` into a code-ready specification for the eventual runtime implementation of Session Lifecycle permissions binding, Beacon heartbeat integration, and Prime autonomy recommendation inputs.

Do not implement until this checklist is reviewed and approved.

## Domain Objects

### PermissionContext (Frozen Dataclass)

Required fields:

- `approved_by: str` — who approved the operation (Scott, Prime, Orchestrator, Aegis)
- `approved_by_secondary: Optional[str]` — secondary approver for permanent unlock (must be different from approved_by)
- `approval_scope: frozenset[OperationScope]` — approved operation types (deeply immutable enum set)
- `escalation_gate: bool` — whether Aegis review is pending
- `escalation_reason: Optional[str]` — why Aegis approval is required
- `branch_permission_state: PermissionState` — current state (locked_by_default, unlocked_temporary, unlocked_permanent)
- `unlock_expiry: Optional[datetime]` — when temporary unlock expires (None for permanent/locked)
- `task_scope: Optional[str]` — which task this unlock is scoped to (None if all tasks)
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
- `finding_type: FindingType` — restart or resteer (enum)
- `reason: str` — why this finding
- `evidence_stale_seconds: int` — how many seconds since last_prompt_sent_at
- `evidence_last_queue_read_at: datetime` — when this session last read its queue
- `evidence_blocker_summary: Optional[str]` — what is blocking this session
- `recommended_action: str` — what Prime/human should do
- `timestamp: datetime` — when finding was generated

### PrimeAutonomyInput (Frozen Dataclass)

What Prime receives when selecting next action:

- `current_sessions: list[SessionLifecycleState]` — all active sessions with heartbeat/blocker state
- `queues_by_harness: dict[str, list[str]]` — queue assignment map
- `approvals_pending: list[tuple[str, str]]` — (session_id, escalation_reason) for sessions blocked on approval
- `restart_resteer_findings: list[RestartResteerFinding]` — stale/blocked session recommendations
- `recent_completions: list[str]` — recently completed task hashes
- `timestamp: datetime` — when this input was gathered

### SessionCommandPlan (Deferred)

**Deferred to Session Lifecycle runtime permissions binding slice.** The contract references `SessionCommandPlan` as Prime's typed action proposals with evidence, state transitions, and gates. This checklist focuses on permission state and Beacon findings. `SessionCommandPlan` will be defined in the runtime implementation checklist alongside Prime binding logic.

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

- `is_permission_locked() -> bool` — check if branch is currently locked (state == PermissionState.locked_by_default)
- `requires_approval_for_operation(operation: OperationScope) -> bool` — check if this operation is in approval_scope
- `can_accept_work() -> bool` — return True only if status is not blocked AND is_permission_locked() is False AND unlock_expiry (if temporary) has not passed
- `heartbeat_stale(threshold_seconds: int) -> bool` — return (now - last_prompt_sent_at).total_seconds() > threshold_seconds
- `health_from_heartbeat(stale_threshold: int, degraded_threshold: int) -> HealthState` — map heartbeat age to STALE/DEGRADED/HEALTHY
- `to_permission_context() -> PermissionContext` — serialize permission state
- `approve_operation(by: str, by_secondary: Optional[str], scope: frozenset[OperationScope], state: PermissionState, expiry: Optional[datetime] = None, task: Optional[str] = None) -> SessionLifecycleState` — return new state with updated permissions; enforce invariants (permanent unlock requires both by and by_secondary; temporary requires expiry)

### Beacon Helper Methods

- `generate_restart_finding(session: SessionLifecycleState, threshold: int) -> Optional[RestartResteerFinding]` — create restart recommendation if stale
- `generate_resteer_finding(session: SessionLifecycleState, blocker: str) -> Optional[RestartResteerFinding]` — create redirect recommendation if blocked
- `gather_prime_autonomy_input(sessions: list[SessionLifecycleState], ...) -> PrimeAutonomyInput` — collect all inputs Prime needs

## Tests to Write (Not Implemented Yet)

**Total test count: 25 tests** (10 PermissionContext + 4 heartbeat + 4 restart/resteer + 2 Prime input + 5 integration)

Unit tests for PermissionContext (10 tests):

- [ ] immutability_frozen: PermissionContext is frozen; cannot modify fields
- [ ] immutability_scope: approval_scope is frozenset; cannot mutate contents
- [ ] locked_by_default: new contexts have permission_state = locked_by_default
- [ ] unlock_temporary: permission can be set to unlocked_temporary with expiry/task
- [ ] unlock_expiry_enforcement: temporary unlock with past expiry_timestamp cannot be used
- [ ] unlock_permanent: requires both approved_by and approved_by_secondary (dual signer)
- [ ] unlock_permanent_single_approval_fails: setting permanent with only one approver raises error
- [ ] approval_scope_enum: approval_scope accepts only OperationScope enum values
- [ ] approval_scope_filtering: can_accept_work respects approval_scope membership
- [ ] escalation_gate_reason: setting escalation_gate=True requires non-None escalation_reason

Unit tests for heartbeat staleness (4 tests):

- [ ] fresh_heartbeat: recent last_prompt_sent_at returns False from heartbeat_stale()
- [ ] stale_heartbeat: old last_prompt_sent_at returns True from heartbeat_stale()
- [ ] health_mapping_stale: heartbeat age > stale_threshold maps to HealthState.STALE
- [ ] health_mapping_degraded: heartbeat age > degraded_threshold (but < stale) maps to HealthState.DEGRADED

Unit tests for restart/resteer findings (4 tests):

- [ ] restart_finding: generate_restart_finding returns finding with FindingType.RESTART when stale
- [ ] resteer_finding: generate_resteer_finding returns finding with FindingType.RESTEER when blocked
- [ ] finding_evidence_complete: findings include evidence_stale_seconds, evidence_last_queue_read_at, and evidence_blocker_summary
- [ ] finding_timestamp: findings have deterministic timestamp matching input time

Unit tests for Prime autonomy input (2 tests):

- [ ] gather_input: gather_prime_autonomy_input collects all sessions/queues/pending approvals/findings
- [ ] input_completeness: returned input has all required fields populated and is immutable

Integration tests (5 tests):

- [ ] session_locked_cannot_work: can_accept_work returns False when branch_permission_state == locked
- [ ] session_temporary_unlock_works: can_accept_work returns True with unexpired temporary unlock
- [ ] session_expired_unlock_blocked: can_accept_work returns False when unlock_expiry has passed
- [ ] task_scope_enforcement: can_accept_work respects task_scope if set
- [ ] full_workflow: locked → temporary_unlock → work_accepted → unlock_expires → locked_again

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
