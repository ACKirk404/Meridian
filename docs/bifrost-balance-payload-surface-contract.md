# Bifrost Balance And Prompt Payload Surface Contract

**Owner:** Bifrost Harness
**Status:** V2 UI/product contract
**Purpose:** Define how Meridian exposes provider balance and prompt-payload visibility without letting Bifrost make routing decisions.

## Principle

Bifrost displays structured Relay and Model Harness telemetry. It does not choose providers, bypass Aegis, mutate queues, or infer hidden budget state. Prime and Relay own routing; Aegis owns gates; Bifrost makes the state visible enough that Scott and Prime can catch prompt drag, provider pressure, and degraded Q-mode behavior early.

## Required Surface

Bifrost must expose a compact provider balance surface that can be opened verbally, clicked from a harness panel, or shown as a status rail when provider risk is elevated.

The surface must include:

- Provider health for Claude, OpenAI, DeepSeek, and future adapters.
- Current model name when known.
- Trust state: trusted, candidate, degraded, blocked, or unknown.
- Context budget and prompt payload budget when known.
- Prompt payload label for the current dispatch, such as `(under 1k)`, `(12.4k)`, or `(over budget)`.
- Prompt payload budget percent.
- Growth delta from the previous Q-mode or dispatch prompt.
- Cost/token pressure when available.
- Remaining credit or quota only when explicitly available from a trusted source.
- Last update time and evidence source.

## Provider Balance Model

Provider balance should be represented as structured view-model data:

```text
ProviderBalanceView
- providers: ProviderBalanceItem[]
- selected_provider: optional provider id
- routing_owner: Relay | Prime | unknown
- policy_state: ok | warning | degraded | blocked
- evidence_refs: telemetry, adapter metadata, budget snapshot, user override

ProviderBalanceItem
- provider_id: claude | openai | deepseek | openrouter | local | other
- display_name
- model_name
- trust_state: trusted | candidate | degraded | blocked | unknown
- health: ok | warning | degraded | blocked
- context_budget_tokens: optional int
- prompt_budget_tokens: optional int
- current_prompt_tokens: optional int
- prompt_budget_percent: optional float
- prompt_delta_tokens: optional int
- cost_pressure: none | low | medium | high | unknown
- quota_state: available | limited | exhausted | unknown
- notes: short human-readable status
```

## Prompt Payload Visibility

Every model dispatch or Q-mode build prompt must have an observable payload snapshot.

Bifrost must show:

- Current prompt size label.
- Estimated tokens.
- Budget percent.
- Delta from the previous prompt in the same session/lane.
- Whether the prompt is flat, growing, or over budget.
- Which component produced the payload: Relay, queue/Q-mode, review, or manual prompt.
- Evidence reference to the Relay/Model Harness payload snapshot.

This is the Meridian version of the Polaris prompt-size visibility that exposed additive DeepSeek prompts. Bifrost should make additive prompt growth obvious before it burns credits or fills context.

## Q-Mode Prompt Drag Rules

For queue polling and build-lane prompts:

- Repeated Q-mode checks should normally send the current task or bounded delta, not the entire accumulated session history.
- If prompt size grows across idle checks without a task-changing reason, Bifrost must display a degraded prompt-drag warning.
- If DeepSeek Q-mode payloads grow additively, Bifrost must mark DeepSeek as degraded for Q-mode until Relay/Model Harness proves flat prompts.
- Read-check-only activity must not be treated as productive work and must not hide payload growth.
- Prompt-drag warnings must be visible in the provider balance surface and available to Prime as structured telemetry.

## DeepSeek Requirements

DeepSeek is a primary provider candidate, but not automatically trusted.

Bifrost must display:

- Direct API vs aggregator/OpenRouter route when known.
- Candidate trust state until the DeepSeek validation gate passes.
- Q-mode flatness status.
- Whether external Codex review is required for DeepSeek-produced code.
- Whether DeepSeek is blocked from review-clearing, branch movement, or autonomous coding authority.

If a direct DeepSeek test is expected but telemetry shows an OpenRouter route, Bifrost must display a route mismatch warning.

## Warning States

Bifrost must surface these warning/degraded states:

- Prompt payload over budget.
- Prompt payload grows unexpectedly across Q-mode checks.
- Provider quota exhausted or unknown during active dispatch.
- Provider trust state is candidate/degraded/blocked.
- DeepSeek direct-vs-aggregator route mismatch.
- Missing prompt snapshot evidence.
- Missing provider metadata.
- Aegis blocks dispatch due to risk tier or proof requirements.
- Relay cannot identify the routing owner.

## Out Of Scope

- Bifrost does not calculate provider pricing from scratch.
- Bifrost does not call vendor billing APIs in this contract.
- Bifrost does not decide provider routing.
- Bifrost does not approve DeepSeek trust promotion.
- Bifrost does not hide prompt payload growth to keep the UI clean.

## Acceptance Criteria

- Provider balance is represented as structured view-model data.
- Prompt payload visibility is available for every dispatch/Q-mode prompt.
- Q-mode additive prompt growth is visible as degraded prompt drag.
- DeepSeek route/trust state is visible and cannot be confused with OpenRouter fallback.
- Bifrost displays Relay/Model Harness telemetry but does not make routing decisions.
