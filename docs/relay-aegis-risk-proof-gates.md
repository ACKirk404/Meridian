# Relay-Aegis Risk and Proof Gates

**Status:** V2 architecture contract — defines gates for Aegis to validate Relay routing decisions
**Date:** 2026-06-01
**Owner harness:** Aegis (validation), Relay (dispatch), Model Harness (metadata)
**Audience:** Aegis runtime, Relay dispatch logic, Scott, Build 1-5, Codex Reviews
**Purpose:** Prevent Relay from routing to unsafe, unproven, or unvalidated model routes by defining explicit gates that Aegis must enforce.

---

## Why These Gates Exist

Relay answers 44 questions before choosing a model route. Aegis does not answer those questions — Relay does. But Aegis *validates* that Relay answered correctly and *blocks* routes that fail validation.

This contract tells Aegis exactly when a Relay route is allowed, requires dual-lane review, must be demoted to a lower tier, is blocked unconditionally, or requires human approval.

---

## Gate Categories

Aegis enforces gates in this order. A route that fails any gate is blocked unless explicitly waived at the gate level (human gate only).

### 1. Unknown Route Class Gate

**Trigger:** `route_class` is missing, unknown, or ambiguous.

**Allowed values:** `account_session | local_cli | direct_api | aggregator_api`

**Gate logic:**
- If `route_class` is not declared, **block** unconditionally. Relay must choose account/session first, then local CLI, then direct API, then aggregator.
- If `route_class` is `account_session`, gate passes (see Account/Session Risk gate below).
- If `route_class` is `local_cli`, gate passes (see CLI Risk gate below).
- If `route_class` is `direct_api`, gate passes (see Direct API Risk gate below).
- If `route_class` is `aggregator_api`, gate passes (see Aggregator Authority gate below).

**Action on block:** Return error to Prime: "Relay route class unknown. Route not available."

---

### 2. Missing Exact Model ID Gate

**Trigger:** `model_id` is missing, empty, or unversioned.

**Allowed for:** Tier 0, Tier 1 only (with cost/latency pressure noted).

**Gate logic:**
- For Tier 0 (no model call), gate passes (no model ID needed).
- For Tier 1, if `model_id` is missing or unversioned (e.g., `"gpt-latest"` instead of `"gpt-4o-2025-05-13"`), **allow with warning**. Bifrost shows "model version unknown; route may alias silently."
- For Tier 2+, if `model_id` is missing or unversioned, **block** and return error: "Tier 2+ requires exact model ID for audit trail."

**Action on block:** Return error to Prime: "Route model ID unknown or unversioned. Not allowed for this risk tier."

---

### 3. Tier 3 Dual-Lane Requirement Gate

**Trigger:** `risk_tier` is 3 and `dual_lane_required` is not `True`.

**Gate logic:**
- If `risk_tier == 3` and `dual_lane_required == False`, **check for explicit waiver**.
  - If waiver exists (stored in decision record), **allow but demote to Tier 2** unless waiver explicitly permits Tier 3 single-lane.
  - If no waiver, **block** and return error: "Tier 3 requires independent dual-lane reasoning. Request waiver or use Tier 2."
- If `risk_tier == 3` and `dual_lane_required == True`, gate passes.
- The second lane must use a different model family (Claude + OpenAI, Claude + DeepSeek, etc.), never the same model twice.

**Action on block:** Return error to Prime: "Tier 3 single-lane blocked. Dual-lane required or explicit waiver needed."

---

### 4. Unknown Proof Requirement Gate

**Trigger:** `proof_required` is missing or unknown.

**Allowed values:** 
- Tier 0: `proof_type: none`
- Tier 1: `proof_type: none | artifact | telemetry`
- Tier 2: `proof_type: artifact | telemetry | code_review`
- Tier 3: `proof_type: code_review | security_review | dual_review`
- Tier 4: `proof_type: human_gate | security_review`

**Gate logic:**
- If `proof_required` is missing or not a recognized type, **block**.
- If `proof_required: none` and `risk_tier >= 2`, **demote to Tier 1** and return warning: "Proof requirement mismatch. Demoting to Tier 1."
- If `proof_required: artifact | telemetry` and `risk_tier >= 3`, **demote to Tier 2** and return warning: "Proof insufficient for Tier 3+. Demoting to Tier 2."
- If `proof_required: code_review` and `risk_tier == 4`, **block** and return error: "Tier 4 requires human gate + security review, not code review alone."

**Action on block:** Return error to Prime: "Proof requirement unknown or insufficient for risk tier. Route blocked."

---

### 5. Unsafe Fallback Gate

**Trigger:** `fallback_allowed` is `True` but `fallback_blockers` contains risk flags.

**Gate logic:**
- If `fallback_allowed == True` and `fallback_blockers` is non-empty:
  - If blocker is `"silent_fallback"`, **block unconditionally**. Silent fallback is never allowed for Tier 2+.
  - If blocker is `"trust_downgrade"` and `risk_tier >= 2`, **allow with warning** but require human acknowledgment: "Fallback route has lower trust. Continue? [Y/N]"
  - If blocker is `"cost_increase"` and `cost_posture == PREMIUM`, **allow but warn**: "Fallback costs more than primary route."
  - If blocker is `"model_mismatch"` and `risk_tier >= 3`, **block** and return error: "Fallback model differs. Not allowed for Tier 3+ without explicit waiver."
- If `fallback_allowed == False`, gate passes (no fallback to validate).

**Action on block:** Return error to Prime: "Fallback route has unsafe blockers. Route blocked without waiver."

---

### 6. Unvalidated DeepSeek Gate

**Trigger:** `provider == "deepseek"` and `external_review_status` is not `PASSED`.

**Gate logic:**
- If `provider == "deepseek"`:
  - If `trust_mode != DIRECT`, **block** immediately: "DeepSeek through aggregator not allowed. Use direct API."
  - If `trust_mode == DIRECT`:
    - If `external_review_status == PENDING`, **allow Tier 0-1 only** with warning: "DeepSeek validation pending. Limited to Tier 0-1."
    - If `external_review_status == PASSED` and timestamp is within 30 days, gate passes.
    - If `external_review_status == PASSED` but timestamp is older than 30 days, **demote to Tier 1** with warning: "DeepSeek validation expired. Demoting to Tier 1."
    - If `external_review_status == FAILED` or `EXPIRED`, **block**: "DeepSeek validation failed. Not available."
    - If `external_review_status == NOT_REQUIRED`, **block**: "DeepSeek requires external validation before Tier 2+ dispatch."
    - If `external_review_required == True` but no `external_review_evidence`, **block**: "DeepSeek validation evidence missing."

**Action on block:** Return error to Prime: "DeepSeek route validation incomplete. Not available for this tier."

---

### 7. Aggregator Authority Gate

**Trigger:** `trust_mode == AGGREGATOR` and evidence of proof/trust metadata.

**Gate logic:**
- If `trust_mode == AGGREGATOR` and `risk_tier >= 3`, **block** unconditionally: "Aggregator routes not allowed for Tier 3+."
- If `trust_mode == AGGREGATOR` and `risk_tier <= 2`:
  - For Tier 2: **Allow only if proof_strength is EXPLICIT (code review + metadata)** and `selected_model` is known before dispatch.
  - For Tier 0-1:
    - If `proof_strength == WEAK` (telemetry only), **allow with warning**: "Aggregator route for Tier 0-2 exploration only."
    - If `proof_strength == NONE`, **block**: "Aggregator route with no proof. Not allowed."
- **All aggregator routes must show actual selected model/vendor to Bifrost before dispatch.** If selected model is unknown, **block**: "Aggregator route model not resolved. Cannot dispatch."

**Action on block:** Return error to Prime: "Aggregator route not authorized for this risk tier."

---

### 8. Account/Session Risk Gate

**Trigger:** `route_class == account_session`.

**Gate logic:**
- If `route_class == account_session`:
  - If `account_risk_level` is missing, assume `UNKNOWN` and **demote to Tier 1**.
  - If `account_risk_level == HIGH` and `risk_tier >= 2`, **block**: "Account risk level high for this tier."
  - If `account_risk_level == STANDARD` or `LOW`, gate passes.
  - If `session_health_status` is `POLLUTED | STALE | WRONG_PROJECT`, **block** and return error: "Session context invalid. Start fresh session."

**Action on block:** Return error to Prime: "Account/session route has risk or state issues. Use different route."

---

### 9. Cost Exposure Gate

**Trigger:** `cost_posture == PREMIUM` or `risk_tier == 4`.

**Gate logic:**
- If `cost_posture == PREMIUM` and `cost_justified` is not `True`:
  - If `risk_tier <= 1`, **allow with warning**: "Route is premium cost. Confirm use?"
  - If `risk_tier >= 2`, **block** unless user explicitly approves: "Premium cost route requires user approval for Tier 2+."
- If `risk_tier == 4` and `cost_pressure == QUOTA_LIMITED` or `EXHAUSTED`, **block**: "Account cost limit reached. Cannot route Tier 4 work."

**Action on block:** Return error to Prime: "Cost exposure not justified or limit reached. Route blocked."

---

## Per-Tier Gate Enforcement

| Tier | Active Gates | Key Decisions |
|---|---|---|
| Tier 0 | Route Class, Model ID (optional), Proof (none) | No model call. Return immediately. |
| Tier 1 | Route Class, Model ID (optional), Proof (telemetry), DeepSeek (Tier 0-1), Aggregator OK, Cost Exposure (warning) | Single lane OK. Account/session preferred. No silent fallback. |
| Tier 2 | Route Class, Exact Model ID, Proof (code review), DeepSeek (requires PASSED), Aggregator OK (with proof), Account/Session Risk, Cost Exposure (approval needed), Unsafe Fallback | Single or dual lane. Aggregator allowed with explicit proof. Account/session preferred. Review required. |
| Tier 3 | All gates active | Dual-lane required (waiver only). Direct API only for Tier 3+. No aggregator. External review required for new providers. |
| Tier 4 | All gates active + Human Gate | Human approval required before dispatch. Direct API only. Strongest proof required. Dual review mandatory. No fallback without explicit waiver. |

---

## Gating Examples

### Example 1: Routine Planning (Tier 1)

- **Input:** Prime asks to plan a feature. Risk tier = 1.
- **Relay chooses:** DeepSeek direct, `q_mode_flat = True`, cost = MINIMAL, route_class = `direct_api`.
- **Aegis gates:**
  1. Route Class: `direct_api` ✓ allowed.
  2. Model ID: `deepseek-v4-pro` ✓ versioned.
  3. Proof Required: `telemetry` ✓ acceptable for Tier 1.
  4. Unvalidated DeepSeek: `external_review_status = PENDING` ✓ allowed for Tier 1 with warning.
  5. Cost Exposure: `cost_posture = MINIMAL` ✓ no approval needed.
- **Result:** Route allowed with warning: "DeepSeek validation pending. Limited to Tier 1."

### Example 2: Code Build (Tier 3)

- **Input:** Prime building a feature. Risk tier = 3.
- **Relay chooses:** Dual lane: primary = `openai/gpt-5-3-codex`, secondary = `claude-sonnet-4-6`, both direct API.
- **Aegis gates:**
  1. Route Class: `direct_api` ✓ for both lanes.
  2. Model ID: Both versioned ✓.
  3. Proof Required: `code_review` ✓ required for Tier 3.
  4. Tier 3 Dual-Lane: `dual_lane_required = True` ✓.
  5. Different families: OpenAI + Claude ✓.
  6. DeepSeek: Not in use ✓.
  7. Aggregator: Not in use ✓.
  8. Account/Session: Not primary route for Tier 3 code ✓.
  9. Cost Exposure: `cost_posture = STANDARD` ✓ no special approval.
- **Result:** Both lanes allowed. Code review proof required before commit.

### Example 3: Settings Change (Tier 4)

- **Input:** User changing account/billing. Risk tier = 4.
- **Relay chooses:** `claude-opus-4-8` direct API with human gate.
- **Aegis gates:**
  1. Route Class: `direct_api` ✓.
  2. Model ID: Versioned ✓.
  3. Proof Required: `human_gate | security_review` ✓ required for Tier 4.
  4. Cost Exposure: Not relevant for settings ✓.
  5. **Human Gate:** `human_gate_required = True` ✓.
- **Result:** Route allowed, but **requires user button-click approval before dispatch**. Prime waits for Scott to confirm.

---

## Stop Conditions for Aegis Block

Aegis blocks unconditionally (no waiver, no demotion) when:

1. `route_class` is unknown or missing.
2. `model_id` is missing for Tier 2+.
3. `risk_tier == 3` and `dual_lane_required == False` (except with explicit waiver in decision record).
4. `proof_required` is missing or unknown for the tier.
5. `fallback_allowed == True` and blocker is `silent_fallback`.
6. `provider == deepseek` and `trust_mode != DIRECT` (aggregator DeepSeek not allowed).
7. `provider == deepseek` and `external_review_status == FAILED | NOT_REQUIRED`.
8. `trust_mode == AGGREGATOR` and `risk_tier >= 3`.
9. `account_risk_level == HIGH` and `risk_tier >= 2`.
10. `session_health_status` is `POLLUTED | STALE | WRONG_PROJECT` and `route_class == account_session`.
11. Route has `blocked_authorities` entries (from ModelTrustState).
12. Relay cannot explain the selection or provide evidence.

---

## Aegis Decision Record Output

When Aegis validates a Relay route, it produces:

```text
route_validation_id
timestamp
relay_route_class
primary_model_id
secondary_model_id (if dual-lane)
risk_tier
gates_passed (list)
gates_failed (list)
gates_demoted_to (list)
gates_requiring_human_approval (list)
final_dispatch_decision (allow | demote_to_tier | block)
block_reason (if blocked)
demotion_reason (if demoted)
warning_messages (list)
proof_requirements (list)
bifrost_display_fields (model, vendor, trust, cost, payload, warning_state)
```

If any gate fails, the entire route is blocked unless explicitly waived in the decision record.

---

## Integration with Relay

Relay must provide Aegis with:

- `route_class` (account_session | local_cli | direct_api | aggregator_api)
- `primary_model_id` and `secondary_model_id` (if dual-lane)
- `risk_tier` (0-4)
- `proof_required` (none | telemetry | artifact | code_review | security_review | human_gate)
- `dual_lane_required` (bool)
- `fallback_allowed` (bool)
- `fallback_blockers` (list of risk flags if allowed)
- `cost_justified` (bool if cost_posture == PREMIUM)
- `human_gate_required` (bool)
- `waiver_record` (optional, see Waiver/Approval Records below)
- `approval_record` (optional, see Waiver/Approval Records below)

Model Harness must provide:

- `ProviderCapability` (via `model_adapter.py`)
- `ModelTrustState` (via `model_adapter.py`)
- `AllowedTaskTypes` (via `model_adapter.py`)

Aegis gates the route using all three sources.

---

## Waiver/Approval Records

When gates allow demotion or conditional passage via waiver or approval, Relay/Aegis must capture evidence:

### Waiver Record (for policy exceptions)

```json
{
  "waiver_id": "unique identifier",
  "actor": "email or system identity authorizing waiver",
  "scope": "gate name or condition being waived",
  "timestamp": "ISO 8601 when waiver was recorded",
  "reason": "explicit justification for waiver",
  "expiration": "ISO 8601 if waiver is time-limited (optional)",
  "evidence_url": "link to decision record or bug ID (optional)"
}
```

### Approval Record (for user consent)

```json
{
  "approval_id": "unique identifier",
  "actor": "email or system identity approving",
  "scope": "gate name or condition requiring approval",
  "timestamp": "ISO 8601 when approval was recorded",
  "reason": "brief summary of what user approved",
  "expiration": "ISO 8601 if approval is time-limited or request-scoped (optional)"
}
```

### Validation Rules

- Bare boolean flags (has_waiver: true) are **not acceptable**. All waivers/approvals must include actor, scope, timestamp, and reason.
- Waivers with expired timestamps must be treated as void.
- Approval records are route-request scoped (single-use by default) unless expiration is explicitly set.
- Aegis records both waiver_record and approval_record in its decision output for audit trail.

---

## Next Steps

After this contract lands:

1. Build 1 implements `ProviderCapability`, `ModelTrustState`, `AllowedTaskTypes` in `meridian_core/model_adapter.py`.
2. Aegis runtime (`meridian_core/aegis.py`) implements gate logic using this contract.
3. Relay (`meridian_core/relay.py`) supplies route metadata to Aegis for validation before dispatch.
4. Tests in `tests/test_aegis.py` validate every gate condition and block/allow/demotion decision.
5. Bifrost displays gate status, warnings, and proof requirements to Scott.
