# Meridian V2 Progress Tracker

**Purpose:** Give Prime, Codex, and Scott a countable progress view for V2 capability builds. This is the canonical tracker for V2 progress reports: totals first, details second.

**Tracker rule:** Every item is owned by Prime or a harness. No loose feature names without owner assignment.

**Source:** `docs/v2-detailed-build-plan.md`

**Harness stage view:** `docs/harness-stage-checklist.md` tracks each harness across Contract/Baseline, V2 Backend, Core Implementation, Prime Integration, Runtime Logic UI, Proofs/Review, and Operations.

## V2 Progress Summary

| Owner | Built/Review-Cleared | Built-Awaiting-Review | Contract Baseline | Needs Build | Total | Percent Complete |
|---|---:|---:|---:|---:|---:|---:|
| Prime Autonomy | 2 | 1 | 0 | 0 | 3 | 67% clear + 33% awaiting |
| Echo Harness | 2 | 0 | 2 | 0 | 4 | 100% |
| Atlas Harness | 2 | 0 | 1 | 0 | 3 | 100% |
| Relay/Model Harness | 2 | 0 | 2 | 6 | 10 | 20% clear + 20% baseline |
| Aegis Harness | 2 | 0 | 0 | 0 | 2 | 100% |
| Compass Harness | 0 | 0 | 1 | 4 | 5 | 20% baseline |
| Session Lifecycle Harness | 1 | 0 | 1 | 5 | 7 | 29% |
| Bifrost Harness | 1 | 0 | 2 | 6 | 9 | 33% |
| Federation Harness | 1 | 0 | 0 | 0 | 1 | 100% |
| **Total V2** | **13** | **1** | **9** | **21** | **44** | **30% Clear + 2% Awaiting + 20% Baseline** |

## Built and Review-Cleared V2 Capabilities

### Prime Autonomy

- [x] **Prime + Autonomy Contract:** `PrimeNextAction` domain object with action type, confidence, blockers, human-gate requirements, immutable evidence, and deterministic executability semantics - built in `40def3d`, repaired in `39c9ac8`; review cleared by Reviews C on 2026-05-31.
- [x] **Prime + Project State:** deterministic next-action selector taking project/backlog/lane/tier/review gate state - built in `57aad9a`, queue provenance in `a2b8cd0`; review cleared by Reviews A on 2026-05-31 with 55 `tests/test_prime_autonomy.py` tests passing.

### Aegis Harness

- [x] **Aegis + Prime:** `CognitionPolicy` domain model with action-type/lane/decision enums and policy tier mapping - built in `3cdc74d`; exposes `CognitionPolicy`, `CognitionPolicyResult`, `cognition_policy_for_tier()`, `evaluate_cognition_policy()` through package root for Relay binding; review cleared.
- [x] **Relay + Aegis:** policy-aware Relay executor wrapper with `execute_relay_dispatch_plan_with_policy` - built in `b99ce1d`; evaluates cognition_policy against route tier before model calls, blocks dispatch with proof gate requirements; 157 tests passing (relay_executor, cognition_policy, aegis); review cleared.

### Relay/Model Harness

- [x] **Relay + CognitionPolicy Integration:** dispatching with proof gate enforcement - see Aegis entry above, commit `b99ce1d`; review cleared.
- [x] **Relay + Prompt Payload Meter Helper:** `PromptPayloadSnapshot` / `PayloadStatus` domain helper - built in `638117f`, repaired in `8e8c87b`; review cleared by Reviews A on 2026-05-31. This is the runtime helper only; Bifrost visibility remains a separate item below.

### Echo Harness

- [x] **Echo + Runtime:** `MemoryRecord`, `MemoryQuery`, `MemoryHit` domain objects with deterministic ranking by project/recency/importance/pinning - built in `2bccb55`, repaired in `8e8c87b`; review cleared by Reviews A on 2026-05-31.
- [x] **Echo + FileMap Integration:** `meridian_core/echo.py` and `tests/test_echo.py` registered in runtime FileMap and required-path coverage - built in `a138b1d`; review cleared by Reviews B on 2026-05-31.

### Atlas Harness

- [x] **Atlas + Ranking:** deterministic file/docs-first retrieval using `AtlasQuery`, `AtlasHit`, `AtlasResult`, source-aware ranking, and failure-soft behavior - built in `7e95ede`; review cleared by Reviews A on 2026-05-31 with `tests/test_atlas.py` passing.
- [x] **Atlas + FileMap Integration:** `meridian_core/atlas.py` and `tests/test_atlas.py` registered in runtime FileMap and required-path coverage - built in `a138b1d`; review cleared by Reviews B on 2026-05-31.

### Session Lifecycle Harness

- [x] **Prime + Session Lifecycle:** `restart_resteer.py` domain objects and deterministic evaluator for empty build queues, wrong queue routing, shared/main worktree violations, quota blocks, proof blocks, launch failures, and review cadence gates - built in `8b4c8ac`, repaired in `40def3d`; contract baseline in `27e1b1f`; review cleared by Reviews A on 2026-05-31.

### Federation Harness

- [x] **Federation Harness + Planning:** `docs/federation-harness-horizon.md` defines the planning-only multi-Meridian boundary, consent model, typed handoff packets, unsafe shared-state exclusions, Bifrost panel implication, and V2 out-of-scope limits - built in `e37030e`; review cleared by Reviews B on 2026-05-31.

### Bifrost Harness

- [x] **Bifrost + FileMap Integration:** active Bifrost V2 cockpit direction docs (`docs/bifrost-v2-cockpit-extensions.md`, `docs/jarvis-ui-source-assessment.md`) registered in runtime FileMap, `docs/FileMap.md`, and required-path coverage - built in `d496472`; review cleared by Reviews B on 2026-05-31.

## Built But Awaiting Review

- [ ] **Prime + Runtime Logic UI Completion:** Prime Runtime Logic UI renders the `/bridge/prime-logic` backend packet with Prime backend source, runtime truth map, typed interaction request, decision/owner logic, no-drift audit logic, backend context logic, Aegis risk logic, backend source refs, proof/invalidation logic, visible-to-Scott declarations, execution blockers, and backend capability sections. Built awaiting review; not review-cleared.

## Contract Baselines Complete (Not Runtime Implementation)

### Echo Harness

- [x] **Echo + Memory Contract:** `docs/echo-memory-contract.md` - architecture and interface contract defined; runtime implementation awaiting.
- [x] **Echo + Repository Integration:** contract defined for local storage abstraction and query interface.

### Atlas Harness

- [x] **Atlas + Retrieval Contract:** `docs/atlas-retrieval-contract.md` - file/docs-first RAG interface contract defined; source-aware ranking principles established; runtime implementation awaiting.

### Session Lifecycle Harness

- [x] **Session Lifecycle + Workflow Contract:** `docs/workflow-subagent-harness-contract.md` - workflow/sub-agent dispatch contract for bounded harness work defined; Prime work order and heartbeat interface specified; runtime implementation awaiting.

### Compass Harness

- [x] **Compass + Project Boundary Contract:** backend checklist baseline for project definition, bounds, scope, difference, cross-project communication, and Compass/Vulcan ownership split recorded in this tracker. Runtime implementation awaiting.

### Relay/Model Harness

- [x] **Model Harness + DeepSeek Validation Gate:** `docs/deepseek-provider-validation-gate.md` - DeepSeek is a primary provider candidate, but not trusted for autonomous coding/review-clearing until direct API routing, prompt payload metering, bounded Q-mode behavior, and coding benchmark proof are recorded.
- [x] **Model Harness + Metadata Contract:** `docs/model-harness-v2-contract.md` - provider capability metadata, prompt-drag telemetry, trust state, route ownership, direct-vs-aggregator evidence, allowed/blocked task types, external-review requirements, and Aegis/Relay policy binding; review-cleared by Reviews B on 2026-05-31. Runtime metadata implementation remains in Needs Build.

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

- [ ] **Model Harness + Metadata:** capability metadata and prompt-drag telemetry fields - module: `meridian_core/model_adapter.py`; contract: `docs/model-harness-v2-contract.md`.
- [ ] **Model Harness + DeepSeek Primary Provider:** DeepSeek direct-API adapter metadata and routing preset - default `deepseek-v4-pro`, fast lane `deepseek-v4-flash`; must route through Relay/Aegis like Claude and OpenAI, not as a bypass; starts in candidate trust state until the validation gate proves coding reliability.
- [ ] **Relay/Bifrost + Visible Prompt Payload Meter:** wire the reviewed `PromptPayloadSnapshot` helper into dispatch and cockpit visibility - show `(under 1k)` / `(12.4k)` style label, budget percent, and growth delta for every model dispatch; queue/Q-mode growth across polls is a DEGRADED prompt-drag finding.
- [ ] **Relay + Model Adapter:** route capability/tier/budget metadata binding - no vendor-specific presets in first slice.
- [ ] **Relay + Dispatch Hardening:** provider-neutral HTTP transport envelope updates for metadata pass-through.
- [ ] **Relay + PromptPacket:** proof metadata integration into dispatch (prompt_packet.py already v1 complete; v2 adds budget/proof bindings).

### Session Lifecycle Harness

- [ ] **Session Lifecycle + Implementation:** `SessionLifecycleState` and `SessionCommandPlan` domain objects - module: `meridian_core/session_lifecycle.py`; tests: `tests/test_session_lifecycle.py`; models spawn/watch/steer/stop/transfer/archive/stale/recover actions; builds on contract baseline `docs/session-lifecycle-v2-contract.md`.
- [ ] **Session Lifecycle + Permissions:** wire the restart/resteer evaluator into Prime/Beacon runtime state; branch/worktree movement still requires Scott or Prime permission object before live execution.
- [ ] **Session Lifecycle + State Evidence Completeness:** live state payload must expose queue, worktree, branch, model, read/write/prompt timestamps, proof state, blocker summary, and project assignment without raw worker chat.
- [ ] **Session Lifecycle + Command Plan Proof:** every command preview must include target, reason, expected transition, evidence refs, queue, worktree/branch, Aegis gate result, executability, and rollback/recovery note before execution.
- [ ] **Session Lifecycle + Close/Archive Write-Through:** close, archive, stop-before-close, and write-through are explicit Vulcan actions with failure visibility; no UI one-click close may bypass this backend proof.

### Compass Harness

- [ ] **Compass + Project Definition Runtime:** domain object/API must define project as a bounded body of work with outcome, context, artifacts, objectives, tasks, proof trail, and relationship to repo/venture/session.
- [ ] **Compass + Bounds And Scope Runtime:** backend must decide what is inside/outside project context, surface ambiguous scope as a Compass question, and require project identity/evidence refs before project-scoped actions.
- [ ] **Compass + Project Difference Runtime:** backend must distinguish projects by mission/bearing, objectives, artifacts, memory pins, blockers, and proof expectations; same repo or venture must not imply same project.
- [ ] **Compass + Cross-Project Handoff Runtime:** backend must model source project, target project, reason, payload type, evidence refs, approval need, and blocked raw context bleed for cross-project communication.

### Bifrost Harness

- [ ] **Bifrost + JARVIS-Source V2 Extensions:** source-first cockpit adaptation using existing JARVIS/HUD repo patterns, then view-model placeholders for Prime next action, Echo memory hits, Atlas retrieval hits, session lifecycle preview, Aegis policy result - module: `bifrost/cockpit.py` (extends v1 snapshot); tests: `tests/test_bifrost_cockpit.py`; source note: `docs/jarvis-ui-source-assessment.md`; contract: `docs/bifrost-v2-cockpit-extensions.md`.
- [ ] **Bifrost + Browser-First Cockpit:** keep the primary cockpit as deterministic HTML/CSS preview; Electron remains optional packaging unless desktop-only capability is needed.
- [ ] **Bifrost + Balance Button:** Polaris-style provider balance and usage surface for Claude, OpenAI, DeepSeek, and aggregator/local adapters; must show provider health, remaining credit where available, token usage, estimated spend, and cost pressure warnings for Prime routing.
- [ ] **Bifrost + Prompt Payload Visibility:** surface Relay prompt payload size, budget pressure, and growth/flat status next to model dispatch and queue-poll events so Scott and Prime can see prompt drag in real time.
- [ ] **Bifrost + Voice I/O Surface:** visible microphone input, spoken Prime output, NASA-style boot/status audio state, mute controls, and listening/thinking/speaking indicators; runtime speech plumbing may follow the initial surface.
- [ ] **Bifrost + Cockpit Render:** static render tests and HTML escaping tests for new V2 view-model fields.
## Review Gates for V2

- Every V2 domain slice must include unit tests and pass before marked built.
- Every new module/doc must be routed to FileMap by Build 3.
- Every three task-changing commits per lane must trigger Codex Reviews.
- Any track introducing model calls must prove Aegis policy tests first.
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
4. **Prime Autonomy:** `PrimeNextAction` selector using Echo/Atlas placeholders
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
