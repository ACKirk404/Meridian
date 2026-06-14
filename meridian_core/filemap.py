"""
File Map Knowledge Tracker — living registry of important Meridian files.

Allows Prime, Echo, Atlas, and worker sessions to look up key files by path
or architecture area without rediscovering the codebase each session.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Known area labels — use these constants for consistency; arbitrary strings
# are also accepted.
# ---------------------------------------------------------------------------

class FileArea:
    MISSION          = "Mission / Prime authority"
    ARCHITECTURE     = "Architecture memory"
    PRODUCT_RECALL   = "Product recall"
    PRIME_DIRECTIVES = "Prime Directives"
    PACKAGE_API      = "Package API"
    DOMAIN_MODEL     = "Domain model"
    SAMPLE_DATA      = "Demo/sample data"
    DEMO_CLI         = "Demo CLI"
    DECISION_LOOP    = "Local decision loop"
    INJECTIONS       = "Session/directive modeling"
    EVENTS           = "Event recording"
    MISSION_BOOT     = "Mission boot"
    WAKE_SEQUENCE    = "Wake sequence"
    COMPASS          = "Progress Intention / Compass"
    OBJECTIVES       = "Mission Objectives recall"
    RISK_ENGINE      = "Risk Tier Engine"
    COUNCIL          = "Council cognition"
    PRIME_AUTONOMY   = "Prime Autonomy"
    PLANNING         = "Planning harness"
    RELAY_ROUTING    = "Relay routing"
    RELAY_DISPATCH   = "Relay dispatch"
    MODEL_HARNESS    = "Model Harness"
    PROMPT_BUDGET    = "Relay prompt budget"
    PROMPT_METRICS   = "Relay prompt metrics"
    PROMPT_PACKET    = "Relay prompt packet"
    AEGIS            = "Aegis / Proof harness"
    REVIEW_CONSOLE   = "Review Console"
    BEACON           = "Beacon / liveness harness"
    BUILD_MATURITY   = "Build/maturity registry"
    FILE_MAP         = "File map / knowledge tracker"
    BUILD_PROCESS    = "Build process"
    PACKAGE_POLICY   = "Package API policy"
    BIFROST          = "Bifrost / session harness"
    GOAL_RUNTIME     = "Goal Runtime / Goal Harness"
    BACKLOG          = "Backlog Authority"
    VOICE_IO         = "Voice I/O Authority"
    ROUTINES         = "Routine Authority"
    SESSION_ARCHIVE  = "Session Archive Authority"
    PROVIDER_BALANCE = "Provider Balance / Usage"
    WORKFLOW_DISPATCH = "Workflow Sub-Agent Harness / Dispatch"
    WORKFLOW_ATLAS    = "Atlas Workflow Adapter"


@dataclass
class FileMapEntry:
    path: str
    area: str
    purpose: str
    related_tests: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class FileMap:
    _entries: dict[str, FileMapEntry] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add(self, entry: FileMapEntry) -> None:
        """Register or replace an entry (upsert by path)."""
        self._entries[entry.path] = entry

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, path: str) -> FileMapEntry | None:
        """Return the entry for path, or None if not registered."""
        return self._entries.get(path)

    def require(self, path: str) -> FileMapEntry:
        """Return the entry for path. Raises KeyError if not registered."""
        entry = self._entries.get(path)
        if entry is None:
            raise KeyError(f"No file map entry for {path!r}")
        return entry

    # ------------------------------------------------------------------
    # Filtered views — stable sort order: path alphabetically
    # ------------------------------------------------------------------

    def all_entries(self) -> list[FileMapEntry]:
        """All entries sorted by path."""
        return sorted(self._entries.values(), key=lambda e: e.path)

    def by_area(self, area: str) -> list[FileMapEntry]:
        """Entries whose area matches exactly, sorted by path."""
        return sorted(
            (e for e in self._entries.values() if e.area == area),
            key=lambda e: e.path,
        )

    def with_tests(self) -> list[FileMapEntry]:
        """Entries that have at least one related test, sorted by path."""
        return sorted(
            (e for e in self._entries.values() if e.related_tests),
            key=lambda e: e.path,
        )

    # ------------------------------------------------------------------
    # Memory injection
    # ------------------------------------------------------------------

    def injection_summary(self, area: str | None = None) -> str:
        """
        Compact multi-line summary for session memory injection.

        Includes path, purpose, and related tests for each entry.
        Pass area to limit to a single architecture area.
        """
        entries = self.by_area(area) if area else self.all_entries()
        if not entries:
            return "(no file map entries)"
        lines: list[str] = ["# Meridian File Map — Key Files"]
        current_area: str | None = None
        for e in entries:
            if e.area != current_area:
                lines.append(f"\n## {e.area}")
                current_area = e.area
            lines.append(f"- {e.path}: {e.purpose}")
            if e.related_tests:
                tests = ", ".join(e.related_tests)
                lines.append(f"  tests: {tests}")
            if e.notes:
                lines.append(f"  note: {e.notes}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Default map — deterministic sample of current important Meridian files
# ---------------------------------------------------------------------------

def make_default_map() -> FileMap:
    """
    Return a deterministic FileMap covering all current important Meridian files.

    Update this when adding a significant new source file or document.
    """
    fm = FileMap()

    entries = [
        # -- Authority / context ----------------------------------------
        FileMapEntry(
            path="MISSION.md",
            area=FileArea.MISSION,
            purpose="Prime's first boot authority file: directives, harness boot order, current mission objective, queue guidance.",
            related_tests=["tests/test_mission.py"],
            notes="Prime should read this before meaningful action.",
        ),
        FileMapEntry(
            path="context.md",
            area=FileArea.ARCHITECTURE,
            purpose="Working architecture vocabulary, product rules, Prime directives, UI decisions, harness naming, collaboration rules.",
            related_tests=[],
            notes="Update when major architecture decisions are made.",
        ),
        FileMapEntry(
            path="docs/polaris-lessons-for-meridian.md",
            area=FileArea.ARCHITECTURE,
            purpose="Structured lessons from Polaris: what worked, why, carry-forward principles, and what not to repeat. Includes Relay prompt efficiency (Lesson 16).",
            related_tests=[],
            notes="Reference before designing a new harness or major subsystem.",
        ),
        FileMapEntry(
            path="docs/meridian-capabilities-architecture-map.md",
            area=FileArea.ARCHITECTURE,
            purpose="High-level capability positioning and maturity map. Covers what makes Meridian distinct and where each capability stands today (planned/domain-slice/integrated/needs-hardening).",
            related_tests=[],
            notes="Strategic; does not list file paths or class names. Companion to docs/meridian-capabilities.md and the live FileMap.",
        ),
        FileMapEntry(
            path="docs/FileMap.md",
            area=FileArea.FILE_MAP,
            purpose="Human-readable living knowledge tracker for important Meridian files.",
            related_tests=[],
            notes="Obsidian mirror: G:\\My Drive\\Obsidian\\Meridian_Build\\FileMap.md",
        ),
        FileMapEntry(
            path="docs/harness-stage-checklist.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Cross-harness stage tracker for Contract/Baseline, V2 Backend, Core Implementation, Prime Integration, Runtime Logic UI, Proofs/Review, and Operations status.",
            related_tests=["tests/test_filemap.py"],
            notes="Use when Scott asks what stage a harness is in or requests a harness/stage-specific build.",
        ),
        FileMapEntry(
            path="docs/harness-stage-checklist.html",
            area=FileArea.BUILD_PROCESS,
            purpose="Visual HTML dashboard for the harness stage checklist matrix; mirrors docs/harness-stage-checklist.md for easier status review.",
            related_tests=["tests/test_filemap.py"],
            notes="Update with docs/harness-stage-checklist.md in the same checkpoint.",
        ),
        FileMapEntry(
            path="docs/prime-core-handoff-20260602.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Current handoff for the Prime core and harness-stage work: active worktree, commits, Prime runtime internals, bridge/UI wiring, harness matrix, verification, rules, and next build recommendations.",
            related_tests=["tests/test_filemap.py"],
            notes="Read first when continuing this thread in a new session.",
        ),
        FileMapEntry(
            path="docs/v2-continuation-handoff-20260607.md",
            area=FileArea.BUILD_PROCESS,
            purpose="V2 continuation handoff for the June 7 coordinator pass: Main authority rules, Opus/Codex worker-review requirements, promoted backend commits, workflow dispatch proof, Electron UI authority, and next backend direction.",
            related_tests=["tests/test_filemap.py"],
            notes="Read when resuming the June 7 continuation thread or verifying current backend build provenance.",
        ),
        FileMapEntry(
            path="docs/prime-planning-harness-answers.md",
            area=FileArea.PLANNING,
            purpose="First Council-run planning answer brief: answers all Planning Harness questions for V0 Relay model/API dispatch and records the recommended adapter-first path.",
            related_tests=[],
            notes="Read before building real Relay dispatch or provider adapters.",
        ),

        # -- Core package -----------------------------------------------
        FileMapEntry(
            path="meridian_core/__init__.py",
            area=FileArea.PACKAGE_API,
            purpose="Intentional root exports for stable public package surface.",
            related_tests=[],
            notes="Do not export every internal helper automatically.",
        ),
        FileMapEntry(
            path="meridian_core/models.py",
            area=FileArea.DOMAIN_MODEL,
            purpose="Native Python objects for portfolio, projects, harnesses, heartbeat, proof, tasks, moves, adapters.",
            related_tests=["tests/test_decisions.py"],
            notes="Foundation for all higher-level slices.",
        ),
        FileMapEntry(
            path="meridian_core/sample_state.py",
            area=FileArea.SAMPLE_DATA,
            purpose="Deterministic sample portfolio and heartbeat state for CLI/demo/tests.",
            related_tests=[],
            notes="Keep realistic but small.",
        ),
        FileMapEntry(
            path="meridian_core/cli.py",
            area=FileArea.DEMO_CLI,
            purpose="Prints mission load, wake sequence, progress intention, objectives, heartbeat, decisions, injections.",
            related_tests=["tests/test_cli.py"],
            notes="Demo surface only, not the final UI.",
        ),

        # -- Decision loop ----------------------------------------------
        FileMapEntry(
            path="meridian_core/decisions.py",
            area=FileArea.DECISION_LOOP,
            purpose="Deterministic local brain decisions from portfolio and heartbeat.",
            related_tests=["tests/test_decisions.py"],
            notes="No model calls.",
        ),
        FileMapEntry(
            path="meridian_core/injections.py",
            area=FileArea.INJECTIONS,
            purpose="Builds session injection objects for future worker steering.",
            related_tests=["tests/test_injections.py"],
            notes="Models future worker steering, not live automation yet.",
        ),
        FileMapEntry(
            path="meridian_core/events.py",
            area=FileArea.EVENTS,
            purpose="Records structured events for proof/history input.",
            related_tests=[],
            notes="Currently light coverage.",
        ),

        # -- Mission, Wake, Compass -------------------------------------
        FileMapEntry(
            path="meridian_core/mission.py",
            area=FileArea.MISSION_BOOT,
            purpose="Loads and parses MISSION.md into native Python objects.",
            related_tests=["tests/test_mission.py"],
            notes="Required before Prime acts.",
        ),
        FileMapEntry(
            path="meridian_core/wake.py",
            area=FileArea.WAKE_SEQUENCE,
            purpose="Builds structured wake brief from harness heartbeat state.",
            related_tests=["tests/test_wake.py"],
            notes="NASA-style Go calls are UI/audio concerns later.",
        ),
        FileMapEntry(
            path="meridian_core/beacon.py",
            area=FileArea.BEACON,
            purpose="File-backed liveness checks that convert queue/sentinel freshness into Heartbeat objects.",
            related_tests=["tests/test_beacon.py"],
            notes="V0 Beacon slice only; process supervision and restart/resteer actions belong to later Prime runtime.",
        ),
        FileMapEntry(
            path="meridian_core/beacon_liveness_snapshot.py",
            area=FileArea.BEACON,
            purpose="Display-safe backend snapshot for the Electron Beacon Liveness panel.",
            related_tests=["tests/test_bifrost_cockpit.py", "tests/test_beacon.py"],
            notes="Bifrost consumes this through /bridge/beacon-liveness; no raw sentinel paths, process inspection, or session controls.",
        ),
        FileMapEntry(
            path="tests/test_beacon.py",
            area=FileArea.BEACON,
            purpose="Test suite for meridian_core/beacon.py: covers file-backed liveness checks, heartbeat conversion, and Beacon freshness behavior.",
            related_tests=[],
            notes="Run before changing Beacon liveness, sentinel freshness, or heartbeat observation behavior.",
        ),
        FileMapEntry(
            path="meridian_core/intention.py",
            area=FileArea.COMPASS,
            purpose="Builds stage/objective/risk-tier view from portfolio and decision state.",
            related_tests=["tests/test_intention.py"],
            notes="Functional seed for Prime's work intention.",
        ),
        FileMapEntry(
            path="meridian_core/compass.py",
            area=FileArea.COMPASS,
            purpose="Compass project runtime: project definition, scope evaluation, project-difference evidence, and cross-project handoff review objects.",
            related_tests=["tests/test_compass.py"],
            notes="Pure domain runtime; no repo mutation, session control, or model/provider calls.",
        ),
        FileMapEntry(
            path="meridian_core/compass_logic_snapshot.py",
            area=FileArea.COMPASS,
            purpose="Backend snapshot for Compass project-context logic shown in the visible harness panel.",
            related_tests=["tests/test_bifrost_cockpit.py"],
            notes="Bifrost consumes this through /bridge/compass-logic; keeps Compass UI documentation backend-sourced.",
        ),
        FileMapEntry(
            path="tests/test_compass.py",
            area=FileArea.COMPASS,
            purpose="Regression tests for meridian_core/compass.py project runtime definitions, scope checks, project-difference evaluation, and handoff review serialization.",
            related_tests=[],
            notes="Run before changing meridian_core/compass.py or Compass project-boundary behavior.",
        ),
        FileMapEntry(
            path="meridian_core/objectives.py",
            area=FileArea.OBJECTIVES,
            purpose="Stable on-demand API for Compass-derived mission objectives.",
            related_tests=["tests/test_objectives.py"],
            notes="Future cockpit Mission Objectives button uses this.",
        ),

        # -- Risk, Relay, Aegis, Review ----------------------------------------
        FileMapEntry(
            path="meridian_core/risk.py",
            area=FileArea.RISK_ENGINE,
            purpose="First-class risk assessment and requirements for tiers 0-4.",
            related_tests=["tests/test_risk.py"],
            notes="Decision engine foundation.",
        ),
        FileMapEntry(
            path="meridian_core/council.py",
            area=FileArea.COUNCIL,
            purpose="Structured Council cognition roles and deterministic role planning by risk tier.",
            related_tests=["tests/test_council.py"],
            notes="Consumed by Relay (RelayRoute.council_plan) and Compass (ProgressIntention). Domain-only; no model calls.",
        ),
        FileMapEntry(
            path="meridian_core/planning.py",
            area=FileArea.PLANNING,
            purpose="Council-shaped planning harness: objective questions, researched/default answers, Chairman recommendation, and memory/ADR capture candidates.",
            related_tests=["tests/test_planning.py"],
            notes="Inspired by grill-with-docs, but extended with Polaris-style recommendations and decision-journal behavior.",
        ),
        FileMapEntry(
            path="docs/planning-harness-council-brief.md",
            area=FileArea.PLANNING,
            purpose="Architecture brief for Prime's automated planning engine: question, research, recommendation, and Council ownership.",
            related_tests=[],
            notes="Read before adding prime_plan, research retrieval, or decision-journal planning behavior.",
        ),
        FileMapEntry(
            path="meridian_core/relay.py",
            area=FileArea.RELAY_ROUTING,
            purpose="Deterministic model/session routing plan from risk tier. Each RelayRoute carries a CouncilPlan and PromptBudgetPlan for every dispatch.",
            related_tests=["tests/test_relay.py"],
            notes="No real model calls yet. council_plan and prompt_budget populated for all tiers. See relay_packet.py for PromptPacket assembly.",
        ),
        FileMapEntry(
            path="meridian_core/relay_packet.py",
            area=FileArea.RELAY_ROUTING,
            purpose="Relay-owned glue: assembles a validated PromptPacket from a RelayRoute. Reads route.prompt_budget for budget constraints and count_tokens() for token count.",
            related_tests=["tests/test_relay_packet.py"],
            notes="Internal to Relay dispatch; not a package-root export.",
        ),
        FileMapEntry(
            path="meridian_core/relay_dispatch.py",
            area=FileArea.RELAY_DISPATCH,
            purpose="Immutable dispatch plan mapping a RelayRoute and PromptPacket to per-lane model work. Pure domain structure; no model calls. RelayDispatchLane.payload is always packet.model_payload().",
            related_tests=["tests/test_relay_dispatch.py"],
            notes="Frozen dataclass. No metadata, lineage, or tokens sent to model.",
        ),
        FileMapEntry(
            path="meridian_core/relay_auto_routing.py",
            area=FileArea.RELAY_DISPATCH,
            purpose="BR7 Prime/Relay Auto routing evidence: converts Prime intent and constraints into Relay-owned route, prompt packet, dispatch plan, and display-safe evidence without provider transport or UI route selection.",
            related_tests=["tests/test_relay_auto_routing.py"],
            notes="Run before changing Auto routing evidence, Prime/Relay ownership boundaries, prompt visibility, or BR7 dispatch proof fields.",
        ),
        FileMapEntry(
            path="meridian_core/relay_executor.py",
            area=FileArea.RELAY_DISPATCH,
            purpose="Relay executor: executes RelayDispatch routing plans and dispatches work to model providers via model_adapter.",
            related_tests=["tests/test_relay_executor.py"],
            notes="V2 Relay runtime execution layer. Consumes RelayRoute decisions and executes dispatch to adapters.",
        ),
        FileMapEntry(
            path="meridian_core/relay_logic_snapshot.py",
            area=FileArea.RELAY_ROUTING,
            purpose="Serializable Relay model-routing logic snapshot consumed by visible harnesses, including route precedence, audit depth, dispatch lanes, and proof prompts.",
            related_tests=["tests/test_relay_logic_snapshot.py"],
            notes="Run before changing Relay harness snapshot payloads or the /bridge/relay-logic bridge contract.",
        ),
        FileMapEntry(
            path="tests/test_relay_executor.py",
            area=FileArea.RELAY_DISPATCH,
            purpose="Test suite for meridian_core/relay_executor.py: coverage for dispatch execution, provider routing, error handling, and state transitions.",
            related_tests=[],
            notes="Run before changing meridian_core/relay_executor.py or Relay execution behavior.",
        ),
        FileMapEntry(
            path="tests/test_relay_logic_snapshot.py",
            area=FileArea.RELAY_ROUTING,
            purpose="Test suite for meridian_core/relay_logic_snapshot.py: proves the visible Relay harness snapshot stays JSON-serializable, source-identified, account/session-first, and free of prompt text leakage.",
            related_tests=[],
            notes="Run before changing Relay snapshot fields, bridge exposure, or harness logic rendering.",
        ),
        FileMapEntry(
            path="tests/test_relay.py",
            area=FileArea.RELAY_ROUTING,
            purpose="Test suite for meridian_core/relay.py: covers deterministic routing plan, CouncilPlan integration, PromptBudgetPlan, and risk tier mapping.",
            related_tests=[],
            notes="Run before changing meridian_core/relay.py or Relay routing logic.",
        ),
        FileMapEntry(
            path="tests/test_relay_packet.py",
            area=FileArea.RELAY_DISPATCH,
            purpose="Test suite for meridian_core/relay_packet.py: covers validated PromptPacket assembly, token budget enforcement, and source lineage.",
            related_tests=[],
            notes="Run before changing meridian_core/relay_packet.py or prompt packet construction.",
        ),
        FileMapEntry(
            path="tests/test_relay_dispatch.py",
            area=FileArea.RELAY_DISPATCH,
            purpose="Test suite for meridian_core/relay_dispatch.py: covers immutable dispatch plan mapping and per-lane model work routing.",
            related_tests=[],
            notes="Run before changing meridian_core/relay_dispatch.py or dispatch planning logic.",
        ),
        FileMapEntry(
            path="tests/test_relay_auto_routing.py",
            area=FileArea.RELAY_DISPATCH,
            purpose="Test suite for meridian_core/relay_auto_routing.py: proves BR7 Auto routing evidence is Relay-owned, deterministic, display-safe, and free of provider transport or UI route-selection authority.",
            related_tests=[],
            notes="Run before promoting Auto routing evidence or changing Prime/Relay BR7 boundaries.",
        ),
        FileMapEntry(
            path="meridian_core/model_adapter.py",
            area=FileArea.MODEL_HARNESS,
            purpose="Provider-neutral Model Adapter contract: payload-only callable boundary, deterministic fake adapter, and env-safe live adapter configuration wrapper.",
            related_tests=["tests/test_model_adapter.py"],
            notes="Public/private provider implementations stay outside Relay core; adapter receives only approved payload text.",
        ),
        FileMapEntry(
            path="tests/test_model_adapter.py",
            area=FileArea.MODEL_HARNESS,
            purpose="Test suite for meridian_core/model_adapter.py: covers provider-neutral adapter contracts, deterministic fake adapters, payload-only boundaries, and live adapter configuration wrappers.",
            related_tests=[],
            notes="Run before changing model adapter contracts, fake adapter behavior, or provider configuration handling.",
        ),
        FileMapEntry(
            path="docs/deepseek-provider-validation-gate.md",
            area=FileArea.MODEL_HARNESS,
            purpose="DeepSeek provider validation gate: proof requirements before DeepSeek can become a trusted primary provider for Q-mode build work.",
            related_tests=[],
            notes="DeepSeek remains candidate-gated until direct API, prompt-payload flatness, benchmark, and Codex review proof pass.",
        ),
        FileMapEntry(
            path="docs/deepseek-validation-benchmark-plan.md",
            area=FileArea.MODEL_HARNESS,
            purpose="DeepSeek validation benchmark plan: repeatable proof ladder for direct API routing, Q-mode prompt flatness, coding trust, promotion, and demotion.",
            related_tests=[],
            notes="Use before promoting DeepSeek beyond candidate state or routing DeepSeek build-lane queue work.",
        ),
        FileMapEntry(
            path="docs/deepseek-direct-provider-implementation-handoff.md",
            area=FileArea.MODEL_HARNESS,
            purpose="DeepSeek direct provider implementation handoff: implementation plan for direct-provider routing, credential boundaries, trust gating, and validation proof expectations.",
            related_tests=[],
            notes="Model Harness handoff. Read before adding DeepSeek direct provider runtime behavior or changing DeepSeek trust gates.",
        ),
        FileMapEntry(
            path="docs/deepseek-candidate-trust-metadata-implementation-checklist.md",
            area=FileArea.MODEL_HARNESS,
            purpose="Build-ready checklist for DeepSeek candidate-trust metadata, exact dispatch identity, direct-versus-aggregator proof, prompt-drag telemetry, and Bifrost-safe display.",
            related_tests=["tests/test_model_adapter.py", "tests/test_bifrost_cockpit.py"],
            notes="Runtime implementation is not authorized by the checklist alone. Read before wiring DeepSeek candidate trust metadata into Model Harness, Relay, Aegis, or Bifrost.",
        ),
        FileMapEntry(
            path="docs/model-harness-v2-contract.md",
            area=FileArea.MODEL_HARNESS,
            purpose="Model harness V2 contract: provider capability metadata, prompt-drag telemetry, trust state, route ownership, direct-vs-aggregator evidence, allowed/blocked task types, external-review requirements, and Aegis/Relay policy binding.",
            related_tests=[],
            notes="V2 entry-point. Read before implementing model capability metadata, trust routing, or provider telemetry integration.",
        ),
        FileMapEntry(
            path="docs/model-harness-metadata-implementation-checklist.md",
            area=FileArea.MODEL_HARNESS,
            purpose="Build-ready checklist for provider capability metadata, trust state, prompt drag, direct-vs-aggregator evidence, and Bifrost-visible model harness status.",
            related_tests=["tests/test_model_adapter.py", "tests/test_bifrost_cockpit.py"],
            notes="Runtime implementation is not authorized by the checklist alone. Read before wiring model metadata into Relay, Aegis, or Bifrost surfaces.",
        ),
        FileMapEntry(
            path="docs/model-harness-runtime-validation-checklist.md",
            area=FileArea.MODEL_HARNESS,
            purpose="Build-ready checklist for provider-neutral Model Harness runtime validation gates before live provider dispatch: metadata validation, exact dispatch identity, trust proof, prompt payload, and display-safe evidence.",
            related_tests=["tests/test_model_adapter.py", "tests/test_relay_executor.py", "tests/test_bifrost_cockpit.py"],
            notes="Runtime implementation is not authorized by the checklist alone. Read before adding provider metadata validators or allowing metadata-bound live dispatch.",
        ),
        FileMapEntry(
            path="docs/provider-transport-metadata-pass-through-checklist.md",
            area=FileArea.MODEL_HARNESS,
            purpose="Build-ready checklist for passing provider/model metadata through Relay and Model Harness transport boundaries without prompt or response leakage.",
            related_tests=["tests/test_model_adapter.py", "tests/test_relay_executor.py", "tests/test_bifrost_cockpit.py"],
            notes="Runtime implementation is not authorized by the checklist alone. Read before passing provider metadata through Relay transport envelopes or Bifrost display records.",
        ),
        FileMapEntry(
            path="docs/provider-result-validation-evidence-checklist.md",
            area=FileArea.MODEL_HARNESS,
            purpose="Build-ready checklist for provider-return and adapter-result validation evidence summaries without raw response leakage.",
            related_tests=["tests/test_model_adapter.py", "tests/test_relay_executor.py", "tests/test_bifrost_cockpit.py"],
            notes="Runtime implementation is not authorized by the checklist alone. Read before storing provider result metadata, validation evidence, or Bifrost-visible result summaries.",
        ),
        FileMapEntry(
            path="meridian_core/restart_resteer.py",
            area=FileArea.DOMAIN_MODEL,
            purpose="Prime restart/resteer domain objects and evaluator: detects empty queues, wrong queue routing, shared/main worktree violations, quota blocks, proof blocks, launch failures, and review cadence gates.",
            related_tests=["tests/test_restart_resteer.py"],
            notes="V2 Session Lifecycle / Prime recovery slice. Pure deterministic logic only; no live process control, branch movement, or file mutation.",
        ),
        FileMapEntry(
            path="meridian_core/prompt_budget.py",
            area=FileArea.PROMPT_BUDGET,
            purpose="Deterministic prompt token budget per risk tier. Prevents Relay prompt drag by bounding context sources and token limits per dispatch.",
            related_tests=["tests/test_prompt_budget.py"],
            notes="Tiers 0-1 minimal; Tier 2 focused; Tier 3 bounded proof/review; Tier 4 explained for human gate.",
        ),
        FileMapEntry(
            path="meridian_core/prompt_metrics.py",
            area=FileArea.PROMPT_METRICS,
            purpose="Per-sample and summary metrics for Relay prompt performance. Token count, construction time, TTFT, overhead delta vs. baseline. Status: HEALTHY/WATCH/DEGRADED.",
            related_tests=["tests/test_prompt_metrics.py"],
            notes="Domain-only. Measures Relay overhead vs. vendor baseline. See docs/relay-prompt-metrics-integration-brief.md.",
        ),
        FileMapEntry(
            path="meridian_core/prompt_payload_meter.py",
            area=FileArea.PROMPT_METRICS,
            purpose="Relay prompt payload visibility helper: PromptPayloadSnapshot and PayloadStatus classify prompt size, budget pressure, growth deltas, and Q-mode prompt drag.",
            related_tests=["tests/test_prompt_payload_meter.py"],
            notes="V2 helper for visible prompt payload meter. Pure deterministic logic; no model calls, filesystem reads, or live dispatch.",
        ),
        FileMapEntry(
            path="tests/test_prompt_payload_meter.py",
            area=FileArea.PROMPT_METRICS,
            purpose="Regression tests for PromptPayloadSnapshot and PayloadStatus, including zero/invalid budget failure-soft behavior and queue-mode growth detection.",
            related_tests=[],
            notes="Read before changing prompt payload thresholds or display-label semantics.",
        ),
        FileMapEntry(
            path="docs/relay-prompt-metrics-integration-brief.md",
            area=FileArea.PROMPT_METRICS,
            purpose="Architectural plan for wiring PromptMetricSample collection into Relay dispatch, including Polaris-style visible prompt payload size, budget pressure, and growth/flat status in Bifrost/Compass surfaces.",
            related_tests=[],
            notes="Planning only; no runtime changes yet.",
        ),
        FileMapEntry(
            path="docs/relay-prompt-payload-visibility-implementation-checklist.md",
            area=FileArea.PROMPT_METRICS,
            purpose="Build-ready checklist for wiring Relay prompt payload evidence into dispatch records and Bifrost-visible payload status without authorizing live model calls or UI implementation.",
            related_tests=["tests/test_prompt_payload_meter.py", "tests/test_relay_executor.py", "tests/test_bifrost_cockpit.py"],
            notes="Read before implementing prompt payload evidence, budget labels, growth/watch/degraded states, or Bifrost payload visibility.",
        ),
        FileMapEntry(
            path="docs/relay-bifrost-prompt-payload-meter-checklist.md",
            area=FileArea.PROMPT_METRICS,
            purpose="Build-ready checklist for carrying reviewed PromptPayloadSnapshot, budget, and growth metadata through Relay dispatch into a Bifrost-visible prompt payload meter.",
            related_tests=["tests/test_prompt_payload_meter.py", "tests/test_relay_executor.py", "tests/test_bifrost_cockpit.py"],
            notes="Docs-only checklist. Read before wiring prompt payload meter evidence into Relay dispatch, Aegis policy blockers, or Bifrost cockpit rendering.",
        ),
        FileMapEntry(
            path="docs/relay-dispatch-hardening-implementation-checklist.md",
            area=FileArea.RELAY_DISPATCH,
            purpose="Build-ready checklist for provider-neutral Relay dispatch hardening: envelope boundaries, exact model id handling, payload evidence propagation, Aegis proof hooks, blocked/error states, and Bifrost handoff.",
            related_tests=["tests/test_relay_executor.py", "tests/test_bifrost_cockpit.py"],
            notes="Read before changing Relay dispatch metadata pass-through, provider id handling, blocked/error evidence, or Bifrost-visible dispatch payload fields.",
        ),
        FileMapEntry(
            path="docs/relay-promptpacket-proof-metadata-implementation-checklist.md",
            area=FileArea.PROMPT_PACKET,
            purpose="Build-ready checklist for binding PromptPacket proof metadata into Relay dispatch envelopes and audit output: packet id/hash, budget refs, source-lineage compliance, Aegis evidence ids, snapshot/hash gaps, and raw-prompt exclusions.",
            related_tests=["tests/test_prompt_packet.py", "tests/test_relay_packet.py", "tests/test_relay_executor.py", "tests/test_bifrost_cockpit.py"],
            notes="Read before implementing PromptPacket proof metadata, packet hash evidence, budget/source-lineage gates, Aegis evidence bindings, or Bifrost-visible packet proof fields.",
        ),
        FileMapEntry(
            path="docs/relay-aegis-promptpacket-policy-integration-checklist.md",
            area=FileArea.RELAY_DISPATCH,
            purpose="Build-ready checklist for wiring Aegis PromptPacket proof policy evaluation into Relay dispatch: metadata translation, fail-closed preconditions, adapter-call gating, decision records, and Bifrost handoff.",
            related_tests=["tests/test_aegis.py", "tests/test_relay_executor.py", "tests/test_bifrost_cockpit.py"],
            notes="Read before integrating evaluate_prompt_packet_proof_policy() into Relay dispatch or mapping Aegis PromptPacket outcomes into Relay/Bifrost proof records.",
        ),
        FileMapEntry(
            path="docs/relay-aegis-demotion-retry-handoff-checklist.md",
            area=FileArea.RELAY_DISPATCH,
            purpose="Build-ready checklist for Relay/Aegis demotion, retry, fallback, human-gate, fail-closed, and display-safe Bifrost handoff behavior after PromptPacket policy review clearance.",
            related_tests=["tests/test_aegis.py", "tests/test_relay_executor.py", "tests/test_bifrost_cockpit.py"],
            notes="Read before wiring Aegis demotion or retry outcomes into Relay dispatch records or Bifrost handoff/view-model display fields.",
        ),
        FileMapEntry(
            path="meridian_core/prime_autonomy.py",
            area=FileArea.PRIME_AUTONOMY,
            purpose="Prime next-action domain model: immutable PrimeNextAction with action type, confidence, risk tier, source, targets, blockers, human gate, rationale, and evidence refs.",
            related_tests=["tests/test_prime_autonomy.py"],
            notes="V2 Prime Autonomy seed. Human-gated actions are not executable until a later approval model records approval.",
        ),
        FileMapEntry(
            path="meridian_core/prime_runtime.py",
            area=FileArea.PRIME_AUTONOMY,
            purpose="Prime runtime decision contract: assembles typed PrimeInteractionRequest plus Compass, Vulcan, Relay, Aegis risk, and Beacon liveness source refs into one visible PrimeDecision with owner resolution, executability gates, proof packet, no-drift audit, and bridge snapshot.",
            related_tests=["tests/test_prime_runtime.py", "tests/test_bifrost_cockpit.py"],
            notes="Bifrost consumes this through /bridge/prime-logic; Aegis aggregate gate summaries feed PrimeAegisRiskInput, Beacon liveness feeds advisory-only PrimeBeaconLivenessInput, and request fields stay visible. Keep Prime harness logic backend-sourced.",
        ),
        FileMapEntry(
            path="tests/test_prime_autonomy.py",
            area=FileArea.PRIME_AUTONOMY,
            purpose="Regression tests for PrimeNextAction, fallback/strict constructors, immutable evidence/blocker sets, confidence/risk mappings, and human-gate executability.",
            related_tests=[],
            notes="Read before changing PrimeNextAction execution semantics or public constructor behavior.",
        ),
        FileMapEntry(
            path="tests/test_prime_runtime.py",
            area=FileArea.PRIME_AUTONOMY,
            purpose="Regression tests for PrimeRuntimeContext, PrimeDecision shape, owner resolver, executability gates, Beacon advisory liveness input, source-missing blockers, and backend snapshot payload.",
            related_tests=[],
            notes="Run before changing Prime runtime bridge fields or visible Prime harness rendering.",
        ),
        FileMapEntry(
            path="meridian_core/prompt_packet.py",
            area=FileArea.PROMPT_PACKET,
            purpose="Validated, immutable prompt bundle for Relay dispatch. Enforces budget, source compliance, and serialization integrity at construction. Only serialized_prompt is sent to the model.",
            related_tests=["tests/test_prompt_packet.py"],
            notes="PromptPacketValidationError raised on invalid construction. source_lineage stored as immutable MappingProxyType.",
        ),
        FileMapEntry(
            path="tests/test_prompt_packet.py",
            area=FileArea.PROMPT_PACKET,
            purpose="Test suite for meridian_core/prompt_packet.py: covers PromptPacket validation, token budget enforcement, source compliance, serialization integrity, and model_payload boundaries.",
            related_tests=[],
            notes="Run before changing meridian_core/prompt_packet.py or PromptPacket proof metadata behavior.",
        ),
        FileMapEntry(
            path="docs/prompt-packet-implementation-checklist.md",
            area=FileArea.PROMPT_PACKET,
            purpose="Prompt packet implementation checklist: verification items for prompt packet construction, source compliance, serialization, and budget behavior.",
            related_tests=["tests/test_prompt_packet.py"],
            notes="Run prompt packet tests before changing prompt packet runtime behavior.",
        ),
        FileMapEntry(
            path="docs/relay-executor-api-policy.md",
            area=FileArea.RELAY_DISPATCH,
            purpose="Relay executor API policy: defines boundaries for Relay executor behavior, provider adapter use, payload handling, and public API expectations.",
            related_tests=["tests/test_relay_executor.py"],
            notes="Read before changing Relay executor interfaces, package exports, or adapter-call boundaries.",
        ),
        FileMapEntry(
            path="docs/relay-package-api-policy-note.md",
            area=FileArea.PACKAGE_POLICY,
            purpose="Relay package API policy note: documents which Relay helpers should remain internal versus exported through package APIs.",
            related_tests=[],
            notes="Read before adding Relay-related root exports or changing package API policy.",
        ),
        FileMapEntry(
            path="meridian_core/aegis.py",
            area=FileArea.AEGIS,
            purpose="Proof harness: AegisEvidence, ProofTrail, and Review Console bridge for cross-check findings.",
            related_tests=["tests/test_aegis.py"],
            notes="Proof-blocking is severity + status aware; ESCALATED is always blocking.",
        ),
        FileMapEntry(
            path="meridian_core/cross_check.py",
            area=FileArea.AEGIS,
            purpose="Backend cross-check authority: typed run requests/results, findings, repair routes, approve/dismiss/waive disposition, and repair verification reruns.",
            related_tests=["tests/test_cross_check.py"],
            notes="Pure domain authority for XCK rows; no UI, bridge, model/provider calls, persistence, process/session control, or repair execution.",
        ),
        FileMapEntry(
            path="meridian_core/aegis_logic_snapshot.py",
            area=FileArea.AEGIS,
            purpose="Display-safe backend Aegis Runtime Logic snapshot: ProofTrail evidence counts, cognition-policy gate result, Relay route posture, non-executable guardrails, and source refs.",
            related_tests=["tests/test_aegis_logic_snapshot.py", "tests/test_aegis.py", "tests/test_cognition_policy.py"],
            notes="Backend-owned snapshot only; no UI wiring, model calls, review responses, live dispatch, branch movement, or raw evidence bodies.",
        ),
        FileMapEntry(
            path="tests/test_aegis.py",
            area=FileArea.AEGIS,
            purpose="Test suite for meridian_core/aegis.py: covers proof harness, AegisEvidence, ProofTrail, and review console integration.",
            related_tests=[],
        ),
        FileMapEntry(
            path="tests/test_cross_check.py",
            area=FileArea.AEGIS,
            purpose="Test suite for meridian_core/cross_check.py: covers cross-check execution, repair routing, approve/dismiss/waive disposition, verification reruns, and display-safety boundaries.",
            related_tests=[],
            notes="Run before changing backend cross-check authority or XCK row semantics.",
        ),
        FileMapEntry(
            path="tests/test_aegis_logic_snapshot.py",
            area=FileArea.AEGIS,
            purpose="Regression tests for the backend-owned Aegis Runtime Logic snapshot, including display-only guardrails, proof trail serialization, and cognition-policy blocking behavior.",
            related_tests=[],
            notes="Run before changing meridian_core/aegis_logic_snapshot.py or the backend Aegis Runtime Logic payload.",
        ),
        FileMapEntry(
            path="docs/cross-check-authority-contract.md",
            area=FileArea.AEGIS,
            purpose="Backend contract for V2 cross-check authority: execution, repair routing, disposition, rerun verification, and display-safety guardrails.",
            related_tests=["tests/test_cross_check.py"],
            notes="Read before wiring XCK authority into Prime, Aegis, Review Console, or Bifrost-visible display surfaces.",
        ),
        FileMapEntry(
            path="docs/aegis-relay-summary-handoff-contract.md",
            area=FileArea.AEGIS,
            purpose="Aegis-to-Relay summary handoff contract: stable gate-result, aggregate-summary, waiver/approval, and model/vendor evidence shapes for Relay and Bifrost consumption.",
            related_tests=["tests/test_aegis.py", "tests/test_relay_executor.py"],
            notes="Read before changing Aegis gate summaries, Relay proof-context consumption, or Bifrost gate display fields.",
        ),
        FileMapEntry(
            path="docs/aegis-promptpacket-proof-policy-checklist.md",
            area=FileArea.AEGIS,
            purpose="Build-ready checklist for deterministic Aegis evaluation of PromptPacket proof metadata before Relay dispatch: packet id/hash, source-lineage compliance, budget gates, evidence ids, snapshot/hash gaps, and allow/warn/demote/block/human-gate outcomes.",
            related_tests=["tests/test_aegis.py", "tests/test_relay_executor.py", "tests/test_bifrost_cockpit.py"],
            notes="Read before implementing Aegis PromptPacket proof policy evaluation or wiring packet proof outcomes into Relay/Bifrost handoff fields.",
        ),
        FileMapEntry(
            path="meridian_core/review_console.py",
            area=FileArea.REVIEW_CONSOLE,
            purpose="Promptable review/gating surface for cross-check, proof, artifacts, plans, gates.",
            related_tests=["tests/test_review_console.py"],
            notes="Replaces 'non-orchestrator window' name.",
        ),
        FileMapEntry(
            path="meridian_core/review_console_snapshot.py",
            area=FileArea.REVIEW_CONSOLE,
            purpose="Display-safe backend snapshot for the Electron Arbiter / Review Console panel.",
            related_tests=["tests/test_bifrost_cockpit.py", "tests/test_review_console.py"],
            notes="Bifrost consumes this through /bridge/review-console; no response route, approval buttons, or raw item content.",
        ),
        FileMapEntry(
            path="docs/review-console-surface-contract.md",
            area=FileArea.REVIEW_CONSOLE,
            purpose="Review Console surface contract: defines what belongs in the review surface, how Prime populates it, available disposition actions, and Bifrost/Beacon rendering expectations.",
            related_tests=[],
            notes="Domain slice exists; Bifrost UI rendering and live Prime routing are planned.",
        ),
        FileMapEntry(
            path="docs/prime-status-console-cli-brief.md",
            area=FileArea.REVIEW_CONSOLE,
            purpose="Prime Status Console and Review Console CLI bridge: routes NASA-style mission logs and system messages to the Review Console surface, keeping Prime's conversational thread clean.",
            related_tests=[],
            notes="Architecture note, no runtime code. Owner: Build 4. Read before designing any Prime to Review Console message routing.",
        ),
        FileMapEntry(
            path="docs/non-orchestrator-surface-naming.md",
            area=FileArea.REVIEW_CONSOLE,
            purpose="Naming rationale for the Review Console surface: establishes 'Review Console' as the canonical product-ready name, replacing the 'non-orchestrator window' placeholder.",
            related_tests=[],
            notes="Vocabulary doc. Read before writing docs or code that names this surface.",
        ),

        # -- Build and maturity -----------------------------------------
        FileMapEntry(
            path="meridian_core/builds.py",
            area=FileArea.BUILD_MATURITY,
            purpose="Tracks Meridian build number plus per-harness build number and maturity state.",
            related_tests=["tests/test_builds.py"],
            notes="register() raises on duplicates; use upsert() for intentional replacement.",
        ),

        # -- Build process ----------------------------------------------
        FileMapEntry(
            path="docs/live-codex-reviews.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Standing queue for the Codex Reviews A lane: independent review of completed build slices, repair routing back to build lanes, and checkpoint ledger. Prototype of Prime's future orchestration review loop.",
            related_tests=[],
            notes="Read before running or setting up a Codex review. Do not edit from build lanes.",
        ),
        FileMapEntry(
            path="docs/live-codex-reviews-2.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Standing queue for the Codex Reviews B lane: docs, architecture, FileMap, Bifrost, and strategic consistency reviews; checkpoint ledger and proof log parallel to live-codex-reviews.md. Scaling prototype for spawning additional review capacity.",
            related_tests=[],
            notes="Read before running or setting up a Reviews B round. Do not edit from build lanes.",
        ),
        FileMapEntry(
            path="docs/live-build-queue-hygiene.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Live build queue hygiene: maintenance standards for live-build-*.md queue files, lint rules, stale-marker cleanup, archive policies, and cross-lane coordination rules.",
            related_tests=[],
            notes="Governance. Read before modifying any live-build-*.md queue structure.",
        ),
        FileMapEntry(
            path="docs/live-build-1.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Live queue file for Build 1 (Relay/model harness runtime lane): active tasks, completions, cadence, and review-ready markers.",
            related_tests=[],
            notes="Do not edit from other build lanes except for approved FileMap/queue coordination markers.",
        ),
        FileMapEntry(
            path="docs/live-build-2.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Live queue file for Build 2 (Session Lifecycle lane): active tasks, permissions/runtime completions, cadence, and review-ready markers.",
            related_tests=[],
            notes="Do not edit from other build lanes except for approved FileMap/queue coordination markers.",
        ),
        FileMapEntry(
            path="docs/live-build-3.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Live queue file for Build 3 (FileMap / knowledge tracker lane): active FileMap maintenance tasks, completions, cadence, and review-ready markers.",
            related_tests=[],
            notes="Build 3 owns this queue. Read before running FileMap audits or recording FileMap completion markers.",
        ),
        FileMapEntry(
            path="docs/live-build-4.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Live queue file for Build 4 (Aegis/architecture lane): active tasks, contract/checklist completions, cadence, and review-ready markers.",
            related_tests=[],
            notes="Do not edit from other build lanes except for approved FileMap/queue coordination markers.",
        ),
        FileMapEntry(
            path="docs/live-build-5.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Live queue file for Build 5 (Bifrost / session-harness product lane): UI behavior briefs, session queue activation, cockpit interaction contracts, cadence, and review-ready markers.",
            related_tests=[],
            notes="Do not edit from other build lanes except for approved FileMap/queue coordination markers.",
        ),
        FileMapEntry(
            path="docs/prime-queue-runway-policy.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Prime queue runway policy: defines when Prime is allowed to queue work and when to respect runway constraints. Coordination rules between live build lanes and Prime's task-routing autonomy.",
            related_tests=[],
            notes="Queue governance. Read before implementing Prime's autonomous task queueing or modifying build-lane submission rules.",
        ),
        FileMapEntry(
            path="docs/live-build-active-polling-contract.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Live build active polling contract: defines worker polling-loop requirements, idle rules, completion behavior, and harness expectations for markdown-backed build queues.",
            related_tests=[],
            notes="Process contract. Read before changing build-lane polling cadence, idle semantics, or session harness wake behavior.",
        ),
        FileMapEntry(
            path="docs/queue-runway-runtime-object.md",
            area=FileArea.BUILD_PROCESS,
            purpose="V2 QueueRunway runtime object contract: machine-readable build-lane queue state, task entries, cadence, review gates, escalation, and markdown mirror mapping.",
            related_tests=[],
            notes="V2 domain contract. Read before implementing queue runway state objects or replacing markdown-only queue parsing.",
        ),
        FileMapEntry(
            path="docs/v2-orchestrator-handoff-20260601.md",
            area=FileArea.BUILD_PROCESS,
            purpose="V2 orchestrator handoff: containment, routing, review pressure, queue-update, and supervised transition rules for the replacement coordinator.",
            related_tests=[],
            notes="Coordinator architecture handoff. Read before changing V2 orchestration ownership or routing approvals.",
        ),
        FileMapEntry(
            path="docs/v2-orchestrator-transition-ledger.md",
            area=FileArea.BUILD_PROCESS,
            purpose="V2 orchestrator transition ledger: shared coordination surface for replacement coordinator intake checks, routing recommendations, and takeover status.",
            related_tests=[],
            notes="Coordinator ledger. Read before declaring takeover complete or approving branch/worktree movement during transition.",
        ),
        FileMapEntry(
            path="docs/main-write-coordination-ledger.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Main-write coordination ledger: tracks reviewed branch landings, main advancement, worktree syncs, and provenance for coordinator-approved writes.",
            related_tests=[],
            notes="Read before reasoning about mainline movement, reviewed landings, or coordinator write provenance.",
        ),

        # -- V2 Contract Docs (Echo, Atlas, Workflow subagent) ---------
        FileMapEntry(
            path="docs/agentic-ai-framework-checklist.md",
            area=FileArea.ARCHITECTURE,
            purpose="Agentic AI framework checklist: key design decisions and verification items for Meridian as an agentic AI system. Gate for V2 entry-point design, memory contracts, and harness expansion.",
            related_tests=[],
            notes="V2 entry-point. Defines contract requirements for Echo, Atlas, workflow harnesses, and extended Prime autonomy.",
        ),
        FileMapEntry(
            path="docs/atlas-retrieval-contract.md",
            area=FileArea.ARCHITECTURE,
            purpose="Atlas retrieval contract: Prime's memory and context retrieval interface for V2. Defines query patterns, response guarantees, conflict resolution, and harness integration points.",
            related_tests=[],
            notes="V2 entry-point. Read before implementing or extending Atlas harness or Prime's context query logic.",
        ),
        FileMapEntry(
            path="meridian_core/atlas.py",
            area=FileArea.FILE_MAP,
            purpose="Atlas runtime harness: deterministic FileMap/docs-first retrieval with source-aware ranking for Prime context selection.",
            related_tests=["tests/test_atlas.py"],
            notes="Pure retrieval/ranking helper; no embeddings, network calls, or live filesystem mutation.",
        ),
        FileMapEntry(
            path="tests/test_atlas.py",
            area=FileArea.FILE_MAP,
            purpose="Test suite for Atlas deterministic retrieval, source-aware ranking, and failure-soft behavior.",
            related_tests=[],
            notes="Run before changing meridian_core/atlas.py or Atlas FileMap behavior.",
        ),
        FileMapEntry(
            path="docs/echo-memory-contract.md",
            area=FileArea.ARCHITECTURE,
            purpose="Echo memory contract: persistent memory interface for V2. Defines storage structure, session isolation, recall guarantees, and integration with Prime's long-term decision making.",
            related_tests=[],
            notes="V2 entry-point. Read before implementing or extending Echo harness or Prime's persistent state logic.",
        ),
        FileMapEntry(
            path="docs/echo-atlas-handoff-contract.md",
            area=FileArea.ARCHITECTURE,
            purpose="Echo-to-Atlas retrieval handoff contract: defines when Prime queries Echo memory versus Atlas file/doc retrieval and how results compose without stale-context risk.",
            related_tests=[],
            notes="V2 first-wave contract. Read before wiring Echo/Atlas cooperation, retrieval composition, or context-source ranking.",
        ),
        FileMapEntry(
            path="meridian_core/echo.py",
            area=FileArea.PRODUCT_RECALL,
            purpose="Echo runtime harness: deterministic memory records, query filters, and ranking for Prime recall without model calls.",
            related_tests=["tests/test_echo.py"],
            notes="Pure in-memory repository/domain slice; durable storage integration remains future work.",
        ),
        FileMapEntry(
            path="tests/test_echo.py",
            area=FileArea.PRODUCT_RECALL,
            purpose="Test suite for Echo memory records, query ranking, pinning, recency, and corrupt-record failure-soft behavior.",
            related_tests=[],
            notes="Run before changing meridian_core/echo.py or Echo ranking semantics.",
        ),
        FileMapEntry(
            path="docs/graphiti-sidecar-contract.md",
            area=FileArea.ARCHITECTURE,
            purpose="Graphiti sidecar contract: defines optional advisory context-graph use while Echo and Atlas remain authoritative deterministic memory and retrieval surfaces.",
            related_tests=["tests/test_graphiti_memory.py"],
            notes="Read before live Graphiti spikes, Neo4j/FalkorDB wiring, or any attempt to promote Graphiti results into Prime decisions.",
        ),
        FileMapEntry(
            path="meridian_core/graphiti_memory.py",
            area=FileArea.PRODUCT_RECALL,
            purpose="Graphiti advisory memory sidecar boundary: projects Echo summaries and Atlas excerpts into safe episodes, preserves source refs, and projects Graphiti search results back as advisory hits only.",
            related_tests=["tests/test_graphiti_memory.py", "tests/test_package_api.py"],
            notes="Disabled by default; no hard Graphiti import, graph DB, provider key, network call, Echo write, Atlas write, or prompt injection.",
        ),
        FileMapEntry(
            path="tests/test_graphiti_memory.py",
            area=FileArea.PRODUCT_RECALL,
            purpose="Test suite for Graphiti sidecar config, safe Echo/Atlas projection, superseded-memory skip behavior, optional async client boundary, and advisory-only search hits.",
            related_tests=[],
            notes="Run before changing Graphiti sidecar authority, source-ref, or prompt-drag boundaries.",
        ),
        FileMapEntry(
            path="docs/workflow-subagent-harness-contract.md",
            area=FileArea.ARCHITECTURE,
            purpose="Workflow subagent harness contract: expanded harness framework for V2. Defines multi-step workflows, tool orchestration, decision parallelism, and integration with Prime's stronger autonomy.",
            related_tests=[],
            notes="V2 entry-point. Read before designing or implementing new harness types or multi-step workflow orchestration.",
        ),
        FileMapEntry(
            path="docs/workflows-subagent-harness-architecture.md",
            area=FileArea.ARCHITECTURE,
            purpose="Workflow/sub-agent harness architecture note: explains how harness work should run in bounded workflow contexts so Prime's orchestrator context stays lean.",
            related_tests=[],
            notes="Read before designing Prime workflow delegation, harness offloading, or context-window protection behavior.",
        ),
        FileMapEntry(
            path="docs/workflow-subagent-usage-checklist.md",
            area=FileArea.ARCHITECTURE,
            purpose="Operational checklist Prime uses to decide when bounded harness work should run in a workflow/sub-agent context instead of Prime's orchestrator window or a single Relay call.",
            related_tests=[],
            notes="V2 workflow operating guide. Read before dispatching Echo, Atlas, Aegis, Relay, Bifrost, Beacon, or Session Lifecycle work into workflow contexts.",
        ),
        FileMapEntry(
            path="docs/session-lifecycle-v2-contract.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Session Lifecycle V2 contract: typed state and command-plan responsibilities for spawning, watching, steering, recovering, and handing off sessions.",
            related_tests=[],
            notes="Read before implementing meridian_core/session_lifecycle.py or any live session orchestration controls.",
        ),
        FileMapEntry(
            path="docs/session-lifecycle-implementation-checklist.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Session Lifecycle implementation checklist: verification steps for spawning, watching, steering, recovering, and handing off sessions per V2 contract.",
            related_tests=[],
            notes="Implementation guide. Use during development of meridian_core/session_lifecycle.py and live session orchestration features.",
        ),
        FileMapEntry(
            path="docs/session-lifecycle-permissions-prime-beacon-contract.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Session Lifecycle permissions and Prime/Beacon binding contract: branch/worktree permissions, Beacon heartbeat observations, Prime recommendations, and restart/resteer proof boundaries.",
            related_tests=[],
            notes="V2 domain contract. Read before implementing permission contexts, Beacon staleness binding, or Prime restart/resteer recommendations.",
        ),
        FileMapEntry(
            path="docs/session-lifecycle-permissions-implementation-checklist.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Session Lifecycle permissions implementation checklist: code-ready checklist for PermissionContext invariants, PrimeAutonomyInput, heartbeat staleness, and restart/resteer findings.",
            related_tests=["tests/test_session_lifecycle.py"],
            notes="Implementation checklist. Run Session Lifecycle tests before changing permission-boundary runtime code.",
        ),
        FileMapEntry(
            path="meridian_core/session_lifecycle.py",
            area=FileArea.BIFROST,
            purpose="Session Lifecycle domain objects: typed enums and frozen dataclasses for session state, command planning, legality checking, executability gates, and SK9 backend close/write-through authority per V2 contract.",
            related_tests=["tests/test_session_lifecycle.py"],
            notes="Core harness implementation; read the v2-contract and implementation-checklist before modifying.",
        ),
        FileMapEntry(
            path="meridian_core/vulcan_logic_snapshot.py",
            area=FileArea.BIFROST,
            purpose="Backend snapshot for Vulcan Session Lifecycle logic shown in the visible harness panel.",
            related_tests=["tests/test_bifrost_cockpit.py"],
            notes="Bifrost consumes this through /bridge/vulcan-logic; keeps session target and lifecycle UI documentation Vulcan-owned.",
        ),
        FileMapEntry(
            path="tests/test_session_lifecycle.py",
            area=FileArea.BIFROST,
            purpose="Test suite for meridian_core/session_lifecycle.py: session state transitions, legality matrix, executability helpers, immutability, proof progression, and SK9 close/write-through authority.",
            related_tests=[],
            notes="Run before changing meridian_core/session_lifecycle.py or Session Lifecycle behavior.",
        ),
        FileMapEntry(
            path="docs/federation-harness-horizon.md",
            area=FileArea.ARCHITECTURE,
            purpose="Federation harness horizon plan: multi-Meridian and multi-user collaboration concepts, permission boundaries, and Prime-to-Prime handoff vocabulary.",
            related_tests=[],
            notes="Planning only; V2 architecture entry point for later V3 federation runtime.",
        ),
        FileMapEntry(
            path="meridian_core/federation_horizon_snapshot.py",
            area=FileArea.ARCHITECTURE,
            purpose="Display-safe backend snapshot for the Electron Federation Horizon panel.",
            related_tests=["tests/test_bifrost_cockpit.py"],
            notes="Bifrost consumes this through /bridge/federation-horizon; planning-only, no network protocol, remote execution, or shared state.",
        ),

        FileMapEntry(
            path="docs/prime-orchestration-harness-prototype.md",
            area=FileArea.ARCHITECTURE,
            purpose="Documents the live build queue pattern as the first working prototype of Prime's orchestration harness: slice assignment, lane routing, allowed-file ownership, completion signals, and review coordination.",
            related_tests=[],
            notes="Strategic. Read before designing any orchestration harness slice.",
        ),
        FileMapEntry(
            path="docs/v0-build-readiness-map.md",
            area=FileArea.ARCHITECTURE,
            purpose="V0 gap analysis: names the minimum Meridian capabilities needed before Prime can wake and coordinate work. Honest per-capability assessment of what is missing for the smallest end-to-end Prime-as-coordinator loop.",
            related_tests=[],
            notes="Strategic. Owner: Build 4. Read before planning any V0 milestone or capability integration slice.",
        ),
        FileMapEntry(
            path="docs/v0-v1-progress-tracker.md",
            area=FileArea.ARCHITECTURE,
            purpose="Countable V0/V1 progress view for Prime, Codex, and Scott. Totals-first format: built/in-progress/needs-build counts by gate item. Scope source: v0-build-readiness-map.md gate summary.",
            related_tests=[],
            notes="Update when a gate item status changes. Companion to v0-build-readiness-map.md.",
        ),
        FileMapEntry(
            path="docs/v1-capability-plan.md",
            area=FileArea.ARCHITECTURE,
            purpose="V1 capability plan: defines V1 as the Bifrost cockpit release — Prime's intention, harness liveness, Review Console, Relay session state, Aegis findings, and build progress visible without CLI commands.",
            related_tests=[],
            notes="Owner: Build 4. V1 = cockpit UI live, wired to V0 domain. Read before planning any V1 capability or Bifrost integration.",
        ),
        FileMapEntry(
            path="docs/v2-detailed-build-plan.md",
            area=FileArea.ARCHITECTURE,
            purpose="V2 detailed build plan: phased roadmap for Echo integration, Atlas context retrieval, stronger Prime autonomy, and expanded model harnesses. Refines the v2-horizon-plan with concrete phases and decision gates.",
            related_tests=[],
            notes="Owner: Build 4. Read before planning V2 implementation phases or making architecture decisions about persistence and context.",
        ),
        FileMapEntry(
            path="docs/v2-horizon-plan.md",
            area=FileArea.ARCHITECTURE,
            purpose="V2 horizon plan: persistent memory via Echo, context retrieval via Atlas, stronger Prime autonomy, richer model harnesses. Not active V1 scope — start detailed V2 planning only after V1 cockpit is locked.",
            related_tests=[],
            notes="Horizon only. Do not pull V2 work into V0 or V1 build.",
        ),
        FileMapEntry(
            path="docs/v3-parking-lot.md",
            area=FileArea.ARCHITECTURE,
            purpose="V3 parking lot: horizon ideas for external reach, federation, and deeper distribution. Not active scope — do not pull V3 effort during V0, V1, or V2.",
            related_tests=[],
            notes="Parking lot, not a roadmap. Owner: Build 4. Ideas only until V2 closes.",
        ),
        FileMapEntry(
            path="docs/v3-intake-resolution.md",
            area=FileArea.ARCHITECTURE,
            purpose="V3 intake resolution: deterministic gate that resolves every agentic-ai-framework-checklist [~]/[ ] item into Promote to V3, Move earlier, Park for later, or Reject with a named owner.",
            related_tests=[],
            notes="V3 entry-point. Read before promoting any agentic-ai-framework-checklist item to a V3 spec or runtime build.",
        ),
        FileMapEntry(
            path="docs/v3-goal-runtime-contract.md",
            area=FileArea.ARCHITECTURE,
            purpose="V3 Goal Runtime / Goal Harness contract: bounded backend decision surface for native goal objects, status lifecycle, telemetry, continuation/resume policy, and proof-trail semantics across Prime, Compass, and Echo.",
            related_tests=[],
            notes="V3 first-wave contract. Read before designing any V3 goal runtime, Compass continuation policy, or Echo goal-lineage code.",
        ),
        FileMapEntry(
            path="meridian_core/goal_runtime.py",
            area=FileArea.GOAL_RUNTIME,
            purpose="V3 Goal Runtime / Goal Harness domain slice: closed GoalStatus lifecycle (ACTIVE/BLOCKED/USAGE_LIMITED/COMPLETE) with HarnessWriter-gated single-writer transition matrix, GoalRecord with GoalContinuationPolicy, Beacon-authored GoalTelemetrySnapshot, Echo-authored GoalLineageEntry, Aegis proof_trail_ref and final_proof_ref, and a display-safe to_safe_dict serializer.",
            related_tests=["tests/test_goal_runtime.py"],
            notes="Pure deterministic domain only: no model calls, no network, no persistence, no UI. Ownership: Prime creates and writes ACTIVE -> COMPLETE; Compass writes every transition among ACTIVE/BLOCKED/USAGE_LIMITED and edits continuation_policy; Echo appends lineage; Beacon appends telemetry; Aegis writes proof_trail_ref and never writes status. Implements docs/v3-goal-runtime-contract.md. Field caps and regex-based display-safety rejection enforced at construction.",
        ),
        FileMapEntry(
            path="tests/test_goal_runtime.py",
            area=FileArea.GOAL_RUNTIME,
            purpose="Test suite for meridian_core/goal_runtime.py: closed GoalStatus lifecycle, single-writer transition matrix (Prime creation and ACTIVE -> COMPLETE; Compass for non-terminal transitions; Echo lineage; Beacon telemetry; Aegis proof refs), proof-trail-ref requirements (risk_tier >= 2, dispatched, blocked, usage-limited, or COMPLETE), display-safe to_safe_dict serialization, and field-cap enforcement.",
            related_tests=[],
            notes="Run before changing meridian_core/goal_runtime.py or any Goal Runtime ownership, lifecycle, transition matrix, proof requirement, or display-safety behavior.",
        ),
        FileMapEntry(
            path="docs/backlog-authority-contract.md",
            area=FileArea.BACKLOG,
            purpose="Backlog Authority backend contract for BAK3-BAK11: capture, modify, approve/reject/defer, task-draft conversion, project/initiative links, import candidates, archive, and query/filter field ownership.",
            related_tests=["tests/test_backlog.py"],
            notes="Backend-only contract. Read before adding backlog persistence, UI routes, bridge mutations, Polaris imports, or Prime backlog recommendations.",
        ),
        FileMapEntry(
            path="meridian_core/backlog.py",
            area=FileArea.BACKLOG,
            purpose="Backlog Authority domain slice: typed backlog records, revisions, audit entries, task drafts, import batches, query filters, display-safety validation, and caller-supplied JSON load/save for BAK3-BAK11.",
            related_tests=["tests/test_backlog.py"],
            notes="Pure backend authority only: no UI bridge, no live session dispatch, no model calls, and no writeback to Polaris or external systems.",
        ),
        FileMapEntry(
            path="tests/test_backlog.py",
            area=FileArea.BACKLOG,
            purpose="Test suite for meridian_core/backlog.py: capture/provenance, revision persistence/reload, legal transitions, archive inspectability, Polaris import no-writeback, task-draft projection, query/filter fields, and display-safety rejection.",
            related_tests=[],
            notes="Run before changing meridian_core/backlog.py or Backlog Authority behavior.",
        ),
        FileMapEntry(
            path="docs/voice-io-authority-contract.md",
            area=FileArea.VOICE_IO,
            purpose="Voice I/O Authority backend contract for VOC1/VOC3-VOC10 provider/runtime and command-recognition boundary: fail-closed capability state, transcript metadata, command intent normalization, output job state, VOC10 command-family recognition, and privacy redaction.",
            related_tests=["tests/test_voice_io.py"],
            notes="Backend-only contract. Read before adding voice providers, capture, read-aloud, mute/interrupt, correction, command-intent runtime, or UI/bridge wiring.",
        ),
        FileMapEntry(
            path="meridian_core/voice_io.py",
            area=FileArea.VOICE_IO,
            purpose="Voice I/O Authority domain slice: typed provider capabilities, fail-closed runtime state, transcript draft metadata, command intents, VOC10 deterministic command-family recognition, output jobs, and display-safe serialization.",
            related_tests=["tests/test_voice_io.py"],
            notes="Pure backend authority only: no microphone capture, browser speech APIs, audio playback, provider/network calls, Relay prompt submission, bridge routes, or UI wiring.",
        ),
        FileMapEntry(
            path="tests/test_voice_io.py",
            area=FileArea.VOICE_IO,
            purpose="Test suite for meridian_core/voice_io.py: fail-closed runtime defaults, capability-gated authorization, transcript/output metadata privacy, correction metadata, VOC10 command-family recognition, command confirmation gates, mute/interrupt state, and unsafe text/ref rejection.",
            related_tests=[],
            notes="Run before changing meridian_core/voice_io.py or Voice I/O Authority behavior.",
        ),
        FileMapEntry(
            path="docs/routine-authority-contract.md",
            area=FileArea.ROUTINES,
            purpose="Routine Authority backend contract for ROU2-ROU4 and ROU9: routine definitions, enable/disable state, non-executable run plans, and Prime-owned routine review posture.",
            related_tests=["tests/test_routines.py"],
            notes="Backend-only contract. Read before adding routine scheduler mutation, workflow execution, executable review actions, run history, UI routes, or bridge controls.",
        ),
        FileMapEntry(
            path="meridian_core/routines.py",
            area=FileArea.ROUTINES,
            purpose="Routine Authority domain slice: typed routine triggers, definitions, enable/disable transitions, display-safe non-executable run plans, and Prime routine review decisions.",
            related_tests=["tests/test_routines.py"],
            notes="Pure backend authority only: no scheduler, no workflow execution, no provider calls, no queue mutation, no executable accept/reroute/retry/escalate action, no bridge route, and no UI wiring.",
        ),
        FileMapEntry(
            path="tests/test_routines.py",
            area=FileArea.ROUTINES,
            purpose="Test suite for meridian_core/routines.py: routine creation, enable/disable transitions, disabled-run blocking, enabled-run non-executable planning, Prime review posture, trigger validation, and display-safety rejection.",
            related_tests=[],
            notes="Run before changing meridian_core/routines.py or Routine Authority behavior.",
        ),
        FileMapEntry(
            path="docs/session-archive-authority-contract.md",
            area=FileArea.SESSION_ARCHIVE,
            purpose="Session Archive Authority backend contract for archive catalog records, reload plans, run-again plans, and authorized transcript access handles.",
            related_tests=["tests/test_session_archive.py"],
            notes="Backend-only contract. Read before adding archive storage, reload execution, run-again execution, transcript retrieval, UI routes, or bridge controls.",
        ),
        FileMapEntry(
            path="meridian_core/session_archive.py",
            area=FileArea.SESSION_ARCHIVE,
            purpose="Session Archive Authority domain slice: metadata-only archive records from close/write-through results, catalog entries, non-executable reload/run-again plans, and transcript access handles.",
            related_tests=["tests/test_session_archive.py"],
            notes="Pure backend authority only: no raw transcripts, no UI bridge, no live session restart/replay, no provider calls, and no filesystem persistence.",
        ),
        FileMapEntry(
            path="tests/test_session_archive.py",
            area=FileArea.SESSION_ARCHIVE,
            purpose="Test suite for meridian_core/session_archive.py: archive record ingestion, catalog posture, non-executable reload/run-again plans, transcript handle authorization, and display-safety rejection.",
            related_tests=[],
            notes="Run before changing meridian_core/session_archive.py or Session Archive Authority behavior.",
        ),
        FileMapEntry(
            path="meridian_core/provider_balance.py",
            area=FileArea.PROVIDER_BALANCE,
            purpose="V3 Provider Balance / Usage domain slice: frozen ProviderBalanceSnapshot and ProviderBalanceSummary dataclasses carrying provider health, route kind, quota state, credit status, token-usage counters, estimated-spend labels, cost-pressure state, selected-provider policy state, provider-neutral provider families, and display-safe evidence refs. Exposes build_provider_balance_snapshot, build_provider_balance_summary, unknown_provider_snapshot, and safe_display_label / safe_display_notes / safe_provider_id / safe_evidence_ref helpers; summary mapping shape is structurally compatible with bifrost.cockpit.provider_balance_view_from_summary without importing Bifrost.",
            related_tests=["tests/test_provider_balance.py"],
            notes="Pure deterministic backend domain only: no live provider calls, no credentials, no account probing, no provider SDKs, no network, no UI/Electron behavior, and no Bifrost import. Ownership: Relay Harness (primary) writes route kind / policy state / snapshot composition; Model Harness writes token-usage counters and estimated-spend labels; Bifrost is a read-only consumer of the to_mapping() summary. Unknown balances serialize as unknown / unavailable; cost pressure falls back to UNKNOWN; raw prompt/response text, credentials, filesystem paths, and branch/worktree text are redacted to fixed sentinels before reaching any serialized summary.",
        ),
        FileMapEntry(
            path="tests/test_provider_balance.py",
            area=FileArea.PROVIDER_BALANCE,
            purpose="Test suite for meridian_core/provider_balance.py: frozen-dataclass invariants for ProviderBalanceSnapshot and ProviderBalanceSummary, fail-safe unknown / unavailable defaults, deterministic ordering and selected-provider handling, cost-pressure fallback to UNKNOWN, display-safety redaction of raw prompt/response text, credentials, filesystem paths, and branch/worktree text, evidence-ref normalization and caps, and structural compatibility of the to_mapping() summary shape with the Bifrost cockpit consumer contract.",
            related_tests=[],
            notes="Run before changing meridian_core/provider_balance.py or any Provider Balance / Usage ownership, snapshot/summary shape, display-safety policy, fail-safe defaults, cost-pressure fallback, or selected-provider policy behavior. Bifrost is not imported here; the module is the source of truth for provider-balance policy.",
        ),
        FileMapEntry(
            path="meridian_core/workflow_dispatch.py",
            area=FileArea.WORKFLOW_DISPATCH,
            purpose="Workflow Sub-Agent Harness dispatch domain slice: frozen WorkflowWorkOrder / WorkflowInputRecord / WorkflowInputPacket / WorkflowPromptBudget / WorkflowGateContext / WorkflowHeartbeat / WorkflowResultSummary / WorkflowErrorSummary / WorkflowResteerRequest / WorkflowResteerChanges / WorkflowPromotionDecision dataclasses, closed WorkflowHarness / WorkflowPhase / WorkflowFailureKind enums, pure dispatch_work_order helper that invokes a registered fake/stub handler and converts handler exceptions to a typed WorkflowErrorSummary, tier proof and gate enforcement (tier-3+ requires gate_context; tier-2+ result requires non-empty proof_trail; tier-4 result requires requires_human_gate=True at promote_workflow_result), segment-aware allowed/forbidden path scoping for WorkflowInputPacket inputs, UTC-only ISO-8601 timestamp validation with bounded year range, tri-state resteer overrides via WorkflowResteerChanges, prompt-drag / display-safety guards over free-text fields and handler return payloads, nested workflow depth capped at WORKFLOW_NESTING_CAP, and no heartbeat-history exposure in any Prime-visible return value.",
            related_tests=["tests/test_workflow_dispatch.py"],
            notes="Pure deterministic backend domain only: no live workflow execution, no process/session control, no model calls, no network, no UI/Electron/Bifrost behavior, no Echo/FileMap durable writes, no provider/account calls, no FileMap self-registration inside the workflow module, and no branch/worktree movement. Ownership: Workflow Sub-Agent Harness owns the dispatch domain; Prime coordination issues work orders and consumes WorkflowResultSummary / WorkflowErrorSummary / WorkflowResteerRequest. Aegis, Beacon, Session Lifecycle, Echo, Atlas, Relay, and Bifrost are downstream or adjacent consumers only and are not imported by this slice. Implements docs/workflow-subagent-harness-contract.md, docs/workflow-subagent-usage-checklist.md, and docs/workflows-subagent-harness-architecture.md. Handler returns that expose transcripts, raw logs, raw file/search bodies, free-text plans, heartbeat history, credentials, or filesystem/branch/worktree text become typed dispatch failures rather than successful results.",
        ),
        FileMapEntry(
            path="tests/test_workflow_dispatch.py",
            area=FileArea.WORKFLOW_DISPATCH,
            purpose="161-test proof suite for meridian_core/workflow_dispatch.py: frozen-dataclass invariants and field caps for every Workflow* shape, closed WorkflowHarness / WorkflowPhase / WorkflowFailureKind enums, fake/stub handler dispatch including exception-to-WorkflowErrorSummary conversion and unsafe-return rejection, tier proof and gate enforcement (tier-3+ gate_context requirement and tier-2+ proof_trail requirement at dispatch; tier-4 requires_human_gate enforcement at promote_workflow_result), segment-aware allowed/forbidden path scoping for WorkflowInputPacket inputs, UTC-only ISO-8601 timestamp validation, tri-state WorkflowResteerChanges override semantics, prompt-drag / display-safety guards across free-text fields and handler return payloads, WORKFLOW_NESTING_CAP enforcement, and the no-heartbeat-history exposure rule on Prime-visible return payloads.",
            related_tests=[],
            notes="Run before changing meridian_core/workflow_dispatch.py or any Workflow Sub-Agent Harness dispatch ownership, work-order/input/heartbeat/result/error/resteer/promotion shape, closed enums, tier proof or gate enforcement, segment-aware path scope, UTC timestamp validation, tri-state resteer override, prompt-drag/display-safety policy, nesting cap, or no-heartbeat-history rule. No live workflow execution, process/session control, model calls, network, UI/Electron/Bifrost behavior, Echo/FileMap durable writes, provider/account calls, or FileMap self-registration are exercised here; this slice is the source of truth for workflow dispatch policy.",
        ),
        FileMapEntry(
            path="meridian_core/workflow_atlas.py",
            area=FileArea.WORKFLOW_ATLAS,
            purpose="Atlas Workflow Adapter: pure deterministic adapter that bridges the promoted Atlas retrieval surface (meridian_core/atlas.py) and the promoted Workflow Sub-Agent Harness dispatch contract (meridian_core/workflow_dispatch.py). Builds Atlas WorkflowWorkOrders by encoding an AtlasQuery as bounded WorkflowInputRecord entries on a WorkflowInputPacket (required paths carried under kind='file_path' so allowed_paths/forbidden_paths scope is enforced at construction); decodes typed inputs back into an AtlasQuery on every handler call so the handler never closes over a sidecar query; filters FileMap candidates through the work order's promoted workflow path scope; fails closed on out-of-scope FileMap and DOC result paths; preserves Echo echo:// refs unchanged when an echo_store is injected; preserves the promoted AtlasResult shape verbatim (hits, missing_paths, truncated) and AtlasHit source attribution / ranking order through AtlasOutputRecord and AtlasResultRecord; imports only public workflow_dispatch symbols and exposes ADAPTER_IMPORTS_PRIVATE_DISPATCH_HELPER=False as a self-evident no-private-helper sentinel; and treats an empty AtlasQuery as a successful empty AtlasResult rather than a WorkflowResteerRequest.",
            related_tests=["tests/test_workflow_atlas.py"],
            notes="Pure deterministic backend domain only: no live workflow execution, no process/session control, no model calls, no network, no filesystem writes, no branch/worktree movement, no Echo durable writes, no FileMap durable writes, no UI/Electron/Bifrost behavior, no generated artifacts, no provider/account calls, and no FileMap self-registration inside the adapter. Ownership: Atlas Workflow Adapter / Workflow Sub-Agent Harness owns the adapter slice; Prime coordination issues Atlas work orders and consumes the promoted WorkflowResultSummary / WorkflowErrorSummary; Atlas retrieval provides the promoted query surface used by the handler. Workflow Dispatch private helpers are not imported. Implements docs/atlas-retrieval-contract.md and docs/workflow-subagent-harness-contract.md against the promoted Atlas and Workflow Dispatch slices. Display-safety rejection is end-to-end through dispatch_work_order; unsafe title/reason/excerpt fields and unsafe handler payload content surface as typed INPUT_INVALID failures rather than silently blanked hits.",
        ),
        FileMapEntry(
            path="tests/test_workflow_atlas.py",
            area=FileArea.WORKFLOW_ATLAS,
            purpose="63-test proof suite for meridian_core/workflow_atlas.py: covers Atlas adapter work-order construction (typed input encoding, required-path placement under kind='file_path', additional_inputs guards, AtlasQuery instance validation), Atlas work-order decoding (harness=ATLAS gate, unknown atlas input kind rejection, atlas_include_echo true/false parsing, atlas_limit integer bounds, non-atlas-sourced records ignored gracefully), handler factory dispatch (query_fn callability, ATLAS harness/action/result-shape gates, INPUT_INVALID on decode failure, INTERNAL_ERROR on raised exceptions, INPUT_INVALID on non-AtlasResult returns), required-path scope enforcement, FileMap candidate filtering through promoted workflow path scope, fail-closed behavior on out-of-scope FileMap and DOC result paths, display-safety end-to-end through dispatch_work_order, sidecar-query avoidance (handler reconstructs the query each call), empty-query success returning an empty AtlasResult instead of a WorkflowResteerRequest, Echo echo:// ref preservation when an echo_store is injected, AtlasResult shape preservation (hits, missing_paths, truncated) and AtlasHit source/score preservation through AtlasOutputRecord, the no-private-workflow-dispatch-helper contract via ADAPTER_IMPORTS_PRIVATE_DISPATCH_HELPER, and Review A/B regressions for required-path scope, display safety, sidecar-query avoidance, empty-query success, Echo preservation, and non-required FileMap/DOC path-scope leakage.",
            related_tests=[],
            notes="Run before changing meridian_core/workflow_atlas.py or any Atlas Workflow Adapter ownership, work-order builder, decoder, handler factory, FileMap candidate scoping, fail-closed result-path scoping, display-safety boundary, sidecar-query avoidance, empty-query behavior, Echo echo:// preservation, AtlasResult shape preservation, or no-private-helper contract. No live workflow execution, process/session control, model calls, network, UI/Electron/Bifrost behavior, Echo/FileMap durable writes, provider/account calls, or FileMap self-registration are exercised here; this suite is the source of truth for Atlas Workflow Adapter policy.",
        ),
        FileMapEntry(
            path="docs/filemap-v2-v3-discoverability-audit.md",
            area=FileArea.FILE_MAP,
            purpose="V2/V3 FileMap discoverability audit: identifies architecture and horizon docs Prime must find at wake, plus follow-up FileMap registration gaps.",
            related_tests=[],
            notes="Build 3 audit. Update after new V2/V3 architecture docs land.",
        ),
        FileMapEntry(
            path="docs/prime-orchestration-state-model.md",
            area=FileArea.ARCHITECTURE,
            purpose="Design bridge from the live build queue prototype to Python domain objects for Prime's state model. Names WorkerLane, TaskSlice, and other state objects with defined transitions.",
            related_tests=[],
            notes="Architecture only; no runtime code. Owner: Build 4. Read before implementing Prime orchestration Python domain objects.",
        ),
        FileMapEntry(
            path="docs/prime-restart-resteer-contract.md",
            area=FileArea.ARCHITECTURE,
            purpose="Prime restart/resteer contract: typed detection and recovery contract for stale lanes, wrong queues, shared worktrees, quota blocks, launch failures, proof blocks, and empty queue runway.",
            related_tests=[],
            notes="V2 entry-point. Read before implementing Prime recovery, session lifecycle restart logic, or queue runway automation.",
        ),
        FileMapEntry(
            path="docs/v2-package-api-surface-note.md",
            area=FileArea.ARCHITECTURE,
            purpose="V2 package API surface note: extends the core Meridian package surface for V2 harnesses, Echo integration, and Atlas context retrieval.",
            related_tests=[],
            notes="V2 entry-point. Read before extending the package root exports for V2 features.",
        ),
        FileMapEntry(
            path="docs/v2-progress-tracker.md",
            area=FileArea.ARCHITECTURE,
            purpose="V2 progress tracker: countable progress view for Echo, Atlas, workflow subagent harnesses, and expanded model harnesses. Refines v0-v1-progress-tracker.md for V2 capabilities.",
            related_tests=[],
            notes="Companion to v0-v1-progress-tracker.md. Update when a V2 capability status changes.",
        ),
        FileMapEntry(
            path="docs/v2-backend-completion-audit-20260608.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Backend completion audit for the June 8 V2 restart wave: records tracker counts, reviewed backend closure evidence, contract-baseline disposition, harness matrix dependencies, and UI-owned exclusions.",
            related_tests=["tests/test_filemap.py"],
            notes="Read before declaring backend V2 closed, launching more backend workers, or confusing UI-owned Runtime Logic wiring with backend scope.",
        ),
        FileMapEntry(
            path="docs/prime-autonomy-v2-contract.md",
            area=FileArea.ARCHITECTURE,
            purpose="Prime autonomy V2 contract: defines stronger autonomy boundaries for V2. Establishes coordination rules between Prime, extended harnesses, and worker sessions.",
            related_tests=[],
            notes="V2 entry-point. Read before implementing stronger Prime autonomy or expanding harness delegation.",
        ),
        FileMapEntry(
            path="meridian_core/release_autonomy_snapshot.py",
            area=FileArea.PRIME_AUTONOMY,
            purpose="Display-only Autonomy/Release snapshot for the Electron Release panel: wraps Prime autonomy's DeepSeek validation non-authority export into a safe posture payload for `/bridge/prime-autonomy`.",
            related_tests=["tests/test_bifrost_cockpit.py"],
            notes="No release execution, deployment, credential/account probing, raw prompt/response/evidence bodies, raw worker chat, PIDs, or absolute/local filesystem paths. Bifrost/Electron consumes it as display-only status; it is not a release executor.",
        ),

        # -- Bifrost / session harness ---------------------------------
        FileMapEntry(
            path="docs/bifrost-cockpit-queue-status-brief.md",
            area=FileArea.BIFROST,
            purpose="Design brief for how the Meridian cockpit displays queue-driven worker activity — display, not activation. What Scott sees and how build-lane events surface without flooding the cockpit.",
            related_tests=[],
            notes="Companion to bifrost-session-queue-activation-brief.md. Owner: Build 5. Read before designing cockpit queue-status display.",
        ),
        FileMapEntry(
            path="docs/bifrost-v0-cockpit-layout-brief.md",
            area=FileArea.BIFROST,
            purpose="V0 cockpit layout brief: where each surface lives on screen, what is dominant vs. supportive, and what V0 omits to achieve the Prime-centered command center inversion.",
            related_tests=[],
            notes="Design-only. Owner: Build 5. Companion to bifrost-cockpit-queue-status-brief.md and bifrost-session-queue-activation-brief.md.",
        ),
        FileMapEntry(
            path="docs/bifrost-harness-dashboard-brief.md",
            area=FileArea.BIFROST,
            purpose="Harness dashboard surface brief: what opens when Scott clicks the Harness button — observability of every harness (heartbeat, capabilities, maturity, recent events). Observation-first; no controls in V0.",
            related_tests=[],
            notes="Design-only. Owner: Build 5. Companion to bifrost-v0-cockpit-layout-brief.md.",
        ),
        FileMapEntry(
            path="docs/bifrost-session-queue-activation-brief.md",
            area=FileArea.BIFROST,
            purpose="Session queue activation brief: how the Bifrost harness activates and manages worker sessions from the live build queue. Covers queue polling, lane state tracking, and session lifecycle.",
            related_tests=[],
            notes="Design brief. Owner: Build 5. Companion to bifrost-cockpit-queue-status-brief.md.",
        ),
        FileMapEntry(
            path="docs/session-card-queue-activation-contract.md",
            area=FileArea.BIFROST,
            purpose="Session-card queue activation product contract: Meridian Q-mode behavior, queue routing, heartbeat status, and degraded-state visibility.",
            related_tests=[],
            notes="Read before adding Q controls, polling UI, queue state display, or session-card lifecycle wiring.",
        ),
        FileMapEntry(
            path="docs/bifrost-voice-command-contract.md",
            area=FileArea.BIFROST,
            purpose="Bifrost voice command contract: voice input/output states, typed command intents, harness panel commands, dictation, read-aloud controls, and proof/status commands.",
            related_tests=[],
            notes="UI/product contract only. Read before adding microphone, dictation, spoken Prime output, or voice-command cockpit behavior.",
        ),
        FileMapEntry(
            path="docs/bifrost-balance-payload-surface-contract.md",
            area=FileArea.BIFROST,
            purpose="Bifrost provider balance and prompt payload surface contract: provider health, trust state, prompt-size visibility, Q-mode prompt drag, and DeepSeek route/trust warnings.",
            related_tests=[],
            notes="UI/product contract only. Bifrost displays Relay/Model Harness telemetry but does not choose provider routing.",
        ),
        FileMapEntry(
            path="docs/jarvis-ui-source-assessment.md",
            area=FileArea.BIFROST,
            purpose="Source assessment for JARVIS/HUD UI references that can shape Bifrost's Prime-first command center without importing unsafe or incompatible code.",
            related_tests=[],
            notes="Read before reusing external UI patterns. Source assessment only; not proof of completed runtime UI implementation.",
        ),
        FileMapEntry(
            path="docs/bifrost-v2-cockpit-extensions.md",
            area=FileArea.BIFROST,
            purpose="Bifrost V2 cockpit extension contract: Electron-app HUD direction, central Prime command bay, quiet PRIMED presence core, project rail, harness consoles, and voice-first interaction layer.",
            related_tests=["tests/test_bifrost_cockpit.py"],
            notes="Active V2 UI direction. Bifrost displays state; Prime/Relay/Aegis own decisions and routing.",
        ),
        FileMapEntry(
            path="docs/v1-bifrost-cockpit-implementation-brief.md",
            area=FileArea.BIFROST,
            purpose="V1 Bifrost cockpit implementation brief: what V1 builds, what it omits, and which UI slices land first. Turns V0's domain capabilities into a Prime-centered, browser-rendered cockpit surface.",
            related_tests=[],
            notes="Owner: Build 5. Read before implementing any V1 cockpit UI slice. Source briefs: bifrost-v0-cockpit-layout-brief.md, bifrost-harness-dashboard-brief.md, bifrost-cockpit-queue-status-brief.md.",
        ),
        FileMapEntry(
            path="docs/bifrost-configurable-progress-surface-brief.md",
            area=FileArea.BIFROST,
            purpose="Bifrost configurable progress and proof surface brief: how routine build-lane events, progress updates, and Aegis/Codex proof items are routed to a non-Prime surface, keeping the cockpit uncluttered.",
            related_tests=[],
            notes="Design-only. Owner: Build 5. Read before designing cockpit progress/proof routing.",
        ),
        FileMapEntry(
            path="docs/v1-bifrost-live-data-contract.md",
            area=FileArea.BIFROST,
            purpose="V1 Bifrost live-data integration contract: how CockpitViewModel fields are populated from live Prime, Beacon, and Relay state at runtime. Bridges the static scaffold to real domain data.",
            related_tests=[],
            notes="Owner: Build 4. Read before wiring any live domain data into render_cockpit_html.",
        ),
        FileMapEntry(
            path="docs/v1-bifrost-integration-sequence.md",
            area=FileArea.BIFROST,
            purpose="V1 Bifrost cockpit integration sequence: ordered steps from scaffold to live Prime-driven cockpit — build order, dependency contracts, and gate conditions for each integration slice.",
            related_tests=[],
            notes="Owner: Build 4. Read before planning or executing any V1 Bifrost integration slice.",
        ),
        FileMapEntry(
            path="docs/bifrost-preview-package-api-note.md",
            area=FileArea.BIFROST,
            purpose="Bifrost Electron preview package API policy: establishes that Bifrost exports (preview generation, app-shell helpers) should not automatically become meridian_core root exports due to deployment optionality and infrastructure concerns.",
            related_tests=[],
            notes="Design policy document. Read before adding public exports to bifrost.__init__ or considering root-level re-exports.",
        ),
        FileMapEntry(
            path="docs/v1-bifrost-runtime-acceptance-checklist.md",
            area=FileArea.BIFROST,
            purpose="V1 Bifrost cockpit runtime acceptance checklist: gate document for declaring V1 cockpit ready for session use, organized by harness owner with proof expectations.",
            related_tests=[],
            notes="Owner: Build 4. Build process gate. Read before declaring V1 cockpit runtime complete.",
        ),
        FileMapEntry(
            path="docs/bifrost-right-panel-mode-contract.md",
            area=FileArea.BIFROST,
            purpose="Bifrost right-panel mode contract: defines three UI modes (User Session, Settings, Harness) for the right panel with interaction contracts with Prime, Sessions, and Harness logic.",
            related_tests=[],
            notes="Owner: Build 5. Product/UI contract only; do not implement runtime code here.",
        ),
        FileMapEntry(
            path="meridian_core/cockpit_state.py",
            area=FileArea.BIFROST,
            purpose="Prime cockpit snapshot and event domain types for V1 Bifrost: CockpitStatus, CockpitSnapshot, CockpitEvent, and lane/harness state models. Pure immutable data — no filesystem, CLI, or UI code.",
            related_tests=["tests/test_cockpit_state.py"],
            notes="Owner: Build 1. Read before designing any Prime-state-to-cockpit data flow.",
        ),
        FileMapEntry(
            path="meridian_core/cockpit_provider.py",
            area=FileArea.BIFROST,
            purpose="Pure factory layer for Prime cockpit snapshots: build_snapshot() validates inputs and returns an immutable PrimeCockpitSnapshot with lanes sorted attention-first; demo_snapshot() returns a deterministic sample for Bifrost preview wiring.",
            related_tests=["tests/test_cockpit_provider.py"],
            notes="No filesystem, no live queue reads, no CLI. Owner: Build 1 commit 6c9a397.",
        ),
        FileMapEntry(
            path="bifrost/__init__.py",
            area=FileArea.BIFROST,
            purpose="Bifrost package init: re-exports CockpitViewModel, render_cockpit_html, sample_cockpit_view_model, and related types from bifrost.cockpit.",
            related_tests=["tests/test_bifrost_cockpit.py"],
            notes="Public surface of the Bifrost package. Import from here, not from bifrost.cockpit directly.",
        ),
        FileMapEntry(
            path="bifrost/cockpit.py",
            area=FileArea.BIFROST,
            purpose="Static HTML renderer for the Bifrost cockpit: CockpitViewModel dataclass, render_cockpit_html returning a self-contained HTML document, XSS-safe escaping, and sample_cockpit_view_model for deterministic previews.",
            related_tests=["tests/test_bifrost_cockpit.py"],
            notes="Dependency-free (stdlib only). Owner: Build 5. Read before adding any cockpit rendering, nav, or panel logic.",
        ),
        FileMapEntry(
            path="bifrost/static/cockpit.css",
            area=FileArea.BIFROST,
            purpose="Cockpit CSS: V1 dark-mode palette, layout rules for Prime panel, lane strip, progress surface, and instrument band. Inlined into the HTML output by render_cockpit_html.",
            related_tests=[],
            notes="Loaded at render time via Path(__file__).parent / 'static' / 'cockpit.css'. Edit here to change cockpit visual style.",
        ),
        FileMapEntry(
            path="bifrost/static/media/spark-center-final.png",
            area=FileArea.BIFROST,
            purpose="Bifrost cockpit visual asset for the central Prime/Spark presentation used by the rendered cockpit surface.",
            related_tests=["tests/test_bifrost_cockpit.py"],
            notes="Static media referenced by cockpit rendering/styling. Keep path stable when changing Bifrost visual assets.",
        ),
        FileMapEntry(
            path="bifrost/static/media/spark-hud-reference.jpg",
            area=FileArea.BIFROST,
            purpose="Bifrost cockpit HUD reference visual asset used by the rendered cockpit surface.",
            related_tests=["tests/test_bifrost_cockpit.py"],
            notes="Static media referenced by cockpit rendering/styling. Keep path stable when changing Bifrost visual assets.",
        ),
        FileMapEntry(
            path="tests/test_bifrost_cockpit.py",
            area=FileArea.BIFROST,
            purpose="49-test suite for the V1 Bifrost cockpit scaffold (bifrost/cockpit.py and bifrost/__init__.py). Covers rendering, HTML structure, XSS safety, and sample view model.",
            related_tests=[],
            notes="Build 5 commit d13f1d1.",
        ),
        FileMapEntry(
            path="tests/test_cockpit_state.py",
            area=FileArea.BIFROST,
            purpose="Test suite for meridian_core/cockpit_state.py cockpit snapshot domain types: CockpitStatus, LaneSummary, PrimeCockpitSnapshot, sort_lanes, filter_events.",
            related_tests=[],
            notes="Build 1 commit f56af55.",
        ),
        FileMapEntry(
            path="tests/test_cockpit_provider.py",
            area=FileArea.BIFROST,
            purpose="Test suite for meridian_core/cockpit_provider.py: covers build_snapshot() validation, lane sorting, immutability, and demo_snapshot() determinism.",
            related_tests=[],
            notes="Build 1 commit 6c9a397.",
        ),
        FileMapEntry(
            path="tests/test_restart_resteer.py",
            area=FileArea.BIFROST,
            purpose="Test suite for meridian_core/restart_resteer.py: covers empty queue, shared/main worktree, wrong queue, cadence, quota, proof, launch, and Obsidian divergence recovery decisions.",
            related_tests=[],
            notes="V2 Session Lifecycle / Prime recovery proof coverage.",
        ),

        # -- V1 Electron cockpit app -----------------------------------
        FileMapEntry(
            path="docs/meridian-ui-authority.md",
            area=FileArea.BIFROST,
            purpose="Explicit authority note: the Electron app is the Meridian UI, root index.html is only the renderer source file loaded by that app, and bifrost/preview.html is only generated proof output.",
            related_tests=["tests/test_filemap.py"],
            notes="Read before changing UI launch behavior or interpreting preview artifacts.",
        ),
        FileMapEntry(
            path="index.html",
            area=FileArea.BIFROST,
            purpose="Active renderer source file loaded by the Meridian Electron app: Electron uses it to draw the harness dock, Prime panel, user/session panel, Spark center, right-panel modes, model bridge status, and backend-sourced Prime/Relay/Compass/Vulcan logic surfaces.",
            related_tests=["tests/test_relay_logic_snapshot.py", "tests/test_bifrost_cockpit.py", "tests/test_bifrost_preview.py"],
            notes="Edits to this file are edits to the Electron app's visible UI because Electron currently renders it inside the desktop app. It is part of the app today, not obsolete, detached, historical-only, independent, the launch command, the Meridian UI by itself, or a separate app. Electron loads it via electron/main.js; do not replace the Electron app with bifrost/preview.html for demos/startup.",
        ),
        FileMapEntry(
            path="scripts/meridian-model-bridge.js",
            area=FileArea.BIFROST,
            purpose="Local Node model bridge for the browser cockpit: exposes model message, recent-call, restart, health, and Relay logic snapshot endpoints.",
            related_tests=["tests/test_relay_logic_snapshot.py"],
            notes="Development bridge on 127.0.0.1:8767. Spawns meridian_core.relay_logic_snapshot for /bridge/relay-logic.",
        ),
        FileMapEntry(
            path="package.json",
            area=FileArea.BIFROST,
            purpose="Meridian Electron app package manifest: dependencies, entry point (electron/main.js), scripts, and proof command.",
            related_tests=[],
            notes="npm start opens index.html through Electron. Keep preview generation out of the app startup path.",
        ),
        FileMapEntry(
            path="electron/main.js",
            area=FileArea.BIFROST,
            purpose="Meridian Electron main process: creates the desktop window and loads root index.html as the app renderer with secure defaults.",
            related_tests=["tests/test_bifrost_preview.py"],
            notes="Electron wrapper only. It must not load or regenerate bifrost/preview.html.",
        ),
        FileMapEntry(
            path="bifrost/preview.py",
            area=FileArea.BIFROST,
            purpose="Preview renderer and proof mode for Bifrost cockpit: sample_cockpit_view_model() integration, HTML pre-render validation, and generated backend/view-model preview output.",
            related_tests=["tests/test_bifrost_preview.py"],
            notes="Development proof tool. Safe to edit for generated preview behavior only; not the app UI entrypoint.",
        ),
        FileMapEntry(
            path="bifrost/preview.html",
            area=FileArea.BIFROST,
            purpose="Generated deterministic Bifrost cockpit preview HTML used for backend/view-model rendering proof and review.",
            related_tests=["tests/test_bifrost_preview.py", "tests/test_bifrost_cockpit.py"],
            notes="Generated by bifrost/preview.py; not the Meridian Electron UI and not the app target.",
        ),
        FileMapEntry(
            path="tests/test_bifrost_preview.py",
            area=FileArea.BIFROST,
            purpose="Test suite for bifrost/preview.py and Electron launch wiring: keeps generated preview behavior separate from the Electron app renderer startup path.",
            related_tests=[],
            notes="Preview dev-time tool tests.",
        ),
        FileMapEntry(
            path="docs/prime-queue-reconciliation-requirement.md",
            area=FileArea.ARCHITECTURE,
            purpose="Prime queue reconciliation requirement: defines state-reconciliation guarantees for Prime's live-queue polling, lane state consistency, and task-completion signal safety when Prime coordinates worker sessions.",
            related_tests=[],
            notes="Architecture spec for V1. Required reading before implementing Prime's task-routing loop or queue-state safety gates.",
        ),
        # -- File map itself --------------------------------------------
        FileMapEntry(
            path="meridian_core/filemap.py",
            area=FileArea.FILE_MAP,
            purpose="Domain-level knowledge tracker: FileMapEntry, FileMap, make_default_map().",
            related_tests=["tests/test_filemap.py"],
            notes="Feed to Echo/Atlas for session memory injection.",
        ),
        FileMapEntry(
            path="tests/test_filemap.py",
            area=FileArea.FILE_MAP,
            purpose="Test suite for meridian_core/filemap.py: verifies required FileMap entries, deterministic summaries, area filtering, and injection-summary coverage.",
            related_tests=[],
            notes="Run before changing FileMap entries, required-path coverage, or FileMap summary behavior.",
        ),

        # -- New Relay/UI docs (2026-06-12) --------------------------------
        FileMapEntry(
            path="docs/relay-completeness-audit.md",
            area=FileArea.RELAY_ROUTING,
            purpose="Active design audit: prevent Relay from being under-specified before Auto routing, model dispatch, or harness UI wiring.",
            related_tests=[],
            notes="Use before enabling Auto routing, adding a provider route, wiring Relay UI, or promoting a candidate route to trusted.",
        ),
        FileMapEntry(
            path="docs/relay-heartbeat-model-routing-logic.md",
            area=FileArea.RELAY_ROUTING,
            purpose="First model/vendor routing logic for Meridian: answers what model, vendor/route, risks, and proof gates Relay needs when heartbeat directs Prime to model work.",
            related_tests=[],
            notes="Draft routing logic; not runtime code yet. Provides context for Relay route selection, vendor decisions, and proof requirements.",
        ),
        FileMapEntry(
            path="docs/relay-heartbeat-model-routing-implementation-checklist.md",
            area=FileArea.RELAY_ROUTING,
            purpose="Build-ready Relay heartbeat model-routing implementation checklist: account-first intake, wrong-scope correction, fallback gates, exact model identity, metadata/trust binding, and review proof.",
            related_tests=[],
            notes="Runtime routing is not authorized by the checklist alone. Read before implementing Relay model/vendor/session routing.",
        ),
        FileMapEntry(
            path="docs/relay-aegis-risk-proof-gates.md",
            area=FileArea.AEGIS,
            purpose="Relay-Aegis risk and proof gates contract: defines gates for Aegis to validate Relay routing decisions and enforce safety, proof, and validation requirements.",
            related_tests=[],
            notes="V2 architecture contract. Defines when Aegis must block, waive, or approve a Relay route based on risk tier, vendor validation, proof status, and human gates.",
        ),
        FileMapEntry(
            path="docs/relay-bifrost-proof-payload-contract.md",
            area=FileArea.AEGIS,
            purpose="Relay-Bifrost proof payload contract: defines stable proof payload keys (gate decision, severity, evidence IDs, waiver status, explanation, fallback blockers) that Bifrost surfaces consume to display Aegis gate evidence.",
            related_tests=[],
            notes="V0 contract for FileMap registration. Defines immutable proof payload structure for decision display; read before wiring Aegis proof results into Bifrost UI.",
        ),
        FileMapEntry(
            path="docs/ui-integration-checklist.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Active UI integration gate: checklist for plugging live behavior into Meridian UI. Ensures every visible piece works, shows unavailability, or stays hidden.",
            related_tests=[],
            notes="Owner: Prime/Bifrost coordination. Use when adding or changing UI controls, session behavior, or harness integration.",
        ),

        # -- Missing test suites (backend restart wave audit 2026-06-06) ------
        FileMapEntry(
            path="meridian_core/cognition_policy.py",
            area=FileArea.AEGIS,
            purpose="Proof harness cognition policy: domain objects and evaluators for Aegis proof requirements by action type and risk tier.",
            related_tests=["tests/test_cognition_policy.py"],
            notes="Consumed by Relay and Aegis dispatch gating. Pure domain logic; no model calls.",
        ),
        FileMapEntry(
            path="tests/test_cognition_policy.py",
            area=FileArea.AEGIS,
            purpose="Test suite for meridian_core/cognition_policy.py: covers cognition policy evaluation by risk tier and action type.",
            related_tests=[],
            notes="Run before changing cognition policy evaluation logic or Aegis gating behavior.",
        ),
        FileMapEntry(
            path="meridian_core/lane_state.py",
            area=FileArea.DECISION_LOOP,
            purpose="Lane state tracking for Prime build queues: deterministic lane status, task counts, recent commits, and queue health assessment.",
            related_tests=["tests/test_lane_state.py"],
            notes="Used by Prime to assess queue lane health and dispatch routing.",
        ),
        FileMapEntry(
            path="tests/test_lane_state.py",
            area=FileArea.DECISION_LOOP,
            purpose="Test suite for meridian_core/lane_state.py: covers lane status tracking, task counting, and queue health assessment.",
            related_tests=[],
            notes="Run before changing lane state logic or Prime queue assessment behavior.",
        ),
        FileMapEntry(
            path="meridian_core/tokens.py",
            area=FileArea.PROMPT_PACKET,
            purpose="Conservative, deterministic token count approximation for Relay prompt construction. No vendor tokenizer dependency; replace with tiktoken when provider integration is ready.",
            related_tests=["tests/test_tokens.py"],
            notes="Read before adding token-counting logic to any Relay or Prompt Packet path.",
        ),
        FileMapEntry(
            path="tests/test_tokens.py",
            area=FileArea.PROMPT_PACKET,
            purpose="Test suite for meridian_core/tokens.py: covers conservative token approximation and budget enforcement.",
            related_tests=[],
            notes="Run before changing token-counting logic or prompt budget enforcement.",
        ),
        FileMapEntry(
            path="tests/test_cli.py",
            area=FileArea.DEMO_CLI,
            purpose="Test suite for meridian_core/cli.py: covers demo CLI output and mission load, wake sequence, progress intention, and objectives rendering.",
            related_tests=[],
            notes="Demo surface only. Edit for demo/CLI output format changes.",
        ),
        FileMapEntry(
            path="tests/test_decisions.py",
            area=FileArea.DECISION_LOOP,
            purpose="Test suite for meridian_core/decisions.py: covers deterministic local brain decisions from portfolio and heartbeat state.",
            related_tests=[],
            notes="Run before changing Prime decision logic or heartbeat-to-action routing.",
        ),
        FileMapEntry(
            path="tests/test_injections.py",
            area=FileArea.INJECTIONS,
            purpose="Test suite for meridian_core/injections.py: covers session injection object construction and worker steering directives.",
            related_tests=[],
            notes="Run before changing session injection or worker directive structure.",
        ),
        FileMapEntry(
            path="tests/test_intention.py",
            area=FileArea.COMPASS,
            purpose="Test suite for meridian_core/intention.py: covers stage/objective/risk-tier view construction from portfolio and decision state.",
            related_tests=[],
            notes="Run before changing progress intention or risk tier assessment logic.",
        ),
        FileMapEntry(
            path="tests/test_mission.py",
            area=FileArea.MISSION_BOOT,
            purpose="Test suite for meridian_core/mission.py: covers MISSION.md parsing, Prime directives, and harness boot order.",
            related_tests=[],
            notes="Run before changing MISSION.md parsing, Prime directives, or harness boot order.",
        ),
        FileMapEntry(
            path="tests/test_objectives.py",
            area=FileArea.OBJECTIVES,
            purpose="Test suite for meridian_core/objectives.py: covers mission objectives recall API and Compass-derived objective queries.",
            related_tests=[],
            notes="Run before changing mission objectives API or Compass objective derivation.",
        ),
        FileMapEntry(
            path="tests/test_package_api.py",
            area=FileArea.PACKAGE_API,
            purpose="Test suite for package API exports: verifies meridian_core/__init__.py public surface stability and intentional exports.",
            related_tests=[],
            notes="Run before adding or removing root package exports.",
        ),
        FileMapEntry(
            path="tests/test_planning.py",
            area=FileArea.PLANNING,
            purpose="Test suite for meridian_core/planning.py: covers Council planning harness, objective questions, answers, and recommendations.",
            related_tests=[],
            notes="Run before changing planning harness logic or Council question/answer structure.",
        ),
        FileMapEntry(
            path="tests/test_prompt_budget.py",
            area=FileArea.PROMPT_BUDGET,
            purpose="Test suite for meridian_core/prompt_budget.py: covers deterministic prompt budget by risk tier and prompt budget enforcement.",
            related_tests=[],
            notes="Run before changing prompt budget tiers, limits, or Relay budget gating.",
        ),
        FileMapEntry(
            path="tests/test_prompt_metrics.py",
            area=FileArea.PROMPT_METRICS,
            purpose="Test suite for meridian_core/prompt_metrics.py: covers per-sample and summary metrics for Relay prompt performance.",
            related_tests=[],
            notes="Run before changing prompt metrics collection, status classification, or Relay performance observability.",
        ),
        FileMapEntry(
            path="tests/test_relay_dispatch.py",
            area=FileArea.RELAY_DISPATCH,
            purpose="Test suite for meridian_core/relay_dispatch.py: covers immutable dispatch plan mapping, per-lane model work routing, and payload boundaries.",
            related_tests=[],
            notes="Run before changing dispatch planning logic or payload boundary enforcement.",
        ),
        FileMapEntry(
            path="tests/test_review_console.py",
            area=FileArea.REVIEW_CONSOLE,
            purpose="Test suite for meridian_core/review_console.py: covers review/gating surface, cross-check findings, and proof artifacts.",
            related_tests=[],
            notes="Run before changing review console structure or proof artifact handling.",
        ),
        FileMapEntry(
            path="tests/test_risk.py",
            area=FileArea.RISK_ENGINE,
            purpose="Test suite for meridian_core/risk.py: covers risk assessment, tier requirements, and decision engine foundation.",
            related_tests=[],
            notes="Run before changing risk tiers, tier requirements, or decision logic.",
        ),
        FileMapEntry(
            path="tests/test_wake.py",
            area=FileArea.WAKE_SEQUENCE,
            purpose="Test suite for meridian_core/wake.py: covers wake sequence brief construction and harness heartbeat status reporting.",
            related_tests=[],
            notes="Run before changing wake sequence logic or heartbeat status reporting.",
        ),
        FileMapEntry(
            path="tests/test_council.py",
            area=FileArea.COUNCIL,
            purpose="Test suite for meridian_core/council.py: covers Council cognition roles, deterministic role planning by risk tier, and Chairman recommendations.",
            related_tests=[],
            notes="Run before changing Council role planning or risk tier role mapping.",
        ),
        FileMapEntry(
            path="tests/test_builds.py",
            area=FileArea.BUILD_MATURITY,
            purpose="Test suite for meridian_core/builds.py: covers build number tracking and per-harness maturity registry.",
            related_tests=[],
            notes="Run before changing build number assignment or maturity tracking logic.",
        ),
    ]

    for entry in entries:
        fm.add(entry)

    return fm


