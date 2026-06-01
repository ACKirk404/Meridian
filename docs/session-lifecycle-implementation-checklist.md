# Session Lifecycle Implementation Checklist

**Status:** Code-Ready Specification  
**Based on:** docs/session-lifecycle-v2-contract.md  
**Purpose:** Bounded specification for runtime Session Lifecycle domain objects before implementation begins.

---

## Part 1: Enums

### SessionStatus (10 values)

```python
class SessionStatus(Enum):
    STARTING = "starting"      # Initial state when session is booting
    POLLING = "polling"        # Idle, waiting for work in assigned queue
    RUNNING = "running"        # Actively executing task
    WAITING = "waiting"        # Blocked on external dependency (review, capacity, etc.)
    BLOCKED = "blocked"        # Temporarily blocked, can resume
    REVIEW_GATED = "review_gated"       # Awaiting review cadence approval
    CAPACITY_LIMITED = "capacity_limited" # Hit capacity limit, awaiting recovery
    STALE = "stale"            # Heartbeat lost, may require restart
    STOPPED = "stopped"        # Gracefully stopped, not archived
    ARCHIVED = "archived"      # Terminal state, session complete
```

### HarnessRole (6 values)

```python
class HarnessRole(Enum):
    BUILD = "build"             # Worker building/coding
    REVIEW = "review"          # Worker reviewing code
    UI = "ui"                  # UI automation worker
    ARCHITECTURE = "architecture"  # Architecture design worker
    COORDINATOR = "coordinator"    # Coordinator managing queue/tasks
    SPECIALIST = "specialist"      # Special-purpose worker
```

### CommandIntent (11 values)

```python
class CommandIntent(Enum):
    SPAWN = "spawn"                # Boot a new session
    WATCH = "watch"               # Monitor session without steering
    POLL_QUEUE = "poll_queue"      # Read assigned queue, check for work
    STEER = "steer"               # Direct task execution in running session
    STOP_REQUEST = "stop_request"   # Request graceful stop
    TRANSFER = "transfer"         # Hand off session to another worker
    ARCHIVE = "archive"           # Terminal archive action
    RESTART = "restart"           # Restart stale/stopped session
    RESTEER = "resteer"           # Modify steering mid-execution
    RECOVER_FROM_LIMIT = "recover_from_limit"  # Recover from capacity limit
    REQUEST_HUMAN_GATE = "request_human_gate"  # Request human approval
```

### ReviewCadenceState (5 values)

```python
class ReviewCadenceState(Enum):
    NONE = "none"               # No review cadence active
    PENDING = "pending"         # Review cadence pending approval
    REVIEW_GATED = "review_gated"  # Session gated on review approval
    CLEARED = "cleared"         # Review cadence approved
    FAILED = "failed"           # Review cadence rejection
```

### ProofState (7 values)

```python
class ProofState(Enum):
    NO_PROOF = "no_proof"                    # No evidence collected
    QUEUE_READ = "queue_read"               # Queue evidence gathered
    WORKTREE_VERIFIED = "worktree_verified"    # Worktree state verified
    PERMISSION_VALIDATED = "permission_validated" # Permissions validated
    COMMAND_STAGED = "command_staged"       # Command ready for execution
    EXECUTED = "executed"                   # Command executed
    ROLLBACK_READY = "rollback_ready"       # Rollback capability verified
```

### HealthState (4 values)

```python
class HealthState(Enum):
    HEALTHY = "healthy"        # Session operating normally
    DEGRADED = "degraded"      # Session degraded but operational
    STALE = "stale"           # Heartbeat lost
    FAILED = "failed"         # Session failed
```

---

## Part 2: SessionLifecycleState Dataclass

### Definition

Frozen (immutable) dataclass representing the authoritative snapshot of a session.

### Fields

#### Identity (2 fields)
- `session_id: str` — Unique session identifier
- `session_name: str` — Human-readable session name (e.g., "Build 2")

#### Context (2 fields)
- `project_name: str` — Project name (e.g., "Meridian")
- `project_path: Optional[str]` — Absolute path to project root

#### Role and Queue (2 fields)
- `harness_role: HarnessRole` — Role of this session (BUILD, REVIEW, UI, ARCHITECTURE, COORDINATOR, SPECIALIST)
- `assigned_queue_file: str` — Path to assigned queue document (e.g., "docs/live-build-2.md")

#### Model Configuration (2 fields)
- `model_provider: str` — Provider name (e.g., "anthropic")
- `model_name: str` — Model identifier (e.g., "claude-opus-4-7")

#### Execution State (3 fields)
- `status: SessionStatus` — Current session status
- `worktree_path: str` — Absolute path to unique worktree for this session
- `branch_name: str` — Current branch name in worktree

#### Task Context (1 field)
- `current_task_id: Optional[str]` — Currently executing task ID or heading

#### Heartbeat and Metrics (4 fields)
- `last_queue_read_at: datetime` — UTC timestamp of last queue read
- `last_queue_write_at: datetime` — UTC timestamp of last queue write
- `last_prompt_sent_at: datetime` — UTC timestamp of last prompt sent
- `last_prompt_payload_size: int` — Size of last prompt in tokens/bytes

#### Review and Proof (2 fields)
- `review_cadence_state: ReviewCadenceState` — Cadence approval state
- `proof_state: ProofState` — Evidence collection state

#### Health (2 fields)
- `health_state: HealthState` — Overall session health
- `blocker_summary: Optional[str]` — Human-readable description of any blocker

#### Permissions (1 field)
- `permission_context: dict[str, Any]` — Permission metadata (e.g., {"user": "scott"})

### Helper Methods

#### `is_idle() -> bool`
Returns `True` if session is waiting for work.
- **Logic:** `status in (POLLING, WAITING, REVIEW_GATED)`
- **Use Case:** Determine if session can accept new work from queue.

#### `is_healthy() -> bool`
Returns `True` if session is in good operational health.
- **Logic:** `health_state == HEALTHY and blocker_summary is None`
- **Use Case:** Safety check before sending work to session.

#### `can_accept_work() -> bool`
Returns `True` if session is eligible to transition to RUNNING.
- **Logic:** 
  ```
  status not in (BLOCKED, STALE, ARCHIVED, CAPACITY_LIMITED)
  AND is_healthy()
  ```
- **Use Case:** Pre-flight check before queue dispatch.

#### `heartbeat_stale(threshold_minutes: int = 30) -> bool`
Returns `True` if `last_queue_read_at` exceeds threshold.
- **Logic:** 
  ```
  elapsed = now(UTC) - last_queue_read_at
  elapsed.total_seconds() > (threshold_minutes * 60)
  ```
- **Use Case:** Detect stale sessions for health monitoring.

#### `to_dict() -> dict[str, Any]`
Serializes state to JSON-safe dict for Bifrost display.
- **Fields:** All fields converted, enums to `.value`, datetimes to ISO format
- **Use Case:** Wire format for UI rendering and logging.

---

## Part 3: SessionCommandPlan Dataclass

### Definition

Frozen (immutable) dataclass representing Prime's proposed action for a session.

### Fields

#### Target (2 fields)
- `session_id: str` — Session being commanded
- `session_name: str` — Human-readable session name

#### Intent and Reason (2 fields)
- `command_intent: CommandIntent` — Type of command (SPAWN, WATCH, POLL_QUEUE, etc.)
- `reason: str` — Human-readable reason for this command

#### Expected Outcome (1 field)
- `expected_state_transition: tuple[SessionStatus, SessionStatus]` — (from_state, to_state)

#### Evidence References (5 fields)
- `current_state_evidence: str` — Reference to current SessionLifecycleState snapshot
- `queue_file_evidence: str` — Reference to queue file and read timestamp
- `worktree_evidence: str` — Reference to worktree verification result
- `review_gate_evidence: Optional[str]` — Reference to review/cadence evidence if applicable
- `proof_requirement: ProofState` — Required proof level before execution

#### Affected Resources (3 fields)
- `queue_file_affected: str` — Queue file this command may modify
- `worktree_path_affected: str` — Worktree path for this session
- `branch_affected: str` — Branch name in worktree

#### Safety Gates (3 fields)
- `aegis_gate_result: Optional[str]` — Aegis approval result (for high-risk commands)
- `cadence_gate_required: bool` — Whether cadence gate applies
- `cadence_gate_status: ReviewCadenceState` — Current cadence gate state

#### Executability (3 fields)
- `is_executable_now: bool` — Whether all preconditions are met for execution
- `human_approval_required: bool` — Whether human approval is mandatory
- `approval_context: Optional[str]` — Context for human approval decision

#### Recovery (1 field)
- `rollback_or_recovery_note: Optional[str]` — Rollback instructions if needed

### Helper Methods

#### `is_executable() -> bool`
Returns `True` if command can execute immediately.
- **Logic:**
  ```
  is_executable_now AND
  NOT human_approval_required AND
  proof_requirement != ProofState.NO_PROOF
  ```
- **Use Case:** Gate command execution to safe, approved plans only.

#### `requires_aegis_approval() -> bool`
Returns `True` if command needs Aegis security gate.
- **High-Risk Intents:** TRANSFER, ARCHIVE, RESTART, RECOVER_FROM_LIMIT
- **Logic:** `command_intent in high_risk_intents`
- **Use Case:** Route high-risk commands through Aegis approval gate.

#### `is_legal(current_state: SessionLifecycleState) -> bool`
Returns `True` if command is legal given current session state.
- **Logic:** Check against legality matrix (see Part 4).
- **Use Case:** Prevent illegal state transitions.

#### `verify_state_transition_legal() -> bool`
Returns `True` if `expected_state_transition` matches contract rules.
- **Logic:** Validate tuple against legal transitions matrix (see Part 4).
- **Use Case:** Validate command plan before staging.

#### `to_dict() -> dict[str, Any]`
Serializes plan to JSON-safe dict for Bifrost preview.
- **Fields:** All fields converted, enums to `.value`, tuples to arrays
- **Use Case:** Wire format for UI preview and logging.

---

## Part 4: Legality Matrix

### Legal State Transitions

A command's expected state transition must be one of these tuples:

```
(STARTING, POLLING)
(POLLING, POLLING)
(POLLING, RUNNING)
(RUNNING, WAITING)
(RUNNING, BLOCKED)
(WAITING, RUNNING)
(WAITING, BLOCKED)
(BLOCKED, WAITING)
(BLOCKED, POLLING)
(REVIEW_GATED, RUNNING)
(REVIEW_GATED, BLOCKED)
(CAPACITY_LIMITED, RUNNING)
(CAPACITY_LIMITED, WAITING)
(STALE, RUNNING)
(STALE, ARCHIVED)
(STOPPED, ARCHIVED)
(ARCHIVED, ARCHIVED)
```

### Legal Command-State Pairs

For each `CommandIntent`, allowed current states:

| Intent | Allowed Current States |
|--------|------------------------|
| `SPAWN` | {STARTING} |
| `WATCH` | {RUNNING, POLLING} |
| `POLL_QUEUE` | {STARTING, POLLING, RUNNING, WAITING, BLOCKED, REVIEW_GATED, CAPACITY_LIMITED, STALE, STOPPED} |
| `STEER` | {RUNNING} |
| `STOP_REQUEST` | {STARTING, POLLING, RUNNING, WAITING, BLOCKED, REVIEW_GATED, CAPACITY_LIMITED, STALE} |
| `TRANSFER` | {RUNNING, WAITING} |
| `ARCHIVE` | {STOPPED, ARCHIVED} |
| `RESTART` | {STOPPED, STALE} |
| `RESTEER` | {RUNNING} |
| `RECOVER_FROM_LIMIT` | {CAPACITY_LIMITED} |
| `REQUEST_HUMAN_GATE` | {all SessionStatus values} |

---

## Part 5: Proof Expectations

### Proof State Progression

Commands progress through proof states:

1. **NO_PROOF** → No evidence collected yet
2. **QUEUE_READ** → Queue file read and evidence recorded
3. **WORKTREE_VERIFIED** → Worktree state confirmed valid
4. **PERMISSION_VALIDATED** → User permissions verified
5. **COMMAND_STAGED** → Command plan typed and ready
6. **EXECUTED** → Command executed successfully
7. **ROLLBACK_READY** → Rollback capability verified post-execution

### Proof Requirements by Intent

| Intent | Min Proof Level | Notes |
|--------|-----------------|-------|
| POLL_QUEUE | QUEUE_READ | Must have fresh queue evidence |
| WATCH | QUEUE_READ | Must monitor fresh queue state |
| STEER | COMMAND_STAGED | Full command plan required |
| TRANSFER | COMMAND_STAGED + Aegis | High-risk; requires approval |
| ARCHIVE | COMMAND_STAGED + Aegis | High-risk; requires approval |
| RESTART | COMMAND_STAGED + Aegis | High-risk; requires approval |
| RECOVER_FROM_LIMIT | COMMAND_STAGED + Aegis | High-risk; requires approval |

---

## Part 6: Invariants and Constraints

### Worktree Isolation
- **Rule:** Every worker and review session must run in its own unique worktree.
- **Enforcement:** `worktree_path` must be unique per session across the system.
- **Validation:** Before SPAWN, verify no other session uses the same `worktree_path`.

### Queue Routing
- **Rule:** Build sessions read only their assigned build queue; review sessions read only their assigned review queue.
- **Enforcement:** `harness_role` and `assigned_queue_file` must match.
- **Validation:** Before POLL_QUEUE, verify queue matches role.

### Branch Movement
- **Rule:** Branch movement requires Scott or Prime permission.
- **Enforcement:** TRANSFER and RESTEER commands require Aegis approval.
- **Validation:** All branch-affecting commands must carry proof of approval.

### Proof Requirement
- **Rule:** No hidden automation or branch switching without explicit command-plan proof.
- **Enforcement:** All commands must carry evidence references and proof state.
- **Validation:** is_executable() refuses commands below proof threshold.

---

## Part 7: Test Cases (~60 tests)

### TestSessionLifecycleState (12-15 tests)

#### Immutability Tests
- [ ] `test_immutability_frozen` — Verify dataclass is frozen
- [ ] `test_cannot_modify_status` — Attempt to modify status raises error
- [ ] `test_cannot_modify_health_state` — Attempt to modify health raises error

#### is_idle() Tests
- [ ] `test_is_idle_polling` — POLLING → True
- [ ] `test_is_idle_waiting` — WAITING → True
- [ ] `test_is_idle_review_gated` — REVIEW_GATED → True
- [ ] `test_is_not_idle_running` — RUNNING → False
- [ ] `test_is_not_idle_blocked` — BLOCKED → False
- [ ] `test_is_not_idle_archived` — ARCHIVED → False

#### is_healthy() Tests
- [ ] `test_is_healthy_true` — HEALTHY state, no blocker → True
- [ ] `test_is_not_healthy_degraded` — DEGRADED state → False
- [ ] `test_is_not_healthy_with_blocker` — HEALTHY but blocker exists → False
- [ ] `test_is_not_healthy_stale` — STALE health state → False

#### can_accept_work() Tests
- [ ] `test_can_accept_work_polling` — POLLING, healthy → True
- [ ] `test_cannot_accept_work_blocked` — BLOCKED → False
- [ ] `test_cannot_accept_work_stale` — STALE → False
- [ ] `test_cannot_accept_work_archived` — ARCHIVED → False
- [ ] `test_cannot_accept_work_unhealthy` — Unhealthy state → False

#### heartbeat_stale() Tests
- [ ] `test_heartbeat_fresh` — Recent read (< 30 min) → False
- [ ] `test_heartbeat_stale_default_threshold` — 31 min old → True
- [ ] `test_heartbeat_stale_custom_threshold` — Custom threshold respected → True
- [ ] `test_heartbeat_timezone_aware` — UTC conversion handled → Correct

#### to_dict() Tests
- [ ] `test_to_dict_all_fields` — All fields serialized
- [ ] `test_to_dict_enums_to_value` — Enums converted to string values
- [ ] `test_to_dict_datetimes_iso` — Datetimes to ISO format
- [ ] `test_to_dict_none_fields` — None fields handled
- [ ] `test_to_dict_roundtrip` — Dict can be used to reconstruct state

### TestSessionCommandPlan (12-15 tests)

#### Immutability Tests
- [ ] `test_immutability_frozen` — Dataclass is frozen
- [ ] `test_cannot_modify_intent` — Cannot modify command_intent
- [ ] `test_cannot_modify_transition` — Cannot modify expected_state_transition

#### is_executable() Tests
- [ ] `test_is_executable_all_conditions_met` — All conditions → True
- [ ] `test_not_executable_is_executable_now_false` — is_executable_now=False → False
- [ ] `test_not_executable_human_approval_required` — human_approval_required=True → False
- [ ] `test_not_executable_no_proof` — proof_requirement=NO_PROOF → False
- [ ] `test_is_executable_respects_all_gates` — All gates checked

#### requires_aegis_approval() Tests
- [ ] `test_requires_aegis_transfer` — TRANSFER → True
- [ ] `test_requires_aegis_archive` — ARCHIVE → True
- [ ] `test_requires_aegis_restart` — RESTART → True
- [ ] `test_requires_aegis_recover_from_limit` — RECOVER_FROM_LIMIT → True
- [ ] `test_not_requires_aegis_poll_queue` — POLL_QUEUE → False
- [ ] `test_not_requires_aegis_watch` — WATCH → False

#### is_legal() Tests
- [ ] `test_is_legal_spawn_from_starting` — SPAWN in STARTING → True
- [ ] `test_not_legal_spawn_from_running` — SPAWN in RUNNING → False
- [ ] `test_is_legal_poll_queue_any_state` — POLL_QUEUE in various states → All valid
- [ ] `test_is_legal_steer_only_running` — STEER only in RUNNING → Correct
- [ ] `test_is_legal_transfer_running_or_waiting` — TRANSFER in RUNNING/WAITING → True
- [ ] `test_not_legal_transfer_polling` — TRANSFER in POLLING → False

#### verify_state_transition_legal() Tests
- [ ] `test_legal_transition_starting_to_polling` — (STARTING, POLLING) → True
- [ ] `test_legal_transition_polling_to_running` — (POLLING, RUNNING) → True
- [ ] `test_legal_transition_running_to_waiting` — (RUNNING, WAITING) → True
- [ ] `test_legal_transition_blocked_to_polling` — (BLOCKED, POLLING) → True
- [ ] `test_illegal_transition_archived_to_running` — (ARCHIVED, RUNNING) → False
- [ ] `test_illegal_transition_polling_to_blocked` — (POLLING, BLOCKED) → False
- [ ] `test_all_18_legal_transitions` — Verify all 18 legal transitions accepted

#### to_dict() Tests
- [ ] `test_to_dict_all_fields` — All fields serialized
- [ ] `test_to_dict_enums_to_value` — Enums converted to string values
- [ ] `test_to_dict_tuple_to_array` — expected_state_transition to array
- [ ] `test_to_dict_none_fields` — Optional fields handled

### Integration Tests (20-25 tests)

#### Workflow Tests
- [ ] `test_workflow_spawn_to_polling` — SPAWN command → POLLING state
- [ ] `test_workflow_polling_to_running` — POLL_QUEUE+STEER → RUNNING state
- [ ] `test_workflow_running_to_waiting_to_running` — RUNNING → WAITING → RUNNING
- [ ] `test_workflow_capacity_limited_recovery` — RECOVER_FROM_LIMIT → RUNNING
- [ ] `test_workflow_stale_restart` — RESTART from STALE
- [ ] `test_workflow_transfer_mid_running` — TRANSFER during RUNNING

#### Safety Gate Tests
- [ ] `test_aegis_gate_blocks_transfer` — TRANSFER without Aegis approval → not executable
- [ ] `test_aegis_gate_blocks_archive` — ARCHIVE without Aegis approval → not executable
- [ ] `test_human_gate_blocks_execution` — human_approval_required → not executable
- [ ] `test_proof_gate_blocks_no_proof` — NO_PROOF requirement → not executable

#### Health-Based Tests
- [ ] `test_unhealthy_session_cannot_accept_work` — Degraded health blocks dispatch
- [ ] `test_stale_session_detected` — heartbeat_stale() triggers at threshold
- [ ] `test_blocker_prevents_work_dispatch` — blocker_summary present → can_accept_work() = False

#### Constraint Tests
- [ ] `test_unique_worktree_per_session` — Multiple sessions have distinct worktrees
- [ ] `test_queue_routing_build_session` — BUILD session reads only BUILD queue
- [ ] `test_queue_routing_review_session` — REVIEW session reads only REVIEW queue
- [ ] `test_permission_context_preserved` — permission_context survives serialization

---

## Part 8: Out Of Scope

The following are explicitly OUT OF SCOPE for Session Lifecycle V2 runtime implementation:

- **Live Polaris or Electron automation** — No subprocess spawning or UI control
- **Destructive commands** — No filesystem deletion, branch force-reset, or database drops
- **Automatic branch switching** — All branch movement requires explicit approval
- **Vendor account automation** — No cloud provider API calls, deployments, or service management
- **Shared mutable project state** — No global session registry (each session owns its state)
- **Federation networking** — No distributed session coordination across instances
- **Persistent state storage** — Session state lives in queue documents and memory; no database write
- **Bifrost UI rendering** — UI surfaces defined separately; this is typed state only
- **Prime orchestration logic** — Command selection is Prime's responsibility, not runtime
- **Aegis gate implementation** — Gate definitions exist elsewhere; Session Lifecycle carries results

---

## Summary

**SessionLifecycleState** is the immutable, serializable snapshot of session execution with 22 fields and 5 helper methods covering health, idleness, work eligibility, heartbeat staleness, and JSON serialization.

**SessionCommandPlan** is the immutable, auditable command proposal with 16 fields and 4 helper methods covering executability, approval requirements, legality validation, and serialization.

**Enums** define 42 distinct values across 6 type-safe enumerations covering session lifecycle, roles, commands, cadence, proof, and health states.

**Legality Matrix** enforces 18 valid state transitions and 11 command-state pairs, preventing illegal session state operations.

**Test Coverage** includes ~60 tests spanning immutability, helper method behavior, safety gates, constraint enforcement, and end-to-end workflows.

**Invariants** ensure unique worktree isolation, queue routing by role, permission-gated branch movement, and proof-based command execution.

---

## Implementation Notes

- Use `dataclass(frozen=True)` for SessionLifecycleState and SessionCommandPlan.
- Use `Enum` for all type-safe status/state/proof enumerations.
- All timestamps are `datetime(timezone.utc)`.
- All serialization uses `.value` for enums and `.isoformat()` for datetimes.
- Helper methods are pure functions with no side effects.
- No persistence; state is carried in queue documents and Bifrost displays.
- All validation is synchronous and raises on constraint violation.

**File:** `meridian_core/session_lifecycle.py` (estimated 300–350 lines)  
**Tests:** `tests/test_session_lifecycle.py` (estimated 400–500 lines, ~60 test cases)

---

*Specification completed and ready for code implementation.*
