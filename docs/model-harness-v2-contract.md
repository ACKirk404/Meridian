# Model Harness V2 Metadata Contract

**Status:** V2 first-wave contract — domain slice not yet implemented; runtime metadata surface to be added to `meridian_core/model_adapter.py` by Build 1 (or other runtime lane) after this contract lands.
**Owner harness:** Model Harness (provider boundary). Consumed by Relay, Aegis, Beacon.
**Owner lane (doc):** Build 4 (Opus high-level thinking).
**Audience:** Prime, Relay, Aegis, Beacon, Build 1 (runtime), Scott, future contributors.
**Purpose:** Define the metadata surface every provider adapter must expose so Relay can dispatch intelligently, Aegis can gate, and Beacon can report — without leaking credentials, internal transport state, or raw API responses into runtime context.

The Model Harness already has a clean boundary: adapters receive approved prompt payload text and return model text. But V2 needs more than text-in/text-out. Relay needs to know *who* answered, *how* they answered, *what* they cost, and *whether* the answer should be trusted at all. This contract defines that metadata surface.

---

## What This Contract Covers — and What It Excludes

This contract defines:

- **Provider capability metadata:** what each provider/model advertises about itself (context window, cost posture, latency tier, tokenizer compatibility, streaming support, Q-mode flatness).
- **Prompt-drag telemetry:** what Relay must measure and surface about every model call — token counts, latency, source lineage, budget compliance, and snapshot evidence.
- **Trust state:** how each provider adapter declares its audit standing (direct vs. aggregator, proof strength, external-review status, blocked authorities).
- **Route ownership:** how model routing decisions map to lane roles and risk tiers.
- **Allowed/blocked task types:** what work each model is permitted to do, declared by the adapter and enforced by Aegis.
- **Aegis/Relay policy binding:** how the metadata surface feeds Aegis gates and Relay dispatch decisions without ever passing raw API keys or transport state into the prompt context.

This contract does **not** define:

- Individual provider SDKs, transport implementations, or HTTP wire formats — those live inside adapter implementations and are invisible to Relay.
- DeepSeek-specific or OpenAI-specific credential management — the contract defines what the metadata surface looks like; adapter-specific env-var naming and transport details go in implementation handoffs.
- Prompt *content* or serialization format — that belongs to `PromptPacket`, `PromptBudgetPlan`, and Relay's prompt assembly.
- Federation, cross-Meridian provider sharing, or multi-user provider accounts — those are V3/horizon concerns.

---

## Harness Ownership

| Concern | Owner |
|---|---|
| Declare provider capability metadata | Model Harness (each adapter) |
| Declare trust state per provider/model | Model Harness (each adapter) |
| Measure and attach prompt-drag telemetry | Relay (consumes adapter metadata, enriches with runtime metrics) |
| Enforce allowed/blocked task types | Aegis (reads adapter metadata, gates dispatch) |
| Bind metadata to risk-tier dispatch rules | Relay + Aegis (joint) |
| Render provider status and trust to Scott | Bifrost (reads Beacon health + adapter metadata) |
| Report aggregate cost, latency, and trust posture | Beacon |
| Own provider credential lifecycle | Scott (env vars); adapters validate presence before any call |
| Route a model call to an adapter | Relay (via `AdapterRegistry.resolve`) |

The Model Harness owns the metadata *declaration*. Relay and Aegis own the metadata *enforcement*. No metadata field may be populated by Relay or Aegis on behalf of an adapter — the adapter must declare its own values.

Prime/Orchestrator may request an intent, role, risk tier, proof posture, or human-gate constraint. It does not own exact provider/model identity, prompt packet construction, payload fitting, fallback behavior, transport authorization, provider balance, or telemetry fields. Those remain Model Harness/Relay-owned and are exposed to Prime as source refs or display-safe evidence.

---

## GOAL / Intent Per Call

The Model Harness taxonomy includes **GOAL / Intent**, but this is not the same thing as Prime-level user intent analysis.

Prime-level intent answers: "What is Scott asking Meridian to do, why, for which project, and with what risk/proof posture?"

Model Harness per-call intent answers: "Given Prime's already-decided task, what is this single model call supposed to accomplish, and what constraints must Relay enforce while building and dispatching the prompt packet?"

Per-call intent is therefore a bounded dispatch field, not an orchestrator brain. It should be attached to Relay/Model Harness evidence as structured context for routing, payload construction, policy checks, telemetry, and later audit.

### Ownership Split

| Question | Owner |
|---|---|
| What did the user ask for? | Prime / Orchestrator |
| Which project/scope does it belong to? | Compass, consumed by Prime |
| Is this risky, proof-gated, or human-gated? | Aegis/Security, consumed by Prime and Relay |
| Should a model call happen? | Prime, via Relay request |
| What is this specific model call trying to do? | Relay + Model Harness per-call `goal` / `intent` |
| Which provider/model, payload, budget, fallback, and transport gate apply? | Relay + Model Harness |
| How is the result shown to Scott? | Bifrost |

### Per-Call Intent Shape

This contract does not require new backend names. If a future runtime object promotes this field, it should map to existing Relay/Model Harness records rather than creating taxonomy-derived classes directly.

A per-call intent record should be able to express:

- `requested_by`: source of the call request, usually `prime`.
- `prime_intent_ref`: stable ref to the Prime decision or interaction request.
- `project_ref`: Compass project/scope ref when applicable.
- `action_type`: Aegis/Prime action type such as `PLAN`, `BUILD`, `REPAIR`, `VERIFY`, or `EXPLAIN`.
- `call_goal`: concise objective for this one call.
- `expected_output_shape`: expected response form such as patch summary, finding list, score, classification, or explanation.
- `risk_tier`: Aegis risk tier at dispatch.
- `proof_requirement`: proof/evidence expectation for the call.
- `disallowed_outputs`: things the model must not return, such as raw secrets, raw prompt text, or unsupported branch actions.
- `payload_budget_ref`: PromptPacket/PromptBudgetPlan ref.
- `evidence_refs`: upstream refs from Prime, Compass, Aegis, Relay, or prior proof records.

### Examples

**Example 1: Repair request**

Prime-level intent:

```text
Scott wants the V2 checklist language corrected so model-call mechanics stay out of Prime.
Project: Meridian.
Risk: docs/runtime planning, low mutation risk.
Needed action: repair docs and verify doc-sensitive tests.
```

Per-call GOAL / Intent:

```text
call_goal: "Identify remaining checklist language that assigns provider routing, prompt payload, fallback, or transport authority to Prime."
action_type: VERIFY
expected_output_shape: "finding list with file refs and suggested owner correction"
risk_tier: 1
proof_requirement: "cite matching lines; no file writes in this call"
payload_budget_ref: "relay-prompt-budget:doc-scan"
```

Relay/Model Harness may then choose a verification-capable route, build a compact prompt packet containing only the relevant doc excerpts, enforce the budget, attach prompt payload evidence, and return a display-safe result. Prime decides what to do with the findings afterward.

**Example 2: Provider route decision**

Prime-level intent:

```text
Run a bounded verification pass before promoting a Relay/Model Harness change.
```

Per-call GOAL / Intent:

```text
call_goal: "Check whether this change violates DeepSeek transport gates or model-call ownership boundaries."
action_type: VERIFY
expected_output_shape: "pass/fail with blockers and evidence refs"
risk_tier: 2
proof_requirement: "Aegis policy evidence required before dispatch"
disallowed_outputs: "no branch movement, no live provider transport unless validation gate allows it"
```

Relay/Model Harness owns whether Claude, OpenAI, DeepSeek, or a fake/local adapter can serve that request. Prime does not select by marketing name or transport path; it submits the governed request and receives evidence.

**Example 3: Sentiment/content analysis**

Prime-level intent:

```text
Scott wants to understand whether user feedback indicates confusion, frustration, urgency, or approval.
```

Per-call GOAL / Intent:

```text
call_goal: "Classify the provided feedback snippets by sentiment and extract actionable product concerns."
action_type: EXPLAIN
expected_output_shape: "sentiment labels, confidence, and product-action notes"
risk_tier: 1
proof_requirement: "quote-free summary; preserve private data boundaries"
disallowed_outputs: "no psychological diagnosis, no durable memory write"
```

Here, Prime owns why the analysis matters and what decision it supports. Model Harness owns only the call mechanics for producing the bounded classification/explanation.

### Anti-Patterns

- Do not use per-call `goal` as a replacement for Prime's user intent analysis.
- Do not let UI labels such as `GOAL / Intent` create new backend route names without the taxonomy normalization pass.
- Do not let Bifrost infer model-call intent from transcript text when Relay can expose structured evidence.
- Do not store raw prompt or raw provider response bodies as the intent record.
- Do not use per-call intent to bypass Aegis policy, DeepSeek validation gates, or Relay dispatch evidence.

---

## Domain Shape

The runtime metadata surface lives alongside the existing `model_adapter.py` types. It introduces frozen dataclasses that adapters instantiate once at registration time and never mutate.

### `ProviderCapability`

Declared once per provider-model pair. Represents what this provider/model can do and what it costs.

- `provider` — string key: `"claude"`, `"openai"`, `"deepseek"`. Normative. Must match relay dispatch keys.
- `model` — string key: the exact model identifier (e.g. `"claude-sonnet-4-20250514"`, `"gpt-4o"`, `"deepseek-chat"`). Normative. Must match `AdapterRegistry.by_model` key.
- `context_window_tokens` — int. Maximum context window size advertised by the provider. Relay uses this to validate `PromptBudgetPlan.max_context_tokens` does not exceed the model's hard limit.
- `max_output_tokens` — int | None. Provider-advertised maximum output tokens. `None` if the provider does not publish a limit.
- `cost_posture` — `CostPosture` enum (from `relay.py`): `MINIMAL`, `STANDARD`, `PREMIUM`, `UNKNOWN`. Declared per model, not inferred.
- `latency_tier` — `LatencyTier` enum: `IMMEDIATE`, `FAST`, `NORMAL`, `SLOW`, `UNKNOWN`. Expected round-trip category for this model.
- `supports_streaming` — bool. Whether the provider adapter supports token-by-token streaming. Relay uses this to decide output rendering mode.
- `tokenizer_family` — string: e.g. `"claude"`, `"openai"`, `"deepseek"`. Which tokenizer this model uses for `prompt_tokens` counting. Relay uses this to validate token count attribution.
- `supports_thinking` — bool. Whether the model has an extended-thinking/chain-of-thought mode. Relay may route reasoning-heavy tasks to models with this capability.
- `supports_vision` — bool. Whether the model can accept image inputs. Must be `False` for all V2 adapters — vision routes are out of V2 scope.
- `q_mode_flat` — bool. Whether the model always produces deterministic, flat output with no creative variance. DeepSeek direct expected `True`; Claude expected `False`. Used by Aegis for Q-mode flatness proofs (see Aegis contract).
- `known_authorities` — tuple of string tags representing what audit bodies or internal reviews have validated this provider-model pairing (e.g. `"direct-api-only"`, `"deepseek-official-endpoint"`, `"anthropic-verified"`, `"openai-verified"`, `"codex-reviewed"`, `"pqa-review"`). Empty tuple means no known authority.

`ProviderCapability` is immutable and frozen.

### `ModelTrustState`

Declared once per provider-model pair. Represents audit standing and evidence strength.

- `provider` — must match the `ProviderCapability.provider` for the same model.
- `model` — must match `ProviderCapability.model`.
- `trust_mode` — `TrustMode` enum: `DIRECT`, `AGGREGATOR`, `UNKNOWN`. Direct means the adapter connects to the provider's own API (Claude → Anthropic, OpenAI → api.openai.com, DeepSeek → api.deepseek.com). Aggregator means it connects through a third-party API aggregator (e.g. OpenRouter). `UNKNOWN` means the route has not been declared — Aegis must block unknown-trust routes at Tier 2+.
- `direct_api_endpoint` — str | None. The base URL the adapter connects to. Required when `trust_mode` is `DIRECT`; `None` otherwise. Used for audit trail evidence.
- `proof_strength` — `ProofStrength` enum: `NONE`, `WEAK`, `STANDARD`, `STRONG`. Direct API connections with known authorities earn `STANDARD`. Aggregator routes earn `WEAK`. Routes with external review + known authorities + direct API earn `STRONG`. `NONE` is reserved for unvalidated routes — Aegis blocks these unconditionally.
- `external_review_required` — bool. If `True`, this provider-model pairing requires an external Codex or PQA review before Aegis will allow Tier 3+ dispatch. Claude models may be `False`; DeepSeek direct should be `True` until independent validation completes.
- `external_review_status` — `ExternalReviewStatus` enum: `NOT_REQUIRED`, `PENDING`, `PASSED`, `FAILED`, `EXPIRED`. `PASSED` reviews expire after 30 days unless revalidated.
- `external_review_evidence` — str | None. Reference to review commit hash, Codex session ID, or PQA report ID that validated this route. Required when `external_review_status` is `PASSED`; `None` otherwise.
- `blocked_authorities` — tuple of string tags representing audit/security concerns that block this route (e.g. `"aggregator-without-proof"`, `"unvalidated-model-version"`, `"expired-review"`). Non-empty tuple means Aegis blocks dispatch regardless of risk tier.
- `last_validated_at` — str | None. ISO UTC timestamp of last successful validation. `None` if never validated.

`ModelTrustState` is immutable and frozen.

### `AllowedTaskTypes`

Declared once per provider-model pair. Tells Aegis what work this model is permitted to do.

- `provider` — must match `ProviderCapability.provider`.
- `model` — must match `ProviderCapability.model`.
- `allowed_action_types` — tuple of `CognitionActionType` enum values (from Aegis). If empty, Aegis blocks all dispatch to this model.
- `blocked_action_types` — tuple of `CognitionActionType` enum values that are explicitly blocked even if the tier would otherwise allow them. `BUILD` on DeepSeek may be explicitly blocked; `VERIFY` may be allowed. Separating allowed/blocked lets adapters be permissive-by-default but explicit about exclusions.
- `max_risk_tier` — int 0–4. Maximum `RiskTier` this model may serve. DeepSeek without external review may be capped at Tier 1. Claude with verified routing may serve Tier 4.
- `reason` — str. Human-readable reason for the allowed/blocked configuration. Shown in Review Console when a route is gated.

`AllowedTaskTypes` is immutable and frozen.

### `PromptDragTelemetry`

Not declared by the adapter — this is a Relay-side record produced *per model call*. Included in this contract because the adapter must declare what telemetry fields it supports.

- `call_id` — stable identifier for this model call, generated by Relay.
- `provider` — string, from `ProviderCapability.provider`.
- `model` — string, from `ProviderCapability.model`.
- `packet_id` — reference to the `PromptPacket.packet_id` that was dispatched.
- `prompt_tokens` — int. Token count of the serialized prompt (from `PromptPacket`).
- `completion_tokens` — int. Token count of the model response.
- `total_tokens` — int. `prompt_tokens + completion_tokens`.
- `latency_ms` — float. Wall-clock milliseconds from dispatch to response receipt.
- `budget_compliant` — bool. `True` if `prompt_tokens <= budget.max_context_tokens` and all lineage sources are in `budget.allowed_sources`. Already validated by `PromptPacket` construction.
- `trust_mode_at_dispatch` — `TrustMode` value at time of call. Snapshot for audit.
- `proof_strength_at_dispatch` — `ProofStrength` value at time of call.
- `external_review_status_at_dispatch` — `ExternalReviewStatus` value at time of call.
- `prompt_payload_snapshot_hash` — str | None. SHA-256 hash of the `PromptPacket.serialized_prompt` sent to the model. Enables later audit: "did the model receive what Relay said it sent?" Set to `None` when the adapter does not support payload snapshot hashing (DeepSeek aggregator routes, for example, cannot provide this).
- `response_payload_snapshot_hash` — str | None. SHA-256 hash of the raw model response text. Enables proof that the response was not tampered with after receipt.
- `adapter_supports_snapshot` — bool. Whether the adapter declares payload snapshot capability. Derived from adapter metadata, not from the call itself.
- `errors` — tuple of error tags (empty on success). Tags like `"timeout"`, `"rate_limited"`, `"auth_failed"`, `"budget_exceeded"`, `"blocked_authority"`, `"external_review_required"`, `"unknown_trust_route"`.

`PromptDragTelemetry` is not part of the adapter's static declaration — it is a runtime record. But the adapter *must* declare which telemetry fields it can populate, via a `TelemetryCapability` dataclass:

- `supports_completion_tokens` — bool. Adapters that cannot parse token counts from response headers set this to `False`.
- `supports_latency_ms` — bool. Should always be `True` for any live adapter.
- `supports_payload_snapshot` — bool. Direct-provider adapters with known endpoints should set `True`. Aggregator routes set `False`.
- `supports_response_hash` — bool. Direct-provider adapters set `True`. Fake adapters set `False`.

`TelemetryCapability` is immutable and frozen.

---

## Model Identity Registry Resolution

Exact model identifiers (`ProviderCapability.model`) are normative and must match the request field value sent to each provider's API. Provider marketing names, version codes, or aliases (e.g., "deepseek-v4-pro", "Claude 4", "GPT-5.3-Codex") are not exact IDs and must not be used as dispatch keys.

### Model Identity Rules

- **Exact ID is authoritative:** The `model` field in `ProviderCapability` is the value sent in the API request. For DeepSeek, this is `deepseek-chat` (not `deepseek-v4-pro`). For Claude, this is versioned release IDs like `claude-sonnet-4-20250514` (not `claude-sonnet` or `Claude 4`). For OpenAI, this is the released model name (e.g., `gpt-4o`, not `GPT-5.3-Codex`).
- **Aliases are not accepted:** If a provider publishes compatibility aliases or variant names, adapters must not treat them as equivalent. Aliases may have different capabilities, costs, or underlying implementations.
- **Version drift:** If a provider updates the exact model ID (e.g., DeepSeek releases v5), the normative registry and Relay routing docs are updated. Legacy aliases are marked deprecated with a sunset date.
- **Relay dispatch uses exact ID:** Relay resolves `AdapterRegistry.by_model` using the exact model field. If Relay receives a request for a v4 or marketing name variant, it is treated as an unknown route and Aegis blocks dispatch.

### Provider-Specific Registry Notes

- **Anthropic:** Uses date-based versioning (`claude-opus-4-8-20250514`). Is the source of truth for current model IDs.
- **OpenAI:** Uses base model names (`gpt-4o`, `gpt-4-turbo`) without version dates. Check OpenAI API docs for current deployable IDs.
- **DeepSeek:** Uses `deepseek-chat` for the current stable endpoint. Marketing materials reference "v4-pro" / "v4-flash" but the API expects `deepseek-chat`. Future versions (v5, etc.) will update the registry and this contract.

---

## Enum Definitions

All enums follow existing `meridian_core` conventions. Names are normative.

### `TrustMode`

```python
class TrustMode(Enum):
    DIRECT = "direct"           # Adapter connects to provider's own API
    AGGREGATOR = "aggregator"   # Adapter connects through third-party aggregator
    UNKNOWN = "unknown"         # Route not declared — Aegis blocks
```

### `ProofStrength`

```python
class ProofStrength(Enum):
    NONE = "none"           # No validation at all
    WEAK = "weak"           # Aggregator route, no external review
    STANDARD = "standard"   # Direct API + at least one known authority
    STRONG = "strong"       # Direct API + external review passed + known authorities
```

### `ExternalReviewStatus`

```python
class ExternalReviewStatus(Enum):
    NOT_REQUIRED = "not_required"   # Model does not require external review
    PENDING = "pending"             # Review has been requested but not completed
    PASSED = "passed"               # Review passed (expires after 30 days)
    FAILED = "failed"               # Review failed — route is blocked
    EXPIRED = "expired"             # Review was passed but has expired
```

### `LatencyTier`

```python
class LatencyTier(Enum):
    IMMEDIATE = "immediate"   # < 500ms expected
    FAST = "fast"             # 500ms – 2s expected
    NORMAL = "normal"         # 2s – 10s expected
    SLOW = "slow"             # > 10s expected
    UNKNOWN = "unknown"       # Not yet characterized
```

---

## Aegis/Relay Policy Binding

The metadata surface feeds Aegis gating and Relay dispatch through deterministic rules. No model inference is used to decide routing — all decisions are structural.

### Dispatch Resolution Flow

1. **Relay receives a dispatch request** with role, model, tier, and action type.
2. **`AdapterRegistry.resolve(role, model)`** returns the adapter.
3. **Relay reads `AllowedTaskTypes`** for that provider-model pair.
   - If `action_type` is in `blocked_action_types`, dispatch fails with `"blocked_task_type"`.
   - If `action_type` is not in `allowed_action_types`, dispatch fails with `"disallowed_task_type"`.
   - If `risk_tier > max_risk_tier`, dispatch fails with `"risk_tier_exceeded"`.
4. **Relay reads `ModelTrustState`** for that provider-model pair.
   - If `blocked_authorities` is non-empty, dispatch fails with `"blocked_authority"`.
   - If `trust_mode == UNKNOWN`, dispatch fails with `"unknown_trust_route"`.
   - If `external_review_required and external_review_status != PASSED`, dispatch fails with `"external_review_required"`.
   - If `external_review_status == EXPIRED or == FAILED`, dispatch fails with `"external_review_expired"` or `"external_review_failed"`.
5. **Aegis confirms the dispatch** by reading `RiskAssessment`, `CognitionPolicy`, and the adapter metadata together.
6. **Relay builds the `PromptPacket`** within `PromptBudgetPlan` limits.
7. **Relay calls the adapter.** The adapter returns model text.
8. **Relay produces `PromptDragTelemetry`** enriched with runtime metrics.

At no point in this flow do API keys, provider account details, or transport internals enter the prompt context or the dispatch decision logic.

### Tier-Based Gating

| Risk Tier | Trust Mode Required | Proof Strength Required | External Review Required |
|---|---|---|---|
| Tier 0 | Any (deterministic only — no model call) | N/A | N/A |
| Tier 1 | DIRECT or AGGREGATOR | >= NONE | Not required unless adapter declares it |
| Tier 2 | DIRECT or AGGREGATOR | >= WEAK | If `external_review_required`, must be PASSED |
| Tier 3 | DIRECT only | >= STANDARD | If `external_review_required`, must be PASSED |
| Tier 4 | DIRECT only | >= STANDARD | Must be PASSED if adapter declares it; Aegis may also require human gate |

Aggregator routes are capped at Tier 2 regardless of other metadata. DeepSeek aggregator routes (e.g. through OpenRouter) are capped at Tier 1 until independent validation completes and a STRONG proof-strength review passes.

---

## Provider-Specific Metadata (Normative Defaults)

These are the *canonical defaults* for each provider-model pairing. Adapter implementations may refine these values but must document deviations.

### Claude (Anthropic Direct)

| Field | Value |
|---|---|
| `provider` | `"claude"` |
| `model` | `"claude-sonnet-4-20250514"` (primary V2 lane) |
| `context_window_tokens` | 200000 |
| `max_output_tokens` | 32000 |
| `cost_posture` | `PREMIUM` |
| `latency_tier` | `FAST` |
| `supports_streaming` | `True` |
| `tokenizer_family` | `"claude"` |
| `supports_thinking` | `True` |
| `supports_vision` | `False` (V2 scope) |
| `q_mode_flat` | `False` |
| `known_authorities` | `("anthropic-verified", "direct-api-only")` |
| `trust_mode` | `DIRECT` |
| `direct_api_endpoint` | `"https://api.anthropic.com/v1/messages"` |
| `proof_strength` | `STANDARD` |
| `external_review_required` | `False` |
| `external_review_status` | `NOT_REQUIRED` |
| `blocked_authorities` | `()` (none) |

### OpenAI (Direct)

| Field | Value |
|---|---|
| `provider` | `"openai"` |
| `model` | `"gpt-4o"` (primary V2 lane) |
| `context_window_tokens` | 128000 |
| `max_output_tokens` | 16384 |
| `cost_posture` | `PREMIUM` |
| `latency_tier` | `FAST` |
| `supports_streaming` | `True` |
| `tokenizer_family` | `"openai"` |
| `supports_thinking` | `False` |
| `supports_vision` | `False` (V2 scope) |
| `q_mode_flat` | `False` |
| `known_authorities` | `("openai-verified", "direct-api-only")` |
| `trust_mode` | `DIRECT` |
| `direct_api_endpoint` | `"https://api.openai.com/v1/chat/completions"` |
| `proof_strength` | `STANDARD` |
| `external_review_required` | `False` |
| `external_review_status` | `NOT_REQUIRED` |
| `blocked_authorities` | `()` (none) |

### DeepSeek (Direct)

| Field | Value |
|---|---|
| `provider` | `"deepseek"` |
| `model` | `"deepseek-chat"` (primary V2 lane) |
| `context_window_tokens` | 65536 |
| `max_output_tokens` | 8192 |
| `cost_posture` | `MINIMAL` |
| `latency_tier` | `NORMAL` |
| `supports_streaming` | `True` |
| `tokenizer_family` | `"deepseek"` |
| `supports_thinking` | `False` |
| `supports_vision` | `False` (V2 scope) |
| `q_mode_flat` | `True` |
| `known_authorities` | `("deepseek-official-endpoint", "direct-api-only")` |
| `trust_mode` | `DIRECT` |
| `direct_api_endpoint` | `"https://api.deepseek.com/v1/chat/completions"` |
| `proof_strength` | `WEAK` (until external review passes) |
| `external_review_required` | `True` |
| `external_review_status` | `PENDING` |
| `blocked_authorities` | `()` (none, but gated by `external_review_required`) |

### DeepSeek (Aggregator — via OpenRouter or similar)

| Field | Value |
|---|---|
| `trust_mode` | `AGGREGATOR` |
| `direct_api_endpoint` | `None` |
| `proof_strength` | `WEAK` |
| `external_review_required` | `True` |
| `external_review_status` | `PENDING` |
| `blocked_authorities` | `("aggregator-without-proof",)` |

This route is capped at Tier 1 and is expected to be removed once the direct DeepSeek adapter passes external review.

---

## Allowed/Blocked Task Types (Normative Defaults)

### Claude (Direct)

- `allowed_action_types`: `(BUILD, REVIEW, VERIFY, EXPLAIN, PLAN, REPAIR)`
- `blocked_action_types`: `()` (none)
- `max_risk_tier`: `4`
- `reason`: Claude is the default V2 primary lane. Passes every Aegis gate with direct API and known authorities. Can serve human-gate Tier 4 when Aegis confirms.

### OpenAI (Direct)

- `allowed_action_types`: `(BUILD, REVIEW, VERIFY, EXPLAIN)`
- `blocked_action_types`: `(PLAN, REPAIR)`
- `max_risk_tier`: `3`
- `reason`: OpenAI can build, review, verify, and explain. Planning and repair are reserved for Claude and Codex in V2. Capped at Tier 3 to keep human-gate decisions in the Claude lane.

### DeepSeek (Direct)

- `allowed_action_types`: `(VERIFY, EXPLAIN)`
- `blocked_action_types`: `(BUILD, REVIEW, PLAN, REPAIR)`
- `max_risk_tier`: `2`
- `reason`: DeepSeek is a V2 verification lane only. Q-mode flatness (`q_mode_flat = True`) makes it suitable for deterministic output validation and explanation but not for creative building or subjective reviewing. Capped at Tier 2; Tier 3+ requires external review to pass, which would upgrade `proof_strength` to `STRONG` and expand `allowed_action_types`.

### DeepSeek (Aggregator)

- `allowed_action_types`: `(EXPLAIN,)`
- `blocked_action_types`: `(BUILD, REVIEW, VERIFY, PLAN, REPAIR)`
- `max_risk_tier`: `1`
- `reason`: Aggregator route cannot provide payload snapshot evidence. Capped at Tier 1 (single-lane, reversible). Only explain is allowed, and only at low risk. Expected to be removed when direct DeepSeek clears external review.

---

## Prompt Payload Snapshot Evidence

### Why Snapshots Matter

When Relay dispatches a prompt to a model, two questions must be answerable later:

1. Did the model receive exactly what Relay says it sent?
2. Did the model's response arrive unaltered from the provider?

Direct-provider adapters can answer both by hashing the outbound prompt and inbound response. Aggregator routes cannot — an aggregator may modify, cache, or proxy the request/response without the adapter's knowledge.

### Snapshot Requirements by Trust Mode

| Trust Mode | Payload Snapshot Hash Required | Response Snapshot Hash Required |
|---|---|---|
| `DIRECT` | H3 (should) | H3 (should) |
| `AGGREGATOR` | Not possible | Not possible |
| `UNKNOWN` | Blocked before dispatch | Blocked before dispatch |

H3 means: "should provide; missing snapshot is not a dispatch blocker but is a review flag." Aegis may elevate missing-snapshot routes to Review Console for audit.

### Snapshot Evidence in the Audit Trail

When `adapter_supports_snapshot` is `True`, `PromptDragTelemetry` carries both hashes. The Review Console can later:

1. Reconstruct the exact `PromptPacket.serialized_prompt` from logs.
2. Recompute the SHA-256 hash.
3. Compare against `prompt_payload_snapshot_hash` in the telemetry record.
4. Flag any mismatch as a potential prompt-tampering event.

This is not a real-time gate — it is an audit capability that lets Codex Reviews, PQA, or Scott verify dispatch integrity after the fact.

---

## Q-Mode Flatness Proof

DeepSeek's `q_mode_flat = True` declaration is not just a metadata flag — it carries proof expectations.

### What Q-Mode Flatness Means

A model is Q-mode flat if, given the same prompt twice, it produces the same output twice. DeepSeek direct with temperature=0 should be Q-mode flat. Claude is not Q-mode flat — even with temperature=0, Claude may produce different phrasings for the same prompt.

### How Aegis Uses Q-Mode Flatness

When a model is Q-mode flat and the action type is `VERIFY`, Aegis may:

1. Dispatch the same prompt to the Q-mode-flat model twice (dual-lane Q-proof).
2. Compare the two responses byte-for-byte.
3. If responses match, the `PromiseState` is upgraded to `KEPT`.
4. If responses differ, the route is flagged for Review Console and the model's `proof_strength` is downgraded.

This is the only case where dual-lane dispatch does not require two *different* models — two calls to the same Q-mode-flat model serve as self-verification.

### Adapter Responsibility

The DeepSeek adapter must:

- Always set `temperature=0` for Q-mode-flat verification calls.
- Never cache responses across calls — each verification call must be a fresh API request.
- Report `supports_payload_snapshot = True` and `supports_response_hash = True` for the direct route.

If the adapter cannot guarantee these, it must set `q_mode_flat = False`.

---

## Telemetry Capability Declaration

Every adapter must declare its `TelemetryCapability` at registration time. Relay reads this before producing `PromptDragTelemetry`.

| Adapter | `supports_completion_tokens` | `supports_latency_ms` | `supports_payload_snapshot` | `supports_response_hash` |
|---|---|---|---|---|
| Claude (Direct) | `True` | `True` | `True` | `True` |
| OpenAI (Direct) | `True` | `True` | `True` | `True` |
| DeepSeek (Direct) | `True` | `True` | `True` | `True` |
| DeepSeek (Aggregator) | `False` | `True` | `False` | `False` |
| `FakeModelAdapter` (test) | `False` | `False` | `False` | `False` |

When an adapter sets any telemetry field to `False`, Relay records the corresponding `PromptDragTelemetry` field as `None` (for numeric/string fields) or `False` (for boolean fields) and includes an error tag in `errors` tuple: `"telemetry_unavailable"`. This is not a dispatch blocker but is surfaced to Beacon for monitoring.

---

## Registration API (Runtime Shape)

The existing `AdapterRegistry` in `model_adapter.py` gains two new registration methods and one new resolve path:

### Extended `AdapterRegistry`

```python
class AdapterRegistry:
    # Existing: register_model, register_role_default, resolve

    def register_metadata(
        self,
        model: str,
        capability: ProviderCapability,
        trust: ModelTrustState,
        allowed: AllowedTaskTypes,
        telemetry: TelemetryCapability,
    ) -> AdapterRegistry:
        """Return new registry with metadata registered for a model.
        All four metadata structures are required. Partial registration is not allowed.
        """

    def resolve_metadata(self, model: str) -> tuple[ProviderCapability, ModelTrustState, AllowedTaskTypes, TelemetryCapability]:
        """Return the (capability, trust, allowed, telemetry) tuple for a model.
        Raises MissingAdapterError if no metadata is registered for this model.
        """
```

Metadata is registered independently of the adapter callable — a model can have metadata before its transport is wired. This lets Build 4 declare provider capabilities in docs and Build 1 wire transports later.

### Registration Invariant

Every model in `adapter_registry._by_model` must also have metadata registered. Every model with metadata registered must also be resolvable via `resolve()`. Relay validates this invariant at startup and raises `ModelAdapterConfigError` if broken.

---

## Existing Types — No Changes Required

The following types in `model_adapter.py` are unchanged by this contract:

- `ModelAdapter` (Protocol) — unchanged. Adapters still receive `str` payload and return `str`.
- `ModelAdapterConfig` — unchanged. Env-var credential validation stays in the adapter.
- `HttpModelAdapterConfig` — unchanged. Endpoint + API key config stays in the adapter.
- `FakeModelAdapter` — unchanged. Test adapters don't need metadata.
- `MissingAdapterError`, `ModelAdapterConfigError` — unchanged.
- `EnvConfiguredModelAdapter`, `HttpJsonModelAdapter` — unchanged. Transport implementations are not touched.

The metadata surface is *additive* — it lives alongside the existing types and does not modify any existing callable boundary.

---

## Tests

Tests are not required for this docs-only contract. The runtime tests for the metadata surface will be written by Build 1 when implementing `register_metadata`, `resolve_metadata`, and the metadata dataclasses. Expected test coverage:

- Every metadata dataclass validates required fields at construction (no partial records).
- `register_metadata` with all four structures succeeds; with missing structures raises.
- `resolve_metadata` for a registered model returns the correct tuple; for an unregistered model raises `MissingAdapterError`.
- Registration invariant: registering an adapter without metadata (or metadata without an adapter) raises at startup validation.
- `AllowedTaskTypes` blocks correctly: blocked type, disallowed type, tier exceeded all produce the expected error tags.
- `ModelTrustState` gates correctly: `UNKNOWN` trust, `blocked_authorities`, `EXPIRED`/`FAILED` external review all produce the expected error tags.
- `PromptDragTelemetry` construction from a successful and failed dispatch produces expected field values.
- Q-mode flatness: two identical DeepSeek direct calls with temperature=0 produce byte-identical responses (or the adapter correctly reports mismatch).

These tests belong in `tests/test_model_adapter.py` alongside existing `test_*model_adapter*` tests. They are out of scope for this contract.

---

## Future Taxonomy Promotion Gate

The current Model Harness UI taxonomy is a display vocabulary, not a hard backend naming convention. Existing backend names and contract names remain authoritative.

Architecture taxonomy from `2-Architecture.md` is treated the same way for now: useful UI/strategy vocabulary for describing the product shape, but not a source of new backend enums, dataclasses, route fields, package exports, or dispatch keys until a reviewed promotion pass says otherwise.

Before any future backend promotion of Model Harness taxonomy terms, do a small normalization pass that creates one canonical taxonomy name list and maps UI labels to backend-owned concepts. That pass must preserve existing names unless there is a reviewed migration reason, and it must not create new Python enums, dataclasses, route fields, or package exports directly from UI-only labels.

Backend binding for V2 should only use the already-reviewed surfaces represented by `ModelHarnessMetadata`, Relay dispatch/evidence records, Aegis policy evidence, provider balance summaries, prompt payload meter evidence, and DeepSeek validation/transport gates.

---

## Completion Criteria

- [x] `docs/model-harness-v2-contract.md` created with full domain shape, enums, provider defaults, gating rules, telemetry, snapshot evidence, Q-mode flatness, and registration API.
- [x] Ready for Codex Review after coordinator salvage from local Build 4 commit `2bfaf6f`; clean coordinator commit recorded by the queue provenance.
