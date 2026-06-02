# DeepSeek Candidate Trust Metadata Implementation Checklist

**Status:** Build-ready checklist; runtime implementation not authorized by this doc
**Date:** 2026-06-02
**Owner harnesses:** Model Harness (metadata), Relay (routing/telemetry), Aegis (policy gates), Bifrost (display)
**Scope:** DeepSeek candidate-trust metadata and Model Harness prompt-drag evidence

---

## Purpose

Define the implementation checklist for DeepSeek candidate-trust metadata inside the provider-neutral Model Harness. The next runtime slice should be able to wire DeepSeek route metadata, prompt-drag telemetry, and Relay/Aegis policy decisions without waiting on live provider access.

This is docs-only. It does not edit runtime code, tests, FileMap, Bifrost UI, provider credentials, model/account/process code, branches, shared main, or Polaris.

---

## Source Facts To Preserve

- [ ] DeepSeek direct dispatch id is exactly `deepseek-chat`.
- [ ] `deepseek-v4-pro` and `deepseek-v4-flash` are variant/capability labels only; they must not become adapter registry keys or provider request model values.
- [ ] Direct-provider endpoint proof is the exact audit string `https://api.deepseek.com/v1/chat/completions`.
- [ ] Direct routes declare `api_mode` / trust mode as direct; aggregator routes declare aggregator trust separately and never inherit direct-provider authority.
- [ ] DeepSeek starts in candidate trust with external review required and pending until validation evidence passes.
- [ ] Current candidate lanes are `default_quality` / `deepseek-v4-pro` and `fast` / `deepseek-v4-flash`.
- [ ] Current direct candidate budgets are context `65536`, prompt payload `57344`, max output `8192`, and tokenizer family `deepseek`.
- [ ] Initial allowed task types are `verify` and `explain`.
- [ ] Initial blocked task types include `build`, `review`, `release`, `destructive`, `branch_movement`, `review_clearance`, and `autonomous_coding`.
- [ ] Initial max risk tier is `1` until review-cleared policy explicitly raises it.
- [ ] `q_mode_flat` is expected `true` for the direct candidate route, but runtime must still emit proof/telemetry rather than relying on prompt prose.
- [ ] DeepSeek must not clear reviews, move branches, bypass Relay/Aegis, or act as an autonomous coding lane while candidate trust is active.

---

## Metadata Surface

Runtime implementation should expose the DeepSeek facts through provider-neutral Model Harness metadata:

- [ ] Keep exact provider/model identity in immutable provider capability metadata: provider `deepseek`, model `deepseek-chat`, variant label, lane, capability tier, context budget, prompt payload budget, max output tokens, tokenizer family, Q-mode flatness, and known authorities.
- [ ] Keep candidate trust fields in immutable trust metadata: direct-vs-aggregator mode, direct endpoint audit string, proof strength, external review required/status/evidence, blocked authorities, and validation timestamp.
- [ ] Keep task permissions in deterministic allowed/blocked task metadata: allowed actions, blocked actions, max risk tier, and human-readable reason.
- [ ] Keep telemetry capability flags: completion tokens, latency, prompt payload snapshot, and response hash support.
- [ ] Preserve compatibility with current `ModelHarnessMetadata`, `ModelCandidateRoutePreset`, `deepseek_candidate_route_presets()`, `deepseek_candidate_metadata_preset()`, and `ModelRouteMetadataBinding` until replacement surfaces are review-cleared.
- [ ] Serialize `deepseek_candidate_state` as display-safe strings only; no raw prompts, raw responses, credentials, account identifiers, transport headers, process/session-control state, branch/worktree state, or Polaris references.

---

## Exact Dispatch Identity

- [ ] Register and resolve the direct DeepSeek adapter only by `deepseek-chat`.
- [ ] Treat `deepseek-v4-pro`, `deepseek-v4-flash`, marketing names, aliases, and UI labels as metadata attached to the exact dispatch id.
- [ ] Fail closed when Relay receives a DeepSeek direct request whose dispatch model is not `deepseek-chat`.
- [ ] Fail closed when a variant label equals or masquerades as the dispatch model.
- [ ] Emit deterministic `route_mismatch` / `unknown_model_id` style tags when model id, provider id, adapter registry key, or request body model disagree.
- [ ] Verify the outbound provider request body uses `model: "deepseek-chat"` for direct DeepSeek requests.

---

## Direct Versus Aggregator Proof

- [ ] Direct DeepSeek metadata must carry the exact endpoint audit string and direct trust mode.
- [ ] The endpoint must not be supplied by prompt text, runtime UI state, account probing, or a dispatch-time override.
- [ ] Aggregator routes, including OpenRouter-style routes, must be represented as separate aggregator metadata with no direct endpoint and no direct-provider authority.
- [ ] Aggregator routes must not claim Q-mode flatness, prompt snapshot support, response hash support, external review clearance, or validation evidence from the direct route.
- [ ] Relay/Aegis must block direct-required work when only aggregator evidence is present.
- [ ] Bifrost must display direct versus aggregator state and route mismatch warnings without deciding the route.

---

## Candidate Trust And Validation Gate

- [ ] Candidate trust remains active until the validation gate records passing external review evidence.
- [ ] `requires_external_review` is true and `external_review_status` starts as pending.
- [ ] Pending, failed, expired, missing, or mismatched external review status blocks any tier/action requiring passed review.
- [ ] Trust promotion must require structured validation evidence, review evidence id, and a review-cleared code/doc change; successful live calls alone cannot promote trust.
- [ ] Failed validation must demote or block the candidate route before code lands.
- [ ] Candidate trust cannot authorize review clearing, branch/worktree movement, queue orchestration, autonomous implementation, or bypasses around Relay, Aegis, prompt payload metering, or Bifrost visibility.
- [ ] Promotion/demotion evidence must be deterministic and display-safe: review id, validation level, timestamp, pass/fail status, and reason tags only.

---

## Prompt-Drag Telemetry

- [ ] Relay records prompt token estimate from sealed PromptPacket metadata, not raw prompt logging.
- [ ] Relay records context budget, prompt payload budget, budget percent, budget status, growth delta tokens, and growth percent from Model Harness metadata plus prompt payload snapshots.
- [ ] Repeated Q-mode prompts must show flatness or a deterministic degraded prompt-drag tag when prompt growth is unexplained.
- [ ] Direct route snapshot/hash capability must be surfaced through support flags and safe hash fields.
- [ ] Missing snapshot, missing token count, unavailable telemetry, over-budget payload, and degraded growth must emit deterministic warning/block tags.
- [ ] Prompt-drag evidence feeds Relay decision records and Aegis policy; it must not be hidden as a UI-only warning.
- [ ] Telemetry must not include raw prompt text, raw source snippets, raw provider request bodies, raw provider responses, credentials, request headers, account identifiers, process ids, session-control state, branch/worktree state, shared-main paths, or Polaris references.

---

## Relay And Aegis Policy Binding

- [ ] Relay resolves DeepSeek metadata before provider transport.
- [ ] Aegis reads exact model id, route trust mode, external review status, allowed/blocked task type, max risk tier, Q-mode flatness, budget status, prompt-drag state, and blocked authorities.
- [ ] Missing metadata, unknown trust route, wrong dispatch id, variant-as-model, endpoint mismatch, aggregator masquerade, blocked action type, risk tier exceeded, pending/failed/expired review, and degraded prompt-drag state fail closed according to risk policy.
- [ ] Candidate DeepSeek cannot clear reviews, move branches, perform autonomous coding, or bypass Relay/Aegis even when a model call succeeds.
- [ ] Model output must never become proof that the route was safe to dispatch.
- [ ] Relay decision records should include display-safe candidate trust tags and evidence references for Bifrost and review lanes.

---

## Bifrost Display Expectations

Bifrost should receive structured Relay/Model Harness data only:

- [ ] Provider id `deepseek`.
- [ ] Exact model id `deepseek-chat`.
- [ ] Safe variant label, such as `deepseek-v4-pro` or `deepseek-v4-flash`.
- [ ] Lane, capability tier, direct-vs-aggregator state, trust state, and external review status.
- [ ] Direct endpoint proof status or route mismatch warning, without credential/account details.
- [ ] Allowed/blocked task summary, max risk tier, review-clearing false, branch-movement false, autonomous-coding false, bypass false.
- [ ] Context budget, prompt payload budget, token estimate, budget percent/status, growth delta, prompt-drag state, and Q-mode flatness status.
- [ ] Snapshot/hash availability and telemetry capability flags, not raw prompt or raw response bodies.

Bifrost must not choose providers, approve trust promotion, call provider/account/billing APIs, call Relay dispatch helpers, call Aegis evaluators, mutate metadata, hide degraded prompt-drag state, or display credentials/raw prompts/raw provider responses.

---

## Deterministic Test Expectations

Future runtime implementation should add focused tests for:

- [ ] DeepSeek candidate presets dispatch only with `deepseek-chat`.
- [ ] `deepseek-v4-pro` and `deepseek-v4-flash` remain variant labels and cannot masquerade as dispatch ids.
- [ ] Direct endpoint proof equals `https://api.deepseek.com/v1/chat/completions`.
- [ ] Direct and aggregator metadata cannot be conflated.
- [ ] Candidate trust starts with external review required and pending.
- [ ] Pending/failed/expired/missing review status blocks review-required tiers.
- [ ] Allowed actions are limited to `verify` and `explain`; blocked actions include build, review, release, destructive, branch movement, review clearance, and autonomous coding.
- [ ] Max risk tier is enforced while candidate trust is active.
- [ ] Q-mode flatness, prompt token estimate, budget percent/status, growth delta, degraded prompt-drag tag, snapshot support, and response hash support serialize deterministically.
- [ ] Relay/Aegis receive model metadata and prompt-drag tags before provider transport.
- [ ] Bifrost display data contains only display-safe metadata and no raw prompt/response/credential/account/process/session/branch/main/Polaris sentinel strings.
- [ ] Same candidate preset and same prompt payload snapshot produce the same serialized evidence.
- [ ] Tests use fakes/fixtures only and do not perform live provider calls.

---

## Validation-Gate Evidence

- [ ] Level 0 evidence: direct adapter metadata exists; provider, model, endpoint, trust, task permissions, and budgets are structured; prompt payload size is visible before dispatch.
- [ ] Level 0 evidence: repeated Q-mode queue polls do not replay additive prompt history unless the task changed.
- [ ] Level 1+ evidence: any assisted coding use has benchmark proof, unit-test proof, allowlist proof, and external review proof.
- [ ] Level 2+ evidence: any gated build-lane use has representative Meridian slice proof, failure/demotion behavior, prompt-drag comparison, and unique-worktree proof.
- [ ] Level 3 evidence: any primary-provider promotion has sustained pass-rate proof, cost/latency visibility, and Aegis dual-lane/human-gate compatibility.
- [ ] Validation evidence must be stored as structured tags, timestamps, commit/report ids, and pass/fail states; never as raw prompts, raw responses, provider account details, or process/session state.

---

## Explicit Exclusions

This checklist does not authorize:

- Live provider calls or live model validation.
- Credential discovery, provider billing calls, account probing, quota scraping, or provider account mutation.
- Raw prompt, raw source text, raw provider request body, raw provider response, credential, request header, account identifier, process/session-control, branch/worktree, shared-main, push-to-main, or Polaris exposure.
- Runtime code changes, runtime tests, Relay runtime wiring, Bifrost UI implementation, FileMap edits, process/session control, branch movement, merge/rebase/reset/cherry-pick/stash-pop, shared-main writes, pushes to main, or Polaris work.

---

## Runtime Enablement Gate

DeepSeek candidate-trust metadata runtime work is ready only after:

- This checklist clears Codex review.
- Model Harness exposes exact DeepSeek dispatch identity, direct-vs-aggregator metadata, trust state, task permissions, and telemetry capability fields.
- Relay consumes metadata and prompt-drag evidence before provider transport.
- Aegis gates exact model id, candidate trust, external review, task type, risk tier, direct endpoint proof, and prompt-drag state.
- Bifrost receives display-safe DeepSeek candidate trust and prompt payload state.
- Deterministic tests cover identity, trust, routing, prompt-drag, policy, display, redaction, and no-live-call behavior.
- Reviews A/B clear the runtime implementation before any DeepSeek route depends on the new metadata.
