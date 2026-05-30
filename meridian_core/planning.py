"""Planning harness domain model for Prime.

The Planning Harness turns an objective into Council-shaped questions,
repo-grounded answers, and a Chairman recommendation. It is inspired by the
grill-with-docs pattern, but Meridian does not stop at questioning: Prime
researches what it can from context, recommends a path, and only escalates
true unknowns to Scott.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .council import CouncilPlan, CouncilRole, council_plan_for_tier


@dataclass(frozen=True)
class PlanningAnswer:
    """An answer Prime can use while shaping a plan."""

    text: str
    source: str = "inference"
    confidence: float = 0.5


@dataclass(frozen=True)
class PlanningQuestion:
    """A Council-owned question with an optional researched/default answer."""

    role: CouncilRole
    question: str
    answer: PlanningAnswer | None = None
    needs_scott: bool = False


@dataclass(frozen=True)
class PlanningRecommendation:
    """The Chairman's recommended next planning action."""

    action: str
    reason: str
    confidence: float
    evidence_needed: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlanningBrief:
    """A complete Council-shaped planning brief for one objective."""

    objective: str
    council_plan: CouncilPlan
    questions: tuple[PlanningQuestion, ...]
    recommendation: PlanningRecommendation
    terms_to_capture: tuple[str, ...] = ()
    adr_candidates: tuple[str, ...] = ()

    def unresolved_questions(self) -> tuple[PlanningQuestion, ...]:
        """Questions that still need Scott or additional research."""
        return tuple(q for q in self.questions if q.answer is None or q.needs_scott)


@dataclass(frozen=True)
class PlanningContext:
    """Repo-grounded planning context supplied by Prime, Echo, Atlas, or FileMap."""

    known_terms: dict[str, str] = field(default_factory=dict)
    research_notes: tuple[PlanningAnswer, ...] = ()
    hard_decisions: tuple[str, ...] = ()


def build_planning_brief(
    objective: str,
    *,
    risk_tier: int = 2,
    context: PlanningContext | None = None,
) -> PlanningBrief:
    """Build a deterministic Council-shaped planning brief."""
    if not objective.strip():
        raise ValueError("objective must not be empty or whitespace-only")

    ctx = context or PlanningContext()
    council_plan = council_plan_for_tier(risk_tier)
    questions = tuple(
        _question_for_role(role, objective.strip(), ctx)
        for role in council_plan.roles
    )
    recommendation = _chairman_recommendation(questions, risk_tier)
    return PlanningBrief(
        objective=objective.strip(),
        council_plan=council_plan,
        questions=questions,
        recommendation=recommendation,
        terms_to_capture=_terms_to_capture(objective, ctx),
        adr_candidates=tuple(ctx.hard_decisions),
    )


def _question_for_role(
    role: CouncilRole,
    objective: str,
    context: PlanningContext,
) -> PlanningQuestion:
    handlers = {
        CouncilRole.ANALYST: _analyst_question,
        CouncilRole.DEVILS_ADVOCATE: _devils_advocate_question,
        CouncilRole.PRAGMATIST: _pragmatist_question,
        CouncilRole.CONTRARIAN: _contrarian_question,
        CouncilRole.EXPANSIONIST: _expansionist_question,
        CouncilRole.CHAIRMAN: _chairman_question,
    }
    return handlers[role](objective, context)


def _analyst_question(objective: str, context: PlanningContext) -> PlanningQuestion:
    answer = _highest_confidence_note(context)
    return PlanningQuestion(
        role=CouncilRole.ANALYST,
        question=f"What evidence or existing docs constrain '{objective}'?",
        answer=answer,
        needs_scott=answer is None,
    )


def _devils_advocate_question(objective: str, context: PlanningContext) -> PlanningQuestion:
    answer = PlanningAnswer(
        text="The main risk is accepting a vague plan before terms and evidence are pinned down.",
        source="planning_harness",
        confidence=0.72,
    )
    if context.hard_decisions:
        answer = PlanningAnswer(
            text=f"Do not violate existing hard decision: {context.hard_decisions[0]}",
            source="adr_candidate",
            confidence=0.84,
        )
    return PlanningQuestion(
        role=CouncilRole.DEVILS_ADVOCATE,
        question="What assumption would make this plan fail?",
        answer=answer,
    )


def _pragmatist_question(objective: str, context: PlanningContext) -> PlanningQuestion:
    answer = PlanningAnswer(
        text="Create the smallest reviewable planning brief before dispatching workers.",
        source="planning_harness",
        confidence=0.8,
    )
    return PlanningQuestion(
        role=CouncilRole.PRAGMATIST,
        question="What is the next useful planning action?",
        answer=answer,
    )


def _contrarian_question(objective: str, context: PlanningContext) -> PlanningQuestion:
    return PlanningQuestion(
        role=CouncilRole.CONTRARIAN,
        question="What if the obvious implementation path is too rigid?",
        answer=PlanningAnswer(
            text="Prefer a recommendation engine that can choose research, questions, or action by risk tier.",
            source="planning_harness",
            confidence=0.76,
        ),
    )


def _expansionist_question(objective: str, context: PlanningContext) -> PlanningQuestion:
    return PlanningQuestion(
        role=CouncilRole.EXPANSIONIST,
        question="What upside is missing from the current framing?",
        answer=PlanningAnswer(
            text="Resolved terms and decisions can become durable memory, not just one-session planning.",
            source="planning_harness",
            confidence=0.78,
        ),
    )


def _chairman_question(objective: str, context: PlanningContext) -> PlanningQuestion:
    return PlanningQuestion(
        role=CouncilRole.CHAIRMAN,
        question="Which Council voice should decide what Prime presents next?",
        answer=PlanningAnswer(
            text="Use researched answers first, recommendations second, and Scott questions only for unresolved judgment.",
            source="planning_harness",
            confidence=0.86,
        ),
    )


def _highest_confidence_note(context: PlanningContext) -> PlanningAnswer | None:
    if not context.research_notes:
        return None
    return max(context.research_notes, key=lambda note: note.confidence)


def _terms_to_capture(objective: str, context: PlanningContext) -> tuple[str, ...]:
    objective_lower = objective.lower()
    return tuple(
        term
        for term in sorted(context.known_terms)
        if term.lower() in objective_lower
    )


def _chairman_recommendation(
    questions: tuple[PlanningQuestion, ...],
    risk_tier: int,
) -> PlanningRecommendation:
    unresolved = [q for q in questions if q.answer is None or q.needs_scott]
    if unresolved and risk_tier >= 3:
        return PlanningRecommendation(
            action="ask_scott_for_judgment",
            reason="High-risk planning still has unresolved Council questions.",
            confidence=0.82,
            evidence_needed=("Answered Council questions", "Updated context or ADR if terms changed"),
        )
    if unresolved:
        return PlanningRecommendation(
            action="research_then_recommend",
            reason="Some questions are unresolved, but risk tier allows Prime to research before escalating.",
            confidence=0.74,
            evidence_needed=("Research note", "Chairman recommendation"),
        )
    return PlanningRecommendation(
        action="draft_plan_from_council_brief",
        reason="Council questions have researched/default answers sufficient for a first plan.",
        confidence=0.88,
        evidence_needed=("Planning brief", "Acceptance criteria"),
    )
