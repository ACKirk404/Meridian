# Model Harness Runtime Validation Checklist

**Status:** Build-ready checklist; runtime implementation not authorized by this doc
**Date:** 2026-06-02
**Owner harnesses:** Model Harness (metadata validation), Relay (dispatch binding), Aegis (policy gates), Bifrost (display)
**Scope:** Provider-neutral runtime validation gates before live provider enablement

---

## Purpose

Define the runtime validation checklist that must be satisfied before provider-neutral Model Harness metadata can be trusted for live provider dispatch. This checklist turns the reviewed metadata, prompt-drag, and DeepSeek candidate-trust docs into concrete gates for the next implementation slice.

This is docs-only. It does not edit runtime code, tests, FileMap, Bifrost UI, provider credentials, model/account/process code, branches, shared main, pushes to main, or Polaris.

---

## Validation Entry Point

Runtime work should add a pure validation surface that accepts adapter/model metadata plus optional prompt payload snapshot facts and returns deterministic validation evidence before any provider transport:

- [ ] Validate static adapter metadata at adapter registration time.
- [ ] Validate route-bound metadata before Relay transport.
- [ ] Return a structured result with `allowed`, `fail_closed`, blocker tags, warning tags, evidence refs, and display-safe fields.
- [ ] Preserve compatibility with `ModelHarnessMetadata`, `ModelCandidateRoutePreset`, `ModelRouteMetadataBinding`, and `bind_model_route_metadata()` until replacement metadata surfaces are review-cleared.
- [ ] Never read provider credentials, account state, live sessions, process state, branch/worktree state, shared main, or Polaris from the validator.

---

## Required Metadata Fields

- [ ] Provider id is present and non-empty.
- [ ] Exact model id is present and non-empty.
- [ ] Capability tier is present and display-safe.
- [ ] Context budget and prompt payload budget are present, non-negative, and consistent with provider capability metadata.
- [ ] Trust state is present and in the known set for the route.
- [ ] Direct-vs-aggregator route kind is present, with unknown treated as fail-closed for live dispatch.
- [ ] External-review requirement and status are present when the provider declares review-required behavior.
- [ ] Model metadata ref and external review evidence ref are deterministic when metadata is bound for Relay/Bifrost evidence.
- [ ] Telemetry support flags for completion tokens, latency, prompt payload snapshot, and response hash are explicit booleans.
- [ ] Missing, blank, negative, malformed, or unknown required fields produce deterministic blocker tags rather than falling through to transport.

---

## Exact Dispatch Identity

- [ ] Adapter registry keys and route-bound `model_name` use exact provider dispatch ids only.
- [ ] Provider marketing names, capability labels, UI labels, aliases, route-family names, and variant labels remain metadata only.
- [ ] DeepSeek direct dispatch id is exactly `deepseek-chat`.
- [ ] DeepSeek `deepseek-v4-pro` and `deepseek-v4-flash` remain variant labels and must not be accepted as transport ids.
- [ ] Relay requested model id, adapter registry key, route-bound exact model id, and provider request model id must agree before transport.
- [ ] Any mismatch emits a deterministic blocker such as `missing_exact_model_id`, `unknown_model_id`, `variant_label_as_model_id`, or `route_mismatch`.

---

## Direct Versus Aggregator Proof

- [ ] Direct routes carry direct route kind and exact direct API endpoint audit string.
- [ ] Aggregator routes carry aggregator route kind and no direct-provider endpoint authority.
- [ ] Unknown route kind fails closed for live dispatch.
- [ ] Aggregator evidence cannot satisfy direct-required work, direct endpoint proof, Q-mode flatness proof, or direct snapshot/hash proof.
- [ ] DeepSeek direct route proof must carry `https://api.deepseek.com/v1/chat/completions`.
- [ ] Endpoint proof is metadata declared by the adapter, not prompt text, runtime UI state, account probing, or a dispatch-time override.
- [ ] Direct and aggregator route evidence remain separate in Relay decision records and Bifrost display data.

---

## Candidate Trust And External Review

- [ ] Candidate trust is valid only for explicitly allowed low-risk actions and tiers.
- [ ] DeepSeek starts in candidate trust with external review required and pending.
- [ ] Pending, failed, expired, missing, or malformed review status blocks review-required tiers and actions.
- [ ] Successful provider transport cannot promote trust state or clear external review.
- [ ] Trust promotion requires structured validation evidence, review evidence id, timestamp, and a review-cleared change.
- [ ] Candidate routes cannot clear reviews, move branches/worktrees, orchestrate queues, perform autonomous coding, or bypass Relay/Aegis.
- [ ] Validation results preserve demotion/block reason tags so Relay can fail closed and Bifrost can show the route state.

---

## Capability Labels Versus Transport IDs

- [ ] Capability tiers such as `candidate-quality` and `candidate-fast` remain display/routing metadata only.
- [ ] Lane labels such as `default_quality` and `fast` remain metadata only.
- [ ] Variant labels such as `deepseek-v4-pro` and `deepseek-v4-flash` remain metadata only.
- [ ] Validation blocks any runtime path that copies capability, lane, or variant labels into adapter registry keys or provider request model ids.
- [ ] Bifrost may display labels only alongside the exact model id and route kind.

---

## Prompt-Drag And Budget Evidence

- [ ] Prompt token estimate comes from sealed PromptPacket or `PromptPayloadSnapshot` metadata, not raw prompt logging.
- [ ] Context budget and prompt payload budget come from Model Harness metadata.
- [ ] Budget percent, budget status, growth delta tokens, and growth delta percent are bound into `ModelRouteMetadataBinding` when available.
- [ ] Zero, missing, negative, or invalid budgets fail safely and emit deterministic blockers or warnings.
- [ ] Over-budget payloads block before provider transport when policy requires.
- [ ] Repeated Q-mode prompts with unexplained growth emit degraded prompt-drag tags.
- [ ] Snapshot/hash capability flags must match the route kind; missing snapshot/hash support must be visible, not silently assumed.
- [ ] Prompt-drag evidence excludes raw prompt text, raw source snippets, raw provider request bodies, raw provider responses, credentials, request headers, account identifiers, process ids, session-control state, branch/worktree state, shared-main paths, and Polaris references.

---

## Fail-Closed Behavior

Runtime validation must fail closed before provider transport when any of these are true:

- [ ] Required metadata is missing, blank, malformed, or unknown.
- [ ] Exact model id is missing or inconsistent with adapter registry or request body.
- [ ] Capability, lane, alias, or variant label is used as a transport id.
- [ ] Route kind is missing, unknown, or mismatched with direct/aggregator proof.
- [ ] Direct endpoint proof is missing or wrong for a direct route.
- [ ] Aggregator route is used for direct-required work.
- [ ] Candidate trust is used outside allowed task type or max risk tier.
- [ ] External review is required but not passed.
- [ ] Blocked task type, blocked authority, branch/worktree movement, review clearance, or autonomous-coding authority is requested.
- [ ] Prompt payload budget is invalid, over budget, or degraded in a policy-blocking way.

---

## Relay And Aegis Binding

- [ ] Relay resolves and validates adapter metadata before building the transport call.
- [ ] Relay binds route metadata into display-safe decision records with provider, exact model id, route kind, trust state, capability tier, external review status, model metadata ref, and prompt-drag fields.
- [ ] Aegis receives exact model id, trust state, route kind, external-review status, allowed/blocked task tags, max risk tier, budget status, prompt-drag state, and blocker/warning tags.
- [ ] Aegis treats missing metadata, unknown trust, external-review gaps, blocked actions, exceeded risk tier, and degraded prompt-drag state as policy inputs, not optional UI notes.
- [ ] Relay transport disposition preserves fail-closed blockers and retry/demotion requirements without raw prompts or provider responses.
- [ ] Model output never becomes evidence that metadata validation passed.

---

## Bifrost Display Expectations

Bifrost should receive structured, display-safe metadata only:

- [ ] Provider id and display label.
- [ ] Exact model id and safe variant/capability labels.
- [ ] Direct-vs-aggregator route kind and route mismatch warnings.
- [ ] Trust state, external review requirement/status/evidence ref, and candidate/demotion/block tags.
- [ ] Context budget, prompt payload budget, prompt token estimate, budget percent/status, growth tokens/percent, and prompt-drag state.
- [ ] Telemetry support flags and snapshot/hash availability.
- [ ] Allowed/blocked task summary and max risk tier.
- [ ] Review-clearing, branch movement, autonomous-coding, and Relay/Aegis bypass flags when available.

Bifrost must not choose providers, approve trust promotion, call provider/account/billing APIs, call Relay dispatch helpers, call Aegis evaluators, mutate metadata, hide degraded prompt-drag state, or display credentials/raw prompts/raw provider responses.

---

## Deterministic Test Expectations

Future runtime implementation should add focused tests for:

- [ ] Valid metadata passes with stable evidence refs and serialized field order.
- [ ] Missing provider, exact model id, capability tier, trust state, route kind, external review status, context budget, or prompt payload budget fails closed.
- [ ] Negative route risk tier, context budget, or prompt payload budget raises/blocks deterministically.
- [ ] DeepSeek candidate presets dispatch only with `deepseek-chat` and keep `deepseek-v4-pro` / `deepseek-v4-flash` as variant labels.
- [ ] Direct endpoint proof for DeepSeek equals `https://api.deepseek.com/v1/chat/completions`.
- [ ] Aggregator routes cannot satisfy direct-required metadata gates.
- [ ] Candidate trust and pending external review block review-required tiers/actions.
- [ ] Allowed/blocked task and max risk tier checks preserve review-clearance, branch-movement, and autonomous-coding blocks.
- [ ] Prompt-drag budget percent/status/growth/degraded tags serialize deterministically.
- [ ] Relay/Aegis binding receives validated metadata before transport.
- [ ] Bifrost display serialization contains no raw prompt, raw response, credential, account, process/session-control, branch/worktree, shared-main, push-to-main, or Polaris sentinel strings.
- [ ] Tests use fakes/fixtures only and do not perform live provider calls.

---

## Validation Evidence

- [ ] Validation result includes stable blocker tags and warning tags.
- [ ] Validation result includes model metadata ref, external review evidence ref, and prompt payload evidence ref when available.
- [ ] Validation result includes exact model id, provider id, route kind, trust state, external review status, capability tier, and prompt budget status.
- [ ] Validation result distinguishes missing metadata from blocked metadata, degraded metadata, and review-pending metadata.
- [ ] Validation evidence is serializable, deterministic, display-safe, and suitable for Relay/Bifrost handoff.
- [ ] Validation evidence stores ids, tags, timestamps, hashes, and status fields only; never raw prompts, raw provider responses, credentials, account state, process/session-control state, branch/worktree state, shared-main writes, pushes to main, or Polaris references.

---

## Explicit Exclusions

This checklist does not authorize:

- Live provider calls or live model validation.
- Credential discovery, provider billing calls, account probing, quota scraping, or provider account mutation.
- Raw prompt, raw source text, raw provider request body, raw provider response, credential, request header, account identifier, process/session-control, branch/worktree, shared-main, push-to-main, or Polaris exposure.
- Runtime code changes, runtime tests, Relay runtime wiring, Bifrost UI implementation, FileMap edits, process/session control, branch movement, merge/rebase/reset/cherry-pick/stash-pop, shared-main writes, pushes to main, or Polaris work.

---

## Runtime Enablement Gate

Model Harness runtime metadata validation work is ready only after:

- This checklist clears Codex review.
- The validator is implemented as a pure provider-neutral runtime surface.
- Exact identity, route proof, trust, external review, allowed task, budget, prompt-drag, and display-safety gates are tested.
- Relay consumes validation before provider transport.
- Aegis receives validation blockers/warnings as policy inputs.
- Bifrost receives display-safe validation state only.
- Reviews A/B clear the runtime implementation before live provider routing depends on it.
