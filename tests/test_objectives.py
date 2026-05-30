"""Tests for Mission Objectives recall layer and BLOCKED stage behaviour."""

from __future__ import annotations

import pytest

from meridian_core.decisions import DecisionResult, run_decision_loop
from meridian_core.intention import (
    MissionObjectiveLine,
    ObjectiveStage,
    ProgressIntention,
    RiskTier,
    build_progress_intention,
)
from meridian_core.models import (
    Heartbeat,
    HeartbeatStatus,
    Initiative,
    MoveKind,
    NextMove,
    Portfolio,
    Project,
)
from meridian_core.objectives import format_mission_objectives_text, get_mission_objectives
from meridian_core.sample_state import make_sample_heartbeats, make_sample_portfolio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _portfolio_with_move(session_id: str | None = None) -> tuple[Portfolio, Initiative]:
    move = NextMove(
        id="move_x",
        description="Deploy the service",
        kind=MoveKind.AUTONOMOUS,
        objective_id="obj_x",
        session_id=session_id,
    )
    initiative = Initiative(
        id="init_x", title="Deploy Init", description="deploy work", next_moves=[move]
    )
    project = Project(id="proj_x", title="Deploy Project", description=".", initiatives=[initiative])
    return Portfolio(projects=[project]), initiative


# ---------------------------------------------------------------------------
# get_mission_objectives — independent of wake
# ---------------------------------------------------------------------------


class TestGetMissionObjectives:
    def test_callable_independently_of_wake(self) -> None:
        portfolio = make_sample_portfolio()
        result = run_decision_loop(portfolio, make_sample_heartbeats())
        view = get_mission_objectives(portfolio, result)
        assert isinstance(view, ProgressIntention)

    def test_returns_progress_intention(self) -> None:
        view = get_mission_objectives(Portfolio(), DecisionResult())
        assert isinstance(view, ProgressIntention)

    def test_includes_current_stage(self) -> None:
        view = get_mission_objectives(Portfolio(), DecisionResult())
        assert view.current_stage == "Mission Boot"

    def test_includes_initiating_harness(self) -> None:
        view = get_mission_objectives(Portfolio(), DecisionResult())
        assert view.initiating_harness == "Compass"

    def test_includes_next_stage(self) -> None:
        view = get_mission_objectives(Portfolio(), DecisionResult())
        assert view.next_stage == "Intention Engine Bootup"

    def test_custom_stage_labels_pass_through(self) -> None:
        view = get_mission_objectives(
            Portfolio(), DecisionResult(),
            current_stage="Custom", initiating_harness="Relay", next_stage="Next Custom"
        )
        assert view.current_stage == "Custom"
        assert view.initiating_harness == "Relay"
        assert view.next_stage == "Next Custom"

    def test_includes_objective_lines(self) -> None:
        portfolio = make_sample_portfolio()
        result = run_decision_loop(portfolio, make_sample_heartbeats())
        view = get_mission_objectives(portfolio, result)
        assert len(view.objective_lines) == 3

    def test_each_line_has_project_and_stage(self) -> None:
        portfolio = make_sample_portfolio()
        result = run_decision_loop(portfolio, make_sample_heartbeats())
        view = get_mission_objectives(portfolio, result)
        for line in view.objective_lines:
            assert line.project_name
            assert isinstance(line.stage, ObjectiveStage)

    def test_each_line_has_risk_tier(self) -> None:
        portfolio = make_sample_portfolio()
        result = run_decision_loop(portfolio, make_sample_heartbeats())
        view = get_mission_objectives(portfolio, result)
        for line in view.objective_lines:
            assert isinstance(line.risk_tier, RiskTier)

    def test_output_is_deterministic(self) -> None:
        portfolio = make_sample_portfolio()
        result = run_decision_loop(portfolio, make_sample_heartbeats())
        v1 = get_mission_objectives(portfolio, result)
        v2 = get_mission_objectives(portfolio, result)
        assert [(l.initiative_title, l.stage, l.risk_tier) for l in v1.objective_lines] == \
               [(l.initiative_title, l.stage, l.risk_tier) for l in v2.objective_lines]

    def test_result_matches_build_progress_intention(self) -> None:
        portfolio = make_sample_portfolio()
        heartbeats = make_sample_heartbeats()
        result = run_decision_loop(portfolio, heartbeats)
        via_objectives = get_mission_objectives(portfolio, result, heartbeats=heartbeats)
        via_builder = build_progress_intention(portfolio, result, heartbeats=heartbeats)
        assert [(l.stage, l.risk_tier) for l in via_objectives.objective_lines] == \
               [(l.stage, l.risk_tier) for l in via_builder.objective_lines]


# ---------------------------------------------------------------------------
# BLOCKED stage — explicit behaviour
# ---------------------------------------------------------------------------


class TestBlockedStage:
    def test_blocked_harness_session_produces_blocked_stage(self) -> None:
        portfolio, _ = _portfolio_with_move(session_id="worker_harness")
        heartbeats = [Heartbeat("worker_harness", HeartbeatStatus.BLOCKED)]
        result = DecisionResult()
        view = get_mission_objectives(portfolio, result, heartbeats=heartbeats)
        assert view.objective_lines[0].stage == ObjectiveStage.BLOCKED

    def test_failed_harness_session_produces_blocked_stage(self) -> None:
        portfolio, _ = _portfolio_with_move(session_id="worker_harness")
        heartbeats = [Heartbeat("worker_harness", HeartbeatStatus.FAILED)]
        result = DecisionResult()
        view = get_mission_objectives(portfolio, result, heartbeats=heartbeats)
        assert view.objective_lines[0].stage == ObjectiveStage.BLOCKED

    def test_blocked_stage_is_tier_4(self) -> None:
        portfolio, _ = _portfolio_with_move(session_id="worker_harness")
        heartbeats = [Heartbeat("worker_harness", HeartbeatStatus.BLOCKED)]
        result = DecisionResult()
        view = get_mission_objectives(portfolio, result, heartbeats=heartbeats)
        assert view.objective_lines[0].risk_tier == RiskTier.TIER_4

    def test_alive_session_does_not_produce_blocked(self) -> None:
        portfolio, _ = _portfolio_with_move(session_id="worker_harness")
        heartbeats = [Heartbeat("worker_harness", HeartbeatStatus.ALIVE)]
        result = DecisionResult(
            safe_next_moves=[portfolio.projects[0].initiatives[0].next_moves[0]]
        )
        view = get_mission_objectives(portfolio, result, heartbeats=heartbeats)
        assert view.objective_lines[0].stage != ObjectiveStage.BLOCKED

    def test_no_heartbeats_does_not_produce_blocked(self) -> None:
        portfolio, _ = _portfolio_with_move(session_id="worker_harness")
        result = DecisionResult(
            safe_next_moves=[portfolio.projects[0].initiatives[0].next_moves[0]]
        )
        view = get_mission_objectives(portfolio, result, heartbeats=None)
        assert view.objective_lines[0].stage != ObjectiveStage.BLOCKED

    def test_move_without_session_id_does_not_produce_blocked(self) -> None:
        portfolio, _ = _portfolio_with_move(session_id=None)
        heartbeats = [Heartbeat("worker_harness", HeartbeatStatus.BLOCKED)]
        result = DecisionResult()
        view = get_mission_objectives(portfolio, result, heartbeats=heartbeats)
        assert view.objective_lines[0].stage != ObjectiveStage.BLOCKED

    def test_blocked_stage_has_risk_reason(self) -> None:
        portfolio, _ = _portfolio_with_move(session_id="worker_harness")
        heartbeats = [Heartbeat("worker_harness", HeartbeatStatus.BLOCKED)]
        result = DecisionResult()
        view = get_mission_objectives(portfolio, result, heartbeats=heartbeats)
        assert view.objective_lines[0].risk_reason

    def test_sample_state_blocked_harness_does_not_affect_unrelated_initiative(self) -> None:
        # git_harness is BLOCKED but no initiative's moves target it
        portfolio = make_sample_portfolio()
        heartbeats = make_sample_heartbeats()
        result = run_decision_loop(portfolio, heartbeats)
        view = get_mission_objectives(portfolio, result, heartbeats=heartbeats)
        blocked_lines = [l for l in view.objective_lines if l.stage == ObjectiveStage.BLOCKED]
        assert len(blocked_lines) == 0


# ---------------------------------------------------------------------------
# format_mission_objectives_text
# ---------------------------------------------------------------------------


class TestFormatMissionObjectivesText:
    def _view(self) -> ProgressIntention:
        portfolio = make_sample_portfolio()
        result = run_decision_loop(portfolio, make_sample_heartbeats())
        return get_mission_objectives(portfolio, result)

    def test_includes_stage_header(self) -> None:
        text = format_mission_objectives_text(self._view())
        assert "Stage: Mission Boot > Compass Initiating" in text

    def test_includes_mission_objectives_label(self) -> None:
        text = format_mission_objectives_text(self._view())
        assert "Mission Objectives:" in text

    def test_includes_next_stage(self) -> None:
        text = format_mission_objectives_text(self._view())
        assert "Next Stage: Intention Engine Bootup" in text

    def test_each_objective_line_appears(self) -> None:
        view = self._view()
        text = format_mission_objectives_text(view)
        for line in view.objective_lines:
            assert line.project_name in text
            assert line.stage.value in text
            assert f"Risk Tier {line.risk_tier.value}" in text

    def test_format_is_deterministic(self) -> None:
        view = self._view()
        assert format_mission_objectives_text(view) == format_mission_objectives_text(view)

    def test_empty_portfolio_renders_cleanly(self) -> None:
        view = get_mission_objectives(Portfolio(), DecisionResult())
        text = format_mission_objectives_text(view)
        assert "Stage:" in text
        assert "Mission Objectives:" in text
        assert "Next Stage:" in text

    def test_each_objective_line_includes_council(self) -> None:
        view = self._view()
        text = format_mission_objectives_text(view)
        assert "Council:" in text

    def test_full_council_tiers_render_as_full_council(self) -> None:
        view = self._view()
        text = format_mission_objectives_text(view)
        # sample portfolio has GATE and VERIFY lines (Tier 3/4) → full council
        assert "full council" in text

    def test_partial_council_tiers_render_role_names(self) -> None:
        project = Project(
            id="proj_fmt_plan", title="Fmt Plan", description="",
            initiatives=[Initiative(id="init_fmt_plan", title="Fmt Init", description="")]
        )
        view = get_mission_objectives(Portfolio(projects=[project]), DecisionResult())
        text = format_mission_objectives_text(view)
        # Plan → Tier 1 → [pragmatist, chairman]
        assert "pragmatist" in text
        assert "chairman" in text

    def test_council_format_is_deterministic(self) -> None:
        view = self._view()
        assert format_mission_objectives_text(view) == format_mission_objectives_text(view)
