# Relay PromptPacket Integration Plan

**Status:** Ready to implement  
**Prepared by:** Build 1  
**Depends on:** `meridian_core/prompt_packet.py` (complete), `meridian_core/relay.py` (has `prompt_budget` on `RelayRoute`)  
**Next step:** Relay runtime integration slice

---

## What Relay Passes into build_prompt_packet()

`route_from_assessment()` already attaches a `PromptBudgetPlan` to every `RelayRoute`. When Relay prepares a dispatch, it builds one `PromptPacket` per lane before calling the model.

```python
packet = build_prompt_packet(
    packet_id=f"{route.risk_tier}-{lane.role.value}-{uuid4().hex[:8]}",
    serialized_prompt=assembled_prompt,       # built by Relay from context sources
    prompt_tokens=count_tokens(assembled_prompt),
    budget=route.prompt_budget,               # already on RelayRoute
    source_lineage=lineage,                   # {source_name: token_count}
    construction_time_ms=elapsed_ms,          # measured during assembly
)
```

`packet_id` format is stable and traceable: `"2-builder-a3f9c1d2"`.

---

## Where Token Counting Belongs

- Token counting belongs **inside the Relay dispatch-preparation step**, after the prompt is assembled and before `build_prompt_packet()` is called.
- A `count_tokens(text: str) -> int` utility will live in a future `meridian_core/tokens.py` slice — do not add it to `relay.py` or `prompt_packet.py`.
- For now, the Relay integration slice can accept `prompt_tokens` as a caller-supplied int (integration tests can provide exact counts). The tokenizer utility is a separate slice.
- `prompt_tokens` must count `serialized_prompt` only — not raw context inputs before assembly.

---

## How Source Lineage Is Calculated

Relay assembles the serialized prompt by drawing from one or more context sources. Each source contributes a substring; its token count is tracked separately:

```python
lineage: dict[str, int] = {}
parts: list[str] = []

if "direct_input" in route.prompt_budget.allowed_sources:
    text = direct_input_text
    lineage["direct_input"] = count_tokens(text)
    parts.append(text)

if "task_context" in route.prompt_budget.allowed_sources:
    text = task_context_text
    lineage["task_context"] = count_tokens(text)
    parts.append(text)

# ... etc. for each allowed source

assembled_prompt = "\n\n".join(parts)
```

Rules:
- Only sources in `route.prompt_budget.allowed_sources` are included.
- PromptPacket validation will reject any lineage key not in `allowed_sources` — Relay must not add sources outside the budget.
- `sum(lineage.values()) <= prompt_tokens` must hold; PromptPacket enforces this.

---

## How model_payload() Is the Only Model-Facing String

The dispatch call must use exactly one string from the packet:

```python
response = call_model(
    model_id=lane.preferred_model,
    prompt=packet.model_payload(),   # ONLY this — no other packet field
)
```

Relay must never pass `packet.packet_id`, `packet.budget`, `packet.source_lineage`, `packet.construction_time_ms`, or any derived metadata to the model. Those fields exist for Prime, Metrics, and logs only.

This is already enforced structurally: `model_payload()` returns only `serialized_prompt`, and nothing else on `PromptPacket` is a dispatch-suitable string.

---

## How Prompt Metrics Observe Packet Construction

After `build_prompt_packet()` succeeds (before dispatch), Relay creates a metrics sample from packet metadata:

```python
# After build, before model call
sample = PromptMetricSample(
    packet_id=packet.packet_id,
    risk_tier=route.risk_tier,
    prompt_tokens=packet.prompt_tokens,
    max_context_tokens=packet.budget.max_context_tokens,
    construction_time_ms=packet.construction_time_ms,
    budget_tier=packet.budget.tier.value,
)
metrics_recorder.record(sample)
```

Invariants:
- Metrics are created **after** the packet is sealed and **before** the model call.
- No metrics metadata is injected into `serialized_prompt`.
- If the packet fails validation (raises `PromptPacketValidationError`), no metric sample is created — Relay escalates to Prime instead.
- `PromptMetricSample` is a separate domain type (Build 2 slice); Relay observes the packet, it does not modify it.

---

## Tests to Write Before Runtime Integration

These tests belong in a future `tests/test_relay_dispatch.py` or as an addition to `test_relay.py`:

| Test | What it proves |
|------|---------------|
| `test_relay_builds_valid_packet_for_each_tier` | `route.prompt_budget` feeds `build_prompt_packet()` cleanly for tiers 0–4 |
| `test_relay_packet_budget_matches_route_budget` | `packet.budget is route.prompt_budget` |
| `test_relay_packet_model_payload_is_only_dispatch_string` | No other packet field used in model call path |
| `test_relay_rejects_oversized_prompt_before_dispatch` | `PromptPacketValidationError` fires before model is called |
| `test_relay_source_lineage_keys_within_budget_allowed_sources` | Relay never passes disallowed sources to `build_prompt_packet` |
| `test_relay_construction_time_is_positive` | `packet.construction_time_ms > 0` after assembly |
| `test_relay_metrics_created_after_packet_sealed` | Metrics observe packet fields; no injection into serialized_prompt |
| `test_relay_packet_not_created_on_validation_failure` | Packet build failure → escalation path, no metric sample |

---

## What Must Not Happen Yet

- **Do not modify `relay.py`** — the dispatch integration is a separate slice.
- **Do not add token counting** to any existing file — `count_tokens()` is a future `tokens.py` slice.
- **Do not add async dispatch** — synchronous domain model only.
- **Do not add `PromptPacket` to package exports** — Build 2 owns the package API slice.
- **Do not update FileMap** — Build 3 owns FileMap updates.
- **Do not add PromptMetricSample** — that is a Build 2/metrics slice.
- **Do not inject any packet field into `serialized_prompt`** — the boundary is enforced by `model_payload()`.

---

## Sequencing Summary

```
[DONE] PromptBudgetPlan — budget rules per tier
[DONE] RelayRoute.prompt_budget — budget attached to route
[DONE] PromptPacket — validated, immutable dispatch bundle
[DONE] model_payload() — enforced dispatch boundary
[NEXT] tokens.py — count_tokens() utility
[NEXT] Relay dispatch integration — build packet per lane, dispatch via model_payload()
[THEN] PromptMetricSample — observe packet metadata for metrics
[THEN] Package API export — Build 2 slice
[THEN] FileMap update — Build 3 slice
```
