# DeepSeek Direct-Provider Adapter — Implementation Handoff

**Status:** Ready for Build 1 runtime lane
**Author:** Build 4 (Opus high-level thinking)
**Source contract:** `docs/model-harness-v2-contract.md` (landed, Codex-reviewed)
**Supporting docs:** `docs/deepseek-provider-validation-gate.md`, `docs/deepseek-validation-benchmark-plan.md`
**Audience:** Build 1 (primary runtime lane), Scott, future contributors
**Purpose:** Bounded implementation handoff for wiring DeepSeek as a direct-provider adapter through Relay and Aegis — covering environment variables, trust state, snapshot evidence, Q-mode flatness, blocked authorities, tests expected, and the runtime files touched.

This document does **not** implement code. It specifies exactly what Build 1 must build, where, and why. All metadata values are drawn from the normative defaults in the Model Harness V2 contract.

---

## 1. Environment Variables

Build 1 must wire the following environment variable for the DeepSeek direct adapter. No other env vars are needed for the V2 direct route.

| Variable | Required | Purpose |
|---|---|---|
| `DEEPSEEK_API_KEY` | Yes | DeepSeek API bearer token. Validated before any live call. Must not appear in logs, telemetry, error messages, or prompt context. |

**Validation rule:** the adapter calls `require_api_key()` before any HTTP call and raises `ModelAdapterConfigError` if the variable is missing or empty. This follows the existing pattern in `HttpModelAdapterConfig.require_api_key()`.

**No other env vars.** The endpoint URL, model name, and provider name are declared in the metadata dataclasses (see §4), not in the environment. DeepSeek does not have a per-org key, a project key, or a separate endpoint selection env var in the V2 direct configuration.

---

## 2. Direct-Provider Endpoint

The adapter connects to the DeepSeek chat completions API directly — not through OpenRouter or any other aggregator.

| Field | Value |
|---|---|
| Endpoint URL | `https://api.deepseek.com/v1/chat/completions` |
| HTTP method | POST |
| Auth header | `Authorization: Bearer {DEEPSEEK_API_KEY}` |
| Content-Type | `application/json` |
| Request body shape | `{"model": "deepseek-chat", "messages": [...], "temperature": 0, "stream": false}` |

**Direct-vs-aggregator proof:** Build 1 must hardcode this endpoint in the adapter metadata — not derived from env vars, not configurable at dispatch time. If the endpoint does not match `https://api.deepseek.com/v1/chat/completions`, the adapter is not a direct DeepSeek adapter. The metadata `trust_mode` must be `DIRECT` (not `AGGREGATOR`) and `direct_api_endpoint` must equal this URL exactly. Relay and Aegis read these fields at dispatch time; any mismatch is treated as a route mismatch and the dispatch is blocked.

**Why this matters:** the aggregator route (e.g., OpenRouter) cannot provide payload snapshot hashes, cannot guarantee Q-mode flatness (the aggregator may add or strip context), and has `blocked_authorities = ("aggregator-without-proof",)`. The direct route is the only path to external review clearance and Tier 2+ dispatch.

---

## 3. Candidate Trust State

DeepSeek starts in **candidate provider** state (validation Level 0). This is declared in `ModelTrustState`:

| Field | Value | Rationale |
|---|---|---|
| `trust_mode` | `DIRECT` | Hardcoded endpoint = direct API only |
| `direct_api_endpoint` | `"https://api.deepseek.com/v1/chat/completions"` | Fixed, non-configurable |
| `proof_strength` | `WEAK` | No external review has passed yet |
| `external_review_required` | `True` | Codex or PQA must validate the route before Tier 3+ |
| `external_review_status` | `PENDING` | Review requested but not yet completed |
| `external_review_evidence` | `None` | Will be populated when review passes |
| `blocked_authorities` | `()` | Empty — no active blocks. Gated by `external_review_required` instead |
| `last_validated_at` | `None` | Not yet validated |

**Tier gating effect:** With `proof_strength = WEAK` and `external_review_required = True`:

- **Tier 0:** Allowed (no model call)
- **Tier 1:** Allowed (SINGLE_LANE, low-risk reversible)
- **Tier 2:** **Blocked** — Tier 2 requires `proof_strength >= WEAK` but also requires `external_review_status = PASSED` when `external_review_required` is True. DeepSeek is `PENDING`, so Aegis blocks Tier 2 dispatch with error tag `"external_review_required"`.
- **Tier 3+: Blocked** — requires `DIRECT` + `>= STANDARD` proof. DeepSeek is `WEAK`.

**Promotion path:** When the DeepSeek validation benchmark (Rounds 0–4) passes and an independent Codex review records a PASSED verdict, `external_review_status` is promoted to `PASSED`, `proof_strength` is upgraded to `STANDARD` (or `STRONG` if the review quality warrants it), and `external_review_evidence` is populated with the review commit hash. At that point, Tier 2 dispatch becomes available.

---

## 4. Metadata Declaration (Exact Values)

### 4.1 `ProviderCapability`

```python
ProviderCapability(
    provider="deepseek",
    model="deepseek-chat",
    context_window_tokens=65536,
    max_output_tokens=8192,
    cost_posture=CostPosture.MINIMAL,
    latency_tier=LatencyTier.NORMAL,
    supports_streaming=True,
    tokenizer_family="deepseek",
    supports_thinking=False,
    supports_vision=False,
    q_mode_flat=True,             # ← critical: enables Q-mode self-verification
    known_authorities=("deepseek-official-endpoint", "direct-api-only"),
)
```

### 4.2 `ModelTrustState`

```python
ModelTrustState(
    provider="deepseek",
    model="deepseek-chat",
    trust_mode=TrustMode.DIRECT,
    direct_api_endpoint="https://api.deepseek.com/v1/chat/completions",
    proof_strength=ProofStrength.WEAK,
    external_review_required=True,
    external_review_status=ExternalReviewStatus.PENDING,
    external_review_evidence=None,
    blocked_authorities=(),
    last_validated_at=None,
)
```

### 4.3 `AllowedTaskTypes`

```python
AllowedTaskTypes(
    provider="deepseek",
    model="deepseek-chat",
    allowed_action_types=(CognitionActionType.VERIFY, CognitionActionType.EXPLAIN),
    blocked_action_types=(CognitionActionType.BUILD, CognitionActionType.REVIEW, CognitionActionType.RELEASE, CognitionActionType.DESTRUCTIVE),
    max_risk_tier=2,    # effective Tier 1 until external review passes
    reason=(
        "DeepSeek is a V2 verification lane only. Q-mode flatness (q_mode_flat=True) "
        "makes it suitable for deterministic output validation and explanation but not "
        "for creative building or subjective reviewing. Capped at Tier 2; Tier 2+ "
        "requires external review PASSED, which upgrades proof_strength to STANDARD."
    ),
)
```

**Note on action type mismatch:** The contract lists `PLAN` and `REPAIR` as blocked for DeepSeek, but the runtime `CognitionActionType` enum in `cognition_policy.py` does not currently have `PLAN` or `REPAIR` members — it has `LOCAL_LOGIC`, `BUILD`, `REVIEW`, `VERIFY`, `RELEASE`, `DESTRUCTIVE`. The handoff uses only existing enum members. If the contract's `PLAN` and `REPAIR` action types are added later, `AllowedTaskTypes.blocked_action_types` should be updated to include them. This is noted as a cross-boundary gap — see §9.

### 4.4 `TelemetryCapability`

```python
TelemetryCapability(
    supports_completion_tokens=True,
    supports_latency_ms=True,
    supports_payload_snapshot=True,
    supports_response_hash=True,
)
```

All four fields are `True` for the direct route. DeepSeek's API returns `usage.completion_tokens` and `usage.prompt_tokens` in its response object, enabling both token count telemetry and snapshot hashing.

---

## 5. Prompt Payload Snapshot Evidence

### 5.1 Why Snapshots Work for DeepSeek Direct

DeepSeek's API is a plain HTTP endpoint — Relay controls the entire request body. This means:

1. **Outbound hash:** Relay serializes the `PromptPacket.serialized_prompt`, computes SHA-256 of the exact string sent to DeepSeek, and records it as `prompt_payload_snapshot_hash`.
2. **Inbound hash:** Relay receives the raw response body, extracts the model text, computes SHA-256 of the response text, and records it as `response_payload_snapshot_hash`.

Both are possible because there is no intermediary between Relay and DeepSeek's API. Aggregator routes cannot do this — the aggregator may modify, cache, or proxy the request/response.

### 5.2 Hashes in `PromptDragTelemetry`

When `adapter_supports_snapshot` is `True`, the telemetry record carries:

- `prompt_payload_snapshot_hash` — SHA-256 of the outbound serialized prompt
- `response_payload_snapshot_hash` — SHA-256 of the inbound model response text
- `adapter_supports_snapshot` — `True`

### 5.3 Audit Trail Capability

The Review Console can later:
1. Reconstruct the exact `PromptPacket.serialized_prompt` from logs.
2. Recompute SHA-256.
3. Compare against `prompt_payload_snapshot_hash` in the telemetry record.
4. Flag any mismatch as a potential prompt-tampering event.

This is an audit capability, not a real-time gate. Missing snapshots are not dispatch blockers but are surfaced to Beacon and flagged in Review Console.

### 5.4 Implementation Notes

- The SHA-256 hashing should use Python's `hashlib.sha256()` on the UTF-8 encoded string.
- The hash should be computed on the exact string passed to the HTTP POST body, not on a pre-serialization object.
- The response hash should be computed on the extracted `.text` or `.content` field, not on the full JSON response envelope.
- Both hashes should be hex-encoded strings (64 characters).

---

## 6. Q-Mode Flatness Proof

### 6.1 What Q-Mode Flatness Means

DeepSeek with `temperature=0` is Q-mode flat: given the same prompt twice, it produces the same output twice. Claude is not Q-mode flat — even with temperature=0, Claude may produce different phrasings.

### 6.2 Adapter Requirements

The DeepSeek adapter must:

1. **Always set `temperature=0`** for Q-mode-flat verification calls. The contract specifies this is the only temperature value permitted for `VERIFY` action types dispatched to DeepSeek.
2. **Never cache responses** across calls — each verification call must be a fresh API request.
3. **Set `stream=false`** — streaming responses cannot be byte-compared.
4. **Report `q_mode_flat = True`** in `ProviderCapability`.
5. **Report `supports_payload_snapshot = True`** and `supports_response_hash = True` in `TelemetryCapability`.

If any of these cannot be guaranteed, `q_mode_flat` must be set to `False`.

### 6.3 How Aegis Uses It

When `q_mode_flat = True` and `action_type = VERIFY`:

1. Aegis dispatches the same prompt twice (dual-lane Q-proof).
2. Compares the two responses byte-for-byte.
3. If responses match → `PromiseState` upgraded to `KEPT`.
4. If responses differ → route flagged for Review Console, `proof_strength` downgraded.

This is the only Meridian case where dual-lane dispatch uses the *same* model for both lanes — Q-mode flatness serves as self-verification.

### 6.4 Implementation Notes

- The dual-lane dispatch for Q-proof is an Aegis concern, not an adapter concern. The adapter only needs to ensure temperature=0, no caching, no streaming.
- Build 1 should add a `_deepseek_request_body()` helper that constructs the JSON body with `temperature=0` and `stream=false` hardcoded for VERIFY calls. For EXPLAIN calls, temperature may remain 0 but streaming could be enabled if the Bifrost UI expects it.

---

## 7. Blocked Authorities and Dispatch Gating

### 7.1 Current State

DeepSeek direct has `blocked_authorities = ()` — no active blocks. The gate is `external_review_required = True` with `external_review_status = PENDING`.

### 7.2 Dispatch Resolution Flow (DeepSeek-specific)

When Relay receives a dispatch request for `model="deepseek-chat"`:

1. `AdapterRegistry.resolve_metadata("deepseek-chat")` returns the four-tuple.
2. **Action type check:** If `action_type` is in `blocked_action_types` (BUILD, REVIEW, RELEASE, DESTRUCTIVE), dispatch fails with `"blocked_task_type"`.
3. **Tier check:** If `risk_tier > max_risk_tier` (2), dispatch fails with `"risk_tier_exceeded"`.
4. **Trust check:** `trust_mode == DIRECT` → passes. `blocked_authorities` is empty → passes.
5. **External review check:** `external_review_required == True` AND `external_review_status != PASSED` → dispatch fails with `"external_review_required"`.
6. **Proof strength check:** If tier >= 3, requires `>= STANDARD`. DeepSeek is `WEAK` → fails with `"insufficient_proof_strength"`.

**Net effect:** DeepSeek direct is dispatchable at Tier 1 only, for VERIFY and EXPLAIN action types only, until external review passes.

### 7.3 What Happens When External Review Passes

When `external_review_status` is promoted to `PASSED` and `proof_strength` is upgraded to `STANDARD`:

- Tier 2 dispatch becomes available (VERIFY + EXPLAIN).
- Tier 3+ still blocked (requires `>= STANDARD`, which is now met, but `AllowedTaskTypes.blocked_action_types` still excludes BUILD and REVIEW).
- The `allowed_action_types` tuple may be expanded by a later contract update, but that is out of scope for this handoff.

### 7.4 Aggregator Route Comparison

For reference, the DeepSeek aggregator route (if ever registered) would have:

- `trust_mode = AGGREGATOR`
- `direct_api_endpoint = None`
- `proof_strength = WEAK`
- `blocked_authorities = ("aggregator-without-proof",)`
- `allowed_action_types = (EXPLAIN,)` only
- `max_risk_tier = 1`
- `TelemetryCapability` all `False` except `supports_latency_ms`

This route is blocked by `blocked_authorities` being non-empty at dispatch time, regardless of tier.

---

## 8. Tests Expected

Build 1 must write the following tests in `tests/test_model_adapter.py`. These are the metadata-specific tests; transport tests (HTTP POST, auth header, response parsing) are separate and follow existing `HttpJsonModelAdapter` test patterns.

### 8.1 Metadata Construction Tests

| Test | What It Proves |
|---|---|
| `test_deepseek_provider_capability_defaults` | `ProviderCapability` for DeepSeek direct matches the normative values in §4.1 |
| `test_deepseek_trust_state_defaults` | `ModelTrustState` for DeepSeek direct matches the normative values in §4.2 |
| `test_deepseek_allowed_task_types_defaults` | `AllowedTaskTypes` for DeepSeek direct matches §4.3 |
| `test_deepseek_telemetry_capability_defaults` | `TelemetryCapability` is all `True` for the direct route |
| `test_deepseek_metadata_immutable` | All four metadata dataclasses are frozen (attempted mutation raises) |

### 8.2 Registration Tests

| Test | What It Proves |
|---|---|
| `test_register_deepseek_metadata` | `register_metadata("deepseek-chat", ...)` succeeds and `resolve_metadata("deepseek-chat")` returns the correct four-tuple |
| `test_resolve_unregistered_metadata_raises` | `resolve_metadata` for an unregistered model raises `MissingAdapterError` |
| `test_register_metadata_with_missing_field_raises` | Partial registration (missing one of the four structures) raises at construction time |
| `test_registry_invariant_metadata_without_adapter` | Model with metadata but no adapter raises at startup validation |
| `test_registry_invariant_adapter_without_metadata` | Model with adapter but no metadata raises at startup validation |

### 8.3 Gating Tests

| Test | What It Proves |
|---|---|
| `test_deepseek_blocks_build_action` | Dispatch with `BUILD` action type to DeepSeek returns `"blocked_task_type"` |
| `test_deepseek_blocks_review_action` | Dispatch with `REVIEW` action type to DeepSeek returns `"blocked_task_type"` |
| `test_deepseek_allows_verify_at_tier_1` | Dispatch with `VERIFY` at Tier 1 succeeds |
| `test_deepseek_allows_explain_at_tier_1` | Dispatch with `EXPLAIN` at Tier 1 succeeds |
| `test_deepseek_blocks_tier_2_without_review` | Dispatch at Tier 2 fails with `"external_review_required"` when `external_review_status = PENDING` |
| `test_deepseek_blocks_tier_3` | Dispatch at Tier 3 fails with `"insufficient_proof_strength"` when `proof_strength = WEAK` |
| `test_deepseek_blocks_unknown_trust` | Dispatch with `trust_mode = UNKNOWN` fails with `"unknown_trust_route"` |
| `test_deepseek_blocks_when_blocked_authorities_nonempty` | Dispatch with non-empty `blocked_authorities` fails with `"blocked_authority"` |
| `test_deepseek_allows_tier_2_when_review_passed` | Dispatch at Tier 2 succeeds when `external_review_status = PASSED` and `proof_strength = STANDARD` |

### 8.4 Q-Mode Flatness Tests

| Test | What It Proves |
|---|---|
| `test_deepseek_q_mode_flat_identical_prompts` | Two DeepSeek calls with the same prompt and temperature=0 produce byte-identical output (uses `FakeModelAdapter` with deterministic response) |
| `test_deepseek_q_mode_flat_flag_true` | `ProviderCapability.q_mode_flat` is `True` for DeepSeek direct |
| `test_deepseek_temperature_zero_enforced` | Adapter request body includes `"temperature": 0` for VERIFY calls |

### 8.5 Snapshot Tests

| Test | What It Proves |
|---|---|
| `test_deepseek_payload_snapshot_hash_populated` | `PromptDragTelemetry` from a successful DeepSeek dispatch has non-null `prompt_payload_snapshot_hash` |
| `test_deepseek_response_snapshot_hash_populated` | `PromptDragTelemetry` from a successful DeepSeek dispatch has non-null `response_payload_snapshot_hash` |
| `test_deepseek_snapshot_hash_matches_prompt` | Recomputing SHA-256 of the sent prompt matches the recorded hash |

### 8.6 Telemetry Tests

| Test | What It Proves |
|---|---|
| `test_deepseek_telemetry_fields_populated` | `PromptDragTelemetry` from a successful dispatch has non-null token counts, latency, budget compliance |
| `test_deepseek_telemetry_trust_snapshot` | `trust_mode_at_dispatch` and `proof_strength_at_dispatch` match the registered metadata values at time of call |

Tests follow existing patterns in `tests/test_model_adapter.py`. Use `FakeModelAdapter` for deterministic responses; use `HttpJsonModelAdapter` with an injected `http_post` for transport-level tests.

---

## 9. Runtime Files to Touch

This section names every file Build 1 must create or modify, the change type, and what goes in each file. Files are listed in dependency order — earlier files are imported by later files.

### 9.1 `meridian_core/model_adapter.py` — MODIFY

**What to add (after the existing `ModelAdapterConfigError` class, before `ModelAdapterConfig`):**

1. **New enums:** `TrustMode`, `ProofStrength`, `ExternalReviewStatus`, `LatencyTier`
2. **New dataclasses (all frozen):**
   - `ProviderCapability` — 14 fields as defined in the contract §55–70
   - `ModelTrustState` — 11 fields as defined in the contract §78–88
   - `AllowedTaskTypes` — 6 fields as defined in the contract §95–101
   - `TelemetryCapability` — 4 fields as defined in the contract §127–131
3. **New dataclass (not frozen):** `PromptDragTelemetry` — 14 fields as defined in the contract §108–123
4. **New methods on `AdapterRegistry`:**
   - `register_metadata(self, model, capability, trust, allowed, telemetry) -> AdapterRegistry`
   - `resolve_metadata(self, model) -> tuple[ProviderCapability, ModelTrustState, AllowedTaskTypes, TelemetryCapability]`
5. **Internal storage:** `self._metadata: Mapping[str, tuple]` analogous to `self._by_model`

Imports needed: `hashlib` (for SHA-256), additional fields from existing enums (`CostPosture` from `relay.py`, `CognitionActionType` from `cognition_policy.py` — handle circular imports via `TYPE_CHECKING` or local imports).

**Existing types are unchanged.** No modification to `ModelAdapter`, `ModelAdapterConfig`, `HttpModelAdapterConfig`, `FakeModelAdapter`, `EnvConfiguredModelAdapter`, `HttpJsonModelAdapter`, or the existing `register_model`/`register_role_default`/`resolve` methods.

### 9.2 `meridian_core/relay.py` — MODIFY

**What to add:**

1. **`LatencyTier` enum** (if not placed in `model_adapter.py`): `IMMEDIATE`, `FAST`, `NORMAL`, `SLOW`, `UNKNOWN`
2. **`CostPosture` enum already exists** with `MINIMAL`, `STANDARD`, `THOROUGH`. The contract adds `PREMIUM` as a normative value for Claude. If Build 1 wants strict contract compliance, add `PREMIUM` to the enum. If not, map `PREMIUM` to `THOROUGH` in the adapter metadata.

**Decision for Build 1:** Add `PREMIUM` to `CostPosture` or document the deviation from the contract. The handoff recommends adding it — it's a one-line enum addition.

### 9.3 `meridian_core/cognition_policy.py` — MODIFY (optional)

**Gap noted:** The contract lists `PLAN` and `REPAIR` as `CognitionActionType` values used in `AllowedTaskTypes`, but the runtime enum has `LOCAL_LOGIC`, `BUILD`, `REVIEW`, `VERIFY`, `RELEASE`, `DESTRUCTIVE`. Build 1 has two options:

- **Option A (recommended):** Add `PLAN` and `REPAIR` to `CognitionActionType` (and `EXPLAIN` if not already present). This aligns the runtime with the contract.
- **Option B:** Skip for now. The DeepSeek `AllowedTaskTypes` uses only existing members (`VERIFY`, `EXPLAIN`), so the handoff is not blocked. File a cross-boundary gap task for the contract-enum mismatch.

If Option A is chosen, enum members: `LOCAL_LOGIC`, `BUILD`, `REVIEW`, `VERIFY`, `RELEASE`, `DESTRUCTIVE`, `EXPLAIN`, `PLAN`, `REPAIR`.

Note: `CognitionActionType.EXPLAIN` is referenced in the contract but not present in the runtime enum. Check `cognition_policy.py` — if absent, this is a gap for *all* providers, not just DeepSeek.

### 9.4 `meridian_core/relay_dispatch.py` — MODIFY

**What to add:**

A dispatch gating function that wraps `AdapterRegistry.resolve_metadata()` and enforces the dispatch resolution flow from the contract §188–203:

```python
def gate_dispatch(
    registry: AdapterRegistry,
    model: str,
    action_type: CognitionActionType,
    risk_tier: int,
) -> tuple[bool, str]:
    """Return (allowed, reason). If allowed is False, reason is the error tag."""
```

The function must:
1. Call `registry.resolve_metadata(model)` to get the four-tuple.
2. Check `action_type` against `allowed_action_types` and `blocked_action_types`.
3. Check `risk_tier` against `max_risk_tier`.
4. Check `trust_mode` — `UNKNOWN` blocks unconditionally.
5. Check `blocked_authorities` — non-empty blocks unconditionally.
6. Check `external_review_required` and `external_review_status`.
7. Check `proof_strength` against tier-based requirements per the contract's Tier-Based Gating table.

Error tags: `"blocked_task_type"`, `"disallowed_task_type"`, `"risk_tier_exceeded"`, `"blocked_authority"`, `"unknown_trust_route"`, `"external_review_required"`, `"external_review_expired"`, `"external_review_failed"`, `"insufficient_proof_strength"`.

### 9.5 `meridian_core/relay_executor.py` — MODIFY

**What to add:**

1. Integrate `gate_dispatch()` into the execution flow — before calling any model, gate the dispatch through metadata.
2. After a successful model call, produce `PromptDragTelemetry`:
   - `prompt_tokens` from `PromptPacket`
   - `completion_tokens` from adapter response metadata (or estimate if unavailable)
   - `latency_ms` from wall-clock timing
   - `budget_compliant` from budget validation
   - `trust_mode_at_dispatch`, `proof_strength_at_dispatch`, `external_review_status_at_dispatch` snapshotted from metadata at dispatch time
   - `prompt_payload_snapshot_hash` — computed via SHA-256 of the serialized prompt
   - `response_payload_snapshot_hash` — computed via SHA-256 of the response text
   - `adapter_supports_snapshot` from `TelemetryCapability`
   - `errors` tuple — populated with any error tags from gating or transport failures
3. The `RelayExecutionResult` may need a `telemetry: PromptDragTelemetry | None` field.

### 9.6 `meridian_core/aegis.py` — MODIFY

**What to add:**

1. A `QModeFlatnessVerifier` or similar utility that:
   - Receives two model call results from the same DeepSeek dispatch
   - Compares byte-for-byte
   - Returns `(is_flat: bool, reason: str)`
2. Integration of Q-mode flatness into the `PromiseState` / proof trail system — when a VERIFY action is dispatched to a `q_mode_flat = True` model and dual-lane results match, upgrade the proof state.
3. A `blocked_authorities` check in the existing Aegis gate path.

### 9.7 `tests/test_model_adapter.py` — MODIFY

Add all tests listed in §8. Follow existing patterns:
- Use `FakeModelAdapter` for deterministic responses.
- Use `AdapterRegistry` builder pattern (`registry.register_model(...).register_metadata(...)`).
- Test frozen dataclass immutability with `pytest.raises(FrozenInstanceError)` or equivalent.
- Test error paths before happy paths.

### 9.8 New files: NONE

No new files are required. All additions fit within the existing module structure:
- Metadata dataclasses → `model_adapter.py` (the adapter boundary)
- Dispatch gating → `relay_dispatch.py` (dispatch orchestration)
- Telemetry production → `relay_executor.py` (execution boundary)
- Q-mode verification → `aegis.py` (proof harness)

---

## 10. Cross-Boundary Gaps Noted

Build 1 should be aware of these gaps but is not required to resolve them in the DeepSeek direct adapter work. They are filed here for later lanes or upstream contract updates.

| Gap | Where | Severity |
|---|---|---|
| `CognitionActionType` missing `EXPLAIN`, `PLAN`, `REPAIR` | `cognition_policy.py` vs. contract | MEDIUM — `EXPLAIN` is needed for DeepSeek `AllowedTaskTypes`; `PLAN`/`REPAIR` are needed for OpenAI `blocked_action_types` |
| `CostPosture` missing `PREMIUM` | `relay.py` vs. contract | LOW — Claude's normative `cost_posture` is `PREMIUM` but the runtime enum has `MINIMAL`/`STANDARD`/`THOROUGH` |
| `TrustMode`/`ProofStrength`/`ExternalReviewStatus` not yet defined | `model_adapter.py` vs. contract | BLOCKING — these enums are required by the metadata dataclasses; this handoff assumes Build 1 creates them |
| `LatencyTier` not yet defined | `relay.py` or `model_adapter.py` | BLOCKING — required by `ProviderCapability` |
| `PromptDragTelemetry` not yet defined | `model_adapter.py` vs. contract | BLOCKING — required by relay executor telemetry production |

The three BLOCKING gaps are resolved by the work in this handoff — they are the enums and dataclasses Build 1 will create.

---

## 11. What This Handoff Does NOT Cover

- **HTTP transport implementation** for `POST` to `https://api.deepseek.com/v1/chat/completions` — follows existing `_stdlib_http_post` or `HttpJsonModelAdapter` patterns. Adapt the request body shape for DeepSeek's chat completions format.
- **DeepSeek SDK integration** — V2 uses stdlib HTTP only, no vendor SDKs.
- **Streaming response handling** — the adapter sets `stream=false` for all VERIFY calls. EXPLAIN calls may use streaming later; out of scope for initial wiring.
- **DeepSeek API error handling** — rate limits, auth failures, model overload. Follow existing `ModelAdapterConfigError` patterns.
- **Aggregator route** — this handoff is for the direct route only. The aggregator route is a separate adapter registration.
- **Bifrost/Balance UI** — displaying trust state, Q-mode status, and telemetry in the UI is a separate feature task.
- **Codex Review integration** — the review lane reads metadata from the registry; no changes needed to the adapter for that.
- **External review execution** — this handoff describes the metadata state; the actual Codex/PQA review process is in `docs/deepseek-validation-benchmark-plan.md`.

---

## 12. Acceptance Criteria for Build 1

- [ ] `DEEPSEEK_API_KEY` env var is read and validated before any live call.
- [ ] DeepSeek direct adapter is registered with all four metadata structures matching the normative values in §4.
- [ ] `AdapterRegistry.resolve_metadata("deepseek-chat")` returns the correct four-tuple.
- [ ] Dispatch gating blocks BUILD/REVIEW/RELEASE/DESTRUCTIVE action types for DeepSeek.
- [ ] Dispatch gating blocks Tier 2+ until `external_review_status = PASSED`.
- [ ] Dispatch gating allows VERIFY and EXPLAIN at Tier 1.
- [ ] `PromptDragTelemetry` carries payload snapshot hashes for successful DeepSeek dispatches.
- [ ] Q-mode flatness: the adapter sets `temperature=0` and `stream=false` for VERIFY calls.
- [ ] All tests in §8 pass.
- [ ] No existing tests break.
- [ ] No runtime code outside the files listed in §9 is modified.
- [ ] Handoff is marked complete in `docs/live-build-4.md` with commit hash and files changed.

---

## 13. Handoff Provenance

- **Source contract:** `docs/model-harness-v2-contract.md` — all metadata values, enums, gating rules, and telemetry fields.
- **Supporting gate doc:** `docs/deepseek-provider-validation-gate.md` — validation ladder, initial allowed/disallowed use, routing metadata.
- **Benchmark plan:** `docs/deepseek-validation-benchmark-plan.md` — validation rounds, promotion rules, demotion triggers.
- **Runtime reference:** `meridian_core/model_adapter.py` — existing adapter boundary; `meridian_core/relay.py` — existing routing; `meridian_core/cognition_policy.py` — existing action types; `meridian_core/relay_executor.py` — existing execution boundary.
- **Written by:** Build 4 (Opus high-level thinking lane), 2026-06-01.
- **Commit:** to be recorded in Write/Completion Log after push.