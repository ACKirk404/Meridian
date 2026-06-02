# Relay PromptPacket Proof Metadata Implementation Checklist

**Status:** Build-ready checklist; runtime implementation not authorized by this doc
**Owner harnesses:** Relay (packet/dispatch), Aegis (proof policy), Model Harness (telemetry), Bifrost (display)
**Source docs:** `docs/relay-dispatch-hardening-implementation-checklist.md`, `docs/relay-prompt-payload-visibility-implementation-checklist.md`, `docs/model-harness-v2-contract.md`, `docs/relay-prompt-packet-integration-plan.md`, `docs/prompt-packet-implementation-checklist.md`, `docs/relay-bifrost-proof-payload-contract.md`, `docs/v2-progress-tracker.md`

## Boundary

This checklist defines implementation gates for binding PromptPacket proof metadata into Relay dispatch envelopes and audit output. It does not edit runtime code, tests, FileMap, Bifrost UI, model/account/process code, branches, Polaris, or shared main.

The central invariant stays unchanged: `PromptPacket.model_payload()` returns only `serialized_prompt`. Every proof, budget, lineage, hash, Aegis, and Bifrost field below is metadata for Relay, audit, Prime, Review Console, and Bifrost. It must not be injected into the worker prompt.

## 1. Packet Identity And Correlation

- [ ] Include `packet_id` in every Relay dispatch envelope and audit record that references a PromptPacket.
- [ ] Keep `packet_id` stable, unique enough for dispatch correlation, and traceable to risk tier/lane/role where the runtime lane chooses that format.
- [ ] Include packet correlation in PromptDragTelemetry as `packet_id`.
- [ ] Link packet metadata to `dispatch_id`, `route_id`, `heartbeat_id` when available, lane id, selected provider, exact model id, and action type.
- [ ] Block dispatch if a PromptPacket is missing `packet_id`, if the id is empty, or if duplicate packet ids appear in the same dispatch plan.
- [ ] Never include `packet_id` in `serialized_prompt` or `model_payload()`.

## 2. Packet Hash And Snapshot Evidence

- [ ] Compute a packet prompt hash from the exact `serialized_prompt` string that `model_payload()` returns.
- [ ] Store that hash as packet proof metadata and bind it to `prompt_payload_snapshot_hash` when the adapter supports payload snapshots.
- [ ] Preserve hash algorithm/version in metadata, such as `sha256`, so audit can recompute it.
- [ ] Record whether hash evidence is `required`, `present`, `unavailable`, or `missing`.
- [ ] For direct providers with snapshot support, require prompt hash evidence before treating dispatch proof as complete.
- [ ] For aggregator routes, mark packet prompt hash as Relay-side proof only; do not claim the aggregator preserved the exact payload unless adapter telemetry proves it.
- [ ] Never store raw prompt text in Bifrost-visible hash/proof payloads.

## 3. Budget Reference Binding

- [ ] Bind PromptPacket metadata to the `PromptBudgetPlan` used at packet construction.
- [ ] Include safe budget refs: budget tier, max context tokens, allowed sources, prompt tokens, budget percent/status, and budget compliance.
- [ ] Preserve the route's prompt budget identity or stable summary so audit can verify packet budget matched route budget.
- [ ] Block or demote dispatch when `prompt_tokens > budget.max_context_tokens`.
- [ ] Block dispatch when the packet budget is absent, malformed, or not the same budget selected by Relay route planning.
- [ ] Keep budget reason and budget source limits out of worker prompt text unless Relay intentionally includes a source as part of the serialized prompt content.

## 4. Allowed Source And Lineage Proof

- [ ] Carry `source_lineage` as immutable packet metadata for audit and prompt-drag analysis.
- [ ] Validate every lineage key against `budget.allowed_sources`.
- [ ] Preserve token counts per source and ensure `sum(source_lineage.values()) <= prompt_tokens`.
- [ ] Record lineage compliance status in the dispatch envelope.
- [ ] Block dispatch when disallowed sources appear, lineage counts are negative, lineage total exceeds packet tokens, or lineage cannot be represented.
- [ ] Bifrost may display source names and token counts as safe metadata; it must not display raw source text.
- [ ] File/docs/memory/review snippets must be counted by source before packet sealing, not reconstructed after dispatch.

## 5. Proof Requirement Fields

- [ ] Attach Relay proof requirement metadata to the packet's dispatch envelope: required proof type, risk tier, human gate flag, dual-lane requirement, and review requirement.
- [ ] Attach Aegis policy outcome references: cognition policy result id when available, gate decision, severity, waiver/approval status, and fallback blockers.
- [ ] Attach exact model/trust proof fields from Model Harness metadata: trust mode, proof strength, external-review status, blocked authorities, and telemetry capability snapshot.
- [ ] Preserve a clear distinction between packet validity proof and model-output proof.
- [ ] Do not allow a valid PromptPacket by itself to prove that dispatch is allowed; Aegis and route metadata gates still apply.
- [ ] Do not allow model output to retroactively satisfy missing packet proof metadata.

## 6. Aegis Evidence Id Binding

- [ ] Attach ordered Aegis `evidence_ids` to the dispatch audit when a gate or proof check contributes evidence.
- [ ] Preserve the stable proof payload keys: `gate_decision`, `severity`, `evidence_ids`, `waiver_present`, `explanation`, and `fallback_blockers_from_aegis`.
- [ ] Keep evidence ids immutable or snapshot-like once dispatch audit is created.
- [ ] Require evidence ids for risk tiers or policy paths that claim structured proof.
- [ ] Block or route to Review Console when Aegis evidence is required but absent.
- [ ] Bifrost must display evidence ids as references only; it must not call Aegis validators or mutate evidence.

## 7. Raw Prompt And Metadata Exclusions

- [ ] Confirm `model_payload()` remains the only model-facing string.
- [ ] Confirm `packet_id`, budget fields, source lineage, construction time, Aegis fields, hashes, dispatch ids, provider metadata, and Bifrost labels do not appear in `serialized_prompt` unless intentionally included as user/task content before packet construction.
- [ ] Exclude raw prompt text from Bifrost-visible packet metadata; use packet id, prompt label, token counts, source lineage summary, and hash instead.
- [ ] Exclude credentials, API keys, account identifiers, request headers, raw provider responses, and process handles from packet proof metadata.
- [ ] Redact or block serialized audit output if secret-like values appear in packet metadata fields.

## 8. Relay Dispatch Envelope Integration

- [ ] Add packet proof metadata to the provider-neutral dispatch envelope before adapter transport.
- [ ] Include packet id, packet hash, budget refs, lineage compliance, prompt token counts, proof requirement, Aegis evidence ids, and payload snapshot status.
- [ ] Keep provider-specific HTTP bodies inside adapters; dispatch envelope metadata is not a provider request body.
- [ ] Fail closed when PromptPacket validation fails; no dispatch envelope may proceed to model transport from an invalid packet.
- [ ] Preserve pre-dispatch block reasons separately from transport failures and post-response telemetry gaps.
- [ ] Ensure retry/fallback does not reuse stale packet proof metadata if the prompt, route, provider, model, or source lineage changed.

## 9. Bifrost Handoff

- [ ] Bifrost must receive packet proof metadata as structured handoff data from Relay.
- [ ] Bifrost must show packet id/reference, prompt label, prompt tokens, budget percent/status, allowed source compliance, prompt hash availability, Aegis evidence ids, gate decision, and fallback blockers.
- [ ] Bifrost must not call Relay packet assembly, Aegis validators, Model Harness adapters, or provider APIs to reconstruct packet proof state.
- [ ] Bifrost must display missing packet proof metadata, disallowed sources, over-budget packets, missing Aegis evidence, and hash/snapshot gaps as warnings or blocks according to Relay state.
- [ ] Bifrost must not display raw prompt text or raw source content in the packet proof surface.
- [ ] Bifrost must not mutate packet proof payloads or create waiver/approval/evidence records.

## 10. Block Conditions

Relay must block or route to Review Console before model dispatch when:

- [ ] PromptPacket construction fails validation.
- [ ] `packet_id` is missing, empty, or duplicated in the dispatch plan.
- [ ] Packet budget is missing, malformed, or does not match the selected Relay route budget.
- [ ] `prompt_tokens` exceeds `budget.max_context_tokens`.
- [ ] `source_lineage` includes disallowed sources or invalid counts.
- [ ] Packet prompt hash is required but cannot be computed.
- [ ] Required Aegis evidence ids or proof payload keys are absent.
- [ ] Packet proof metadata would leak raw prompt text, credentials, raw provider response, or transport internals.
- [ ] Bifrost cannot show packet proof state from structured metadata.
- [ ] A retry/fallback would change route/model/provider/source lineage without a new packet proof snapshot.

## 11. Tests And Proof Expectations

- [ ] Unit tests for packet proof metadata construction from a valid PromptPacket.
- [ ] Unit tests for packet id correlation across dispatch envelope, telemetry, and audit record.
- [ ] Unit tests for packet hash calculation from `model_payload()` and hash stability for unchanged prompts.
- [ ] Unit tests proving packet metadata does not appear in `serialized_prompt` or `model_payload()`.
- [ ] Unit tests for budget ref binding, budget mismatch blocks, and over-budget blocks.
- [ ] Unit tests for allowed source lineage compliance, disallowed source blocks, and lineage total validation.
- [ ] Unit tests for Aegis evidence id binding and missing-evidence blocks.
- [ ] Unit tests for raw prompt, credential, raw response, and transport-internal exclusion from serialized audit/Bifrost handoff.
- [ ] Unit tests for retry/fallback requiring a fresh packet proof snapshot when prompt or route inputs change.
- [ ] Snapshot/render tests proving Bifrost can display packet proof metadata from structured data only.
- [ ] Scope proof that packet proof metadata assembly does not call live models, probe accounts, start sessions, inspect live processes, edit branches, or touch Polaris.
- [ ] FileMap registration must be routed for any new runtime module, test file, or implementation doc created by implementation lanes.

## 12. Runtime Enablement Gate

PromptPacket proof metadata may be treated as runtime-ready only after:

- [ ] Packet id/hash/budget/source-lineage proof metadata exists and is tested.
- [ ] Aegis evidence ids and proof payload keys are bound into dispatch audit without mutation.
- [ ] Dispatch envelopes carry packet proof metadata before provider transport.
- [ ] Raw prompt and secret exclusions are tested.
- [ ] Bifrost displays packet proof state from structured metadata.
- [ ] Required runtime/UI tests pass in owning lanes.
- [ ] Codex review clears this checklist and the future runtime implementation.
- [ ] Auto routing remains disabled until routing, prompt payload visibility, dispatch hardening, PromptPacket proof metadata, Aegis policy, and Bifrost proof display are reviewed together.
