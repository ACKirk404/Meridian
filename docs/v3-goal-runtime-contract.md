# V3 Goal Runtime / Goal Harness Contract

**Status:** V3 first-wave spec — bounded contract only. No runtime module, no
database, no process/session automation, no UI surface, no FileMap entry, no
generated artifacts, and no tests are introduced by this artifact.
Implementation lands in a later V3 build after this contract is reviewed.
**Owner harness:** Prime (primary, creation and completion). Compass Harness
(continuation/resume and `ACTIVE` / `BLOCKED` / `USAGE_LIMITED` transitions).
Echo Harness (lineage of goal history). Consumes Session Lifecycle, Beacon,
Aegis, and Relay/Model telemetry inputs only — no new runtime obligations on
those harnesses.
**Owner lane (doc):** Build 2 (Opus high-level thinking).
**Audience:** Prime, Compass, Echo, Session Lifecycle, Beacon, Aegis, Scott,
and future V3 runtime contributors.
**Purpose:** Pin the backend decision surface of a native goal runtime so
Meridian can coordinate long-running work without depending on external Codex
thread goals. This document defines the goal object, the bounded status
lifecycle, telemetry fields, continuation/resume policy boundaries, proof
trail requirements, completion and blocker semantics, ownership splits, and
explicit non-goals.

V0–V2 made Meridian capable of one focused action at a time and capable of
coordinating short bursts of execution through Session Lifecycle. V3 must add
a durable goal layer that survives session restarts, usage limits, model
swaps, and operator handoffs. The Goal Runtime is that layer. It is *not* a
planner, not a model call, not an executor, and not a backlog rewriter. It is
the typed, reviewable record of "what is Meridian trying to accomplish, how
is it going, and what would unblock or end it" that Prime and Compass advise
on.

---

## Source Of Authority

- `docs/v3-intake-resolution.md` row 15 (line 106 of the checklist) promotes
  *Long-term autonomy and goal chaining* to V3 with owners Prime (primary) /
  Compass Harness / Echo Harness, and pins the deliverables as goal-object
  shape, status lifecycle, telemetry, continuation/resume policy, and
  proof-trail semantics.
- `docs/v3-parking-lot.md` Prime section *Native Goal Runtime / Goal Harness*
  pre-lists the same horizon item with the lifecycle tokens `active`,
  `complete`, `blocked`, `usage-limited`, token/time/budget telemetry,
  continuation/resume policy, proof trail, and completion/blocker semantics
  so Meridian can coordinate long-running work without external Codex thread
  goals.
- `docs/agentic-ai-framework-checklist.md` line 106 (*Long-term autonomy and
  goal chaining*) is the V3 intake source row this contract resolves.

This contract may not introduce decisions outside what those three sources
authorize. Where they are silent, this contract defers the decision to a
later V3 spec rather than inventing it here. In particular: only the four
lifecycle tokens above are valid status values; no extra states, no extra
kind enums, and no extra terminal states are introduced here.

---

## What The Goal Runtime Is — And Is Not

The Goal Runtime is the durable goal-record layer that Prime and Compass
read and update. It is:

- **Domain-owned and display-safe.** Every goal field is either a typed value
  a future display consumer can render directly or a structured reference
  (id + short label) that resolves to one. No model prose, no embedded
  prompts, no executable payload.
- **Read-mostly for everything except its owning harness.** Prime authors and
  completes goals; Compass advances `ACTIVE` / `BLOCKED` / `USAGE_LIMITED`
  transitions; Echo records lineage; Beacon attaches telemetry snapshots;
  Aegis attaches the proof-trail reference and supplies policy results;
  Session Lifecycle consumes goal references when dispatching work. No other
  harness writes goal fields.
- **A decision surface, not an execution surface.** A goal record carries
  the evidence and constraints needed to decide what comes next; the doing
  happens in Session Lifecycle under Aegis policy as today.

The Goal Runtime is not:

- **A planner.** It does not invent multi-step roadmaps or task graphs. Task
  graphs remain a backlog/Compass concern; goals point at backlog items, not
  the other way around.
- **A model call.** No inference is allowed inside a goal-runtime operation.
  Selectors over goal state are deterministic.
- **An executor.** Goals do not spawn sessions, mutate worktrees, or move
  branches. Session Lifecycle still owns execution.
- **A bypass.** A goal cannot skip Aegis, cannot skip Review Console gates,
  cannot grant Prime new permissions it does not already hold, and cannot
  move branches or worktrees.
- **A replacement for backlog records.** Backlog entries remain the unit of
  work. A goal is the *objective frame* that one or more backlog entries
  advance.
- **A new memory store.** Goal lineage is recorded by Echo under the
  existing memory contract; the Goal Runtime does not introduce a parallel
  memory.
- **A budget enforcer.** The Goal Runtime *records* telemetry inputs that
  Beacon assembles from Relay and Model harnesses; it does not meter,
  throttle, or charge. Enforcement remains with the upstream harnesses.

---

## Harness Ownership

The split below is normative. Each row names the harness that *writes* the
field or transition; every other harness that touches that field is reading
only. Every field has exactly one writing harness per transition.

| Concern | Owner (writes) | Readers |
|---|---|---|
| Create a goal record; set `objective_text`, `objective_ref`, `owners`, initial `risk_tier`, initial `continuation_policy`; transition to `COMPLETE` | Prime | All |
| Status transitions among `ACTIVE`, `BLOCKED`, `USAGE_LIMITED` | Compass Harness | All |
| Continuation/resume policy edits after creation (`continuation_policy`) | Compass Harness | Prime, Aegis, Session Lifecycle |
| Append entries to the goal's lineage (`GoalLineageEntry`) | Echo Harness | All |
| Telemetry snapshots (`GoalTelemetrySnapshot`) — sole appender | Beacon Harness | All |
| Proof trail reference (`proof_trail_ref`) and `CognitionPolicy` result attached to the goal | Aegis Harness | All |
| Reference a goal from a dispatched session | Session Lifecycle | All |

### How Other Harnesses Influence Status Without Writing It

- **Aegis** evaluates `CognitionPolicy` and may *request* a `BLOCKED` status
  by emitting a policy result with a deny verdict and a blocker reference.
  Aegis never writes `status` itself. Compass reads the policy result and
  performs the `ACTIVE → BLOCKED` write under continuation policy. Aegis
  does write `proof_trail_ref` on the goal record; that is the only goal
  field Aegis writes.
- **Beacon** emits telemetry snapshots that may carry a `note` flagging a
  threshold crossing (e.g., provider quota reached). Beacon never writes
  `status`. Compass reads the snapshot and performs the `ACTIVE →
  USAGE_LIMITED` write under continuation policy.
- **Relay / Model harnesses** supply token, cost, and provider-label inputs
  to Beacon through their existing telemetry contracts. They never write a
  `GoalTelemetrySnapshot` directly and never write any goal field.
- **Session Lifecycle** writes its own session records that *reference* a
  `goal_id`. It does not write goal fields.
- **Prime autonomy** (`docs/prime-autonomy-v2-contract.md`) consumes goal
  records as input when proposing next actions. It does not write goal
  fields outside the creation and `COMPLETE` writes already listed.

### Single Author Per Transition

Every status transition has exactly one writing harness:

- Creation: **Prime**.
- `ACTIVE ↔ BLOCKED`: **Compass**.
- `ACTIVE ↔ USAGE_LIMITED`: **Compass**.
- `BLOCKED ↔ USAGE_LIMITED`: **Compass**.
- `ACTIVE → COMPLETE`: **Prime**.

Compass does not write `COMPLETE`. Prime does not write `BLOCKED` or
`USAGE_LIMITED`. Aegis, Beacon, Session Lifecycle, Echo, and the
Relay/Model harnesses do not write status under any condition.

---

## Goal Object Identity And Display-Safe Fields

The runtime introduces a small set of frozen, display-safe records.
Concrete types are deferred to the implementation slice; the field shape
below is normative.

### `GoalRecord`

The durable, display-safe goal object.

- `goal_id` — stable identifier; deterministic from `project` +
  `objective_ref` + `created_at` where possible so reissues are detectable.
  Required.
- `project` — project key (e.g., `meridian`, `polaris`, `aesop`). Required.
- `objective_text` — short human-authored objective, ≤ ~280 chars, plain
  text, no embedded prompts or model directives. Required.
- `objective_ref` — typed reference to the backlog / docs / contract record
  the goal advances: `id` and short label, with a short string `source` tag
  identifying the producing system (e.g., `backlog`, `doc`, `contract`).
  Optional only when no such reference exists (`objective_text` then carries
  the full framing).
- `owners` — tuple of harness names that own progressing this goal. Always
  includes `Prime`; usually adds `Compass` and sometimes `Echo`. Authored
  by Prime at creation; not edited afterward without a new goal.
- `status` — `GoalStatus` enum (see Lifecycle). Closed set of four values.
- `risk_tier` — integer 1–4 carried from Aegis's existing tier engine for
  the (project, objective_ref) pair. Not a new enum.
- `continuation_policy` — `GoalContinuationPolicy` record (see Continuation
  and Resume). Authored by Prime at creation; subsequent edits by Compass.
- `telemetry` — tuple of `GoalTelemetrySnapshot` records, append-only,
  capped by retention policy. Appended only by Beacon.
- `lineage` — tuple of `GoalLineageEntry` records, append-only. Appended
  only by Echo.
- `proof_trail_ref` — reference to an Aegis `ProofTrail` handle (see Proof
  Trail Requirements for when required).
- `blocked_reason` — optional `GoalBlockedReason` record; present iff
  `status == BLOCKED` or `status == USAGE_LIMITED`.
- `completion_summary` — optional short human-readable string ≤ ~200
  chars; present iff `status == COMPLETE`. Written by Prime alongside the
  `COMPLETE` transition.
- `final_proof_ref` — optional reference to the closing Aegis `ProofTrail`
  entry. Required when `status == COMPLETE` and `risk_tier >= 2`.
- `created_at` — UTC timestamp.
- `updated_at` — UTC timestamp of the last write to this record.
- `contract_version` — short string identifying the contract revision that
  produced the record. Bumps when this document changes in a way that
  affects field semantics.

`GoalRecord` is logically immutable: each write produces a new versioned
snapshot; the public reference is the latest snapshot for a given
`goal_id`. Once `status == COMPLETE`, the record is terminal — no further
writes are accepted on that `goal_id`. New work that supersedes a completed
goal happens by creating a new goal whose `objective_ref` or `lineage`
points at the completed goal. The Goal Runtime does not define separate
"abandoned" or "superseded" status values; an abandoned line of work is
expressed by creating no further goals against it, and a superseding line
of work is expressed by creating a new goal that references the prior one.

### Display-Safety Rule

Every field above must either be:

1. a typed scalar / enum / timestamp, or
2. a short human-authored string with a documented character cap, or
3. a structured reference (`id` + short label + optional source tag).

No field may carry free-form model output, embedded prompts, executable
payload, or HTML. Any future display consumer must be able to render any
`GoalRecord` without sanitization or re-templating. This rule is normative
for every nested record defined below.

### `GoalBlockedReason`

- `kind` — closed enum: `MISSING_PROOF`, `FAILED_PROOF`, `HUMAN_GATE`,
  `BRANCH_PERMISSION_REQUIRED`, `WORKTREE_COLLISION`, `OPEN_REVIEW_GATE`,
  `MISSING_FILEMAP_ENTRY`, `MISSING_ECHO_CONTEXT`, `MISSING_ATLAS_CONTEXT`,
  `POLICY_DENIED`, `DEPENDENCY_INCOMPLETE`, `OPERATOR_HOLD`,
  `EXTERNAL_DEPENDENCY`.
- `summary` — short human-readable explanation, ≤ ~200 chars.
- `reference` — optional structured reference (e.g., the blocking
  review-gate id, blocking goal id, blocking backlog id).
- `recorded_at` — UTC timestamp.
- `recorded_by` — harness name; for status-write-induced blocks this is
  always `Compass`. Aegis-supplied references that *triggered* the block are
  captured via `reference`, not via `recorded_by`.

---

## Allowed Status Lifecycle And Transition Rules

`GoalStatus` is a closed enum with exactly four values, matching the
lifecycle tokens authorized by `docs/v3-parking-lot.md`:

- `ACTIVE` — the goal is the current frame for at least one ongoing or
  imminent dispatch.
- `BLOCKED` — progress requires an external resolution captured in
  `blocked_reason`. Compass will not resume until the block is cleared.
- `USAGE_LIMITED` — a Relay / Model telemetry signal indicates the goal
  cannot consume more resources right now (quota, balance, rate). Carried
  as a distinct state so the lifecycle can model resource-quota blockers
  without conflating them with policy blocks.
- `COMPLETE` — Prime has accepted that `objective_text` is satisfied. The
  goal record is terminal.

No other status values are valid. No other terminal states exist. There are
no `paused`, `abandoned`, or `superseded` states in this contract; the
lifecycle is exhaustively defined by the four tokens above.

### Allowed Transitions

Source → permitted targets:

- `ACTIVE` → `BLOCKED`, `USAGE_LIMITED`, `COMPLETE`.
- `BLOCKED` → `ACTIVE` (block cleared), `USAGE_LIMITED`.
- `USAGE_LIMITED` → `ACTIVE`, `BLOCKED`.
- `COMPLETE` → terminal; no transitions allowed.

### Authorship Rules For Transitions

- Only **Prime** writes `ACTIVE → COMPLETE`. Compass never writes
  `COMPLETE`.
- Only **Compass** writes `ACTIVE → BLOCKED`, `ACTIVE → USAGE_LIMITED`,
  `BLOCKED → ACTIVE`, `BLOCKED → USAGE_LIMITED`, `USAGE_LIMITED → ACTIVE`,
  and `USAGE_LIMITED → BLOCKED`. Prime never writes these transitions.
- **Aegis** never writes `status`. It supplies `CognitionPolicy` results
  and the `proof_trail_ref` field. A deny verdict from Aegis is the signal
  Compass acts on to write `BLOCKED`; the act of writing the status is
  still Compass's.
- **Beacon** never writes `status`. A threshold-crossing snapshot is the
  signal Compass acts on to write `USAGE_LIMITED`; the act of writing the
  status is still Compass's.
- Every status transition appends a `GoalLineageEntry` authored by Echo
  capturing the prior status, new status, and writing harness.

### Forbidden Transitions

The lifecycle is closed. Any transition not enumerated above is forbidden
even if a future caller appears to need it. New states or transitions
require a contract revision and a bumped `contract_version`.

### Abandonment And Supersession Without New States

The narrowed lifecycle does not include `ABANDONED` or `SUPERSEDED` status
values. Equivalent operational outcomes are expressed inside the existing
four-state lifecycle:

- A goal that the operator chooses not to pursue further is left in its
  current non-`COMPLETE` state (typically `BLOCKED` with a `blocked_reason`
  of `OPERATOR_HOLD`). It is not "closed" in the runtime; it simply stops
  accruing telemetry as no further work is dispatched against it.
- A goal that is replaced by new framing is left in its current
  non-`COMPLETE` state, and a new goal is created whose `objective_ref` or
  `lineage` references the prior goal_id. The Goal Runtime does not need a
  separate status to express this; the lineage chain is the record.
- A goal that the operator wants to mark resolved despite incomplete
  outcome is written `COMPLETE` by Prime with a `completion_summary` that
  records the truth of the outcome. Prime owns this decision under existing
  Aegis policy.

If a future V3 spec needs a distinct terminal state for abandonment or
supersession, it is a contract revision — not a runtime convenience.

---

## Token / Time / Budget Telemetry Fields And Update Semantics

Telemetry is **observational**, not authoritative. Authoritative metering
remains with the Relay and Model harnesses; the Goal Runtime carries
snapshots so Prime and Compass can reason about a goal's resource cost
without querying upstream harnesses on every read.

**Sole appender.** Only **Beacon** appends `GoalTelemetrySnapshot` records
to a `GoalRecord`. No other harness writes the goal's telemetry tuple.
Relay and Model harnesses supply token, cost, and provider-label inputs to
Beacon through their existing telemetry contracts; Beacon is the one that
assembles a snapshot and appends it. This is the only allowed write path.

### `GoalTelemetrySnapshot`

- `snapshot_id` — stable identifier, deterministic from `goal_id` +
  `recorded_at`.
- `recorded_at` — UTC timestamp.
- `recorded_by` — always `Beacon`.
- `token_source` — short string identifying which upstream harness supplied
  the token counts (e.g., `relay`, `model`). Captures provenance without
  granting that harness a write capability.
- `cost_source` — short string identifying which upstream harness supplied
  the cost figures (e.g., `relay`, `model`).
- `token_window` — `GoalTokenWindow`: `prompt_tokens`, `completion_tokens`,
  `total_tokens`, and a denormalized `provider_label` (short string).
  Counters are cumulative from goal creation.
- `time_window` — `GoalTimeWindow`: `wall_seconds_active`,
  `wall_seconds_blocked`, `wall_seconds_usage_limited`. Cumulative from
  goal creation.
- `budget_window` — `GoalBudgetWindow`: `cost_units`, `cost_currency`
  (short string, defaults to the project default), `provider_label`.
  Cumulative from goal creation; `cost_units` is whatever the Relay/Model
  harness emits — the Goal Runtime does not redefine cost.
- `session_window` — `GoalSessionWindow`: `dispatched_sessions`,
  `completed_sessions`, `failed_sessions`. Cumulative from goal creation.
- `note` — optional short string (≤ ~200 chars) used by Beacon to flag a
  notable snapshot (e.g., usage-limit threshold reached). No model prose.

### Update Semantics

- Snapshots are **append-only**. The Goal Runtime never edits a prior
  snapshot.
- Snapshots may be **emitted on demand** by Beacon at session-lifecycle
  boundaries (session start, session complete, session fail), or **emitted
  on threshold** when Relay/Model telemetry indicates a cap was crossed.
- The Goal Runtime applies a **retention cap** on snapshots per goal
  (`telemetry_snapshot_cap`, configurable; default deferred to
  implementation). When the cap is hit, the oldest snapshot is dropped
  from the in-record tuple but persisted to Echo lineage so the historical
  record is recoverable.
- Telemetry snapshots must be **monotonic**. If an upstream signal would
  produce a non-monotonic counter (e.g., a corrected token count from a
  provider), Beacon emits a new snapshot with the corrected value and a
  `note` flagging the correction; it does not overwrite the prior
  snapshot.
- Telemetry must not carry **session-private data**: no transcripts, no
  prompt bodies, no model output. Only the typed counters above and short
  labels.

### What Telemetry Does Not Do

- It does not throttle. Relay and Model harness enforcement remains
  authoritative.
- It does not compute predictions or forecasts. Forecasting, if
  introduced, is a separate spec.
- It does not normalize across providers. The `provider_label` and
  `cost_currency` carry the raw label; cross-provider normalization is a
  later V3 decision.

---

## Continuation And Resume Policy Boundaries

A `GoalContinuationPolicy` carries the deterministic, machine-readable
bounds that Compass uses to decide whether to advance a `BLOCKED` or
`USAGE_LIMITED` goal back to `ACTIVE`.

### `GoalContinuationPolicy` Fields

- `max_active_attempts` — integer cap on total times the goal may transition
  into `ACTIVE` before the goal must be reviewed by Prime.
- `cooldown_seconds` — minimum wall-clock interval Compass must observe
  between consecutive `BLOCKED → ACTIVE` or `USAGE_LIMITED → ACTIVE`
  transitions.
- `usage_limit_resume_kind` — closed enum: `WAIT_FOR_SIGNAL` (Compass
  resumes only when Relay/Model telemetry emits a quota-clear signal),
  `WAIT_FOR_TIMEOUT` (resume after a fixed delay), `MANUAL` (resume
  requires Prime or Scott).
- `block_resume_kind` — closed enum: `MANUAL` (default for `HUMAN_GATE`,
  `BRANCH_PERMISSION_REQUIRED`, `WORKTREE_COLLISION`, `POLICY_DENIED`,
  `OPERATOR_HOLD`), `AUTO_ON_DEPENDENCY_CLEAR` (allowed only for
  `DEPENDENCY_INCOMPLETE`, `MISSING_PROOF`, `MISSING_FILEMAP_ENTRY`,
  `MISSING_ECHO_CONTEXT`, `MISSING_ATLAS_CONTEXT`, `OPEN_REVIEW_GATE`),
  `EXTERNAL_SIGNAL` (allowed only for `EXTERNAL_DEPENDENCY`).
- `proof_required_for_resume` — boolean; when true, Compass must read an
  attached Aegis proof trail entry before transitioning from `BLOCKED` or
  `USAGE_LIMITED` back to `ACTIVE`.
- `human_gate_on_resume_kinds` — tuple of `GoalBlockedReason.kind` values
  that always require a human gate before resume, regardless of other
  policy fields. Always includes `HUMAN_GATE`,
  `BRANCH_PERMISSION_REQUIRED`, `WORKTREE_COLLISION`, and `POLICY_DENIED`.

### Policy Boundaries

- A continuation policy **must not** widen any permission Prime or Compass
  does not already hold under existing contracts. It can only narrow.
- A policy **must not** authorize automatic branch moves, worktree moves,
  cherry-picks, or any operation the global branch-isolation rule reserves
  for explicit operator approval.
- A policy **must not** allow auto-resume past `max_active_attempts`. When
  the cap is reached, Compass writes `BLOCKED` with kind
  `DEPENDENCY_INCOMPLETE` (or a more specific kind if available) and
  surfaces the goal for Prime review.
- Policies **must not** be edited mid-lifecycle without producing a new
  `GoalLineageEntry` capturing the prior policy snapshot. Policy edits
  after creation are Compass writes.

### What Continuation Policy Does Not Cover

- It does not pick the next session command. That is a Session Lifecycle
  and Prime autonomy concern.
- It does not allocate worker tiers, model providers, or routes. Those
  remain with Model Harness and Relay.
- It does not encode prompt-drag posture. Prompt-drag remains a Prime
  autonomy concern (`docs/prime-autonomy-v2-contract.md`).

---

## Proof Trail Requirements

Every goal must be traceable from objective to outcome. The Goal Runtime
does not introduce a new proof store; it requires that goals reference
Aegis's existing `ProofTrail` contract. This section is the single source
of truth for when `proof_trail_ref` must be present; the `GoalRecord`
field definition above defers to it.

`proof_trail_ref` is **required** on a `GoalRecord` when any of the
following is true:

1. `risk_tier >= 2`.
2. The goal has produced one or more Session Lifecycle dispatches.
3. The goal has reached `BLOCKED` at least once.
4. The goal has reached `USAGE_LIMITED` at least once.
5. `status == COMPLETE`.

`proof_trail_ref` is **optional** only when none of conditions 1–5 holds
(typically a low-risk goal that has never been dispatched, never blocked,
never resource-limited, and is not yet complete).

`final_proof_ref` is **required** when `status == COMPLETE` and
`risk_tier >= 2`. It points at the closing Aegis proof entry. Prime may
not write `COMPLETE` without it under that condition.

Additional rules:

- The Goal Runtime **must not duplicate** proof contents inside the goal
  record. The record carries a reference; the contents live in Aegis.
- Every `BLOCKED` reason of kind `MISSING_PROOF` or `FAILED_PROOF` must
  point at a specific Aegis proof entry via `reference`; the Goal Runtime
  does not describe the proof, only points to it.
- `GoalLineageEntry` entries authored by Echo may include a structured
  reference to proof entries when relevant; they must not duplicate the
  proof contents.

---

## Completion And Blocked Semantics

### Completion

- A goal is `COMPLETE` only when **Prime** writes the `ACTIVE → COMPLETE`
  transition with a `completion_summary`. No other harness may declare
  completion.
- For `risk_tier >= 2`, `final_proof_ref` is required (see Proof Trail
  Requirements).
- Once `COMPLETE`, the record is terminal: no telemetry snapshot, no
  continuation policy edit, and no status change is permitted. The lineage
  remains readable for audit.
- Successor work uses a new goal that references the completed goal in
  `objective_ref` or `lineage`, never by mutating the terminal record.

### Blocked

- `BLOCKED` requires a non-empty `blocked_reason`.
- The blocker `kind` must be one of the closed enum values defined above.
  Free-form blocker descriptions are not allowed.
- Compass writes the transition into and out of `BLOCKED`. Aegis may
  supply the deny verdict that triggers it; Compass performs the write.
- Resuming from `BLOCKED` requires Compass to verify that
  `continuation_policy.block_resume_kind` permits the kind of resume being
  taken and that `human_gate_on_resume_kinds` does not require a human
  gate that is still open.
- `proof_required_for_resume` must be satisfied before the
  `BLOCKED → ACTIVE` write.

### Usage-Limited

- `USAGE_LIMITED` is reserved for resource-quota blockers surfaced by
  Beacon-assembled Relay/Model telemetry. It is *not* the same as
  `POLICY_DENIED`.
- A `USAGE_LIMITED` goal must carry a `blocked_reason` with kind
  `EXTERNAL_DEPENDENCY` (or a future kind explicitly added under contract
  revision). The triggering telemetry snapshot may set `note` to a short
  label (e.g., `provider_quota`, `local_budget`) for future display
  consumers.
- Compass writes the transition into and out of `USAGE_LIMITED`.
- `proof_required_for_resume`, when set on the policy, applies equally
  to `USAGE_LIMITED → ACTIVE`.

### Walking Away From A Goal

There is no `ABANDONED` status. A goal that the operator stops pursuing
remains in its last non-`COMPLETE` status (typically `BLOCKED` with kind
`OPERATOR_HOLD`). It simply accrues no further telemetry because no
sessions are dispatched against it. If the operator later wants to record
the outcome explicitly, Prime may write `ACTIVE → COMPLETE` with a
`completion_summary` that names the truth of the outcome and a
`final_proof_ref` if `risk_tier >= 2`.

### Replacing A Goal

There is no `SUPERSEDED` status. Replacement is expressed by creating a
new `GoalRecord` whose `objective_ref` or first `lineage` entry points at
the prior `goal_id`. The Goal Runtime does not need to modify the prior
record for the relationship to be discoverable.

---

## Ownership Boundaries Between Harnesses

The following table is the normative cross-harness boundary for the Goal
Runtime. It does not redefine any existing contract; it pins where each
existing harness touches goal state, with a single writer per field per
transition.

| Harness | Writes to goal record | Reads goal record |
|---|---|---|
| Prime | Create record (`objective_text`, `objective_ref`, `owners`, `risk_tier`, initial `continuation_policy`); transition `ACTIVE → COMPLETE`; write `completion_summary` | Always |
| Compass Harness | Status transitions among `ACTIVE`, `BLOCKED`, `USAGE_LIMITED`; `continuation_policy` edits after creation; `blocked_reason` on the transition into `BLOCKED` or `USAGE_LIMITED` | Always |
| Echo Harness | `lineage` (append-only) | Always |
| Session Lifecycle | None directly; emits dispatch events that Beacon turns into `session_window` deltas; references `goal_id` on its own session records | Reads `goal_id`, `continuation_policy`, `status`, `proof_trail_ref` |
| Beacon Harness | `telemetry` snapshots (sole appender, with `token_source` / `cost_source` provenance fields) | Reads `status`, `continuation_policy` for surfacing thresholds |
| Aegis Harness | `proof_trail_ref`; supplies `CognitionPolicy` results that Compass acts on when transitioning status | Reads everything |
| Relay / Model Harness | None on the goal record; supplies token / cost telemetry inputs to Beacon | Reads `goal_id` for attribution only |

A future read-only display consumer (e.g., a Bifrost surface) reads goal
records but writes nothing. Any such display surface is out of scope for
this contract; it is mentioned here only to make explicit that displays
are read-only consumers, not writers.

### Anti-Patterns Explicitly Forbidden

- **Cross-harness status writes.** Aegis cannot move a goal to `BLOCKED`
  itself; it surfaces a policy result that Compass acts on. Beacon cannot
  move a goal to `USAGE_LIMITED` itself; it emits a telemetry snapshot
  that Compass acts on. Prime cannot move a goal to `BLOCKED` or
  `USAGE_LIMITED`; only Compass can.
- **Cross-harness telemetry writes.** Only Beacon appends
  `GoalTelemetrySnapshot`. Relay and Model never write a snapshot; they
  supply inputs.
- **Lineage forgery.** Only Echo writes `GoalLineageEntry`. Other harnesses
  request entries via Echo's existing contract.
- **Inline proof.** Proof contents never live on the goal record. Only
  references.
- **Telemetry by Prime or Compass.** Neither Prime nor Compass writes
  telemetry snapshots. If either has signal that should produce one, it
  goes through Beacon.
- **Continuation policy by anyone except Prime (at creation) or Compass
  (afterward).**

---

## Non-Goals (V3 First Slice)

The following are explicitly out of scope for this contract and for the
first V3 implementation slice that lands it:

- Lifecycle states beyond `ACTIVE`, `BLOCKED`, `USAGE_LIMITED`, and
  `COMPLETE`. No `PAUSED`, `ABANDONED`, or `SUPERSEDED` states.
- Goal-kind classification enums (`WORK` / `OBSERVE` / `MAINTENANCE` /
  `REPAIR` etc.) or any other classification taxonomy on goals.
- Cross-instance / federated goals. Multi-Prime coordination and
  federated goal sharing are V4+ horizon items (see Federation Harness
  section of `docs/v3-parking-lot.md`).
- Goal forecasting. No predictive token / time / completion estimates.
- Goal prioritization across projects. The Goal Runtime carries one
  project per goal; cross-project prioritization is Prime autonomy's
  concern.
- Goal marketplaces or external goal contracts. Park-for-later under
  Federation Harness.
- Provider-normalized cost. Cost is recorded as the upstream Relay/Model
  harness emits it.
- Automatic backlog rewriting from goal state. Backlog edits remain
  human-gated through existing contracts.
- Automatic worktree, branch, or repository operations driven by goal
  status. Branch isolation rules override every goal-runtime decision.
- A new UI surface. Display surfacing of goal records is not in scope for
  this contract or its first implementation slice; any future display
  consumer is read-only and is specified separately.
- Tests, FileMap entries, or generated artifacts in this slice. Those land
  with the implementation slice and must obey the harness-maturity build
  policy.

---

## Safety Constraints

The Goal Runtime is a high-trust seam: it spans multiple harnesses and
survives across sessions, so a defect here propagates further than a
single-session bug. The following constraints are normative.

1. **Display-safety is mandatory.** No field carries free-form model
   output, prompts, executable code, HTML, or session-private data.
   Violations are contract bugs, not stylistic preferences.
2. **No model calls inside the Goal Runtime.** Reading a goal, deciding a
   transition under policy, and emitting telemetry are deterministic. If
   a harness needs a model call to *form* a transition request, the call
   happens in that harness and the goal record only records the typed
   result.
3. **Aegis is non-bypassable.** Every status transition that touches
   dispatch capacity must be evaluable by Aegis under existing
   `CognitionPolicy` rules. The Goal Runtime does not introduce a parallel
   policy layer.
4. **Branch isolation overrides goal policy.** No continuation policy
   field may authorize an operation that the global branch-isolation rule
   reserves for explicit operator approval. If a continuation policy and
   the branch rule disagree, the branch rule wins.
5. **Closed enums everywhere.** `GoalStatus`, blocker kinds, continuation
   enums are closed. Extensions require a contract revision and a
   `contract_version` bump.
6. **Append-only history.** Telemetry and lineage are append-only.
   Retention caps drop old entries to Echo lineage; they do not
   overwrite.
7. **Single writer per field per transition.** Every field has exactly
   one writing harness for each transition. Multi-writer fields are a
   contract bug.
8. **Reissue, do not mutate, on terminal state.** Completed goals are
   read-only forever. New work uses new goals that reference them.
9. **No silent retries.** A continuation policy that auto-resumes must
   produce a `GoalLineageEntry` per resume so the audit trail is
   complete.

---

## Stop Conditions For Implementation

The implementation slice that follows this contract must stop and surface
a Review Console gate when any of the following holds:

- A required field on `GoalRecord` is absent or fails the display-safety
  rule.
- A forbidden status transition is requested.
- A continuation policy would authorize an operation outside Prime /
  Compass's existing permissions.
- A telemetry snapshot would be written by any harness other than Beacon,
  or would carry session-private data.
- A status transition is attempted by a harness other than the single
  authoring harness for that transition.
- A `COMPLETE` write lacks `final_proof_ref` for `risk_tier >= 2`.
- A `BLOCKED` write carries a blocker `kind` not in the closed enum.

In every stop case, the runtime emits a `GoalLineageEntry` capturing the
attempted write and the rejection, and the goal status remains unchanged.

---

## Open Questions Deferred To Later V3 Specs

These items are intentionally not decided here. Later V3 specs may decide
them; this contract gives them names so reviewers can confirm the omission
is deliberate.

- Concrete persistence layer for goal records (database, file store,
  both).
- Snapshot retention cap defaults (`telemetry_snapshot_cap`) and lineage
  retention defaults.
- Whether a future display consumer (e.g., Bifrost) presents goal records;
  its surface is out of scope here and not a ship gate for this contract.
- Cross-project goal aggregation and prioritization.
- Federated goal sharing across Meridian instances.
- Forecasting / predictive cost surfaces.
- Goal-driven backlog generation.
- Goal-runtime contract guard tests; first slice ships docs only.

---

## Cross-References

- `docs/v3-intake-resolution.md` row 15 (Long-term autonomy and goal
  chaining → V3).
- `docs/v3-parking-lot.md` Prime section, *Native Goal Runtime / Goal
  Harness* horizon item.
- `docs/agentic-ai-framework-checklist.md` line 106.
- `docs/prime-autonomy-v2-contract.md` (selector that will read goal
  records).
- `docs/aegis-relay-summary-handoff-contract.md` and the proof-policy
  checklist (Aegis ownership of `ProofTrail`).
- `docs/echo-memory-contract.md` (lineage / memory store).
- `docs/session-lifecycle-v2-contract.md` (consumer of `goal_id`
  references).
