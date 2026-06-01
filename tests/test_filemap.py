"""Tests for the File Map Knowledge Tracker (meridian_core/filemap.py)."""

from __future__ import annotations

import pytest

from meridian_core.filemap import FileArea, FileMap, FileMapEntry, make_default_map

# Paths that must be present in the default map
_REQUIRED_PATHS = [
    "MISSION.md",
    "context.md",
    "docs/FileMap.md",
    "docs/agentic-ai-framework-checklist.md",
    "docs/atlas-retrieval-contract.md",
    "meridian_core/atlas.py",
    "tests/test_atlas.py",
    "docs/echo-memory-contract.md",
    "meridian_core/echo.py",
    "tests/test_echo.py",
    "docs/polaris-lessons-for-meridian.md",
    "docs/workflow-subagent-harness-contract.md",
    "docs/workflows-subagent-harness-architecture.md",
    "docs/workflow-subagent-usage-checklist.md",
    "docs/session-lifecycle-v2-contract.md",
    "docs/session-lifecycle-implementation-checklist.md",
    "meridian_core/session_lifecycle.py",
    "tests/test_session_lifecycle.py",
    "docs/federation-harness-horizon.md",
    "docs/session-card-queue-activation-contract.md",
    "docs/bifrost-voice-command-contract.md",
    "docs/bifrost-balance-payload-surface-contract.md",
    "docs/bifrost-v2-cockpit-extensions.md",
    "docs/jarvis-ui-source-assessment.md",
    "docs/deepseek-provider-validation-gate.md",
    "docs/deepseek-validation-benchmark-plan.md",
    "docs/model-harness-v2-contract.md",
    "meridian_core/models.py",
    "meridian_core/mission.py",
    "meridian_core/wake.py",
    "meridian_core/beacon.py",
    "meridian_core/intention.py",
    "meridian_core/objectives.py",
    "meridian_core/risk.py",
    "meridian_core/council.py",
    "meridian_core/planning.py",
    "meridian_core/relay.py",
    "meridian_core/prompt_budget.py",
    "meridian_core/prompt_metrics.py",
    "meridian_core/prompt_payload_meter.py",
    "tests/test_prompt_payload_meter.py",
    "meridian_core/prime_autonomy.py",
    "tests/test_prime_autonomy.py",
    "meridian_core/prompt_packet.py",
    "meridian_core/relay_packet.py",
    "meridian_core/relay_dispatch.py",
    "meridian_core/relay_executor.py",
    "tests/test_relay_executor.py",
    "meridian_core/model_adapter.py",
    "meridian_core/restart_resteer.py",
    "docs/relay-prompt-metrics-integration-brief.md",
    "docs/planning-harness-council-brief.md",
    "docs/prime-planning-harness-answers.md",
    "docs/meridian-capabilities-architecture-map.md",
    "meridian_core/review_console.py",
    "meridian_core/builds.py",
    "meridian_core/filemap.py",
    "docs/v0-build-readiness-map.md",
    "docs/prime-orchestration-state-model.md",
    "docs/prime-restart-resteer-contract.md",
    "docs/bifrost-v0-cockpit-layout-brief.md",
    "docs/bifrost-harness-dashboard-brief.md",
    "docs/live-codex-reviews-2.md",
    "docs/v0-v1-progress-tracker.md",
    "docs/v1-capability-plan.md",
    "docs/v1-bifrost-cockpit-implementation-brief.md",
    "docs/v2-detailed-build-plan.md",
    "docs/v2-horizon-plan.md",
    "docs/v3-parking-lot.md",
    "docs/filemap-v2-v3-discoverability-audit.md",
    "docs/prime-status-console-cli-brief.md",
    "docs/non-orchestrator-surface-naming.md",
    "docs/bifrost-configurable-progress-surface-brief.md",
    "docs/v1-bifrost-live-data-contract.md",
    "docs/v1-bifrost-integration-sequence.md",
    "docs/live-build-queue-hygiene.md",
    "docs/prime-queue-runway-policy.md",
    "docs/v2-package-api-surface-note.md",
    "docs/v2-progress-tracker.md",
    "docs/prime-autonomy-v2-contract.md",
    "docs/bifrost-session-queue-activation-brief.md",
    "meridian_core/cockpit_state.py",
    "meridian_core/cockpit_provider.py",
    "bifrost/__init__.py",
    "bifrost/cockpit.py",
    "bifrost/static/cockpit.css",
    "tests/test_bifrost_cockpit.py",
    "tests/test_cockpit_state.py",
    "package.json",
    "electron/main.js",
    "bifrost/preview.py",
    "tests/test_bifrost_preview.py",
    "docs/prime-queue-reconciliation-requirement.md",
    "docs/relay-completeness-audit.md",
    "docs/relay-heartbeat-model-routing-logic.md",
    "docs/relay-aegis-risk-proof-gates.md",
    "docs/ui-integration-checklist.md",
    "tests/test_cockpit_provider.py",
    "tests/test_restart_resteer.py",
]


# ---------------------------------------------------------------------------
# FileMapEntry
# ---------------------------------------------------------------------------


class TestFileMapEntry:
    def test_has_path(self):
        e = FileMapEntry(path="meridian_core/risk.py", area=FileArea.RISK_ENGINE, purpose="Risk engine")
        assert e.path == "meridian_core/risk.py"

    def test_has_area(self):
        e = FileMapEntry(path="a.py", area=FileArea.DOMAIN_MODEL, purpose="models")
        assert e.area == FileArea.DOMAIN_MODEL

    def test_has_purpose(self):
        e = FileMapEntry(path="a.py", area="X", purpose="does X")
        assert e.purpose == "does X"

    def test_related_tests_defaults_empty(self):
        e = FileMapEntry(path="a.py", area="X", purpose="X")
        assert e.related_tests == []

    def test_notes_defaults_empty(self):
        e = FileMapEntry(path="a.py", area="X", purpose="X")
        assert e.notes == ""

    def test_related_tests_stored(self):
        e = FileMapEntry(path="a.py", area="X", purpose="X", related_tests=["tests/test_a.py"])
        assert "tests/test_a.py" in e.related_tests

    def test_notes_stored(self):
        e = FileMapEntry(path="a.py", area="X", purpose="X", notes="caution")
        assert e.notes == "caution"


# ---------------------------------------------------------------------------
# FileMap — add and lookup
# ---------------------------------------------------------------------------


class TestFileMapAddAndGet:
    def _entry(self, path: str = "a.py", area: str = "Core", purpose: str = "does A") -> FileMapEntry:
        return FileMapEntry(path=path, area=area, purpose=purpose)

    def test_get_registered_path(self):
        fm = FileMap()
        fm.add(self._entry("a.py"))
        assert fm.get("a.py") is not None

    def test_get_unknown_path_returns_none(self):
        fm = FileMap()
        assert fm.get("nonexistent.py") is None

    def test_require_registered_path(self):
        fm = FileMap()
        fm.add(self._entry("b.py"))
        assert fm.require("b.py").path == "b.py"

    def test_require_unknown_path_raises_key_error(self):
        fm = FileMap()
        with pytest.raises(KeyError, match="nonexistent"):
            fm.require("nonexistent.py")

    def test_add_upserts_on_duplicate(self):
        fm = FileMap()
        fm.add(FileMapEntry(path="a.py", area="Old", purpose="old"))
        fm.add(FileMapEntry(path="a.py", area="New", purpose="new"))
        assert fm.require("a.py").area == "New"

    def test_get_returns_correct_entry(self):
        fm = FileMap()
        fm.add(self._entry("c.py", purpose="specific purpose"))
        assert fm.get("c.py").purpose == "specific purpose"


# ---------------------------------------------------------------------------
# FileMap — filtered views
# ---------------------------------------------------------------------------


class TestFileMapFilteredViews:
    def _populated_map(self) -> FileMap:
        fm = FileMap()
        fm.add(FileMapEntry("a.py", area="Core", purpose="A", related_tests=["tests/test_a.py"]))
        fm.add(FileMapEntry("b.py", area="Core", purpose="B", related_tests=[]))
        fm.add(FileMapEntry("c.py", area="Risk", purpose="C", related_tests=["tests/test_c.py"]))
        fm.add(FileMapEntry("d.py", area="Risk", purpose="D", related_tests=[]))
        return fm

    def test_by_area_returns_matching_entries(self):
        fm = self._populated_map()
        core = fm.by_area("Core")
        assert len(core) == 2
        assert all(e.area == "Core" for e in core)

    def test_by_area_returns_empty_for_unknown_area(self):
        fm = self._populated_map()
        assert fm.by_area("Nonexistent") == []

    def test_by_area_order_is_alphabetical_by_path(self):
        fm = self._populated_map()
        paths = [e.path for e in fm.by_area("Core")]
        assert paths == sorted(paths)

    def test_with_tests_returns_only_entries_with_tests(self):
        fm = self._populated_map()
        tested = fm.with_tests()
        assert all(len(e.related_tests) > 0 for e in tested)

    def test_with_tests_count(self):
        fm = self._populated_map()
        assert len(fm.with_tests()) == 2

    def test_with_tests_order_is_alphabetical(self):
        fm = self._populated_map()
        paths = [e.path for e in fm.with_tests()]
        assert paths == sorted(paths)

    def test_all_entries_sorted(self):
        fm = self._populated_map()
        paths = [e.path for e in fm.all_entries()]
        assert paths == sorted(paths)

    def test_all_entries_count(self):
        fm = self._populated_map()
        assert len(fm.all_entries()) == 4


# ---------------------------------------------------------------------------
# Memory injection summary
# ---------------------------------------------------------------------------


class TestInjectionSummary:
    def _simple_map(self) -> FileMap:
        fm = FileMap()
        fm.add(FileMapEntry(
            path="meridian_core/risk.py",
            area=FileArea.RISK_ENGINE,
            purpose="Risk assessment for tiers 0–4.",
            related_tests=["tests/test_risk.py"],
            notes="Decision engine foundation.",
        ))
        fm.add(FileMapEntry(
            path="MISSION.md",
            area=FileArea.MISSION,
            purpose="Prime authority file.",
            related_tests=["tests/test_mission.py"],
        ))
        return fm

    def test_summary_is_non_empty(self):
        fm = self._simple_map()
        assert fm.injection_summary()

    def test_summary_contains_path(self):
        fm = self._simple_map()
        assert "meridian_core/risk.py" in fm.injection_summary()

    def test_summary_contains_purpose(self):
        fm = self._simple_map()
        assert "Risk assessment" in fm.injection_summary()

    def test_summary_contains_related_tests(self):
        fm = self._simple_map()
        assert "tests/test_risk.py" in fm.injection_summary()

    def test_summary_contains_notes(self):
        fm = self._simple_map()
        assert "Decision engine foundation" in fm.injection_summary()

    def test_summary_area_filter(self):
        fm = self._simple_map()
        summary = fm.injection_summary(area=FileArea.RISK_ENGINE)
        assert "meridian_core/risk.py" in summary
        assert "MISSION.md" not in summary

    def test_summary_empty_map(self):
        fm = FileMap()
        assert "no file map entries" in fm.injection_summary()

    def test_summary_has_header(self):
        fm = self._simple_map()
        assert "Meridian File Map" in fm.injection_summary()


# ---------------------------------------------------------------------------
# Default map — required files present
# ---------------------------------------------------------------------------


class TestDefaultMap:
    def test_required_files_present(self):
        fm = make_default_map()
        for path in _REQUIRED_PATHS:
            assert fm.get(path) is not None, f"Missing required path: {path}"

    def test_all_entries_have_non_empty_purpose(self):
        fm = make_default_map()
        for entry in fm.all_entries():
            assert entry.purpose, f"{entry.path} has empty purpose"

    def test_all_entries_have_non_empty_area(self):
        fm = make_default_map()
        for entry in fm.all_entries():
            assert entry.area, f"{entry.path} has empty area"

    def test_entries_with_tests_are_tracked(self):
        fm = make_default_map()
        tested = fm.with_tests()
        tested_paths = {e.path for e in tested}
        for path in ["meridian_core/risk.py", "meridian_core/council.py", "meridian_core/relay.py", "meridian_core/builds.py", "meridian_core/model_adapter.py"]:
            assert path in tested_paths, f"{path} should have related tests"

    def test_mission_md_in_mission_area(self):
        fm = make_default_map()
        entry = fm.require("MISSION.md")
        assert entry.area == FileArea.MISSION

    def test_filemap_itself_is_registered(self):
        fm = make_default_map()
        entry = fm.require("meridian_core/filemap.py")
        assert "filemap" in entry.purpose.lower() or "knowledge" in entry.purpose.lower()

    def test_unknown_path_returns_none(self):
        fm = make_default_map()
        assert fm.get("nonexistent/bogus.py") is None

    def test_unknown_path_require_raises(self):
        fm = make_default_map()
        with pytest.raises(KeyError):
            fm.require("nonexistent/bogus.py")

    def test_output_is_deterministic(self):
        fm1 = make_default_map()
        fm2 = make_default_map()
        paths1 = [e.path for e in fm1.all_entries()]
        paths2 = [e.path for e in fm2.all_entries()]
        assert paths1 == paths2

    def test_by_area_risk_engine(self):
        fm = make_default_map()
        risk_entries = fm.by_area(FileArea.RISK_ENGINE)
        assert any(e.path == "meridian_core/risk.py" for e in risk_entries)

    def test_by_area_council(self):
        fm = make_default_map()
        council_entries = fm.by_area(FileArea.COUNCIL)
        assert any(e.path == "meridian_core/council.py" for e in council_entries)

    def test_multiple_areas_present(self):
        fm = make_default_map()
        areas = {e.area for e in fm.all_entries()}
        assert len(areas) >= 5

    def test_injection_summary_includes_all_paths(self):
        fm = make_default_map()
        summary = fm.injection_summary()
        for path in _REQUIRED_PATHS:
            assert path in summary, f"{path} missing from injection summary"

    def test_council_entry_notes_relay_consumption(self):
        fm = make_default_map()
        entry = fm.require("meridian_core/council.py")
        assert "Relay" in entry.notes or "relay" in entry.notes.lower(), \
            "council.py notes should mention Relay consumption"

    def test_council_entry_notes_compass_consumption(self):
        fm = make_default_map()
        entry = fm.require("meridian_core/council.py")
        assert "Compass" in entry.notes or "Intention" in entry.notes or "compass" in entry.notes.lower(), \
            "council.py notes should mention Compass/Intention consumption"

    def test_relay_entry_purpose_mentions_council_plan(self):
        fm = make_default_map()
        entry = fm.require("meridian_core/relay.py")
        assert "council" in entry.purpose.lower() or "CouncilPlan" in entry.purpose, \
            "relay.py purpose should mention CouncilPlan integration"

    def test_relay_entry_notes_mention_council_plan_field(self):
        fm = make_default_map()
        entry = fm.require("meridian_core/relay.py")
        assert "council_plan" in entry.notes, \
            "relay.py notes should reference the council_plan field"


