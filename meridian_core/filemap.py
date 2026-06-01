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
            notes="Obsidian mirror: G:\\My Drive\\Aesop Academy\\Obsidian\\Meridian_Build\\FileMap.md",
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
            related_tests=[],
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
            path="meridian_core/intention.py",
            area=FileArea.COMPASS,
            purpose="Builds stage/objective/risk-tier view from portfolio and decision state.",
            related_tests=["tests/test_intention.py"],
            notes="Functional seed for Prime's work intention.",
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
            path="meridian_core/relay_executor.py",
            area=FileArea.RELAY_DISPATCH,
            purpose="Relay executor: executes RelayDispatch routing plans and dispatches work to model providers via model_adapter.",
            related_tests=["tests/test_relay_executor.py"],
            notes="V2 Relay runtime execution layer. Consumes RelayRoute decisions and executes dispatch to adapters.",
        ),
        FileMapEntry(
            path="tests/test_relay_executor.py",
            area=FileArea.RELAY_DISPATCH,
            purpose="Test suite for meridian_core/relay_executor.py: coverage for dispatch execution, provider routing, error handling, and state transitions.",
            related_tests=[],
            notes="Run before changing meridian_core/relay_executor.py or Relay execution behavior.",
        ),
        FileMapEntry(
            path="meridian_core/model_adapter.py",
            area=FileArea.MODEL_HARNESS,
            purpose="Provider-neutral Model Adapter contract: payload-only callable boundary, deterministic fake adapter, and env-safe live adapter configuration wrapper.",
            related_tests=["tests/test_model_adapter.py"],
            notes="Public/private provider implementations stay outside Relay core; adapter receives only approved payload text.",
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
            path="docs/model-harness-v2-contract.md",
            area=FileArea.MODEL_HARNESS,
            purpose="Model harness V2 contract: provider capability metadata, prompt-drag telemetry, trust state, route ownership, direct-vs-aggregator evidence, allowed/blocked task types, external-review requirements, and Aegis/Relay policy binding.",
            related_tests=[],
            notes="V2 entry-point. Read before implementing model capability metadata, trust routing, or provider telemetry integration.",
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
            path="meridian_core/prime_autonomy.py",
            area=FileArea.PRIME_AUTONOMY,
            purpose="Prime next-action domain model: immutable PrimeNextAction with action type, confidence, risk tier, source, targets, blockers, human gate, rationale, and evidence refs.",
            related_tests=["tests/test_prime_autonomy.py"],
            notes="V2 Prime Autonomy seed. Human-gated actions are not executable until a later approval model records approval.",
        ),
        FileMapEntry(
            path="tests/test_prime_autonomy.py",
            area=FileArea.PRIME_AUTONOMY,
            purpose="Regression tests for PrimeNextAction, fallback/strict constructors, immutable evidence/blocker sets, confidence/risk mappings, and human-gate executability.",
            related_tests=[],
            notes="Read before changing PrimeNextAction execution semantics or public constructor behavior.",
        ),
        FileMapEntry(
            path="meridian_core/prompt_packet.py",
            area=FileArea.PROMPT_PACKET,
            purpose="Validated, immutable prompt bundle for Relay dispatch. Enforces budget, source compliance, and serialization integrity at construction. Only serialized_prompt is sent to the model.",
            related_tests=["tests/test_prompt_packet.py"],
            notes="PromptPacketValidationError raised on invalid construction. source_lineage stored as immutable MappingProxyType.",
        ),
        FileMapEntry(
            path="meridian_core/aegis.py",
            area=FileArea.AEGIS,
            purpose="Proof harness: AegisEvidence, ProofTrail, and Review Console bridge for cross-check findings.",
            related_tests=["tests/test_aegis.py"],
            notes="Proof-blocking is severity + status aware; ESCALATED is always blocking.",
        ),
        FileMapEntry(
            path="meridian_core/review_console.py",
            area=FileArea.REVIEW_CONSOLE,
            purpose="Promptable review/gating surface for cross-check, proof, artifacts, plans, gates.",
            related_tests=["tests/test_review_console.py"],
            notes="Replaces 'non-orchestrator window' name.",
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
            path="docs/prime-queue-runway-policy.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Prime queue runway policy: defines when Prime is allowed to queue work and when to respect runway constraints. Coordination rules between live build lanes and Prime's task-routing autonomy.",
            related_tests=[],
            notes="Queue governance. Read before implementing Prime's autonomous task queueing or modifying build-lane submission rules.",
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
            path="meridian_core/session_lifecycle.py",
            area=FileArea.BIFROST,
            purpose="Session Lifecycle domain objects: typed enums and frozen dataclasses for session state, command planning, legality checking, and executability gates per V2 contract.",
            related_tests=["tests/test_session_lifecycle.py"],
            notes="Core harness implementation; read the v2-contract and implementation-checklist before modifying.",
        ),
        FileMapEntry(
            path="tests/test_session_lifecycle.py",
            area=FileArea.BIFROST,
            purpose="Test suite for meridian_core/session_lifecycle.py: session state transitions, legality matrix, executability helpers, immutability, and proof progression.",
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
            path="docs/prime-autonomy-v2-contract.md",
            area=FileArea.ARCHITECTURE,
            purpose="Prime autonomy V2 contract: defines stronger autonomy boundaries for V2. Establishes coordination rules between Prime, extended harnesses, and worker sessions.",
            related_tests=[],
            notes="V2 entry-point. Read before implementing stronger Prime autonomy or expanding harness delegation.",
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
            purpose="Bifrost V2 cockpit extension contract: browser-first HUD direction, central Prime command bay, quiet PRIMED presence core, project rail, harness consoles, and voice-first interaction layer.",
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
            path="package.json",
            area=FileArea.BIFROST,
            purpose="V1 Electron cockpit app shell package manifest: dependencies, entry point (electron/main.js), build scripts, and distribution configuration.",
            related_tests=[],
            notes="Electron app root. Do not edit unless updating dependencies or build config.",
        ),
        FileMapEntry(
            path="electron/main.js",
            area=FileArea.BIFROST,
            purpose="V1 Electron main process: window creation, lifecycle management, and IPC bridge between Electron and web renderer for cockpit state sync.",
            related_tests=[],
            notes="Electron main thread. Do not edit unless adding new IPC channels or window lifecycle behavior.",
        ),
        FileMapEntry(
            path="bifrost/preview.py",
            area=FileArea.BIFROST,
            purpose="Preview renderer and demo mode for Bifrost cockpit: sample_cockpit_view_model() integration, HTML pre-render validation, and dev-time cockpit preview without Prime.",
            related_tests=["tests/test_bifrost_preview.py"],
            notes="Development tool. Safe to edit for preview/demo behavior only.",
        ),
        FileMapEntry(
            path="tests/test_bifrost_preview.py",
            area=FileArea.BIFROST,
            purpose="Test suite for bifrost/preview.py: covers preview rendering, sample data generation, and HTML structure validation.",
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
            path="docs/relay-aegis-risk-proof-gates.md",
            area=FileArea.AEGIS,
            purpose="Relay-Aegis risk and proof gates contract: defines gates for Aegis to validate Relay routing decisions and enforce safety, proof, and validation requirements.",
            related_tests=[],
            notes="V2 architecture contract. Defines when Aegis must block, waive, or approve a Relay route based on risk tier, vendor validation, proof status, and human gates.",
        ),
        FileMapEntry(
            path="docs/ui-integration-checklist.md",
            area=FileArea.BUILD_PROCESS,
            purpose="Active UI integration gate: checklist for plugging live behavior into Meridian UI. Ensures every visible piece works, shows unavailability, or stays hidden.",
            related_tests=[],
            notes="Owner: Prime/Bifrost coordination. Use when adding or changing UI controls, session behavior, or harness integration.",
        ),
    ]

    for entry in entries:
        fm.add(entry)

    return fm


