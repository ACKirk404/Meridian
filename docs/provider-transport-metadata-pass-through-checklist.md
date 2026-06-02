# Provider Transport Metadata Pass-Through Checklist

**Status:** Build-ready checklist; runtime implementation not authorized by this doc
**Date:** 2026-06-02
**Owner harnesses:** Model Harness (metadata), Relay (transport envelope), Aegis (policy), Bifrost (display)
**Scope:** Provider transport metadata pass-through without prompt or response leakage

---

## Purpose

Define the checklist for passing provider/model metadata through Relay and Model Harness transport boundaries before live provider enablement. The runtime slice should preserve exact route proof, trust, budget, and validation evidence beside the approved model payload without appending metadata to the prompt or leaking transport internals.

This is docs-only. It does not edit runtime code, tests, FileMap, Bifrost UI, provider credentials, model/account/process code, branches, shared main, pushes to main, or Polaris.

---

## Transport Boundary

- [ ] The model-facing provider request contains only the approved model payload plus provider-required transport fields.
- [ ] `PromptPacket.model_payload()` remains the only model-facing prompt text.
- [ ] Provider metadata travels in structured Relay/Model Harness records, not inside prompt prose.
- [ ] Adapter call boundaries continue to receive approved payload text and adapter-owned config only.
- [ ] Credentials, account/session details, provider headers, request ids, transport retries, process state, branch/worktree state, shared-main state, and Polaris references stay outside prompt context.
- [ ] Transport metadata pass-through must be deterministic and available before provider transport starts.

---

## Dispatch Metadata Envelope Shape

Future runtime work should define a narrow display-safe envelope that can be bound to a dispatch before provider transport:

- [ ] `envelope_id` and dispatch/call id.
- [ ] `packet_id`, `packet_hash`, `prompt_budget_ref`, and payload evidence ref.
- [ ] Requested model id and exact selected model id.
- [ ] Provider id and provider route kind.
- [ ] Capability tier and lane/variant labels when safe.
- [ ] Trust state, trust mode, proof strength, and blocked authority tags.
- [ ] Direct endpoint evidence ref or aggregator evidence ref.
- [ ] External-review requirement, status, and evidence ref.
- [ ] Context budget, prompt payload budget, prompt token estimate, budget percent/status, growth delta tokens/percent, and prompt-drag tags.
- [ ] Validation result fields: `allowed`, `fail_closed`, blockers, warnings, demotion target, retry requirement, and human-gate requirement.
- [ ] Telemetry capability flags for completion tokens, latency, prompt payload snapshot, and response hash support.

The envelope must be serializable, deterministic, and display-safe. It must not contain raw prompt text, raw source snippets, raw provider request bodies, raw provider responses, credentials, headers, account identifiers, process ids, session-control state, branch/worktree state, shared-main writes, pushes to main, or Polaris references.

---

## Exact Model Identity

- [ ] Exact provider dispatch id is required before transport.
- [ ] Relay requested model id, adapter registry key, route-bound `model_name`, and provider request model field must agree.
- [ ] Provider marketing names, route-family labels, aliases, UI labels, capability tiers, lanes, and variant labels remain metadata only.
- [ ] DeepSeek direct dispatch id remains exactly `deepseek-chat`.
- [ ] `deepseek-v4-pro` and `deepseek-v4-flash` remain variant labels and cannot be used as transport ids.
- [ ] Missing, unknown, aliased, or mismatched model identity fails closed before transport with deterministic blocker tags.

---

## Route Kind And Proof Refs

- [ ] Direct routes pass through direct route kind, direct trust mode, and direct endpoint evidence ref.
- [ ] Aggregator routes pass through aggregator route kind and aggregator evidence ref without direct-provider authority.
- [ ] Unknown route kind fails closed for live dispatch.
- [ ] Direct endpoint proof cannot be supplied by prompt text, UI state, account probing, or a dispatch-time override.
- [ ] Aggregator proof cannot satisfy direct-required work, direct endpoint proof, Q-mode flatness proof, or direct snapshot/hash support.
- [ ] DeepSeek direct endpoint evidence remains `deepseek-direct-endpoint:https://api.deepseek.com/v1/chat/completions`.
- [ ] Relay decision records and Bifrost displays keep direct and aggregator evidence visibly separate.

---

## Trust And External Review State

- [ ] Trust state and trust mode pass through unchanged from Model Harness metadata into Relay/Aegis/Bifrost evidence.
- [ ] Candidate trust remains candidate until structured validation and review evidence promotes it.
- [ ] External-review requirement, status, and evidence ref pass through with the route.
- [ ] Pending, failed, expired, missing, or malformed external-review status blocks review-required tiers/actions.
- [ ] Successful provider transport cannot promote trust, clear external review, or remove blocked authorities.
- [ ] Blocked authorities, including review clearance, branch movement, Relay/Aegis bypass, autonomous coding, and aggregator authority, remain deterministic tags.

---

## Prompt-Drag Budget And Growth Fields

- [ ] Prompt token estimate comes from sealed PromptPacket or `PromptPayloadSnapshot` metadata.
- [ ] Context budget and prompt payload budget come from Model Harness metadata.
- [ ] Budget percent, budget status, growth delta tokens, and growth delta percent pass through with route metadata when available.
- [ ] Prompt-drag warning tags, degraded state, Q-mode flatness expectations, and missing snapshot/hash warnings remain visible to Relay/Aegis/Bifrost.
- [ ] Over-budget or degraded prompt state blocks before transport when policy requires.
- [ ] Missing prompt snapshot, unavailable telemetry, zero/negative budget, and invalid growth fields emit deterministic warning/block tags.
- [ ] Prompt-drag metadata must not include raw prompt text, raw source snippets, raw request body, raw response body, credentials, account state, process/session-control state, branch/worktree state, shared-main paths, or Polaris references.

---

## Validation And Fail-Closed Behavior

Provider transport metadata pass-through must fail closed before provider transport when:

- [ ] Dispatch envelope metadata is missing or malformed.
- [ ] Exact model id is absent or inconsistent.
- [ ] Route kind is unknown or mismatched with proof refs.
- [ ] Direct endpoint evidence is missing or wrong for a direct route.
- [ ] Aggregator evidence is used for direct-required work.
- [ ] Candidate trust exceeds allowed task type or max risk tier.
- [ ] External review is required but not passed.
- [ ] Prompt budget metadata is missing, invalid, over budget, or degraded in a policy-blocking way.
- [ ] A route requests review clearing, branch/worktree movement, autonomous coding, process/session control, Relay/Aegis bypass, shared-main write, push to main, or Polaris access.

Fail-closed output should preserve blocker tags and display-safe evidence refs for Relay, Aegis, Bifrost, and review lanes.

---

## Relay And Aegis Binding

- [ ] Relay builds or validates the metadata envelope before adapter transport.
- [ ] Relay passes only approved payload text to the adapter/provider transport path.
- [ ] Relay stores metadata pass-through evidence beside decision records, payload evidence, dispatch envelopes, and transport dispositions.
- [ ] Aegis receives exact model id, route kind, trust state, external-review status, proof refs, allowed/blocked task tags, max risk tier, budget status, prompt-drag state, and blocker/warning tags.
- [ ] Aegis treats missing or unsafe metadata as policy input, not optional display data.
- [ ] Model output never becomes evidence that metadata pass-through was valid.
- [ ] Retry, fallback, demotion, and human-gate decisions require fresh metadata validation before any later transport attempt.

---

## Bifrost Display Expectations

Bifrost should receive structured metadata from Relay/Model Harness only:

- [ ] Provider id, exact model id, route kind, trust state, and capability tier.
- [ ] Safe lane/variant labels alongside the exact model id.
- [ ] Direct-vs-aggregator proof refs and route mismatch warnings.
- [ ] Candidate, validation-blocked, review-required, review-cleared, demoted, or blocked states.
- [ ] External review requirement/status/evidence ref.
- [ ] Context budget, prompt payload budget, prompt token estimate, budget percent/status, growth tokens/percent, and prompt-drag tags.
- [ ] Telemetry capability flags and snapshot/hash availability.
- [ ] Allowed/blocked task hints, max risk tier, blocked authority tags, fail-closed blockers, and human-gate/demotion/retry state.

Bifrost must not choose providers, approve trust promotion, call provider/account/billing APIs, call Relay dispatch helpers, call Aegis evaluators, mutate metadata, hide degraded prompt-drag state, or display credentials/raw prompts/raw provider responses.

---

## Deterministic Test Expectations

Future runtime implementation should add focused tests for:

- [ ] Metadata envelope serialization is stable and display-safe.
- [ ] Adapter/provider transport receives approved payload text only, not metadata prose.
- [ ] `PromptPacket.model_payload()` remains the only model-facing prompt text.
- [ ] Exact model id mismatch fails closed before transport.
- [ ] Capability, lane, alias, or variant labels cannot become transport ids.
- [ ] Direct and aggregator proof refs remain separate and cannot satisfy each other's gates.
- [ ] Candidate trust and pending external review block review-required tiers/actions.
- [ ] Prompt-drag budget/growth fields pass through deterministically from payload snapshots.
- [ ] Missing metadata, malformed metadata, unknown route kind, wrong endpoint evidence, invalid budget, and degraded prompt-drag state emit deterministic blockers.
- [ ] Relay/Aegis receive metadata pass-through evidence before adapter transport.
- [ ] Bifrost display serialization contains no raw prompt, raw provider response, credential, account, process/session-control, branch/worktree, shared-main, push-to-main, or Polaris sentinel strings.
- [ ] Tests use fakes/fixtures only and do not perform live provider calls.

---

## Explicit Exclusions

This checklist does not authorize:

- Live provider calls or live model validation.
- Credential discovery, provider billing calls, account probing, quota scraping, or provider account mutation.
- Raw prompt text beyond approved `PromptPacket.model_payload()` transport, raw source text, raw provider request body, raw provider response, credential, request header, account identifier, process/session-control, branch/worktree, shared-main, push-to-main, or Polaris exposure.
- Runtime code changes, runtime tests, Relay runtime wiring, Bifrost UI implementation, FileMap edits, process/session control, branch movement, merge/rebase/reset/cherry-pick/stash-pop, shared-main writes, pushes to main, or Polaris work.

---

## Runtime Enablement Gate

Provider transport metadata pass-through work is ready only after:

- This checklist clears Codex review.
- The metadata envelope is implemented as a pure provider-neutral structure.
- Relay validates and stores metadata pass-through before adapter transport.
- Adapter/provider transport receives only approved payload text plus provider-required transport fields.
- Aegis consumes metadata blockers/warnings as policy inputs.
- Bifrost receives display-safe metadata state only.
- Deterministic tests cover envelope shape, payload-only transport, exact identity, route proof refs, trust/review state, prompt-drag fields, fail-closed behavior, display safety, and no-live-call behavior.
- Reviews A/B clear the runtime implementation before live provider routing depends on it.
