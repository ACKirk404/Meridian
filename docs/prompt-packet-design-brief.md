# Prompt Packet Design Brief

**Status:** Design planning — no runtime code yet  
**Purpose:** Future domain model for bundled, validated prompts dispatched via Relay  
**Related:** `meridian_core/prompt_budget.py`, `meridian_core/relay.py`

---

## What is a Prompt Packet?

A **Prompt Packet** is a validated, immutable bundle of prompt data ready for dispatch to a worker model. It combines:
- The serialized prompt text
- Metadata (token count, construction time, source lineage)
- Constraints (budget ceiling, allowed sources)
- Validation state (passes all checks or fails cleanly)

It's the point of commitment: before dispatch, the packet is sealed and verified. After dispatch, it becomes the baseline for measuring Relay overhead.

---

## Why It Exists

**Problem:** Relay currently builds prompts inline during dispatch, with no validation checkpoint or clear boundary between "prompt is ready" and "prompt is being used."

**Consequence:** 
- No guarantee prompt fits budget until too late
- Construction overhead unmeasured until response arrives
- No single point to verify context sources match allowed list
- Metrics captured post-dispatch; cannot prevent budget violations

**Solution:** Build and validate the prompt as a discrete Prompt Packet *before* dispatch. The packet is either valid (proceed) or invalid (escalate). No surprises mid-dispatch.

---

## What Fields Prompt Packet Should Eventually Contain

### Core Fields
- `packet_id: str` — Unique identifier
- `serialized_prompt: str` — The actual text sent to model
- `prompt_tokens: int` — Token count of serialized_prompt
- `max_context_tokens: int` — Budget ceiling (from PromptBudgetPlan)
- `allowed_sources: list[str]` — Sources that contributed (from PromptBudgetPlan)

### Metadata
- `construction_time_ms: float` — Time to build the packet
- `source_lineage: dict[str, int]` — Tokens contributed by each source
- `created_at: datetime` — Timestamp

### Validation State
- `is_valid: bool` — Passes all checks
- `validation_errors: list[str]` — Empty if valid, populated if not

### Context for Later
- `tier: int` — Risk tier (for traceability)
- `lane_role: str` — Builder/Reviewer/Verifier (for metrics routing)

---

## What Validations It Should Eventually Perform

### 1. Budget Compliance
```
assert packet.prompt_tokens <= packet.max_context_tokens
# Fail message: "Prompt 4,850 tokens exceeds budget 5,000"
```

### 2. Source Compliance
```
for source in packet.source_lineage.keys():
    assert source in packet.allowed_sources
# Fail message: "Source 'debug_logs' not in allowed_sources"
```

### 3. Serialization Integrity
```
assert len(packet.serialized_prompt) > 0
assert isinstance(packet.serialized_prompt, str)
# Fail message: "Prompt is empty or invalid type"
```

### 4. Construction Time Sanity
```
assert packet.construction_time_ms >= 0
assert packet.construction_time_ms < 30000  # 30-second sanity ceiling
# Fail message: "Construction time {time} is unrealistic"
```

### 5. Lineage Adds Up
```
total_from_lineage = sum(packet.source_lineage.values())
assert total_from_lineage <= packet.prompt_tokens
# Fail message: "Lineage {total} exceeds packet {tokens}"
```

---

## How It Relates to Prompt Budget

**Prompt Budget** (PromptBudgetPlan):
- Sets the *rules*: max tokens, allowed sources, reason
- Created at routing time (deterministic per tier)
- Pure constraint, no validation

**Prompt Packet**:
- Enforces the *rules*: builds prompt within constraints
- Created during dispatch preparation
- Concrete artifact, validates or fails

**Flow:**
```
Risk Tier 
    ↓
PromptBudgetPlan (rules)
    ↓
Build Prompt with Budget Rules
    ↓
Create PromptPacket (validate)
    ├─ If valid → proceed to dispatch
    └─ If invalid → escalate to Prime, cancel dispatch
    ↓
Dispatch Packet
    ↓
Metrics measure (construction_time, prompt_tokens already in packet)
```

---

## How It Prevents Relay Prompt Drag

### 1. Early Failure
- Validate *before* sending to model
- Budget violation discovered at packet creation, not mid-response
- Prime can decide to escalate or retry with simpler context
- Avoids wasted vendor tokens on oversized prompts

### 2. Transparency
- `source_lineage` shows exactly what contributed to final token count
- Construction time measured and logged
- Prime has visibility: "prompt is 4,850 of 5,000 tokens, took 85ms to build"

### 3. Bounded Construction
- Sources are from `allowed_sources` only (no scope creep)
- Lineage tracks which sources added how many tokens
- If construction time exceeds threshold, packet creation fails
- Prevents silent overhead accumulation

### 4. Metrics Foundation
- Packet metadata feeds into PromptMetricSample
- token count, construction time already captured at creation
- No need to re-measure post-dispatch

---

## What Must Stay Out of Worker Prompts

**Packet metadata never injected into the serialized prompt:**
- Construction time (not worker's concern)
- Source lineage (internal accounting)
- Budget rules (boundary-checked, not for worker)
- Validation state (if invalid, packet never sent)
- Packet ID or metadata (would bloat final prompt)

**Only `serialized_prompt` is sent to model.** Everything else is metadata for Prime, Metrics, and logs.

---

## Future Test Checklist (Before Runtime)

- [ ] Packet creation validates budget compliance (tokens ≤ max)
- [ ] Packet creation validates source compliance (all sources in allowed list)
- [ ] Budget violation produces clear error message
- [ ] Source violation produces clear error message
- [ ] Construction time measured and recorded
- [ ] Source lineage totals match or are less than packet tokens
- [ ] Invalid packet creation fails cleanly (raises ValidationError or similar)
- [ ] Valid packet can be serialized and dispatched
- [ ] Packet immutability (no edits after creation)
- [ ] Metrics sample constructed correctly from packet metadata
- [ ] No packet metadata leaks into serialized_prompt
- [ ] Packet ID is unique per creation
- [ ] Construction time sanity check (rejects 30s+ times)

---

## Implementation Notes

### Not in This Brief
- Actual code (design planning only)
- API signatures (defer to implementation)
- Error recovery (what to do if validation fails — Prime decides)
- Async/streaming considerations (future)

### When Ready to Code
- Make PromptPacket immutable (frozen dataclass or equivalent)
- Validation should be exhaustive and fail-fast
- Source lineage as dict (source_name → tokens)
- Keep construction_time_ms as float (allows sub-millisecond precision)

### Integration Points (Future)
- Relay.dispatch() builds PromptPacket before sending
- PromptMetricSample created with packet metadata
- Prime reads validation state; DEGRADED if invalid
- Review Console shows packet details on budget violation

---

## Summary

**Prompt Packet = validated, immutable prompt ready for dispatch.**

- Fields: serialized prompt, tokens, budget, sources, lineage, construction time, validation state
- Validations: budget compliance, source compliance, token totals, construction sanity
- Prevents drag: early failure, transparency, bounded construction, metrics foundation
- Never appears in worker prompts: only metadata for Prime and Metrics

Simple, concrete, deterministic. Ready to implement when Relay dispatch instrumentation is designed.
