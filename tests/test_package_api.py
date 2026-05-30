"""Import smoke tests for Meridian's intentional package-root API."""

from __future__ import annotations

import meridian_core


def test_package_all_is_unique():
    assert len(meridian_core.__all__) == len(set(meridian_core.__all__))


def test_core_decision_api_exports():
    from meridian_core import DecisionResult, Event, EventKind, EventRecorder, make_injection
    from meridian_core import run_decision_loop

    assert DecisionResult
    assert Event
    assert EventKind
    assert EventRecorder
    assert make_injection
    assert run_decision_loop


def test_mission_wake_and_compass_exports():
    from meridian_core import Mission, MissionLoadError, ObjectiveStage, ProgressIntention
    from meridian_core import build_progress_intention, build_wake_brief
    from meridian_core import find_mission_file, format_mission_objectives_text
    from meridian_core import get_mission_objectives, load_mission

    assert Mission
    assert MissionLoadError
    assert ObjectiveStage
    assert ProgressIntention
    assert build_progress_intention
    assert build_wake_brief
    assert find_mission_file
    assert format_mission_objectives_text
    assert get_mission_objectives
    assert load_mission


def test_risk_relay_aegis_review_console_exports():
    from meridian_core import AegisEvidence, EvidenceSeverity, ProofTrail, RelayRoute
    from meridian_core import ReviewConsoleItem, ReviewConsoleQueue, ReviewConsoleResponse
    from meridian_core import RiskTier
    from meridian_core import assess_blocked_action, assess_tier, evidence_from_cross_check
    from meridian_core import make_approval_gate, route_from_tier

    assert AegisEvidence
    assert EvidenceSeverity
    assert ProofTrail
    assert RelayRoute
    assert ReviewConsoleItem
    assert ReviewConsoleQueue
    assert ReviewConsoleResponse
    assert RiskTier
    assert assess_blocked_action
    assert assess_tier
    assert evidence_from_cross_check
    assert make_approval_gate
    assert route_from_tier


def test_build_and_filemap_exports():
    from meridian_core import BuildRegistry, FileArea, FileMap, FileMapEntry
    from meridian_core import HarnessBuild, HarnessMaturity, make_default_map
    from meridian_core import make_initial_registry

    assert BuildRegistry
    assert FileArea
    assert FileMap
    assert FileMapEntry
    assert HarnessBuild
    assert HarnessMaturity
    assert make_default_map
    assert make_initial_registry


def test_council_exports():
    from meridian_core import CouncilPlan, CouncilPosition, CouncilRole
    from meridian_core import council_plan_for_tier, default_council_positions

    assert CouncilPlan
    assert CouncilPosition
    assert CouncilRole
    assert council_plan_for_tier
    assert default_council_positions


def test_internal_helpers_are_not_root_exports():
    assert "_TIER_SEMANTICS" not in meridian_core.__all__
    assert "_ROUTING_TABLE" not in meridian_core.__all__
    assert "_SEVERITY_MAP" not in meridian_core.__all__
