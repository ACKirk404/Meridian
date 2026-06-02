# Model Harness Metadata And Prompt-Drag Telemetry Implementation Checklist

**Status:** Build-ready checklist; runtime implementation not authorized by this doc
**Date:** 2026-06-02
**Owner harnesses:** Model Harness (metadata), Relay (telemetry/enforcement), Aegis (policy gates), Bifrost (display)
**Scope:** Provider-neutral model capability metadata and prompt-drag telemetry implementation plan

---

## Purpose

Define the implementation checklist for the next Model Harness / Relay slice: provider-neutral model capability metadata, trust state, route ownership, prompt-drag telemetry, and Bifrost-visible prompt payload status. This checklist bridges the reviewed `docs/model-harness-v2-contract.md` with the current `meridian_core/model_adapter.py` and Relay prompt-payload evidence surfaces.

This is docs-only. It does not edit runtime code, tests, FileMap, Bifrost UI, model/account/process code, branches, shared main, or Polaris.

---

## Metadata Surface

Runtime implementation should keep or extend the current provider-neutral adapter boundary with frozen, serializable metadata objects:

- [ ] `ProviderCapability`: provider, exact model id, context window, max output tokens, cost posture, latency tier, streaming support, tokenizer family, thinking support, vision scope, Q-mode flatness, and known authorities.
- [ ] `ModelTrustState`: provider, exact model id, direct-vs-aggregator trust mode, direct API endpoint audit string, proof strength, external-review requirement/status/evidence, blocked authorities, and validation timestamp.
- [ ] `AllowedTaskTypes`: allowed action types, blocked action types, max risk tier, and human-readable gate reason.
- [ ] `TelemetryCapability`: completion-token support, latency support, prompt payload snapshot support, and response hash support.
- [ ] Preserve current `ModelHarnessMetadata`, `ModelCandidateRoutePreset`, and `ModelRouteMetadataBinding` compatibility until replacement surfaces are review-cleared.
- [ ] Keep metadata immutable or snapshot-like after adapter registration; later registry changes must not mutate prior dispatch audit records.

---

## Exact Model Identity

- [ ] Use exact provider dispatch ids as the only `AdapterRegistry` keys.
- [ ] Treat provider marketing names, route-family labels, aliases, UI labels, and variant labels as metadata only.
- [ ] Preserve DeepSeek direct dispatch key as `deepseek-chat`; `deepseek-v4-pro` and `deepseek-v4-flash` remain variant labels, not dispatch ids.
- [ ] Block Tier 2+ dispatch when exact model id is missing, unknown, aliased, or inconsistent with provider metadata.
- [ ] Test that exact id, provider id, and adapter registration agree before Relay transport.

---

## Provider And Route Trust

- [ ] Represent direct provider routes and aggregator routes explicitly.
- [ ] Require direct API endpoint audit string for direct routes and `None`/unavailable endpoint for aggregators.
- [ ] Cap aggregator routes according to Aegis/Relay policy; aggregator proof must not imply direct-provider authority.
- [ ] Preserve candidate/degraded/blocked/unknown trust states without Relay promoting them from successful transport alone.
- [ ] Require `external_review_status == passed` when a provider/model declares external review required for the selected tier.
- [ ] Preserve blocked authorities as deterministic tags and feed them into Relay/Aegis block decisions.
- [ ] Verify DeepSeek remains candidate trust until validation evidence clears review.

---

## Prompt-Drag Telemetry

Relay should create one prompt-drag telemetry record per model dispatch or Q-mode prompt:

- [ ] `call_id`, provider, exact model id, packet id, route id, dispatch id, lane/session reference when safe.
- [ ] Prompt token estimate from sealed PromptPacket, not from raw prompt logging.
- [ ] Completion tokens and total tokens when adapter telemetry supports them.
- [ ] Context window and prompt payload budget from model metadata.
- [ ] Budget percent and budget status.
- [ ] Previous prompt token count, growth delta tokens, and growth percent.
- [ ] Growth state: flat, expected_growth, degraded, over_budget, or unknown.
- [ ] Prompt payload snapshot hash when supported and required.
- [ ] Response hash when supported and display-safe.
- [ ] Adapter support flags for completion tokens, latency, prompt snapshot, and response hash.
- [ ] Deterministic error/warning tags such as `prompt_snapshot_missing`, `budget_exceeded`, `telemetry_unavailable`, `prompt_drag_degraded`, and `route_mismatch`.

Telemetry must not include raw prompt text, raw source snippets, raw provider responses, credentials, request headers, account identifiers, process ids, session-control state, branch/worktree data, or Polaris references.

---

## Budget And Prompt Payload Status

- [ ] Compute prompt budget percent from estimated prompt tokens and prompt payload budget; handle zero, missing, or invalid budgets without crashing.
- [ ] Emit budget status values that Bifrost can render, such as healthy, warning, degraded, over_budget, blocked, or unknown.
- [ ] Mark over-budget prompts as blocked before provider transport when policy requires.
- [ ] Preserve prompt size labels for Bifrost, including `(under 1k)`, `(N.Nk)`, and `(over budget)` where the UI surface expects them.
- [ ] Track growth delta between prompts in the same lane/session and explain expected growth reasons.
- [ ] Mark repeated Q-mode prompts as degraded when they grow without a task-changing reason.
- [ ] Treat prompt-drag degraded state as Relay/Aegis evidence, not as a hidden UI-only warning.

---

## Aegis And Relay Policy Binding

- [ ] Relay resolves adapter metadata before dispatch and before provider transport.
- [ ] Aegis checks allowed/blocked task types, max risk tier, trust mode, proof strength, external-review status, blocked authorities, prompt budget, and prompt-drag state.
- [ ] Unknown trust route, missing metadata, missing exact model id, blocked action type, risk tier exceeded, external review failed/expired/pending, and insufficient proof strength fail closed.
- [ ] Model output must not become proof of dispatch safety.
- [ ] Successful transport must not promote trust state or clear external review requirements.
- [ ] Prompt-drag degraded state should produce deterministic warning/block tags for Relay decision records and Bifrost handoff.

---

## Bifrost Display Expectations

Bifrost should receive structured Relay/Model Harness telemetry only:

- [ ] Provider id and display name.
- [ ] Exact model id plus safe variant label when present.
- [ ] Direct-vs-aggregator route and trust state.
- [ ] Context window and prompt payload budget.
- [ ] Current prompt token estimate, budget percent, and status.
- [ ] Growth delta tokens/percent and growth state.
- [ ] Q-mode flatness and prompt-drag degraded state.
- [ ] External review requirement/status/evidence reference.
- [ ] Blocked authorities and Relay/Aegis policy tags.
- [ ] Adapter telemetry capability flags.
- [ ] Snapshot/hash availability, not raw prompt or raw response bodies.

Bifrost must not choose providers, approve trust promotion, call billing/provider APIs, call Aegis, call Relay dispatch helpers, mutate metadata, hide degraded prompt-drag state, or display credentials/raw prompts/raw provider responses.

---

## Deterministic Test Expectations

Future runtime implementation should add focused tests for:

- [ ] Provider capability metadata is immutable, serializable, and uses exact model id.
- [ ] Adapter registry blocks missing, unknown, aliased, or provider-mismatched model ids.
- [ ] DeepSeek candidate presets dispatch with `deepseek-chat` and keep `deepseek-v4-pro` / `deepseek-v4-flash` as variant labels only.
- [ ] Trust state blocks unknown, failed, expired, pending-required, or blocked-authority routes.
- [ ] Allowed/blocked task metadata enforces action type and max risk tier.
- [ ] Prompt token estimate, budget percent/status, growth delta, and degraded prompt-drag tags are deterministic.
- [ ] Zero, missing, or invalid budgets fail safely.
- [ ] Q-mode repeated prompts mark degraded when growth is unexplained.
- [ ] Direct provider snapshot support and aggregator snapshot unavailability map to correct telemetry/status tags.
- [ ] Relay/Aegis decision records receive model metadata and prompt-drag tags without raw prompt leakage.
- [ ] Bifrost receives display-safe provider/payload state from structured data only.
- [ ] Sentinel raw prompt, credential, raw provider response, account, process/session-control, branch/worktree, main-write, and Polaris strings are absent or redacted.
- [ ] Same adapter metadata and prompt snapshot input produce the same telemetry and serialized handoff.

---

## Explicit Exclusions

This checklist does not authorize:

- Live model calls.
- Credential discovery, provider billing calls, account probing, or quota scraping.
- Raw prompt, raw source text, raw provider request/response, credential, account, process/session-control, branch/worktree, main-write, or Polaris exposure.
- Relay runtime implementation, Bifrost UI implementation, FileMap edits, runtime tests, branch movement, merge/rebase/reset/cherry-pick/stash-pop, shared-main writes, or pushes to main.

---

## Runtime Enablement Gate

Model Harness metadata runtime work is ready only after:

- This checklist clears Codex review.
- Provider capability/trust/task/telemetry metadata surfaces are implemented and tested.
- Relay consumes metadata before provider transport.
- Aegis gates exact model id, trust state, external review, allowed tasks, budget, and prompt-drag evidence.
- Bifrost receives structured display-safe metadata and prompt payload telemetry.
- Raw prompt, credential, provider response, account, process/session-control, branch/worktree, main-write, and Polaris exclusions are tested.
- Reviews A/B clear the runtime implementation before live routing depends on it.
