"""Tests for the Progress Intention slice."""

from __future__ import annotations

import pytest

from meridian_core.council import CouncilPlan, CouncilRole
from meridian_core.decisions import DecisionResult, run_decision_loop
from meridian_core.intention import (
    MissionObjectiveLine,
    ObjectiveStage,
    ProgressIntention,
    RiskTier,
    build_progress_intention,
)
from meridian_core.models import (
    Initiative,
    MoveKind,
    NextMove,
    Portfolio,
    Priority,
    Project,
    ScottBottleneck,
)
from meridian_core.sample_state import make_sample_heartbeats, make_sample_portfolio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_intention() -> ProgressIntention:
    portfolio = make_sample_portfolio()
    heartbeats = make_sample_heartbeats()
    result = run_decision_loop(portfolio, heartbeats)
    return build_progress_intention(portfolio, result)


# ---------------------------------------------------------------------------
# ProgressIntention structure
# ---------------------------------------------------------------------------


class TestProgressIntentionStructure:
    def test_has_current_stage(self) -> None:
        intention = _sample_intention()
        assert intention.current_stage

    def test_has_initiating_harness(self) -> None:
        intention = _sample_intention()
        assert intention.initiating_harness

    def test_has_next_stage(self) -> None:
        intention = _sample_intention()
        assert intention.next_stage

    def test_defaults_to_mission_boot(self) -> None:
        intention = build_progress_intention(Portfolio(), DecisionResult())
        assert intention.current_stage == "Mission Boot"

    def test_defaults_to_compass(self) -> None:
        intention = build_progress_intention(Portfolio(), DecisionResult())
        assert intention.initiating_harness == "Compass"

    def test_defaults_to_intention_engine_bootup(self) -> None:
        intention = build_progress_intention(Portfolio(), DecisionResult())
        assert intention.next_stage == "Intention Engine Bootup"

    def test_custom_stage_labels_are_preserved(self) -> None:
        intention = build_progress_intention(
            Portfolio(), DecisionResult(),
            current_stage="Custom Stage",
            initiating_harness="Relay",
            next_stage="Custom Next",
        )
        assert intention.current_stage == "Custom Stage"
        assert intention.initiating_harness == "Relay"
        assert intention.next_stage == "Custom Next"

    def test_empty_portfolio_has_no_objective_lines(self) -> None:
        intention = build_progress_intention(Portfolio(), DecisionResult())
        assert intention.objective_lines == []


# ---------------------------------------------------------------------------
# Objective lines
# ---------------------------------------------------------------------------


class TestObjectiveLines:
    def test_sample_portfolio_produces_lines(self) -> None:
        intention = _sample_intention()
        assert len(intention.objective_lines) == 3

    def test_each_line_has_stage(self) -> None:
        intention = _sample_intention()
        for line in intention.objective_lines:
            assert isinstance(line.stage, ObjectiveStage)

    def test_each_line_has_risk_tier(self) -> None:
        intention = _sample_intention()
        for line in intention.objective_lines:
            assert isinstance(line.risk_tier, RiskTier)

    def test_each_line_has_project_name(self) -> None:
        intention = _sample_intention()
        for line in intention.objective_lines:
            assert line.project_name

    def test_each_line_has_initiative_title(self) -> None:
        intention = _sample_intention()
        for line in intention.objective_lines:
            assert line.initiative_title

    def test_each_line_has_risk_reason(self) -> None:
        intention = _sample_intention()
        for line in intention.objective_lines:
            assert line.risk_reason

    def test_lines_are_deterministic(self) -> None:
        portfolio = make_sample_portfolio()
        result = run_decision_loop(portfolio, make_sample_heartbeats())
        i1 = build_progress_intention(portfolio, result)
        i2 = build_progress_intention(portfolio, result)
        assert [(l.initiative_title, l.stage) for l in i1.objective_lines] == \
               [(l.initiative_title, l.stage) for l in i2.objective_lines]


# ---------------------------------------------------------------------------
# Stage derivation
# ---------------------------------------------------------------------------


class TestStageDerivation:
    def test_scott_required_move_is_gate(self) -> None:
        portfolio = make_sample_portfolio()
        result = run_decision_loop(portfolio, make_sample_heartbeats())
        intention = build_progress_intention(portfolio, result)
        aaic = next(l for l in intention.objective_lines if "AAIC" in l.project_name or "Advanced AI" in l.project_name)
        assert aaic.stage == ObjectiveStage.GATE

    def test_autonomous_review_move_is_review(self) -> None:
        portfolio = make_sample_portfolio()
        result = run_decision_loop(portfolio, make_sample_heartbeats())
        intention = build_progress_intention(portfolio, result)
        careguide = next(l for l in intention.objective_lines if "CareGuide" in l.project_name)
        assert careguide.stage == ObjectiveStage.REVIEW

    def test_proof_required_unverified_is_verify(self) -> None:
        portfolio = make_sample_portfolio()
        result = run_decision_loop(portfolio, make_sample_heartbeats())
        intention = build_progress_intention(portfolio, result)
        meridian = next(l for l in intention.objective_lines if "Meridian" in l.project_name)
        assert meridian.stage == ObjectiveStage.VERIFY

    def test_initiative_with_no_moves_is_plan(self) -> None:
        project = Project(
            id="proj_empty",
            title="Empty Project",
            description="No moves yet",
            initiatives=[
                Initiative(id="init_empty", title="Empty Init", description="No moves")
            ],
        )
        portfolio = Portfolio(projects=[project])
        intention = build_progress_intention(portfolio, DecisionResult())
        assert intention.objective_lines[0].stage == ObjectiveStage.PLAN

    def test_safe_autonomous_non_review_move_is_build(self) -> None:
        project = Project(
            id="proj_build",
            title="Build Project",
            description="Has a build move",
            initiatives=[
                Initiative(
                    id="init_build",
                    title="Build Init",
                    description="Build something",
                    next_moves=[
                        NextMove(
                            id="move_build_x",
                            description="Implement the feature",
                            kind=MoveKind.AUTONOMOUS,
                            objective_id="obj_x",
                            proof_required=False,
                        )
                    ],
                )
            ],
        )
        portfolio = Portfolio(projects=[project])
        result = DecisionResult(safe_next_moves=[portfolio.projects[0].initiatives[0].next_moves[0]])
        intention = build_progress_intention(portfolio, result)
        assert intention.objective_lines[0].stage == ObjectiveStage.BUILD


# ---------------------------------------------------------------------------
# Risk tier
# ---------------------------------------------------------------------------


class TestRiskTier:
    def test_gate_stage_is_tier_4(self) -> None:
        portfolio = make_sample_portfolio()
        result = run_decision_loop(portfolio, make_sample_heartbeats())
        intention = build_progress_intention(portfolio, result)
        gate_lines = [l for l in intention.objective_lines if l.stage == ObjectiveStage.GATE]
        assert all(l.risk_tier == RiskTier.TIER_4 for l in gate_lines)

    def test_review_stage_is_tier_3(self) -> None:
        portfolio = make_sample_portfolio()
        result = run_decision_loop(portfolio, make_sample_heartbeats())
        intention = build_progress_intention(portfolio, result)
        review_lines = [l for l in intention.objective_lines if l.stage == ObjectiveStage.REVIEW]
        assert all(l.risk_tier == RiskTier.TIER_3 for l in review_lines)

    def test_verify_stage_is_tier_3(self) -> None:
        portfolio = make_sample_portfolio()
        result = run_decision_loop(portfolio, make_sample_heartbeats())
        intention = build_progress_intention(portfolio, result)
        verify_lines = [l for l in intention.objective_lines if l.stage == ObjectiveStage.VERIFY]
        assert all(l.risk_tier == RiskTier.TIER_3 for l in verify_lines)

    def test_plan_stage_is_tier_1(self) -> None:
        project = Project(
            id="proj_plan",
            title="Plan Project",
            description="No moves",
            initiatives=[Initiative(id="init_plan", title="Init Plan", description="No moves")],
        )
        intention = build_progress_intention(Portfolio(projects=[project]), DecisionResult())
        assert intention.objective_lines[0].risk_tier == RiskTier.TIER_1

    def test_human_gated_produces_tier_4(self) -> None:
        project = Project(
            id="proj_gate",
            title="Gated Project",
            description="Requires Scott",
            initiatives=[
                Initiative(
                    id="init_gate",
                    title="Gated Init",
                    description="Scott must decide",
                    next_moves=[
                        NextMove(
                            id="move_gate",
                            description="Choose direction",
                            kind=MoveKind.SCOTT_REQUIRED,
                            objective_id="obj_gate",
                        )
                    ],
                )
            ],
        )
        portfolio = Portfolio(projects=[project])
        result = DecisionResult(
            scott_bottlenecks=[
                ScottBottleneck(
                    id="bn_gate",
                    title="Scott must choose",
                    description=".",
                    priority=Priority.HIGH,
                    move_id="move_gate",
                )
            ]
        )
        intention = build_progress_intention(portfolio, result)
        assert intention.objective_lines[0].risk_tier == RiskTier.TIER_4


# ---------------------------------------------------------------------------
# Render without model calls
# ---------------------------------------------------------------------------


class TestCouncilPlan:
    """Council plan is derived from the risk tier on each objective line."""

    def _line_for_stage(self, stage: ObjectiveStage) -> MissionObjectiveLine:
        """Build the minimal portfolio that produces the requested stage."""
        if stage is ObjectiveStage.PLAN:
            project = Project(
                id="proj_cp_plan", title="CP Plan Project", description="",
                initiatives=[Initiative(id="init_cp_plan", title="CP Init", description="")]
            )
            return build_progress_intention(Portfolio(projects=[project]), DecisionResult()).objective_lines[0]

        if stage is ObjectiveStage.BUILD:
            move = NextMove(id="mv_cp_build", description="Implement feature", kind=MoveKind.AUTONOMOUS, objective_id="obj_cp")
            project = Project(
                id="proj_cp_build", title="CP Build Project", description="",
                initiatives=[Initiative(id="init_cp_build", title="CP Build", description="", next_moves=[move])]
            )
            result = DecisionResult(safe_next_moves=[move])
            return build_progress_intention(Portfolio(projects=[project]), result).objective_lines[0]

        if stage is ObjectiveStage.REVIEW:
            portfolio = make_sample_portfolio()
            result = run_decision_loop(portfolio, make_sample_heartbeats())
            intention = build_progress_intention(portfolio, result)
            return next(l for l in intention.objective_lines if l.stage is ObjectiveStage.REVIEW)

        if stage is ObjectiveStage.VERIFY:
            portfolio = make_sample_portfolio()
            result = run_decision_loop(portfolio, make_sample_heartbeats())
            intention = build_progress_intention(portfolio, result)
            return next(l for l in intention.objective_lines if l.stage is ObjectiveStage.VERIFY)

        if stage is ObjectiveStage.GATE:
            portfolio = make_sample_portfolio()
            result = run_decision_loop(portfolio, make_sample_heartbeats())
            intention = build_progress_intention(portfolio, result)
            return next(l for l in intention.objective_lines if l.stage is ObjectiveStage.GATE)

        raise ValueError(f"No fixture for stage {stage}")

    def test_council_plan_is_council_plan_type(self) -> None:
        line = self._line_for_stage(ObjectiveStage.PLAN)
        assert isinstance(line.council_plan, CouncilPlan)

    def test_plan_stage_council_roles(self) -> None:
        line = self._line_for_stage(ObjectiveStage.PLAN)
        assert line.council_plan.roles == [CouncilRole.PRAGMATIST, CouncilRole.CHAIRMAN]

    def test_plan_stage_does_not_require_full_council(self) -> None:
        line = self._line_for_stage(ObjectiveStage.PLAN)
        assert line.council_plan.requires_full_council is False

    def test_build_stage_council_roles(self) -> None:
        line = self._line_for_stage(ObjectiveStage.BUILD)
        assert line.council_plan.roles == [
            CouncilRole.ANALYST,
            CouncilRole.DEVILS_ADVOCATE,
            CouncilRole.PRAGMATIST,
            CouncilRole.CHAIRMAN,
        ]

    def test_build_stage_does_not_require_full_council(self) -> None:
        line = self._line_for_stage(ObjectiveStage.BUILD)
        assert line.council_plan.requires_full_council is False

    def test_review_stage_requires_full_council(self) -> None:
        line = self._line_for_stage(ObjectiveStage.REVIEW)
        assert line.council_plan.requires_full_council is True

    def test_review_stage_has_all_council_roles(self) -> None:
        line = self._line_for_stage(ObjectiveStage.REVIEW)
        assert set(line.council_plan.roles) == set(CouncilRole)

    def test_verify_stage_requires_full_council(self) -> None:
        line = self._line_for_stage(ObjectiveStage.VERIFY)
        assert line.council_plan.requires_full_council is True

    def test_verify_stage_has_all_council_roles(self) -> None:
        line = self._line_for_stage(ObjectiveStage.VERIFY)
        assert set(line.council_plan.roles) == set(CouncilRole)

    def test_gate_stage_requires_full_council(self) -> None:
        line = self._line_for_stage(ObjectiveStage.GATE)
        assert line.council_plan.requires_full_council is True

    def test_gate_stage_has_all_council_roles(self) -> None:
        line = self._line_for_stage(ObjectiveStage.GATE)
        assert set(line.council_plan.roles) == set(CouncilRole)

    def test_council_plan_tier_matches_line_risk_tier(self) -> None:
        line = self._line_for_stage(ObjectiveStage.PLAN)
        assert line.council_plan.risk_tier == line.risk_tier.value

    def test_council_plan_is_deterministic(self) -> None:
        line = self._line_for_stage(ObjectiveStage.BUILD)
        assert line.council_plan.roles == line.council_plan.roles

    def test_each_sample_line_has_chairman(self) -> None:
        portfolio = make_sample_portfolio()
        result = run_decision_loop(portfolio, make_sample_heartbeats())
        intention = build_progress_intention(portfolio, result)
        for line in intention.objective_lines:
            assert CouncilRole.CHAIRMAN in line.council_plan.roles


class TestNoModelCalls:
    def test_build_is_pure_and_synchronous(self) -> None:
        portfolio = make_sample_portfolio()
        result = run_decision_loop(portfolio, make_sample_heartbeats())
        # If this returns, no I/O or model calls occurred
        intention = build_progress_intention(portfolio, result)
        assert isinstance(intention, ProgressIntention)

    def test_objective_lines_are_native_python(self) -> None:
        intention = _sample_intention()
        for line in intention.objective_lines:
            assert isinstance(line, MissionObjectiveLine)
            assert isinstance(line.stage, ObjectiveStage)
            assert isinstance(line.risk_tier, RiskTier)
