# Meridian V2 Progress Tracker

**Purpose:** Give Prime, Codex, and Scott a countable progress view for V2 capability builds. This is the canonical tracker for V2 progress reports: totals first, details second.

**Tracker rule:** Every item is owned by Prime or a harness. No loose feature names without owner assignment.

**Ownership correction:** Prime/Orchestrator owns intent, priority, risk tier, proof/human-gate needs, and final coordination. Relay + Model Harness own provider/model identity, prompt payload construction, context-window fit, dispatch/fallback mechanics, provider balance, transport gates, and per-call telemetry. Bifrost renders those backend-owned concepts; it does not rename or re-own them.

**Source:** `docs/v2-detailed-build-plan.md`

**Harness stage view:** `docs/harness-stage-checklist.md` tracks each harness across Contract/Baseline, V2 Backend, Core Implementation, Prime Integration, Runtime Logic UI, Proofs/Review, and Operations.

## V2 Progress Summary

| Owner | Built/Review-Cleared | Built-Awaiting-Review | Contract Baseline | Needs Build | Total | Percent Complete |
|---|---:|---:|---:|---:|---:|---:|
| Prime Autonomy | 3 | 0 | 0 | 0 | 3 | 100% |
| Echo Harness | 2 | 0 | 2 | 0 | 4 | 100% |
| Atlas Harness | 3 | 0 | 1 | 0 | 4 | 100% |
| Relay/Model Harness | 8 | 0 | 2 | 0 | 10 | 80% clear + 20% baseline |
| Aegis Harness | 2 | 0 | 0 | 0 | 2 | 100% |
| Compass Harness | 4 | 0 | 1 | 0 | 5 | 80% clear + 20% baseline |
| Session Lifecycle Harness | 6 | 0 | 1 | 0 | 7 | 86% clear + 14% baseline |
| Bifrost Harness | 7 | 0 | 2 | 0 | 9 | 78% clear + 22% baseline |
| Federation Harness | 1 | 0 | 0 | 0 | 1 | 100% |
| **Total V2** | **36** | **0** | **9** | **0** | **45** | **80% Clear + 20% Baseline** |

## Built and Review-Cleared V2 Capabilities

### Prime Autonomy

- [x] **Prime + Autonomy Contract:** `PrimeNextAction` domain object with action type, confidence, blockers, human-gate requirements, immutable evidence, and deterministic executability semantics - built in `40def3d`, repaired in `39c9ac8`; review cleared by Reviews C on 2026-05-31.
- [x] **Prime + Project State:** deterministic next-action selector taking project/backlog/lane/tier/review gate state - built in `57aad9a`, queue provenance in `a2b8cd0`; review cleared by Reviews A on 2026-05-31 with 55 `tests/test_prime_autonomy.py` tests passing. Follow-up `70e506131` replaced Echo/Atlas placeholders with bounded typed `ProjectStateSignal` context ingestion: Echo contributes shared `MemoryHitSummary(summary, reason)` values, Atlas contributes sanitized `AtlasHit` values, and missing expected context records soft `MISSING_*` blockers without hard-blocking otherwise executable actions.
- [x] **Prime + Runtime Logic UI Completion:** Prime Runtime Logic UI renders the `/bridge/prime-logic` backend packet with Prime Directives, Prime Directive Proofs, Prime backend source, runtime truth map, typed interaction request, decision/owner logic, no-drift audit logic, backend context logic, Aegis risk logic, backend source refs, proof/invalidation logic, visible-to-user declarations, execution blockers, and backend capability sections. Review cleared on 2026-06-02 with Prime runtime, Bifrost cockpit, FileMap, Prime JSON, and bridge self-tests passing. Operations remain not-live.

Prime runtime packets may consume Relay/Model Harness source refs for model-call posture, but provider selection mechanics, prompt payload assembly, fallback execution, transport authorization, provider balance, and model telemetry remain Relay/Model Harness-owned.

### Aegis Harness

- [x] **Aegis + Prime:** `CognitionPolicy` domain model with action-type/lane/decision enums and policy tier mapping - built in `3cdc74d`; exposes `CognitionPolicy`, `CognitionPolicyResult`, `cognition_policy_for_tier()`, `evaluate_cognition_policy()` through package root for Relay binding; review cleared.
- [x] **Relay + Aegis:** policy-aware Relay executor wrapper with `execute_relay_dispatch_plan_with_policy` - built in `b99ce1d`; evaluates cognition_policy against route tier before model calls, blocks dispatch with proof gate requirements; 157 tests passing (relay_executor, cognition_policy, aegis); review cleared.

### Compass Harness

- [x] **Compass + Project Definition Runtime:** `ProjectDefinition`, project identity candidates/neighbors/evaluations, and `define_project()` / `evaluate_project_identity()` define bounded project work by outcome, context, artifacts, objectives, tasks, proof trail, and repo/venture/session refs. Built through `d4245add7`, repaired through `562d08290`, `72bd6fcc8`, and `843997c2f`; review-promoted on main with `tests/test_compass.py` passing.
- [x] **Compass + Bounds And Scope Runtime:** `ProjectScopeCandidate`, `ProjectBoundsRequest`, `ProjectScopeEvaluation`, `ProjectBoundsEvaluation`, `evaluate_project_scope()`, and `evaluate_project_bounds()` decide inside/outside project context, surface Compass questions, require project identity/evidence refs, and redact raw-context leak paths. Built through `2b7c75050`, repaired through `4837c8312`, `9fd9cf25c`, `6f7b50be8`, `01657e53c`, `46176cc29`, and `3cfb2ca4c`; review-promoted on main with 328 Compass tests passing.
- [x] **Compass + Project Difference Runtime:** `ProjectDifferenceProfile`, `ProjectDifferenceEvidence`, `ProjectDifferenceEvaluation`, and `evaluate_project_difference()` distinguish projects by mission/bearing, objectives, artifacts, memory pins, blockers, proof expectations, and relationship refs; same repo or venture does not imply same project. Built in `b46199ba4`, repaired in `60cc75e17`; review-promoted on main with Compass tests passing.
- [x] **Compass + Cross-Project Handoff Runtime:** `ProjectHandoffRequest`, `ProjectHandoffEvaluation`, and `evaluate_cross_project_handoff()` model source/target project, reason, payload type, evidence refs, approval need, review readiness, and blocked raw-context bleed. Built before the 2026-06-06 Compass repair wave and repaired on main in `501cd2b50`; review-promoted with Compass tests passing.

### Relay/Model Harness

- [x] **Relay + CognitionPolicy Integration:** dispatching with proof gate enforcement - see Aegis entry above, commit `b99ce1d`; review cleared.
- [x] **Relay + Prompt Payload Meter Helper:** `PromptPayloadSnapshot` / `PayloadStatus` domain helper - built in `638117f`, repaired in `8e8c87b`; review cleared by Reviews A on 2026-05-31. This is the runtime helper only; Bifrost visibility remains a separate item below.
- [x] **Model Harness + Metadata Binding:** provider-neutral `ModelHarnessMetadata`, DeepSeek candidate metadata presets, route metadata binding, prompt-drag defaults, external-review evidence refs, and Relay model capability summaries - reviewed in `docs/live-codex-reviews.md` with `tests/test_model_adapter.py tests/test_relay_executor.py` passing.
- [x] **Relay + Prompt Payload Evidence Binding:** Relay dispatch records structured prompt payload evidence, budget status, growth state, tokenizer family, and missing-telemetry tags without storing raw prompt text - review-cleared by Reviews A.
- [x] **Relay + Dispatch Metadata Envelope:** provider-neutral dispatch metadata envelope and validation/fail-closed advisory fields for future HTTP/provider transports - review-cleared by Reviews A.
- [x] **Relay + PromptPacket Proof Metadata Binding:** PromptPacket proof metadata is carried into Relay dispatch envelopes and decision records without changing the model payload boundary - review-cleared by Reviews A.
- [x] **Relay + Aegis PromptPacket Policy Runtime:** Relay evaluates Aegis PromptPacket proof policy before provider transport and records display-safe policy evidence/disposition for allow, warn, demote, human-gate, block, and missing-metadata outcomes - review-cleared by Reviews A.
- [x] **Model Harness + DeepSeek Live Validation/Transport:** DeepSeek validation-gate proof and transport-authority runtime are promoted on main through `2cca03492`, with follow-up gate repairs through `56a539cf2`; direct and registry-backed Relay dispatch both fail closed before adapter invocation unless level-1 proof plus exact lowercase `"true"` human and Prime gate strings authorize transport only. Autonomous implementation, review-clearing, branch/worktree movement, live coding authority, and Relay bypass remain denied.

Ownership correction: future Relay/Model Harness follow-ups should bind existing backend names and evidence surfaces, not create Prime-owned route tables or UI-derived taxonomy fields.

### Echo Harness

- [x] **Echo + Runtime:** `MemoryRecord`, `MemoryQuery`, `MemoryHit` domain objects with deterministic ranking by project/recency/importance/pinning - built in `2bccb55`, repaired in `8e8c87b`; review cleared by Reviews A on 2026-05-31.
- [x] **Echo + FileMap Integration:** `meridian_core/echo.py` and `tests/test_echo.py` registered in runtime FileMap and required-path coverage - built in `a138b1d`; review cleared by Reviews B on 2026-05-31.

### Atlas Harness

- [x] **Atlas + Ranking:** deterministic file/docs-first retrieval using `AtlasQuery`, `AtlasHit`, `AtlasResult`, source-aware ranking, and failure-soft behavior - built in `7e95ede`; review cleared by Reviews A on 2026-05-31 with `tests/test_atlas.py` passing.
- [x] **Atlas + FileMap Integration:** `meridian_core/atlas.py` and `tests/test_atlas.py` registered in runtime FileMap and required-path coverage - built in `a138b1d`; review cleared by Reviews B on 2026-05-31.
- [x] **Atlas + Workflow Adapter:** `meridian_core/workflow_atlas.py` bridges the promoted Atlas retrieval surface and Workflow Sub-Agent Harness dispatch contract. It builds and decodes Atlas work orders, filters FileMap candidates through promoted workflow path scope, fails closed on out-of-scope FileMap and DOC outputs, preserves Echo refs and `AtlasResult` shape, and avoids private Workflow Dispatch helpers. Built and review-promoted in `7ba931bac`; FileMap registration promoted in `4ee0599f4`; proof included `tests/test_workflow_atlas.py`, `tests/test_workflow_dispatch.py`, `tests/test_atlas.py`, and `tests/test_filemap.py`.

### Session Lifecycle Harness

- [x] **Prime + Session Lifecycle:** `restart_resteer.py` domain objects and deterministic evaluator for empty build queues, wrong queue routing, shared/main worktree violations, quota blocks, proof blocks, launch failures, and review cadence gates - built in `8b4c8ac`, repaired in `40def3d`; contract baseline in `27e1b1f`; review cleared by Reviews A on 2026-05-31.
- [x] **Session Lifecycle + Implementation:** `SessionLifecycleState` and `SessionCommandPlan` domain objects model session status, command intent, routing reason, proof state, queue/worktree/branch identity, review state, Aegis gate data, blockers, recovery notes, and deterministic audit evidence. Built and repaired across `558af5554`, `17d70c9d`, `7e96994a`, `e486de2d`, and `e41851ae`; review-promoted on main with `tests/test_session_lifecycle.py` passing.
- [x] **Session Lifecycle + Permissions:** `PermissionContext`, `SessionPermissionSummary`, operation scopes, permission states, restart/resteer findings, Prime/Beacon advisory binding, expiry/task-scope checks, and fail-closed permission boundaries are implemented without live control. Built through `7e96994a`, repaired through `e486de2d`, `e41851ae`, `1b56a098`, `65e2a97f`, `c57306f0`, and `225a5108`; review-promoted on main.
- [x] **Session Lifecycle + State Evidence Completeness:** `SessionLiveStateEvidence` and `SessionLiveStateAdvisoryProjection` expose display-safe queue, worktree, branch, model, timestamp, proof, blocker, and project assignment evidence without raw worker chat or raw filesystem/blocker leakage. Built in `8a769e90`, repaired through `e6e8e1c9`, `dd6a0d1a`, `0ae0027a`, `c7e08b0f`, and `6701c11d`; review-promoted on main.
- [x] **Session Lifecycle + Command Plan Proof:** command preview and V2 proof packets include target, reason, expected transition, evidence refs, queue, worktree/branch, Aegis gate result, executability, permission state, rollback/recovery notes, and affected fields while remaining non-executable. Built through `85037c12`, `763bee58`, `fac1643d`, `db6f2ea0`, and `8ce4a96e`; review-promoted on main.
- [x] **Session Lifecycle + Close/Archive Write-Through:** `SessionCloseArchiveWriteThroughProof`, close/archive/stop-before-close/write-through action family, and V3 checkpoint proof packet provide explicit proof metadata and failure visibility for close/archive workflows without one-click UI execution bypass. Built through the close/archive proof wave and V3 packet commit `488359bb`; review-promoted on main with `tests/test_session_lifecycle.py` passing.

### Federation Harness

- [x] **Federation Harness + Planning:** `docs/federation-harness-horizon.md` defines the planning-only multi-Meridian boundary, consent model, typed handoff packets, unsafe shared-state exclusions, Bifrost panel implication, and V2 out-of-scope limits - built in `e37030e`; review cleared by Reviews B on 2026-05-31.

### Bifrost Harness

- [x] **Bifrost + FileMap Integration:** active Bifrost V2 cockpit direction docs (`docs/bifrost-v2-cockpit-extensions.md`, `docs/jarvis-ui-source-assessment.md`) registered in runtime FileMap, `docs/FileMap.md`, and required-path coverage - built in `d496472`; review cleared by Reviews B on 2026-05-31.
- [x] **Bifrost + Reviewed Backend Evidence / JARVIS-Source V2 Extension Slice:** `ReviewedBackendEvidenceView`, `reviewed_backend_evidence_view_from_summary()`, backend-bound sample wiring, and inert cockpit HTML/CSS rendering display Prime next action, Echo memory-hit summary, Atlas retrieval-hit summary, Session Lifecycle preview, Aegis policy result, Relay/model metadata, evidence refs, and warnings as escaped static markup only. Built in `9a14e73eb`, repaired in `6400e80bd`, review-cleared by Codex Review A/B, and promoted on main in `151de3b40` with `tests/test_bifrost_cockpit.py` passing at 383 tests.
- [x] **Bifrost + Cockpit Render:** static render tests and HTML escaping tests cover new V2 view-model fields through `render_cockpit_html()`, including provider balance, prompt payload visibility, visible payload meter, model capability metadata, model validation envelopes, dispatch hardening, PromptPacket proof, Relay/Aegis policy handoff, reviewed backend evidence, backend-bound sample wiring, provenance/evidence refs, redaction, and no-execution-control guardrails. Cleared from current-main evidence by Codex Review C/D on 2026-06-07 with `python -m pytest tests/test_bifrost_cockpit.py -q` passing at 383 tests.
- [x] **Bifrost + Balance Button:** backend-bound provider balance proof covers Claude, OpenAI, DeepSeek, aggregator, and local adapters with provider health, route kind, remaining credit labels, token usage, estimated spend, and cost-pressure state. OpenAI is supplied through `sample_backend_bound_cockpit_view_model().provider_balance_summary`, repaired by Opus worker `chat_1780849813091`, review-cleared by Codex Review A `codex_1780850388656` and Review B `codex_1780850388968`, with `tests/test_bifrost_cockpit.py` passing at 383 tests.
- [x] **Bifrost + Prompt Payload Visibility:** reviewed no-op backend/view-model proof shows existing `sample_backend_bound_cockpit_view_model()` rendering already carries Relay prompt payload size, budget pressure, growth/flat state, Q-mode prompt-drag, evidence refs, provider/model/route continuity, dispatch adjacency, and queue-poll adjacency without raw prompt/provider leakage or execution controls. Verified by Opus worker `chat_1780851013499`, repaired after Codex findings, review-cleared by Codex Review A `codex_1780851814897` and Review B `codex_1780851815171`, with `tests/test_bifrost_cockpit.py` passing at 384 tests.
- [x] **Bifrost + Voice I/O Surface:** reviewed no-op backend/view-model proof shows existing `VoiceIOState` and `render_cockpit_html()` already render microphone input, spoken Prime output, wake/boot audio status, mute/listening/thinking/speaking states, display-safe status/intent refs, and non-executable voice controls through the static cockpit path. Verified by Opus worker `chat_1780852385348`, repaired after Codex Review B required per-control disabled-state assertions, review-cleared by Codex Review A `019ea31a-5a0b-7c13-9301-fd9bada9ce0d` and Review B `019ea31a-75f7-76b2-8d0a-eed4f8791a63`, with `tests/test_bifrost_cockpit.py` passing at 385 tests.
- [x] **Bifrost + Electron Cockpit:** reviewed authority proof locks the Electron app as the Meridian UI, root `index.html` as renderer internals loaded by Electron rather than a separate UI target, `bifrost/preview.html` as generated backend/view-model proof output only, and `npm start` / Electron startup as non-substituting/non-regenerating preview output. Verified by Opus worker `chat_1780853361884`, repaired after Codex Review A required tighter doc-content guards, review-cleared by Codex Review A `019ea326-9d07-7cd2-94d2-c153edde8906` and Review B `019ea326-b7ab-7851-a5c3-b6cdeda703c7`, with `tests/test_bifrost_preview.py tests/test_filemap.py tests/test_bifrost_cockpit.py` passing at 465 tests.

## Built But Awaiting Review

- None currently.

## Contract Baselines Complete (Not Runtime Implementation)

### Echo Harness

- [x] **Echo + Memory Contract:** `docs/echo-memory-contract.md` - architecture and interface contract defined; runtime implementation awaiting.
- [x] **Echo + Repository Integration:** contract defined for local storage abstraction and query interface.

### Atlas Harness

- [x] **Atlas + Retrieval Contract:** `docs/atlas-retrieval-contract.md` - file/docs-first RAG interface contract defined; source-aware ranking principles established; runtime implementation awaiting.

### Session Lifecycle Harness

- [x] **Session Lifecycle + Workflow Contract:** `docs/workflow-subagent-harness-contract.md` - workflow/sub-agent dispatch contract for bounded harness work defined; Prime work order and heartbeat interface specified. Runtime implementation is now represented above under Built and Review-Cleared V2 Capabilities.

### Compass Harness

- [x] **Compass + Project Boundary Contract:** backend checklist baseline for project definition, bounds, scope, difference, cross-project communication, and Compass/Vulcan ownership split recorded in this tracker. Runtime implementation is now represented above under Built and Review-Cleared V2 Capabilities.

### Relay/Model Harness

- [x] **Model Harness + DeepSeek Validation Gate:** `docs/deepseek-provider-validation-gate.md` - DeepSeek trust criteria and validation-gate baseline. The transport-authority runtime is now represented above under Built and Review-Cleared; DeepSeek still cannot clear reviews, move branches/worktrees, run autonomous implementation lanes, hold live coding authority, or bypass Relay.
- [x] **Model Harness + Metadata Contract:** `docs/model-harness-v2-contract.md` - provider capability metadata, prompt-drag telemetry, trust state, route ownership, direct-vs-aggregator evidence, allowed/blocked task types, external-review requirements, and Aegis/Relay policy binding; review-cleared by Reviews B on 2026-05-31. Runtime metadata binding is now represented above under Built and Review-Cleared.
  - **Per-Call GOAL/Intent disposition:** `docs/model-harness-v2-contract.md` now separates Prime-level user intent analysis from dispatch-scoped per-call intent. This is tracked as part of the Model Harness metadata contract count, not as an additional contract-baseline row. Per-call GOAL/Intent belongs to Relay + Model Harness evidence and should express call goal, action type, output shape, risk tier, proof requirement, disallowed outputs, payload budget ref, and source evidence refs without creating taxonomy-derived backend names.

### Bifrost Harness

- [x] **Bifrost + Voice Command Contract:** `docs/bifrost-voice-command-contract.md` - voice input/output states, typed voice command intents, dictation, read-aloud controls, and proof/status command families defined; review-cleared and FileMap-registered on 2026-05-31.
- [x] **Bifrost + Balance/Payload Contract:** `docs/bifrost-balance-payload-surface-contract.md` - provider balance, prompt payload visibility, Q-mode prompt-drag warnings, and DeepSeek route/trust display contract defined; review-cleared and FileMap-registered on 2026-05-31.

## In Progress / Stabilizing

- None currently.

## V3 Scope Note

**Future capability planning:** `docs/agentic-ai-framework-checklist.md` documents V3 horizon architecture (multi-agent federation, cross-system coordination, adaptive autonomy). V2 focuses on single-Meridian Prime autonomy, memory, retrieval, and session lifecycle. V3 entry point is separate.

## Needs Build: Remaining V2 Items

### Prime Autonomy

- None currently.

### Relay / Model Harness

- None currently. DeepSeek transport authority is review-promoted on main; future Relay/Model work should focus on Bifrost-visible metadata/model-routing follow-ups after tracker and FileMap upkeep.
- Any future backend promotion must first normalize taxonomy labels to existing backend-owned concepts and keep model-call mechanics out of Prime.

### Session Lifecycle Harness

- None currently. Session Lifecycle runtime items are review-promoted on main; future work should be Prime/live orchestration integration, Runtime Logic UI completeness, or operations gating rather than V2 backend runtime build.

### Compass Harness

- None currently. Compass runtime items are review-promoted on main; future Compass work should be Prime integration, Runtime Logic UI completeness, or operations gating rather than V2 backend runtime build.

### Bifrost Harness

- None currently. All V2 Bifrost Needs Build items are review-promoted on main; future Bifrost work should be V3 horizon, runtime wiring, or operations-gated UI integration rather than V2 backend/build closure.

## Review Gates for V2

- Every V2 domain slice must include unit tests and pass before marked built.
- Every new module/doc must be routed to FileMap by Build 3.
- Every three task-changing commits per lane must trigger Codex Reviews.
- Any track introducing model calls must prove Aegis policy tests first.
- Any track introducing or changing model-call mechanics must be owned by Relay/Model Harness unless it is only a Prime intent/risk/proof reference.
- Any track introducing DeepSeek coding use must prove the DeepSeek validation gate first; DeepSeek cannot clear reviews, move branches, or run autonomous implementation lanes while still in candidate state.
- Any track introducing session actions must prove unique worktree and branch-permission rules.

## Out of V2 Scope (Horizon Only)

- Public product packaging and account-based distribution strategy.
- Multi-user federation runtime and shared mutable project state.
- Vector database or large-scale retrieval infrastructure.
- Full autonomous branch movement and direct destructive session controls.

## V2 First-Wave Recommended Build Order

1. **Aegis:** `CognitionPolicy` domain model (DONE: commit e08e598)
2. **Echo Harness:** deterministic memory records and query
3. **Atlas Harness:** FileMap/docs-first retrieval
4. **Prime Autonomy:** `PrimeNextAction` selector using bounded typed Echo/Atlas context inputs
5. **Session Lifecycle Harness:** typed lifecycle state and command plan
6. **Bifrost Harness:** static V2 extensions rendering the above
7. **Relay/Model Harness:** metadata binding and prompt-drag hardening
8. **Federation Harness:** planning and horizon architecture

## Reporting Format

Every V2 progress report should begin with:

```text
V2: <built>/<total> built (<percent>), <in_progress> in progress/review, <remaining> left.
```

Then list by harness:

- **Prime Autonomy** — Next-action selection, project state integration
- **Echo Harness** — Durable memory records, ranked query
- **Atlas Harness** — File/docs-first retrieval, source-aware ranking
- **Relay/Model Harness** — Dispatch safety, capability metadata, prompt-drag telemetry
- **Aegis Harness** — Gated cognition, policy-driven proof enforcement
- **Session Lifecycle Harness** — Typed lifecycle state, workflow/sub-agent dispatch
- **Bifrost Harness** — Cockpit V2 extensions, view-model rendering
- **Federation Harness** — Multi-Meridian collaboration (horizon)
