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
            path="meridian_core/model_adapter.py",
            area=FileArea.MODEL_HARNESS,
            purpose="Provider-neutral Model Adapter contract: payload-only callable boundary, deterministic fake adapter, and env-safe live adapter configuration wrapper.",
            related_tests=["tests/test_model_adapter.py"],
            notes="Public/private provider implementations stay outside Relay core; adapter receives only approved payload text.",
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
            path="docs/relay-prompt-metrics-integration-brief.md",
            area=FileArea.PROMPT_METRICS,
            purpose="Architectural plan for wiring PromptMetricSample collection into the Relay dispatch path and surfacing status in Compass.",
            related_tests=[],
            notes="Planning only; no runtime changes yet.",
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
            path="docs/prime-orchestration-state-model.md",
            area=FileArea.ARCHITECTURE,
            purpose="Design bridge from the live build queue prototype to Python domain objects for Prime's state model. Names WorkerLane, TaskSlice, and other state objects with defined transitions.",
            related_tests=[],
            notes="Architecture only; no runtime code. Owner: Build 4. Read before implementing Prime orchestration Python domain objects.",
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

        # -- File map itself --------------------------------------------
        FileMapEntry(
            path="meridian_core/filemap.py",
            area=FileArea.FILE_MAP,
            purpose="Domain-level knowledge tracker: FileMapEntry, FileMap, make_default_map().",
            related_tests=["tests/test_filemap.py"],
            notes="Feed to Echo/Atlas for session memory injection.",
        ),
    ]

    for entry in entries:
        fm.add(entry)

    return fm

