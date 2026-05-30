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
    RELAY_ROUTING    = "Relay routing"
    AEGIS            = "Aegis / Proof harness"
    REVIEW_CONSOLE   = "Review Console"
    BUILD_MATURITY   = "Build/maturity registry"
    FILE_MAP         = "File map / knowledge tracker"
    BUILD_PROCESS    = "Build process"
    PACKAGE_POLICY   = "Package API policy"


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
            path="docs/FileMap.md",
            area=FileArea.FILE_MAP,
            purpose="Human-readable living knowledge tracker for important Meridian files.",
            related_tests=[],
            notes="Obsidian mirror: G:\\My Drive\\Aesop Academy\\Obsidian\\Meridian_Build\\FileMap.md",
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
            path="meridian_core/relay.py",
            area=FileArea.RELAY_ROUTING,
            purpose="Deterministic model/session routing plan from risk tier. Each RelayRoute carries a CouncilPlan via council_plan_for_tier().",
            related_tests=["tests/test_relay.py"],
            notes="No real model calls yet. council_plan field populated for all tiers.",
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

        # -- Build and maturity -----------------------------------------
        FileMapEntry(
            path="meridian_core/builds.py",
            area=FileArea.BUILD_MATURITY,
            purpose="Tracks Meridian build number plus per-harness build number and maturity state.",
            related_tests=["tests/test_builds.py"],
            notes="register() raises on duplicates; use upsert() for intentional replacement.",
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
