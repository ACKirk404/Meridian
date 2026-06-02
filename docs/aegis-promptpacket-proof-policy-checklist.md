# Aegis PromptPacket Proof Policy Checklist

**Status:** Implementation checklist for review
**Date:** 2026-06-01
**Owner:** Build 4 / Aegis and Relay policy binding
**Scope:** Aegis evaluation of PromptPacket proof metadata before Relay dispatch
**Audience:** Aegis, Relay, Model Harness, Bifrost, FileMap, Reviews B

---

## Purpose

Define the build-ready policy checklist for how Aegis should evaluate PromptPacket proof metadata before Relay may dispatch a model call. This checklist binds the reviewed Relay PromptPacket proof metadata plan to Aegis gate behavior without editing runtime code in this slice.

The policy boundary is:

- Relay assembles the PromptPacket and dispatch envelope.
- Aegis evaluates packet proof metadata deterministically before dispatch proceeds.
- Relay applies Aegis outcomes to allow, demote, warn, block, or require human review.
- Bifrost receives display-safe proof payload fields only.
- The model-facing payload remains `PromptPacket.model_payload()` only.

---

## Non-Negotiable Invariants

- PromptPacket proof metadata must never be appended to the worker prompt.
- Raw prompt text, credentials, API keys, account state, and session secrets must not enter Aegis evidence IDs, Bifrost proof payloads, or FileMap entries.
- Aegis must be pure: no model calls, account inspection, process control, UI rendering, persistence mutation, branch movement, or Polaris dependency.
- Relay must apply the same Aegis decision for the same packet metadata every time.
- Bifrost must display pre-serialized proof payload fields and must not call Relay or Aegis validators.
- FileMap registration is a separate Build 3 action after review clears this checklist.

---

## Required Inputs To Aegis

Aegis policy evaluation must receive a structured PromptPacket proof view with these fields or an explicit absence marker:

- `packet_id`: stable, non-empty PromptPacket identifier.
- `packet_hash`: stable prompt packet hash when hashing is available or required.
- `packet_hash_status`: one of `present`, `not_required`, `unavailable`, `missing`, or `mismatch`.
- `prompt_tokens`: non-negative token count for the sealed serialized prompt.
- `budget_ref`: prompt budget reference, including `max_context_tokens`, route tier, and budget policy identifier.
- `source_lineage`: immutable source-to-token count mapping.
- `allowed_sources`: immutable source allow-list inherited from the budget policy.
- `proof_requirement`: route-specific proof requirement from Relay/Aegis policy.
- `aegis_evidence_ids`: ordered immutable evidence IDs supporting the gate decision.
- `selected_model_id`: exact model identifier chosen by Relay/Model Harness.
- `model_trust_state`: Model Harness trust state for the selected model/provider.
- `snapshot_requirement`: direct-provider or aggregator snapshot proof requirement.
- `snapshot_status`: one of `present`, `not_required`, `unavailable`, `missing`, or `stale`.
- `human_gate_requirement`: whether human approval is required for the route.
- `dual_lane_requirement`: whether dual-lane proof is required for the route.
- `bifrost_handoff_required`: whether Relay must emit display-safe proof payload fields.

Implementation note: these inputs should be copied from immutable dispatch-envelope metadata, not recomputed from raw prompt text inside Aegis.

---

## Packet Identity Policy

- Block when `packet_id` is absent, empty, non-string, or not stable for the sealed PromptPacket.
- Block when the dispatch envelope references multiple packet IDs for one model call.
- Warn when the packet ID format is unknown but stable and the route is Tier 0 or Tier 1.
- Demote when the packet ID format is unknown on Tier 2 and the route has a lower-tier safe lane.
- Block when the packet ID format is unknown on Tier 3+ or any route requiring external review, dual-lane proof, or human approval.
- Require Aegis evidence IDs to reference the packet ID without embedding the raw prompt.

---

## Packet Hash Policy

- Allow when `packet_hash_status == present` and the hash is tied to the sealed PromptPacket metadata.
- Allow when `packet_hash_status == not_required` only for Tier 0 or Tier 1 routes with no snapshot, human-gate, dual-lane, or external-review requirement.
- Warn when hash generation is `unavailable` for Tier 0 or Tier 1 and the packet ID, budget, and source lineage are otherwise valid.
- Demote when hash generation is `unavailable` for Tier 2 and a lower-tier route can preserve the task without weakening required proof.
- Block when hash is `missing`, `mismatch`, or required but unavailable for Tier 3+, human-gated, dual-lane, external-review, or direct-provider snapshot routes.
- Block when the hash is calculated from any value other than the sealed PromptPacket payload plus approved metadata fields.

---

## Allowed-Source Compliance

- Allow only when every `source_lineage` key is present in `allowed_sources`.
- Block when any lineage source is absent from the allow-list.
- Block when any lineage token count is negative, non-integer, or not deterministic.
- Block when source lineage total exceeds `prompt_tokens`.
- Warn when source lineage total is lower than `prompt_tokens` but all named sources are allowed and the unclassified remainder is expected by the packet builder.
- Demote when unclassified source remainder appears on Tier 2 and a lower-tier route can proceed without weakening policy.
- Block unclassified or unknown source remainder on Tier 3+ unless a valid waiver/human approval explicitly covers that proof gap.

---

## Budget And Lineage Gates

- Block when `prompt_tokens > budget_ref.max_context_tokens`.
- Block when the budget reference is missing, malformed, or not tied to the selected route.
- Block when a route attempts to bypass PromptPacket budget validation by providing only raw token counts.
- Warn when budget pressure is high but under the limit and the route tier does not require demotion.
- Demote when budget pressure exceeds the configured Tier 2 demotion threshold and a lower-cost or lower-context route is available.
- Block when budget pressure creates a known truncation risk for proof, dual-lane, human-gated, or external-review routes.
- Require evidence IDs for budget pass, budget warning, budget demotion, and budget block outcomes.

---

## Aegis Evidence ID Requirements

Every non-trivial Aegis PromptPacket decision must emit ordered immutable evidence IDs.

Required evidence IDs:

- Packet identity evidence for every route.
- Packet hash evidence when hash is present, unavailable, missing, mismatched, or waived.
- Budget evidence for every route.
- Source-lineage evidence for every route.
- Snapshot evidence when the selected provider/model requires direct or aggregator proof.
- Human-gate evidence when approval is required, missing, valid, or waived.
- Dual-lane evidence when dual-lane policy applies.
- Bifrost handoff evidence when the proof payload must be surfaced downstream.

Policy:

- Allow may use concise evidence IDs but cannot be evidence-free for Tier 2+.
- Warn must include the warning reason evidence ID.
- Demote must include both the original route proof gap and the selected demotion target.
- Block must include at least one blocking evidence ID.
- Human-gate must include the missing or valid approval evidence ID.
- Evidence IDs must be stable strings and must not include raw prompt text, credentials, account identifiers, or transient object addresses.

---

## Snapshot And Hash Gap Handling

Snapshot/hash gaps must be evaluated before dispatch.

- Direct provider routes that require exact model or provider proof must block when snapshot evidence is missing, stale, or hash-mismatched.
- Aggregator routes may warn for `snapshot_status == unavailable` only when Model Harness marks the provider as acceptable for the route tier and no proof-critical capability is being claimed.
- Aggregator routes must demote or block when unavailable snapshot proof hides exact model identity for Tier 2+ decisions.
- Candidate-trust providers must not be elevated by a packet hash alone; Model Harness trust state and snapshot proof still apply.
- Human approval can acknowledge a proof gap, but it cannot convert malformed packet metadata into a valid packet.
- Waivers may permit a policy exception only when the waiver scope exactly matches the proof gap and expiration is valid.

---

## Human-Gate And Dual-Lane Interactions

- Human-gated routes must not dispatch until a valid approval record is present or Relay returns a human-gate outcome.
- Human-gate outcomes must preserve packet ID, hash status, budget status, source-lineage status, and missing approval evidence for Bifrost display.
- Dual-lane routes must evaluate PromptPacket proof metadata for each lane independently.
- Dual-lane allow requires both lanes to satisfy packet identity, budget, source-lineage, hash, snapshot, and evidence-ID requirements.
- Dual-lane mismatch must block when packet IDs, hashes, selected models, or proof requirements diverge without explicit policy support.
- Dual-lane demotion is allowed only when both lanes can be demoted to a policy-approved lower tier.
- A waiver for dual-lane policy must not waive packet validity, budget validity, or allowed-source compliance.

---

## Outcome Mapping

Aegis should emit one deterministic policy outcome per route:

| Outcome | Meaning | Relay Action | Bifrost Display |
|---|---|---|---|
| `allow` | Packet proof satisfies route policy. | Dispatch may proceed. | Show allowed proof summary when configured. |
| `warn` | Non-blocking proof gap exists. | Dispatch may proceed with warning metadata. | Show warning severity and evidence IDs. |
| `demote` | Route cannot proceed at selected tier but a lower-tier route is valid. | Re-route to specified demotion target. | Show demotion reason and target. |
| `block` | Packet proof is invalid or required proof is missing. | Do not dispatch. | Show blocking proof summary. |
| `human_gate` | Valid human approval is required before dispatch. | Pause route and request approval. | Show escalation-required proof summary. |

Priority order: `block` outranks `human_gate`, `human_gate` outranks `demote`, `demote` outranks `warn`, and `warn` outranks `allow` unless the existing Aegis aggregate gate priority defines a stricter order.

---

## Block Conditions

Block before dispatch when any of these are true:

- Missing, empty, unstable, or conflicting `packet_id`.
- Missing, mismatched, or required-but-unavailable packet hash.
- Prompt token count exceeds budget maximum.
- Budget reference is missing or not tied to the selected route.
- Source lineage contains disallowed, unknown, negative, or non-deterministic entries.
- Source lineage total exceeds prompt token count.
- Tier 3+ route has unclassified source remainder without valid scoped waiver.
- Required Aegis evidence IDs are absent, mutable, duplicated, or unsafe.
- Direct-provider snapshot proof is missing, stale, or inconsistent with selected model ID.
- Aggregator snapshot unavailability hides exact model identity for a proof-critical route.
- Human approval is required and not valid.
- Dual-lane route lacks valid proof for either lane.
- Bifrost handoff is required but Relay cannot emit display-safe proof fields.
- Any proof metadata includes raw prompt text, credentials, account secrets, or process/private state.

---

## Bifrost Handoff Expectations

Relay should pass Bifrost a display-safe proof payload after Aegis policy evaluation.

Required display-safe fields:

- `gate_decision`: `allow`, `demote`, `block`, or `human_gate`; include `warn` only if the existing payload contract is extended to support it or map warning severity to `allow` with `WARNING`.
- `severity`: deterministic severity such as `INFO`, `WARNING`, or `ERROR`.
- `evidence_ids`: ordered immutable proof evidence IDs.
- `waiver_present`: whether a scoped waiver affected the decision.
- `explanation`: plain text explanation without raw prompt content.
- `fallback_blockers_from_aegis`: ordered immutable Relay blocker strings.
- Packet proof metadata display summary: packet ID reference, hash status, budget status, source-lineage status, snapshot status, and human/dual-lane status.

Bifrost must not call Aegis, call Relay executor helpers, mutate proof payloads, create waivers, override decisions, or validate packet metadata. The cockpit only renders the pre-serialized state.

---

## FileMap Routing

After Codex review clears this checklist, Build 3 should register:

| File | Area | Purpose | Related Tests | Notes |
|---|---|---|---|---|
| `docs/aegis-promptpacket-proof-policy-checklist.md` | Aegis / Relay | Implementation checklist for evaluating PromptPacket proof metadata before Relay dispatch. | Future Aegis/Relay PromptPacket policy tests. | Build 4 docs-only checklist; FileMap routing belongs to Build 3 after review. |

Do not edit `docs/FileMap.md` in this Build 4 slice.

---

## Deterministic Test Expectations

Future runtime work should add focused deterministic tests before enabling dispatch policy enforcement.

Required tests:

- Valid packet metadata produces `allow` with packet identity, budget, lineage, and evidence IDs.
- Missing packet ID blocks.
- Conflicting packet IDs block.
- Missing required hash blocks.
- Hash unavailable warns for eligible Tier 0/Tier 1 routes.
- Hash unavailable demotes eligible Tier 2 routes.
- Hash unavailable blocks Tier 3+, human-gated, dual-lane, direct-provider, and external-review routes.
- Over-budget packet blocks before adapter dispatch.
- Missing budget reference blocks.
- Disallowed source blocks.
- Negative or non-deterministic source-lineage counts block.
- Source-lineage total above prompt token count blocks.
- Allowed unclassified remainder warns only where policy permits.
- Required evidence IDs are ordered, immutable, stable, and prompt-safe.
- Missing block evidence ID fails the policy result.
- Missing direct-provider snapshot blocks proof-critical routes.
- Aggregator snapshot unavailable warns, demotes, or blocks according to tier and trust state.
- Human-gated route returns `human_gate` when approval is missing and packet metadata is otherwise valid.
- Human-gated route blocks, not gates, when packet metadata itself is invalid.
- Dual-lane route allows only when both lanes have valid packet proof.
- Dual-lane route blocks on lane proof mismatch without scoped waiver.
- Bifrost proof payload contains display-safe fields and excludes raw prompt text.
- `PromptPacket.model_payload()` remains the only model-facing prompt payload.
- Same metadata input returns the same Aegis outcome, severity, blockers, and evidence ordering.

---

## Runtime Enablement Checklist

- Add an Aegis policy evaluator that accepts structured PromptPacket proof metadata.
- Bind Relay dispatch envelope metadata into that evaluator before adapter dispatch.
- Preserve PromptPacket `model_payload()` as the only model-facing payload.
- Map Aegis outcomes to Relay dispatch, demotion, warning, block, or human-gate behavior.
- Surface display-safe proof payloads to Bifrost without raw prompt leakage.
- Add deterministic tests before turning the policy on for live routing.
- Route reviewed docs and future runtime files through FileMap in the owning Build 3 slice.
