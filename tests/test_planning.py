"""Tests for the Prime Planning Harness."""

from __future__ import annotations

import pytest

from meridian_core.council import CouncilRole
from meridian_core.planning import (
    PlanningAnswer,
    PlanningBrief,
    PlanningContext,
    PlanningQuestion,
    PlanningRecommendation,
    build_planning_brief,
)


class TestPlanningBriefShape:
    def test_builds_planning_brief(self) -> None:
        brief = build_planning_brief("Build the cockpit UI")
        assert isinstance(brief, PlanningBrief)

    def test_empty_objective_raises(self) -> None:
        with pytest.raises(ValueError):
            build_planning_brief("   ")

    def test_objective_is_stripped(self) -> None:
        brief = build_planning_brief("  Build Prime planning  ")
        assert brief.objective == "Build Prime planning"

    def test_default_tier_uses_tier_2_council(self) -> None:
        brief = build_planning_brief("Build Prime planning")
        assert brief.council_plan.risk_tier == 2
        assert brief.council_plan.roles == [
            CouncilRole.ANALYST,
            CouncilRole.DEVILS_ADVOCATE,
            CouncilRole.PRAGMATIST,
            CouncilRole.CHAIRMAN,
        ]

    def test_full_council_used_for_tier_3(self) -> None:
        brief = build_planning_brief("Plan public release", risk_tier=3)
        assert set(q.role for q in brief.questions) == set(CouncilRole)


class TestPlanningQuestions:
    def test_questions_are_council_owned(self) -> None:
        brief = build_planning_brief("Build the cockpit UI")
        assert all(isinstance(q, PlanningQuestion) for q in brief.questions)
        assert all(q.role in brief.council_plan.roles for q in brief.questions)

    def test_research_note_answers_analyst_question(self) -> None:
        context = PlanningContext(
            research_notes=(
                PlanningAnswer("Polaris prompt engine should be reused.", "Polaris", 0.91),
            )
        )
        brief = build_planning_brief("Plan Bifrost prompt engine", context=context)
        analyst = next(q for q in brief.questions if q.role is CouncilRole.ANALYST)
        assert analyst.answer is not None
        assert "Polaris prompt engine" in analyst.answer.text

    def test_highest_confidence_research_note_wins(self) -> None:
        context = PlanningContext(
            research_notes=(
                PlanningAnswer("low confidence", "memory", 0.2),
                PlanningAnswer("high confidence", "docs", 0.9),
            )
        )
        brief = build_planning_brief("Plan with evidence", context=context)
        analyst = next(q for q in brief.questions if q.role is CouncilRole.ANALYST)
        assert analyst.answer is not None
        assert analyst.answer.text == "high confidence"

    def test_unanswered_analyst_question_is_unresolved(self) -> None:
        brief = build_planning_brief("Plan a vague feature")
        unresolved = brief.unresolved_questions()
        assert any(q.role is CouncilRole.ANALYST for q in unresolved)

    def test_default_council_answers_are_not_unresolved(self) -> None:
        context = PlanningContext(
            research_notes=(PlanningAnswer("Known evidence", "docs", 0.8),)
        )
        brief = build_planning_brief("Plan known feature", context=context)
        assert brief.unresolved_questions() == ()


class TestPlanningRecommendation:
    def test_unresolved_low_tier_recommends_research_then_recommend(self) -> None:
        brief = build_planning_brief("Plan a vague feature", risk_tier=2)
        assert brief.recommendation.action == "research_then_recommend"

    def test_unresolved_high_tier_recommends_scott_judgment(self) -> None:
        brief = build_planning_brief("Plan public release", risk_tier=3)
        assert brief.recommendation.action == "ask_scott_for_judgment"

    def test_resolved_questions_recommend_drafting_plan(self) -> None:
        context = PlanningContext(
            research_notes=(PlanningAnswer("Known evidence", "docs", 0.8),)
        )
        brief = build_planning_brief("Plan known feature", risk_tier=2, context=context)
        assert brief.recommendation.action == "draft_plan_from_council_brief"

    def test_recommendation_has_evidence_needed(self) -> None:
        brief = build_planning_brief("Plan known feature")
        assert isinstance(brief.recommendation, PlanningRecommendation)
        assert brief.recommendation.evidence_needed


class TestPlanningMemoryOutputs:
    def test_terms_to_capture_are_matched_from_known_terms(self) -> None:
        context = PlanningContext(
            known_terms={
                "Prime": "Meridian orchestrator",
                "Beacon": "liveness harness",
                "Unused": "not present",
            }
        )
        brief = build_planning_brief("Plan Prime and Beacon behavior", context=context)
        assert brief.terms_to_capture == ("Beacon", "Prime")

    def test_hard_decisions_become_adr_candidates(self) -> None:
        context = PlanningContext(
            hard_decisions=("Use Polaris prompt engine rather than reinventing it.",)
        )
        brief = build_planning_brief("Plan Bifrost prompt support", context=context)
        assert brief.adr_candidates == ("Use Polaris prompt engine rather than reinventing it.",)

    def test_devils_advocate_uses_hard_decision_when_present(self) -> None:
        context = PlanningContext(
            hard_decisions=("Every session must use a unique worktree.",)
        )
        brief = build_planning_brief("Plan build queues", context=context)
        question = next(q for q in brief.questions if q.role is CouncilRole.DEVILS_ADVOCATE)
        assert question.answer is not None
        assert "unique worktree" in question.answer.text
