# Aegis-to-Relay Summary Handoff Contract

## Overview

This contract defines how Aegis gate evaluation outcomes, proof evidence, premium-cost approvals, waiver/approval records, and model/vendor evidence are handed to Relay for prompt packaging, context formatting, and downstream Bifrost display.

Aegis evaluates 9 deterministic gates per route and produces structured evidence. Relay consumes that evidence to make deterministic routing decisions and configure prompt context. Neither system calls models, inspects accounts, or persists shared mutable state — both are pure, stateless evaluators.

---

## Aegis Output Shape

### Core Gate Result

```python
@dataclass
class GateResult:
    gate_name: str              # stable identifier: e.g., "unknown_route_class", "cost_exposure"
    decision: GateDecision      # ALLOW | DEMOTE | BLOCK (from enum)
    reason: str = ""            # human-readable explanation; may reference tiers or proof gaps
    demote_to_tier: int | None  # if DEMOTE, the recommended tier (e.g., 2); else None
```

**Stable fields:** gate_name, decision are required and immutable.  
**Optional fields:** reason can be empty string; demote_to_tier is only populated on DEMOTE.

### Summary Wrapper (Relay/Bifrost Display)

```python
@dataclass
class GateSummary:
    gate_id: str                    # same as gate_name
    gate_label: str                 # human-readable: "Cost Exposure Gate", "Tier 3 Dual-Lane Requirement"
    decision: str                   # "allow", "demote", "block"
    severity: str                   # "info", "warning", "error"
    reason: str                     # explanation for downstream display
    required_evidence: str          # type of proof needed for this gate
    waiver_approval_status: str     # "none", "waived", "approved", "pending"
    downstream_action: str          # deterministic action Relay/Bifrost should take
```

**Display-safe:** all fields are strings; no raw logic or account state.  
**Audit trail:** reason field preserves evidence references for review.

### Aggregate Route Summary

When multiple gates are evaluated per route:

```python
@dataclass
class AggregateGateSummary:
    gate_count: int
    highest_severity: str               # "info" < "warning" < "error" (hierarchy)
    aggregate_action: str               # "route allowed", "demote to tier X", "route blocked"
    blocked_gates: list[str]            # gate_ids that returned BLOCK
    demoted_gates: list[str]            # gate_ids that returned DEMOTE
    allowed_gates: list[str]            # gate_ids that returned ALLOW
    evidence_required: list[str]        # all proof types across gates
    waivers_present: list[str]          # gate_ids with waivers
    approvals_present: list[str]        # gate_ids with approvals
    gate_details: list[GateSummary]     # full summary for each gate
```

**Ordering:** gate_details are in deterministic order by gate_id.  
**Determinism:** severity and action use fixed priority rules; no model-based ordering.

---

## Evidence Records Passed to Relay

### Premium-Cost Approval Evidence

For gates that check premium-cost routes (e.g., `gate_cost_exposure`):

```python
@dataclass
class ApprovalRecord:
    approval_id: str           # stable identifier for this approval
    actor: str                 # user, service, or automation that approved
    scope: str                 # what was approved: "PREMIUM_COST_ROUTE", "TIER_2_ROUTE", etc.
    timestamp: str             # ISO 8601: when approval was granted
    reason: str                # why premium cost is acceptable for this session
    expiration: str = ""       # ISO 8601: when approval expires (optional)
```

**Validation:** Aegis gates check `is_valid()` — all required fields must be non-empty strings.  
**Relay use:** if `ApprovalRecord` is present and valid, Relay may permit cost-sensitive routes; if absent or invalid, Relay blocks.

### Waiver Evidence

For gates that accept policy exceptions (e.g., `gate_tier3_dual_lane_requirement`):

```python
@dataclass
class WaiverRecord:
    waiver_id: str             # stable identifier
    actor: str                 # user who granted waiver
    scope: str                 # what was waived: "DUAL_LANE_REQUIREMENT", "PROOF_GAP", etc.
    timestamp: str             # when waiver was granted
    reason: str                # justification for exception
    expiration: str = ""       # optional: when waiver expires
```

**Validation:** `is_valid()` ensures all required fields are non-empty.  
**Audit:** waiver record presence is noted in gate summary for human review.

### Selected Model/Vendor Evidence

For gates requiring explicit proof of model/vendor capability:

```python
# Passed as metadata in gate result reason field or separate object
selected_model_evidence: {
    "model_name": "Claude Opus 4.7",      # actual model identifier
    "vendor": "Anthropic",                 # vendor name
    "capability_proof": "code_review",    # what capability was validated
    "validated_date": "2026-06-01T12:00:00Z"
}
```

**Stability:** model names are opaque to Aegis; Relay resolves to actual model IDs.  
**Proof type:** Relay/Bifrost display shows capability_proof in gate summary.

---

## Human-Facing vs Audit-Only Fields

### Human-Facing (Bifrost Display)

- `GateSummary.gate_label` — friendly gate name
- `GateSummary.reason` — clear explanation for user
- `GateSummary.decision` — ALLOW/DEMOTE/BLOCK (action needed?)
- `GateSummary.severity` — INFO/WARNING/ERROR
- `AggregateGateSummary.aggregate_action` — what routing decision results
- `ApprovalRecord.scope` — what was approved (human-readable)
- `ApprovalRecord.reason` — why it was approved (user justification)

### Audit-Only (Logs/Reviews)

- `GateResult.demote_to_tier` — used for routing, not displayed
- `GateResult.reason` — may contain internal gate logic references
- `GateSummary.required_evidence` — evidence type (not user-facing)
- `AggregateGateSummary.gate_details` — full list of results for review
- `ApprovalRecord.actor` — who approved (audit trail, not displayed to end user)
- `ApprovalRecord.timestamp` — expiration/valid-since (audit)
- `WaiverRecord.*` — all fields are audit-trail only; not rendered in UI

**Principle:** Bifrost renders only fields marked human-facing. Gates themselves are never shown raw; summaries format them.

---

## Stable Handoff Boundaries

### What Aegis Always Provides

1. **Gate decision** — one of ALLOW/DEMOTE/BLOCK per gate.
2. **Severity** — deterministically computed from decision.
3. **Gate label** — human-readable name for the gate.
4. **Reason** — brief explanation tied to the decision.
5. **Required evidence type** — what proof this gate needs.
6. **Waiver/approval status** — whether gate has valid evidence or is pending.

### What Relay Requires From Aegis

1. **All 9 gate results** must be present or explicitly absent (no partial results).
2. **GateSummary or AggregateGateSummary** for display (raw GateResult is not display-safe).
3. **ApprovalRecord/WaiverRecord** presence when gates reference them.
4. **Deterministic ordering** — results always in same order (by gate_id).

### What Relay Provides Downstream

1. **Routing decision** — accept, demote, block based on aggregate severity.
2. **Context configuration** — prompt budget, session action, latency posture.
3. **Bifrost render parameters** — which summaries to display, severity colors, actions.

---

## Out-of-Scope Boundaries

### Not Handled by This Handoff

- **Model selection:** which specific Claude model Relay routes to. (Relay/Model Harness domain.)
- **Session management:** reuse, reset, or start new. (Relay/Prime Session Lifecycle domain.)
- **Account/cost routing:** which account to bill. (Prime/Model Harness domain.)
- **Fallback logic:** what to do if the primary route fails. (Relay/Prime domain.)
- **Prompt injection:** detecting or sanitizing user input. (Prime/Model Harness domain.)
- **UI rendering:** exact layout, colors, fonts for Bifrost. (Bifrost domain.)
- **Persistence:** storing route decisions, approval records, or waiver history. (Prime/Durable State domain.)
- **Async approval workflows:** polling for human approval, retrying after waiver. (Prime domain.)

### Aegis Stays Pure

- No account inspection (no costs, billing, quota).
- No model calls (no training, validation).
- No session state mutation (no side effects).
- No UI rendering (structured output only).
- No async/polling (synchronous evaluation).

### Relay Stays Deterministic

- Given the same Aegis outputs, Relay always routes the same way.
- Relay does not modify or override gate decisions.
- Relay passes gate outputs to Bifrost unchanged (only formatting).

---

## Example Handoff Flow

1. **Prime routes a request** → calls Aegis with route parameters.
2. **Aegis evaluates 9 gates** → produces list of GateResult objects.
3. **Aegis summarizes results** → wraps in GateSummary + AggregateGateSummary.
4. **Aegis passes to Relay:**
   ```python
   {
       "gate_results": [GateResult, GateResult, ...],
       "gate_summaries": [GateSummary, GateSummary, ...],
       "aggregate": AggregateGateSummary,
       "approvals": [ApprovalRecord],  # if any
       "waivers": [WaiverRecord],      # if any
   }
   ```
5. **Relay makes routing decision** based on aggregate_action.
6. **Relay configures context** (prompt budget, session strategy, etc.).
7. **Relay passes GateSummary to Bifrost** for UI display.
8. **Bifrost renders human-facing fields** (decision, reason, action).

---

## Testing and Proof

- Aegis gate tests verify each gate produces consistent GateResult/GateSummary output.
- Relay tests verify routing decisions align with aggregate gate severity.
- Integration tests verify ApprovalRecord/WaiverRecord validation blocks invalid inputs.
- No E2E model calls or account inspection in tests — all mocked/stubbed.

---

## Version & Stability

- **Version:** V1 (initial release).
- **Stability:** GateResult, GateSummary, ApprovalRecord, WaiverRecord are stable for Relay consumption.
- **Future:** if new gates are added, GateSummary and AggregateGateSummary remain backward-compatible by extending lists.
- **Deprecation:** no planned deprecations; breaking changes would increment version.
