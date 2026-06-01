# Meridian File Map

This is the living knowledge tracker for important Meridian files.

Use it to quickly understand what each file owns, which harness or architecture area it belongs to, and where to look before editing.

This file should eventually feed Echo/Atlas memory injection so Prime and worker sessions can start with the right repository context instead of rediscovering the codebase every time.

Canonical repo path:

```text
C:\Users\scott\Code\Meridian\docs\FileMap.md
```

Obsidian mirror path:

```text
G:\My Drive\Aesop Academy\Obsidian\Meridian_Build\FileMap.md
```

## Core Authority And Context

| File | Area | Purpose | Related Tests | Notes |
| --- | --- | --- | --- | --- |
| `MISSION.md` | Mission / Prime authority | Prime's first boot authority file: directives, harness boot order, current mission objective, queue guidance. | `tests/test_mission.py` | Prime should read this before meaningful action. |
| `context.md` | Architecture memory | Working architecture vocabulary, product rules, Prime directives, UI decisions, harness naming, collaboration rules. | n/a | Update when major architecture decisions are made. |
| `docs/polaris-lessons-for-meridian.md` | Architecture memory | Structured lessons from Polaris: what worked, carry-forward principles, and what not to repeat. Includes Relay prompt efficiency (Lesson 16). | n/a | Reference before designing a new harness or major subsystem. |
| `docs/meridian-capabilities-architecture-map.md` | Architecture memory | High-level capability positioning and maturity map. What makes Meridian distinct and where each capability stands today (planned/domain-slice/integrated/needs-hardening). | n/a | Strategic; does not list file paths or class names. Companion to `docs/meridian-capabilities.md`. |
| `docs/meridian-capabilities.md` | Product recall | Plain-language recall sheet for major Meridian capabilities, including The Council. | n/a | Update when a new major capability is wired up. |
| `docs/meridian-pillars.md` | Prime Directives | Load-bearing Meridian ideas, currently named Prime Directives. | n/a | Public-safe fallback name: Meridian Pillars. |

## Core Package

| File | Area | Purpose | Related Tests | Notes |
| --- | --- | --- | --- | --- |
| `meridian_core/__init__.py` | Package API | Intentional root exports for stable public package surface. | import smoke checks, full suite | Do not export every internal helper automatically. |
| `meridian_core/models.py` | Domain model | Native Python objects for portfolio, projects, harnesses, heartbeat, proof, tasks, moves, adapters. | `tests/test_decisions.py`, others | Foundation for all higher-level slices. |
| `meridian_core/sample_state.py` | Demo/sample data | Deterministic sample portfolio and heartbeat state for CLI/demo/tests. | many tests | Keep realistic but small. |
| `meridian_core/cli.py` | Demo CLI | Prints mission load, wake sequence, progress intention, objectives, heartbeat, decisions, injections. | full suite + CLI smoke | Demo surface only, not the final UI. |

## Prime Decision Loop

| File | Area | Purpose | Related Tests | Notes |
| --- | --- | --- | --- | --- |
| `meridian_core/decisions.py` | Local decision loop | Deterministic local brain decisions from portfolio + heartbeat. | `tests/test_decisions.py` | No model calls. |
| `meridian_core/injections.py` | Session/directive modeling | Builds session injection objects. | `tests/test_injections.py` | Models future worker steering, not live automation yet. |
| `meridian_core/events.py` | Event recording | Records structured events. | currently light coverage | Future proof/history input. |

## Mission, Wake, Compass

| File | Area | Purpose | Related Tests | Notes |
| --- | --- | --- | --- | --- |
| `meridian_core/mission.py` | Mission boot | Loads/parses `MISSION.md` into native objects. | `tests/test_mission.py` | Required before Prime acts. |
| `meridian_core/wake.py` | Wake sequence | Builds structured wake brief from harness heartbeat state. | `tests/test_wake.py` | NASA-style Go calls are UI/audio concerns later. |
| `meridian_core/beacon.py` | Beacon / liveness harness | File-backed liveness checks that convert queue/sentinel freshness into `Heartbeat` objects. | `tests/test_beacon.py` | V0 Beacon slice only; process supervision and restart/resteer actions belong to later Prime runtime. |
| `meridian_core/intention.py` | Progress Intention / Compass | Builds stage/objective/risk-tier view from portfolio and decision state. | `tests/test_intention.py` | Functional seed for Prime's work intention. |
| `meridian_core/objectives.py` | Mission Objectives recall | Stable on-demand API for Compass-derived mission objectives. | `tests/test_objectives.py` | Future cockpit Mission Objectives button uses this. |

## Risk, Relay, Aegis, Review

| File | Area | Purpose | Related Tests | Notes |
| --- | --- | --- | --- | --- |
| `meridian_core/risk.py` | Risk Tier Engine | First-class risk assessment and requirements for tiers 0-4. | `tests/test_risk.py` | Decision engine foundation. |
| `meridian_core/council.py` | Council cognition | Structured Council cognition roles and deterministic role planning by risk tier. | `tests/test_council.py` | Consumed by Relay (RelayRoute.council_plan) and Compass (ProgressIntention). Domain-only; no model calls. |
| `meridian_core/planning.py` | Planning harness | Council-shaped planning harness: objective questions, researched/default answers, Chairman recommendation, and memory/ADR capture candidates. | `tests/test_planning.py` | Inspired by grill-with-docs, but extended with Polaris-style recommendations and decision-journal behavior. |
| `docs/planning-harness-council-brief.md` | Planning harness | Architecture brief for Prime's automated planning engine: question, research, recommendation, and Council ownership. | n/a | Read before adding `prime_plan`, research retrieval, or decision-journal planning behavior. |
| `docs/prime-planning-harness-answers.md` | Planning harness | Answered Council run for V0 Relay dispatch: evidence, risks, next action, unresolved Scott questions, ADR candidates, and build-slice recommendation. | n/a | First durable output of the Planning Harness acting on the live Meridian build. |
| `meridian_core/prompt_budget.py` | Prompt budget planning | Deterministic, tier-locked prompt budgets to prevent prompt drag. PromptBudgetTier enum, PromptBudget/PromptBudgetPlan dataclasses, prompt_budget_for_risk_tier() generator. | `tests/test_prompt_budget.py` | Integrated: RelayRoute.prompt_budget carries a PromptBudgetPlan for every dispatch. See `docs/relay-prompt-budget-integration-brief.md`. |
| `meridian_core/prompt_metrics.py` | Prompt performance measurement | Per-sample and summary metrics for Relay prompt performance: token count, construction time, TTFT, overhead delta vs. baseline. Status classification: HEALTHY, WATCH, DEGRADED based on thresholds. | `tests/test_prompt_metrics.py` | Domain-only; ready for Worker harness integration. Measures Relay overhead vs. vendor baseline. |
| `meridian_core/prompt_payload_meter.py` | Relay prompt metrics | Relay prompt payload visibility helper: `PromptPayloadSnapshot` and `PayloadStatus` classify prompt size, budget pressure, growth deltas, and Q-mode prompt drag. | `tests/test_prompt_payload_meter.py` | V2 helper for visible prompt payload meter. Pure deterministic logic; no model calls, filesystem reads, or live dispatch. |
| `tests/test_prompt_payload_meter.py` | Relay prompt metrics | Regression tests for prompt payload display labels, budget pressure, zero/invalid budget failure-soft behavior, and queue-mode growth detection. | n/a | Read before changing prompt payload thresholds or display-label semantics. |
| `meridian_core/prime_autonomy.py` | Prime Autonomy | Prime next-action domain model: immutable `PrimeNextAction` with action type, confidence, risk tier, source, targets, blockers, human gate, rationale, and evidence refs. | `tests/test_prime_autonomy.py` | V2 Prime Autonomy seed. Human-gated actions are not executable until a later approval model records approval. |
| `tests/test_prime_autonomy.py` | Prime Autonomy | Regression tests for `PrimeNextAction`, fallback/strict constructors, immutable evidence/blocker sets, confidence/risk mappings, and human-gate executability. | n/a | Read before changing PrimeNextAction execution semantics or public constructor behavior. |
| `meridian_core/relay.py` | Relay routing | Deterministic model/session routing plan from risk tier. Each RelayRoute carries a CouncilPlan and a PromptBudgetPlan for every dispatch. | `tests/test_relay.py` | No real model calls yet. council_plan and prompt_budget populated for all tiers. See `meridian_core/relay_packet.py` for PromptPacket assembly. |
| `meridian_core/relay_packet.py` | Relay dispatch | Relay-owned glue: assembles a validated PromptPacket from a RelayRoute. Reads route.prompt_budget for budget constraints and count_tokens() for token count. | `tests/test_relay_packet.py` | Internal to Relay dispatch; not a package-root export. |
| `meridian_core/relay_dispatch.py` | Relay dispatch | Immutable dispatch plan mapping a RelayRoute and PromptPacket to per-lane model work. Pure domain structure; no model calls. RelayDispatchLane.payload is always packet.model_payload(). | `tests/test_relay_dispatch.py` | Frozen dataclass. No metadata, lineage, or tokens sent to model. |
| `meridian_core/relay_executor.py` | Relay dispatch | Relay executor: executes RelayDispatch routing plans and dispatches work to model providers via model_adapter. | `tests/test_relay_executor.py` | V2 Relay runtime execution layer. Consumes RelayRoute decisions and executes dispatch to adapters. |
| `tests/test_relay_executor.py` | Relay dispatch | Test suite for meridian_core/relay_executor.py: coverage for dispatch execution, provider routing, error handling, and state transitions. | n/a | Run before changing meridian_core/relay_executor.py or Relay execution behavior. |
| `docs/relay-completeness-audit.md` | Relay routing | Active design audit: prevent Relay from being under-specified before Auto routing, model dispatch, or harness UI wiring. | n/a | Use before enabling Auto routing, adding a provider route, wiring Relay UI, or promoting a candidate route to trusted. |
| `docs/relay-heartbeat-model-routing-logic.md` | Relay routing | First model/vendor routing logic for Meridian: answers what model, vendor/route, risks, and proof gates Relay needs when heartbeat directs Prime to model work. | n/a | Draft routing logic; not runtime code yet. Provides context for Relay route selection, vendor decisions, and proof requirements. |
| `meridian_core/model_adapter.py` | Model Harness | Provider-neutral Model Adapter contract: payload-only callable boundary, deterministic fake adapter, and env-safe live adapter configuration wrapper. | `tests/test_model_adapter.py` | Public/private provider implementations stay outside Relay core; adapter receives only approved payload text. |
| `docs/deepseek-validation-benchmark-plan.md` | Model Harness | DeepSeek validation benchmark plan: repeatable proof ladder for direct API routing, Q-mode prompt flatness, coding trust, promotion, and demotion. | n/a | Use before promoting DeepSeek beyond candidate state or routing DeepSeek build-lane queue work. |
| `docs/model-harness-v2-contract.md` | Model Harness | Model harness V2 contract: provider capability metadata, prompt-drag telemetry, trust state, route ownership, direct-vs-aggregator evidence, allowed/blocked task types, external-review requirements, and Aegis/Relay policy binding. | n/a | V2 entry-point. Read before implementing model capability metadata, trust routing, or provider telemetry integration. |
| `meridian_core/restart_resteer.py` | Domain model | Prime restart/resteer domain objects and evaluator: detects empty queues, wrong queue routing, shared/main worktree violations, quota blocks, proof blocks, launch failures, and review cadence gates. | `tests/test_restart_resteer.py` | V2 Session Lifecycle / Prime recovery slice. Pure deterministic logic only; no live process control, branch movement, or file mutation. |
| `meridian_core/prompt_packet.py` | Relay prompt packet | Validated, immutable prompt bundle for Relay dispatch. Enforces token budget, source compliance, and serialization integrity at construction. Only `serialized_prompt` is sent to the model. | `tests/test_prompt_packet.py` | `PromptPacketValidationError` raised on invalid construction. `source_lineage` stored as immutable `MappingProxyType`. |
| `meridian_core/tokens.py` | Relay token counting | Conservative, deterministic token count approximation for Relay prompt construction. No vendor tokenizer dependency; replace with tiktoken when provider integration is ready. | `tests/test_tokens.py` | Read before adding token-counting logic to any Relay or Prompt Packet path. |
| `docs/review-console-surface-contract.md` | Review Console | Surface contract for the Review Console: what belongs there, how Prime populates it, what actions Scott can take, and how Bifrost/Beacon should render it. | n/a | Domain slice exists; Bifrost UI rendering and live Prime routing are planned. Owner: Build 4. |
| `meridian_core/aegis.py` | Aegis / Proof harness | Proof harness: AegisEvidence, ProofTrail, and Review Console bridge for cross-check findings. | `tests/test_aegis.py` | Proof-blocking is severity + status aware; ESCALATED is always blocking. |
| `docs/relay-aegis-risk-proof-gates.md` | Aegis / Proof harness | Relay-Aegis risk and proof gates contract: defines gates for Aegis to validate Relay routing decisions and enforce safety, proof, and validation requirements. | n/a | V2 architecture contract. Defines when Aegis must block, waive, or approve a Relay route based on risk tier, vendor validation, proof status, and human gates. |
| `meridian_core/review_console.py` | Review Console | Promptable review/gating surface for cross-check, proof, artifacts, plans, gates. | `tests/test_review_console.py` | Replaces "non-orchestrator window" name. |
| `docs/prime-status-console-cli-brief.md` | Review Console | Prime Status Console and Review Console CLI bridge: routes NASA-style mission logs and system messages to the Review Console surface, keeping Prime's conversational thread clean. | n/a | Architecture note, no runtime code. Owner: Build 4. Read before designing any Prime to Review Console message routing. |
| `docs/non-orchestrator-surface-naming.md` | Review Console | Naming rationale for the Review Console surface: establishes 'Review Console' as the canonical product-ready name, replacing the 'non-orchestrator window' placeholder. | n/a | Vocabulary doc. Read before writing docs or code that names this surface. |

## Build And Maturity

| File | Area | Purpose | Related Tests | Notes |
| --- | --- | --- | --- | --- |
| `meridian_core/builds.py` | Build/maturity registry | Tracks Meridian build number plus per-harness build and maturity. | `tests/test_builds.py` | `register` rejects duplicates; use `upsert` for intentional replacement. |

## File Map

| File | Area | Purpose | Related Tests | Notes |
| --- | --- | --- | --- | --- |
| `meridian_core/filemap.py` | File map / knowledge tracker | Domain-level knowledge tracker: `FileMapEntry`, `FileMap`, `make_default_map()`. | `tests/test_filemap.py` | Feed to Echo/Atlas for session memory injection. |
| `docs/FileMap.md` | File map / knowledge tracker | Human-readable living knowledge tracker for important Meridian files. | n/a | Obsidian mirror: `G:\My Drive\Aesop Academy\Obsidian\Meridian_Build\FileMap.md` |

## Planning And Handoffs

| File | Area | Purpose | Related Tests | Notes |
| --- | --- | --- | --- | --- |
| `docs/claude-handoff-completion-protocol.md` | Build process | Standard test/commit/push/Obsidian completion protocol for Claude handoffs. | n/a | Include in every build handoff unless local-only. |
| `docs/package-api-surface-note.md` | Package API policy | Guidance for intentional root exports. | n/a | Keep root API deliberate. |
| `docs/relay-prompt-budget-integration-brief.md` | Future Relay planning | Architectural integration of PromptBudgetPlan into RelayRoute, token budget enforcement, and prompt metrics. Planning only, no runtime changes yet. | n/a | Covers tier-to-budget mapping, CouncilPlan interaction, metrics pipeline, integration tests. |
| `docs/relay-heartbeat-model-routing-logic.md` | Relay / Model Harness | Draft heartbeat-triggered Relay routing logic: vendor/model list for Anthropic, OpenAI, DeepSeek direct, and OpenRouter; risk gates, route selection flow, trust posture, and promotion rules. | n/a | Read before wiring Relay harness logic items, Auto model routing, model/vendor selection, or provider trust displays. |
| `docs/relay-completeness-audit.md` | Relay / Model Harness | Completeness audit for Relay routing: forces explicit answers for intent, surface mode, account/session-first routing, session lifecycle, context health, risk gates, trust, proof, cost, privacy, fallback, observability, and stop conditions. | n/a | Use before enabling Auto routing, adding providers, promoting model routes, or wiring Relay harness UI. |
| `docs/relay-prompt-metrics-integration-brief.md` | Future Relay planning | Architectural plan for wiring PromptMetricSample collection into the Relay dispatch path and surfacing status in Compass. Planning only, no runtime changes yet. | n/a | Companion to relay-prompt-budget-integration-brief.md. |
| `docs/cross-check-aegis-integration-brief.md` | Future Aegis planning | How automatic cross-check should feed Aegis and Review Console. | n/a | Planning only. |
| `docs/build-next-aegis-cross-check-handoff.md` | Future handoff | Next slice after Review Console: Aegis cross-check evidence. | n/a | Do not run until Review Console is committed. |
| `docs/relay-prompt-packet-integration-plan.md` | Future Relay planning | Ready-to-implement plan for wiring PromptPacket into the Relay dispatch path. Replaces earlier integration brief with concrete implementation steps. | n/a | Status: ready to implement. Prepared by Build 1. |
| `docs/live-build-queue-hygiene.md` | Build process | Operational rules for live build queue task lifecycle: stale Active Task handling, heartbeat sections, allowed-file ownership, Prime idle response, and path to harness-backed queue state. | n/a | Read when setting up or reviewing live build queue operations. |
| `docs/ui-integration-checklist.md` | Build process | Active UI integration gate: checklist for plugging live behavior into Meridian UI. Ensures every visible piece works, shows unavailability, or stays hidden. | n/a | Owner: Prime/Bifrost coordination. Use when adding or changing UI controls, session behavior, or harness integration. |
| `docs/bifrost-session-queue-activation-brief.md` | Bifrost / session harness | Strategic design brief for Bifrost session-queue activation: UI behavior, session routing contracts, cockpit interaction design. No runtime code. | n/a | Owner: Build 5. Read before designing any Bifrost session or queue UI slice. |
| `docs/bifrost-cockpit-queue-status-brief.md` | Bifrost / session harness | Design brief for how the Meridian cockpit displays queue-driven worker activity — display, not activation. What Scott sees and how events surface without flooding the cockpit. | n/a | Companion to bifrost-session-queue-activation-brief.md. Owner: Build 5. Read before designing cockpit queue-status display. |
| `docs/live-build-5.md` | Build process | Live queue file for Build 5 (Bifrost / session-harness product lane). Covers UI behavior briefs, session queue activation, cockpit interaction contracts. | n/a | Do not edit from other build lanes. |
| `docs/live-codex-reviews.md` | Build process | Standing queue for the Codex Reviews A lane: independent review of completed build slices, repair routing back to build lanes, and checkpoint ledger. Prototype of Prime's future orchestration review loop. | n/a | Read before running or setting up a Codex review. Do not edit from build lanes. |
| `docs/live-codex-reviews-2.md` | Build process | Standing queue for the Codex Reviews B lane: docs, architecture, FileMap, Bifrost, and strategic consistency reviews. Parallel review capacity scaling prototype alongside Reviews A. | n/a | Read before running or setting up a Codex B review. Do not edit from build lanes. |
| `docs/prime-orchestration-harness-prototype.md` | Architecture memory | Documents the live build queue pattern as the first working prototype of Prime's orchestration harness: slice assignment, lane routing, allowed-file ownership, completion signals, and review coordination. | n/a | Strategic. Read before designing any orchestration harness slice. |
| `docs/v0-build-readiness-map.md` | Architecture memory | V0 gap analysis: names the minimum Meridian capabilities needed before Prime can wake and coordinate work. Honest per-capability assessment of what is missing for the smallest end-to-end Prime-as-coordinator loop. | n/a | Strategic. Owner: Build 4. Read before planning any V0 milestone or capability integration slice. |
| `docs/v0-v1-progress-tracker.md` | Architecture memory | Countable V0/V1 progress view for Prime, Codex, and Scott. Totals-first format: built/in-progress/needs-build counts by gate item. Scope source: v0-build-readiness-map.md gate summary. | n/a | Update when a gate item status changes. Companion to v0-build-readiness-map.md. |
| `docs/v1-capability-plan.md` | Architecture memory | V1 capability plan: defines V1 as the Bifrost cockpit release — Prime's intention, harness liveness, Review Console, Relay session state, Aegis findings, and build progress visible without CLI commands. | n/a | Owner: Build 4. V1 = cockpit UI live, wired to V0 domain. Read before planning any V1 capability or Bifrost integration. |
| `docs/workflow-subagent-usage-checklist.md` | Architecture memory | Operational checklist Prime uses to decide when bounded harness work should run in a workflow/sub-agent context instead of Prime's orchestrator window or a single Relay call. | n/a | V2 workflow operating guide. Read before dispatching Echo, Atlas, Aegis, Relay, Bifrost, Beacon, or Session Lifecycle work into workflow contexts. |
| `docs/ui-integration-checklist.md` | Bifrost / session harness | Active checklist for plugging behavior into the Meridian UI: prompt panels, reset/reload behavior, model bridge, harness buttons, visual regression checks, and stop conditions. | n/a | Read before changing `index.html`, model bridge UI wiring, or any visible session/harness control. |
| `docs/session-lifecycle-v2-contract.md` | Build process | Session Lifecycle V2 contract: typed state and command-plan responsibilities for spawning, watching, steering, recovering, and handing off sessions. | n/a | Read before implementing meridian_core/session_lifecycle.py or any live session orchestration controls. |
| `docs/session-lifecycle-implementation-checklist.md` | Build process | Session Lifecycle implementation checklist: verification steps for spawning, watching, steering, recovering, and handing off sessions per V2 contract. | n/a | Implementation guide. Use during development of meridian_core/session_lifecycle.py and live session orchestration features. |
| `meridian_core/session_lifecycle.py` | Bifrost / session harness | Session Lifecycle domain objects: typed enums and frozen dataclasses for session state, command planning, legality checking, and executability gates per V2 contract. | tests/test_session_lifecycle.py | Core harness implementation; read the v2-contract and implementation-checklist before modifying. |
| `tests/test_session_lifecycle.py` | Bifrost / session harness | Test suite for meridian_core/session_lifecycle.py: session state transitions, legality matrix, executability helpers, immutability, and proof progression. | n/a | Run before changing meridian_core/session_lifecycle.py or Session Lifecycle behavior. |
| `docs/v2-detailed-build-plan.md` | Architecture memory | V2 detailed build plan: phased roadmap for Echo integration, Atlas context retrieval, stronger Prime autonomy, and expanded model harnesses. Refines the v2-horizon-plan with concrete phases and decision gates. | n/a | Owner: Build 4. Read before planning V2 implementation phases or making architecture decisions about persistence and context. |
| `docs/v2-horizon-plan.md` | Architecture memory | V2 horizon plan: persistent memory via Echo, context retrieval via Atlas, stronger Prime autonomy, richer model harnesses. Not active V1 scope — start detailed V2 planning only after V1 cockpit is locked. | n/a | Horizon only. Do not pull V2 work into V0 or V1 build. |
| `docs/v3-parking-lot.md` | Architecture memory | V3 parking lot: horizon ideas for external reach, federation, and deeper distribution. Not active scope — do not pull V3 effort during V0, V1, or V2. | n/a | Parking lot, not a roadmap. Owner: Build 4. Ideas only until V2 closes. |
| `docs/prime-orchestration-state-model.md` | Architecture memory | Design bridge from the live build queue prototype to Python domain objects for Prime's state model. Names WorkerLane, TaskSlice, and other state objects with defined transitions. | n/a | Architecture only; no runtime code. Owner: Build 4. Read before implementing Prime orchestration Python domain objects. |
| `docs/prime-restart-resteer-contract.md` | Architecture memory | Prime restart/resteer contract: typed detection and recovery contract for stale lanes, wrong queues, shared worktrees, quota blocks, launch failures, proof blocks, and empty queue runway. | n/a | V2 entry-point. Read before implementing Prime recovery, session lifecycle restart logic, or queue runway automation. |
| `docs/bifrost-v0-cockpit-layout-brief.md` | Bifrost / session harness | V0 cockpit layout brief: where each surface lives on screen, what is dominant vs. supportive, and what V0 omits to achieve the Prime-centered command center inversion. | n/a | Design-only. Owner: Build 5. Companion to bifrost-cockpit-queue-status-brief.md and bifrost-session-queue-activation-brief.md. |
| `docs/bifrost-harness-dashboard-brief.md` | Bifrost / session harness | Harness dashboard surface brief: what opens when Scott clicks the Harness button — observability of every harness (heartbeat, capabilities, maturity, recent events). Observation-first; no controls in V0. | n/a | Design-only. Owner: Build 5. Companion to bifrost-v0-cockpit-layout-brief.md. |
| `docs/jarvis-ui-source-assessment.md` | Bifrost / session harness | Source assessment for JARVIS/HUD UI references that can shape Bifrost's Prime-first command center without importing unsafe or incompatible code. | n/a | Read before reusing external UI patterns. Source assessment only; not proof of completed runtime UI implementation. |
| `docs/bifrost-v2-cockpit-extensions.md` | Bifrost / session harness | Bifrost V2 cockpit extension contract: browser-first HUD direction, central Prime command bay, quiet PRIMED presence core, project rail, harness consoles, and voice-first interaction layer. | `tests/test_bifrost_cockpit.py` | Active V2 UI direction. Bifrost displays state; Prime/Relay/Aegis own decisions and routing. |
| `docs/v1-bifrost-cockpit-implementation-brief.md` | Bifrost / session harness | V1 Bifrost cockpit implementation brief: what V1 builds, what it omits, and which UI slices land first. Turns V0's domain capabilities into a Prime-centered, browser-rendered cockpit surface. | n/a | Owner: Build 5. Read before implementing any V1 cockpit UI slice. Source briefs: bifrost-v0-cockpit-layout-brief.md, bifrost-harness-dashboard-brief.md, bifrost-cockpit-queue-status-brief.md. |
| `docs/bifrost-configurable-progress-surface-brief.md` | Bifrost / session harness | Bifrost configurable progress and proof surface brief: how routine build-lane events, progress updates, and Aegis/Codex proof items are routed to a non-Prime surface, keeping the cockpit uncluttered. | n/a | Design-only. Owner: Build 5. Read before designing cockpit progress/proof routing. |
| `docs/v1-bifrost-live-data-contract.md` | Bifrost / session harness | V1 Bifrost live-data integration contract: how CockpitViewModel fields are populated from live Prime, Beacon, and Relay state at runtime. Bridges the static scaffold to real domain data. | n/a | Owner: Build 4. Read before wiring any live domain data into render_cockpit_html. |
| `docs/v1-bifrost-integration-sequence.md` | Bifrost / session harness | V1 Bifrost cockpit integration sequence: ordered steps from scaffold to live Prime-driven cockpit — build order, dependency contracts, and gate conditions for each integration slice. | n/a | Owner: Build 4. Read before planning or executing any V1 Bifrost integration slice. |
| `meridian_core/cockpit_provider.py` | Bifrost / session harness | Pure factory layer for Prime cockpit snapshots: build_snapshot() validates inputs and returns an immutable PrimeCockpitSnapshot with lanes sorted attention-first; demo_snapshot() returns a deterministic sample for Bifrost preview wiring. | `tests/test_cockpit_provider.py` | No filesystem, no live queue reads, no CLI. Owner: Build 1 commit 6c9a397. |
| `meridian_core/cockpit_state.py` | Bifrost / session harness | Prime cockpit snapshot and event domain types for V1 Bifrost: CockpitStatus, CockpitSnapshot, CockpitEvent, and lane/harness state models. Pure immutable data — no filesystem, CLI, or UI code. | `tests/test_cockpit_state.py` | Owner: Build 1. Read before designing any Prime-state-to-cockpit data flow. |
| `bifrost/__init__.py` | Bifrost / session harness | Bifrost package init: re-exports CockpitViewModel, render_cockpit_html, sample_cockpit_view_model, and related types from bifrost.cockpit. | `tests/test_bifrost_cockpit.py` | Public surface of the Bifrost package. Import from here, not from bifrost.cockpit directly. |
| `bifrost/cockpit.py` | Bifrost / session harness | Static HTML renderer for the Bifrost cockpit: CockpitViewModel dataclass, render_cockpit_html returning a self-contained HTML document, XSS-safe escaping, and sample_cockpit_view_model for deterministic previews. | `tests/test_bifrost_cockpit.py` | Dependency-free (stdlib only). Owner: Build 5. Read before adding any cockpit rendering, nav, or panel logic. |
| `bifrost/static/cockpit.css` | Bifrost / session harness | Cockpit CSS: V1 dark-mode palette, layout rules for Prime panel, lane strip, progress surface, and instrument band. Inlined into the HTML output by render_cockpit_html. | n/a | Loaded at render time via Path(__file__).parent / 'static' / 'cockpit.css'. Edit here to change cockpit visual style. |
| `tests/test_bifrost_cockpit.py` | Bifrost / session harness | 49-test suite for the V1 Bifrost cockpit scaffold (bifrost/cockpit.py and bifrost/__init__.py). Covers rendering, HTML structure, XSS safety, and sample view model. | n/a | Build 5 commit d13f1d1. |
| `tests/test_cockpit_state.py` | Bifrost / session harness | Test suite for meridian_core/cockpit_state.py cockpit snapshot domain types: CockpitStatus, LaneSummary, PrimeCockpitSnapshot, sort_lanes, filter_events. | n/a | Build 1 commit f56af55. |
| `tests/test_cockpit_provider.py` | Bifrost / session harness | Test suite for meridian_core/cockpit_provider.py: covers build_snapshot() validation, lane sorting, immutability, and demo_snapshot() determinism. | n/a | Build 1 commit 6c9a397. |
| `tests/test_restart_resteer.py` | Bifrost / session harness | Test suite for meridian_core/restart_resteer.py: covers empty queue, shared/main worktree, wrong queue, cadence, quota, proof, launch, and Obsidian divergence recovery decisions. | n/a | V2 Session Lifecycle / Prime recovery proof coverage. |

## Visual Assets

| File | Area | Purpose | Related Tests | Notes |
| --- | --- | --- | --- | --- |
| `docs/diagram-deck.html` | Architecture visuals | Click-through local HTML diagram deck. | visual/manual | Used for architecture visualization discussions. |
| `docs/assets/diagrams/` | Diagram assets | Generated architecture diagrams and variants. | visual/manual | Some are exploratory; not all are canonical. |

## Update Rule

When adding an important source file, domain slice, harness, or major architecture document, update this file in the same slice.
