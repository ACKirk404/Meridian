# Relay/Aegis Demotion, Retry, And Bifrost Handoff Checklist

**Status:** Build-ready checklist; runtime implementation not authorized by this doc
**Date:** 2026-06-02
**Owner harnesses:** Relay (dispatch/decision records), Aegis (policy result), Bifrost (display adapter)
**Scope:** Runtime wiring requirements after Aegis policy serialization and Bifrost handoff adapter review clearance

---

## Purpose

Define the next Relay/Aegis/Bifrost integration checklist for handling Aegis PromptPacket policy demotion, retry, fallback, human-gate, fail-closed, and display-safe handoff behavior. This doc is intentionally implementation-facing but docs-only: it does not authorize runtime code, tests, FileMap edits, Bifrost UI edits, model/account/process changes, branch movement, shared-main writes, pushes, or Polaris work.

---

## Required Runtime Inputs

Relay runtime wiring should start from reviewed, structured data only:

- `PromptPacketProofMetadata` from sealed PromptPacket and dispatch-envelope fields.
- `PromptPacketProofPolicyResult` returned by `evaluate_prompt_packet_proof_policy()`.
- Display-safe `PromptPacketProofPolicyResult.to_display_dict()` / `serialize_prompt_packet_policy_result()` output.
- Relay decision-record fields such as `aegis_gate_decision`, `aegis_gate_severity`, `aegis_evidence_ids`, `aegis_explanation`, `fallback_blockers`, and `demote_to_tier`.
- Bifrost handoff/view fields such as decision, severity, packet id, hash status, proof requirement, evidence ids, blockers, warnings, demotion target, human-gate state, missing metadata fields, reason tags, and explanation.

Relay must not derive these from raw prompt text, provider request/response bodies, process state, session control state, or branch/worktree state.

---

## Demotion Target Handling

- [ ] Treat Aegis `decision == "demote"` as a request to route only to an explicit lower-tier target.
- [ ] Require `demote_to_tier` from Aegis policy result and a Relay-authorized lower-tier route before any demoted dispatch.
- [ ] Block when `demote_to_tier` is absent, equal to the current tier, higher than the current tier, negative, or not represented by a safe Relay route.
- [ ] Rerun PromptPacket construction and Aegis policy evaluation for the demoted route; do not reuse the original policy result as authorization for the new route.
- [ ] Preserve the original Aegis decision, warnings, blockers, reason tags, and demotion target in the decision record for audit.
- [ ] Surface demotion to Bifrost as a degraded state, not a silent success.
- [ ] Do not demote across provider trust boundaries, exact model-id requirements, human-gate requirements, dual-lane requirements, or proof requirements unless the target route explicitly satisfies them.

---

## Retry And Fallback Boundaries

- [ ] Retry only when the retry policy is explicit and does not change prompt text, packet id, route id, provider, exact model id, risk tier, source lineage, proof requirement, snapshot requirement, or trust state.
- [ ] Rebuild PromptPacket proof metadata and rerun Aegis whenever any route/prompt/proof input changes.
- [ ] Never retry or fallback from an Aegis `block` result without corrected metadata and a fresh Aegis result.
- [ ] Never retry or fallback from an Aegis `human_gate` result until approval state changes and Aegis is rerun.
- [ ] Never silently fallback from direct provider to aggregator, aggregator to direct provider, one exact model id to another, or trusted model to candidate model.
- [ ] Never use provider output, transport success, or post-response telemetry to retroactively satisfy missing pre-dispatch packet proof.
- [ ] Preserve retry/fallback attempts in deterministic audit fields with attempt number, original packet id, new packet id when rebuilt, prior Aegis decision, and new Aegis decision.

---

## Fail-Closed Missing Metadata

Relay must fail closed before provider transport when required packet policy metadata is missing or unsafe:

- [ ] Missing PromptPacket or PromptPacket proof metadata.
- [ ] Missing packet id, packet hash status, prompt token count, budget ref, max context tokens, source lineage, or allowed sources.
- [ ] Missing risk tier, proof requirement, model trust state, snapshot requirement/status, human-gate state, or dual-lane state.
- [ ] Missing or unsafe Aegis evidence ids when the route requires evidence.
- [ ] Missing display-safe serialization from Aegis policy result.
- [ ] Any policy metadata containing raw prompt text, raw source snippets, credentials, provider request bodies, provider responses, account identifiers, cookies, process ids, session-control state, branch/worktree data, or Polaris references.

Fail-closed handling should produce a decision record with `aegis_gate_decision="block"` or an equivalent pre-call block state, deterministic blockers, missing metadata fields, and a Bifrost-safe explanation. It must not call the provider adapter.

---

## Human-Gate Decisions

- [ ] Treat Aegis `decision == "human_gate"` as a hard pause before provider transport.
- [ ] Add `aegis_human_gate_required` to Relay fallback blockers/error tags.
- [ ] Preserve missing approval evidence, packet id, hash status, source-lineage status, budget status, proof requirement, and reason tags in the decision record.
- [ ] Surface human-gate state to Bifrost as escalation required.
- [ ] Resume only after Review Console approval state changes and Relay reruns PromptPacket metadata construction plus Aegis evaluation.
- [ ] If packet metadata is invalid and human approval is also missing, block on invalid metadata first; human approval must not validate malformed packet proof.

---

## Display-Safe Handoff Summary Shape

Relay should build one Bifrost-safe summary from Aegis serialization plus Relay packet context:

| Field | Source | Notes |
|---|---|---|
| `decision` | Aegis serialized result | `allow`, `warn`, `demote`, `block`, or `human_gate`. |
| `severity` | Aegis serialized result | `info`, `warning`, or `error`. |
| `packet_id` | PromptPacket / Relay envelope | Reference only; no prompt text. |
| `packet_hash_status` | Relay/Aegis metadata | Status, not raw prompt. |
| `proof_requirement` | Relay route / Aegis metadata | Stable tag only. |
| `aegis_evidence_ids` | Aegis serialized result | Ordered references only. |
| `blockers` | Aegis/Relay blockers | Deterministic tags. |
| `warnings` | Aegis warnings | Deterministic tags. |
| `demotion_target` | Aegis result / Relay route | Empty unless target is authorized. |
| `human_gate_state` | Relay approval state | `not_required`, `required`, `approved`, or blocked equivalent. |
| `missing_metadata_fail_closed` | Relay fail-closed mapping | True when metadata absence blocked dispatch. |
| `missing_metadata_fields` | Aegis `missing_fields` plus Relay pre-call misses | Display-safe field names only. |
| `reason_tags` | Aegis `reason_tags` plus Relay tags | Display-safe tags only. |
| `explanation` | Aegis/Relay display-safe explanation | Redacted before Bifrost. |

The handoff shape must be deterministic and serializable. Bifrost should display the fields it receives and must not call Aegis, call Relay packet assembly, approve gates, mutate evidence, choose providers, or reconstruct proof state from raw prompt data.

---

## Bifrost Adapter Expectations

- [ ] Bifrost adapter input is structured Relay/Aegis handoff data only.
- [ ] Missing packet id or missing required summary fields should suppress or degrade the card according to the reviewed Bifrost adapter behavior, not trigger Relay/Aegis calls.
- [ ] Bifrost must render missing metadata fields and reason tags from safe lists.
- [ ] Bifrost must render blockers, warnings, demotion target, and human-gate state without hiding degraded or blocked policy state.
- [ ] Bifrost must escape all fields and preserve redaction for raw prompt, secret, provider, and process-id sentinels.
- [ ] Bifrost must not display raw prompt text, credentials, raw provider responses, request bodies, account state, session/process controls, branch/worktree data, or Polaris references.

---

## Deterministic Test Expectations

Future runtime work should add focused tests before enabling the integration:

- [ ] `demote` with authorized lower-tier target builds a fresh packet, reruns Aegis, and records both original and demoted policy evidence.
- [ ] `demote` without authorized target blocks and does not call adapter transport.
- [ ] Retry with identical route/prompt/proof input preserves prior policy result and records deterministic retry attempt metadata.
- [ ] Retry/fallback with changed packet, route, provider, model, budget, source lineage, proof requirement, or trust state rebuilds metadata and reruns Aegis.
- [ ] `block` prevents provider adapter calls and emits `aegis_gate_blocked`.
- [ ] `human_gate` prevents provider adapter calls and emits `aegis_human_gate_required`.
- [ ] Missing PromptPacket proof metadata fails closed before provider transport.
- [ ] Missing summary fields surface as display-safe `missing_metadata_fields`.
- [ ] Aegis serialization output maps into Relay decision records and Bifrost handoff with stable key order and deterministic tuple/list ordering.
- [ ] Raw prompt, credential, provider response, request body, process id, session-control, branch/worktree, main-write, and Polaris sentinel strings are absent or redacted in decision records and Bifrost handoff.
- [ ] Bifrost adapter consumes only structured handoff data and does not call Aegis/Relay runtime helpers.
- [ ] Same input handoff produces the same Bifrost adapter output.

---

## Explicit Exclusions

This checklist does not authorize:

- Runtime code edits in this docs-only slice.
- Relay provider transport changes.
- Bifrost UI/CSS/rendering changes.
- FileMap edits.
- Live model calls, account probing, provider balance checks, session/process control, or local process inspection.
- Raw prompt, raw source text, raw provider request/response, credential, or account-state exposure.
- Branch/worktree movement, merge/rebase/reset/cherry-pick/stash-pop, shared-main writes, pushes to main, or Polaris changes.

---

## Runtime Enablement Gate

Runtime demotion/retry/handoff wiring is ready only after:

- Aegis serialization is review-cleared.
- This checklist is review-cleared.
- Relay decision-record and adapter-call tests prove block/human-gate/demotion/fail-closed behavior.
- Bifrost handoff adapter tests prove display-safe rendering from structured data only.
- Raw prompt, credential, provider response, process/session-control, branch/worktree, main-write, and Polaris exclusions are tested.
- Reviews B clears the implementation before any Relay/Bifrost consumer relies on the serialized policy result in live routing.
