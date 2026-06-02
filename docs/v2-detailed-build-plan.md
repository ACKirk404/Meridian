# Meridian V2 Detailed Build Plan

**Status:** Active V2 planning baseline
**Source:** `docs/v2-horizon-plan.md`
**Trigger:** V1 cockpit is complete and review-cleared at 12/12.
**Rule:** Every V2 item is owned by Prime or a harness. No loose feature work.

## V2 Success Test

V2 succeeds when Prime can use the cockpit to run multiple project threads with less Scott intervention while preserving proof, memory, retrieval, and review discipline.

In practical terms:

- Prime remembers important project/context decisions beyond any single model context window.
- Prime retrieves relevant files, notes, plans, and prior decisions through a ranked interface instead of depending on pasted context.
- Prime selects and routes work by risk tier, using stronger gated cognition only when the action justifies the cost.
- Prime can spawn, watch, steer, and recover sessions through a session lifecycle harness.
- Prime can delegate bounded harness work into workflow/sub-agent contexts so the orchestrator context does not fill with harness working memory.
- Scott sees bottlenecks, review gates, memory/retrieval activity, and harness health in Bifrost without managing worker sessions manually.

## Recommended First V2 Wave

Start V2 with a vertical slice that combines **Prime Autonomy + Echo Memory + Atlas Retrieval + Session Lifecycle visibility**.

Why this first:

- It directly addresses the reason Meridian exists: Scott should be the bottleneck only when judgment is truly needed.
- It uses V1 cockpit surfaces instead of building invisible infrastructure.
- It improves model reliability by giving Prime persistent, queryable context rather than larger prompt dumps.
- It keeps Prime's orchestrator window lean by moving harness execution into workflow/sub-agent contexts when available.
- It creates early proof for the central V2 claim: Prime's effective memory is not bounded by any one model context window.

First wave deliverable:

> Prime can open a project, retrieve its mission/memory/file context, choose the next queued objective, explain the plan in the cockpit, and route the first session-lifecycle action with proof hooks.

## Track 0: Compass Project Boundary Harness

**Objective:** Give Prime a backend definition of project identity, bounds, scope, difference, and cross-project communication before deeper UI controls are wired.

**Why it matters:** Polaris showed that parallel work becomes unsafe when project, repo, session, initiative, and venture boundaries blur. Compass prevents drift by making project context explicit before Prime retrieves memory, routes work, or accepts another project's evidence.

**First vertical slice:**

- Define what a project is: bounded body of work with outcome, context, artifacts, objectives, tasks, and proof trail.
- Distinguish project from repository/path, venture, initiative, and live session.
- Define inside/outside project bounds and ambiguity handling.
- Define project difference: mission/bearing, objectives, artifacts, memory pins, blockers, proof expectations.
- Define cross-project handoff packet: source project, target project, reason, payload type, evidence refs, approval need, and blocked raw-context bleed.

**Likely files/modules/docs:**

- `meridian_core/models.py`
- `meridian_core/intention.py`
- future `meridian_core/compass.py`
- future `tests/test_compass.py`
- `docs/v2-progress-tracker.md`

**Proof/test expectation:**

- Tests for project/repo/venture/session distinction.
- Tests for ambiguous scope returning a visible Compass question instead of selecting hidden context.
- Tests for cross-project handoff metadata and raw transcript/prompt replay blocking.
- Tests that same repo or same venture does not collapse two projects into one.

**Out-of-scope guardrails:**

- No shared mutable project state in V2.
- No raw cross-project transcript injection.
- No User Session retargeting from Compass project changes.

## Track 1: Prime Autonomy

**Objective:** Make Prime choose next work from project/backlog state instead of waiting for Scott to manually direct every worker.

**Why it matters:** V1 made Prime visible. V2 should make Prime meaningfully proactive.

**First vertical slice:**

- Define a `PrimeNextAction` domain object.
- Add a deterministic selector that takes project, backlog priority, active lane state, risk tier, and open review gates.
- Return a proposed action, confidence, blockers, and required human gate status.
- Define a `PrimeDecision` runtime packet that assembles Compass, Vulcan, Relay, and Aegis source refs before visible orchestration.
- Resolve the owning harness, executability status, blockers, proof questions, and invalidation conditions from backend state.
- Expose the runtime packet through `/bridge/prime-logic` so the Prime harness renders backend logic directly.
- Carry a typed `PrimeInteractionRequest` inside every decision packet so intent, action, project, risk, and visible prompt reference stay explicit.
- Consume Aegis aggregate gate summaries as Prime risk input and preserve approval-needed status when proof/risk blocks execution.
- Emit a no-drift audit proving request, context, owner, source refs, proof packet, Aegis risk, and visible fields agree.

**Likely files/modules/docs:**

- `meridian_core/prime_autonomy.py`
- `meridian_core/prime_runtime.py`
- `tests/test_prime_autonomy.py`
- `tests/test_prime_runtime.py`
- `docs/prime-autonomy-v2-contract.md`
- Bifrost view-model extension later, after the domain object is stable.

**Proof/test expectation:**

- Unit tests for priority ordering, blocked review gates, stale lanes, and human-gate required actions.
- Runtime snapshot tests for backend source refs, owner resolution, executability gates, proof packet, and bridge-visible payload shape.
- No-drift audit tests for project mismatch and missing owner-source failure.
- No model calls in the first slice.

**Out-of-scope guardrails:**

- Do not spawn real sessions yet.
- Do not mutate backlog state yet.
- Do not bypass Review Console gates.

## Track 2: Echo Harness Memory

**Objective:** Give Prime durable, ranked memory records that survive context windows and restarts.

**Why it matters:** Prime's effective memory must not be bounded by a single model context window.

**First vertical slice:**

- Define `MemoryRecord`, `MemoryQuery`, and `MemoryHit`.
- Store records in a simple local repository abstraction.
- Rank by project, recency, importance, and explicit pinning.
- Provide a deterministic query function for Prime.

**Likely files/modules/docs:**

- `meridian_core/echo.py`
- `tests/test_echo.py`
- `docs/echo-memory-contract.md`

**Proof/test expectation:**

- Tests for add/query/rank/pin/project-filter behavior.
- Tests for deterministic ordering.
- Tests that missing memory fails soft with an empty result.

**Out-of-scope guardrails:**

- No vector database in the first slice.
- No automatic memory injection into prompts until Relay budget rules are defined.
- No private account scraping.

## Track 3: Atlas Harness Retrieval / RAG

**Objective:** Give Prime ranked retrieval over Meridian files, docs, FileMap entries, and later Echo memory.

**Why it matters:** FileMap tells Meridian what matters; Atlas should retrieve the right thing at the right time.

**First vertical slice:**

- Build a file/docs-first retrieval query over FileMap entries and important docs.
- Return source-aware `AtlasHit` records with path, title, reason, and excerpt/summary.
- Keep ranking deterministic and cheap.

**Likely files/modules/docs:**

- `meridian_core/atlas.py`
- `tests/test_atlas.py`
- `docs/atlas-retrieval-contract.md`
- later FileMap registration by Build 3.

**Proof/test expectation:**

- Tests for matching by path, area, purpose, notes, and required path presence.
- Tests for no-result behavior and source references.

**Out-of-scope guardrails:**

- No embeddings/vector store in the first slice.
- No broad filesystem crawling.
- No raw log dumping into prompts.

## Track 4: Relay + Model Harness Hardening

**Objective:** Make model dispatch safer, cheaper, and more observable.

**Why it matters:** Polaris taught us Relay must not become prompt drag. V2 must preserve lean dispatch while giving Prime enough model capability.

**First vertical slice:**

- Add model capability metadata and prompt-drag telemetry fields.
- Let Relay know a route's intended risk tier, context budget, and adapter capability needs.
- Keep provider-neutral HTTP transport as the stable base.
- Treat **Claude, OpenAI, and DeepSeek** as first-class primary providers in the Model Harness, not optional one-off integrations.
- Add a DeepSeek direct-API adapter target for V4 models (`deepseek-v4-pro` default, `deepseek-v4-flash` fast lane) so Prime can route high-volume build work away from Claude when capacity or cost requires it.
- Gate DeepSeek coding authority through `docs/deepseek-provider-validation-gate.md`: DeepSeek starts as a candidate provider, may be used for bounded Q-mode/build planning, and must prove coding reliability before Prime can route autonomous implementation or review-clearing work through it.
- Bring forward Polaris's **Balance button** pattern: Bifrost exposes provider balances, token/cost telemetry, and model spend visibility for Claude, OpenAI, DeepSeek, and any aggregator routes.
- Bring forward Polaris's **visible prompt payload meter** pattern: every Relay dispatch must expose the final prompt payload size, budget percentage, and growth delta so Prime/Scott can catch additive prompt replay before it becomes latency, quota, or cost drag.

**Likely files/modules/docs:**

- `meridian_core/model_adapter.py`
- `meridian_core/relay_dispatch.py`
- `meridian_core/prompt_packet.py`
- `tests/test_model_adapter.py`
- `tests/test_relay_dispatch.py`
- `docs/model-harness-v2-contract.md`
- `docs/deepseek-provider-validation-gate.md`

**Proof/test expectation:**

- Tests for capability matching and missing-capability failures.
- Tests that prompt budget metadata is copied without inflating prompt content.
- Tests that each dispatch produces a visible prompt-size label such as `(under 1k)` or `(12.4k)` from structured prompt metrics, not scraped transcript text.
- Tests that queue/Q-mode prompt payloads do not grow across polls unless the task packet itself changed; unexpected growth is a DEGRADED prompt-drag finding.
- Tests that DeepSeek provider metadata resolves through the same adapter contract as Claude/OpenAI and never bypasses Relay/Aegis policy checks.
- Tests that DeepSeek starts below autonomous coding trust and cannot receive implementation, review-clearing, or branch/worktree authority until validation metadata records the required proof level.
- Tests that Balance surface data is derived from structured usage/provider telemetry rather than scraped card text.

**Out-of-scope guardrails:**

- No vendor-specific presets beyond the explicit primary-provider plan (Claude, OpenAI, DeepSeek) until the metadata contract is stable.
- No account-based automation public path.
- No hidden prompt expansion.

## Track 5: Aegis Gated Cognition

**Objective:** Turn Dynamic Risk-Tiered Dual-Structured Gated Cognition into runtime behavior.

**Why it matters:** Meridian overcomes weak models by escalating cognition and proof only when risk warrants it.

**First vertical slice:**

- Define a `CognitionPolicy` that maps action type/risk tier to required lanes, proof, review, and human gate.
- Return a proof requirement before Relay dispatch.

**Likely files/modules/docs:**

- `meridian_core/cognition_policy.py`
- `meridian_core/aegis.py`
- `tests/test_cognition_policy.py`
- `docs/cognition-policy-v2-contract.md`

**Proof/test expectation:**

- Tests for tier 1 single-lane, tier 2 normal review, tier 3 dual-lane + proof, tier 4 human gate.
- Tests that Aegis blocks missing proof before model dispatch.

**Out-of-scope guardrails:**

- Do not run dual model calls in the first policy slice.
- Do not allow policy to bypass Aegis.

## Track 6: Session Lifecycle Harness

**Objective:** Make Prime responsible for session lifecycle state instead of Scott manually supervising worker cards.

**Why it matters:** This is the operational heart of Meridian's agent-factory behavior.

**Workflow/sub-agent principle:** Session lifecycle should prefer workflow-backed harness execution when available. Prime should issue typed work orders, receive heartbeats/proof/results, and avoid absorbing each session's full working context.

**First vertical slice:**

- Define `SessionLifecycleState` and `SessionCommandPlan`.
- Define a workflow/sub-agent dispatch contract for bounded harness work.
- Model spawn, watch, steer, stop, transfer, archive, stale, and recover as typed actions.
- Define a session as runtime work state, not a project, repo, initiative, or durable memory record.
- Require state evidence: queue, worktree, branch, model, read/write/prompt timestamps, proof state, blocker summary, and project assignment.
- Require command-plan proof: target, reason, expected transition, evidence refs, queue, worktree/branch, Aegis gate result, executability, and rollback/recovery note.
- Keep close, archive, stop-before-close, and write-through as explicit backend actions before UI execution.
- Keep execution mocked/deterministic first.

**Likely files/modules/docs:**

- `meridian_core/session_lifecycle.py`
- `tests/test_session_lifecycle.py`
- `docs/session-lifecycle-v2-contract.md`
- `docs/workflow-subagent-harness-contract.md`

**Proof/test expectation:**

- Tests for legal/illegal transitions.
- Tests for workflow dispatch request/result summaries once runtime begins.
- Tests that branch/worktree movement requires Scott or Prime permission.
- Tests for stale recovery recommendation.
- Tests that raw worker chat is not required for Bifrost state display.
- Tests that project assignment does not define project scope; Compass owns project definition.
- Tests that close/archive/write-through failure leaves the session visibly recoverable.

**Out-of-scope guardrails:**

- No direct Polaris/Electron automation in the first slice.
- No destructive session operations.
- No branch switching without explicit permission object.
- No raw workflow transcript injection into Prime context.

## Track 7: Bifrost V2 Extensions

**Objective:** Extend the cockpit only where V2 capabilities need visible operation.

**Source-first UI requirement:** Bifrost V2 should not continue as a from-scratch generic dashboard. Start from existing JARVIS/HUD interface repositories and patterns, then adapt them to Meridian's Prime command-center model. The current source assessment lives in `docs/jarvis-ui-source-assessment.md` and includes Open.Jarvis, ethanplusai/jarvis, vierisid/jarvis, and the OpenClaw `jarvis-ui` HUD reference. Code reuse requires license and attribution verification; visual and interaction patterns may be adapted before direct code import.

**Why it matters:** V2 should not become invisible backend work. Scott should see Prime's memory, retrieval, autonomy, and lifecycle state.

**Balance button requirement:** Bifrost must expose the Meridian version of Polaris's Balance button. It should show provider/account health, remaining credits where available, token usage by provider/model, estimated spend, and cost pressure warnings that Prime can use when routing work across Claude, OpenAI, DeepSeek, and future adapters.

**Prompt payload visibility requirement:** Bifrost must expose the Meridian version
of Polaris's per-prompt payload indicator. Every model dispatch should show the
payload-size label and budget pressure in the system/progress surface. Queue/Q-mode
lanes should also show whether the latest prompt was flat or grew against the prior
dispatch, because unexpected growth means Relay is replaying history instead of
sending only the task packet.

**Voice-first cockpit requirement:** Bifrost must expose Meridian as a fully voice-enabled cockpit, not only a typed prompt UI. V2 should define the visible voice state and control surface for microphone input, spoken Prime output, NASA-style boot/status audio, mute/voice toggles, and listening/thinking/speaking indicators. Runtime speech recognition/TTS can land in a later slice, but the cockpit architecture must reserve the surface and data model now.

**Browser-first cockpit requirement:** Bifrost should remain a fast-iterating HTML/CSS cockpit surface. Electron may wrap it later, but V2 should not depend on Electron unless desktop-only capability is required. The preview HTML is a valid primary surface for design, testing, and early operation.

**First vertical slice:**

- Add view-model placeholders for:
  - Prime next action
  - Echo memory hits
  - Atlas retrieval hits
  - session lifecycle command preview
  - Aegis cognition policy result
  - prompt payload size / budget / growth indicator

**Likely files/modules/docs:**

- `bifrost/cockpit.py`
- `bifrost/static/cockpit.css`
- `tests/test_bifrost_cockpit.py`
- `docs/jarvis-ui-source-assessment.md`
- `docs/bifrost-v2-cockpit-extensions.md`

**Proof/test expectation:**

- Static render tests.
- Escaping tests.
- No live reads or JavaScript until the view model is stable.

**Out-of-scope guardrails:**

- Do not rebuild the cockpit layout.
- Do not add controls before domain actions exist.
- Do not add chat-like harness streams.

## Track 8: Federation Harness

**Objective:** Preserve multi-Meridian/multi-user collaboration as a later horizon.

**Why it matters:** Scott wants Meridian-to-Meridian collaboration, but single-user Prime must work first.

**First vertical slice:**

- Planning only unless Prime autonomy, memory, and lifecycle are stable.

**Likely files/modules/docs:**

- `docs/federation-harness-horizon.md`

**Proof/test expectation:**

- Architecture review only.

**Out-of-scope guardrails:**

- No network protocol yet.
- No permission model implementation yet.
- No shared mutable project state until local state is reliable.

## First Implementation Wave

Recommended order:

1. **Prime + Aegis:** `CognitionPolicy` domain model.
2. **Echo Harness:** deterministic memory records and query.
3. **Atlas Harness:** FileMap/docs-first retrieval.
4. **Prime Autonomy:** `PrimeNextAction` selector using Echo/Atlas placeholders.
5. **Session Lifecycle Harness:** typed lifecycle state and command plan.
6. **Bifrost Harness:** static V2 extensions that render the above.

This order gives Prime safer decisions before more autonomy, memory before prompt expansion, and visible cockpit proof before execution grows teeth.

## Review Gates

- Every V2 domain slice must include tests before it is marked built.
- Every new doc or module must be routed to FileMap by Build 3.
- Every three task-changing commits per lane must route Codex Reviews.
- Any track that introduces model calls must pass Aegis policy tests first.
- Any track that introduces session actions must prove unique worktree and branch-permission rules.

## Not V2 Yet

- Public product packaging.
- Multi-user federation runtime.
- Vector database or large retrieval infrastructure.
- Account-based automation public distribution strategy.
- Full autonomous branch movement.
- Direct destructive session controls.
