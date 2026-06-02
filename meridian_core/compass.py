"""Compass project definition, bounds, difference, and handoff runtime.

Pure backend domain objects for defining a Meridian project as a bounded body
of work and evaluating whether summarized context belongs inside the project
boundary, describes a distinct project, or is safe to present for cross-project
handoff review. This module does not query repos, mutate sessions, or call
models/providers.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping


_PROJECT_DEFINITION_DICT_KEYS = (
    "project_id",
    "title",
    "outcome",
    "context",
    "artifacts",
    "objectives",
    "tasks",
    "proof_trail",
    "relationship_refs",
)
_PROJECT_SCOPE_RESULT_DICT_KEYS = (
    "decision",
    "project_id",
    "subject_kind",
    "subject_ref",
    "evidence_refs",
    "matched_refs",
    "blockers",
    "compass_question",
    "execution_authorized",
)
_PROJECT_DIFFERENCE_RESULT_DICT_KEYS = (
    "decision",
    "left_project_id",
    "right_project_id",
    "evidence_refs",
    "difference_evidence",
    "shared_relationship_refs",
    "blockers",
    "compass_question",
    "merge_authorized",
)
_PROJECT_DIFFERENCE_PROFILE_KEYS = (
    "project_id",
    "mission_bearing",
    "objectives",
    "artifacts",
    "memory_pins",
    "blockers",
    "proof_expectations",
    "repo_refs",
    "venture_refs",
)
_PROJECT_DIFFERENCE_EVIDENCE_KEYS = (
    "field",
    "left",
    "right",
)
_PROJECT_DIFFERENCE_REQUIRED_FIELDS = (
    "mission_bearing",
    "objectives",
    "artifacts",
    "memory_pins",
    "blockers",
    "proof_expectations",
)
_PROJECT_HANDOFF_REQUEST_KEYS = (
    "source_project_id",
    "target_project_id",
    "reason_category",
    "payload_type",
    "payload_summary_refs",
    "evidence_refs",
    "approval_required",
    "approval_refs",
    "raw_context_blocked",
)
_PROJECT_HANDOFF_RESULT_DICT_KEYS = (
    "decision",
    "source_project_id",
    "target_project_id",
    "reason_category",
    "payload_type",
    "payload_summary_refs",
    "evidence_refs",
    "approval_required",
    "approval_refs",
    "project_difference_decision",
    "shared_relationship_refs",
    "blockers",
    "compass_question",
    "review_ready",
    "execution_authorized",
)
_SCOPE_SUBJECT_KINDS = {
    "context",
    "artifact",
    "objective",
    "task",
    "proof",
    "repo",
    "venture",
    "session",
    "ambiguous",
}
_HANDOFF_REASON_CATEGORIES = {
    "status_summary",
    "proof_packet",
    "review_result",
    "blocker_notice",
    "task_request",
}
_HANDOFF_PAYLOAD_TYPES = {
    "summary_refs",
    "artifact_refs",
    "proof_refs",
    "blocker_refs",
    "review_refs",
}
_RAW_CONTEXT_PAYLOAD_TYPES = {
    "raw_prompt",
    "raw_transcript",
    "free_form_context",
    "raw_provider_response",
}
_RAW_CONTEXT_REF_PREFIXES = (
    "raw_prompt:",
    "raw_transcript:",
    "free_form_context:",
    "prompt:",
    "transcript:",
    "conversation:",
    "provider_response:",
    "raw_context:",
)


class ProjectScopeDecision(Enum):
    """Deterministic Compass boundary decision for a proposed project subject."""

    IN_SCOPE = "in_scope"
    OUT_OF_SCOPE = "out_of_scope"
    AMBIGUOUS = "ambiguous"
    BLOCKED = "blocked"


class ProjectDifferenceDecision(Enum):
    """Deterministic Compass decision for comparing two project bearings."""

    SAME_PROJECT = "same_project"
    DISTINCT = "distinct"
    AMBIGUOUS = "ambiguous"
    BLOCKED = "blocked"


class ProjectHandoffDecision(Enum):
    """Deterministic Compass decision for cross-project handoff review."""

    REVIEW_READY = "review_ready"
    AMBIGUOUS = "ambiguous"
    BLOCKED = "blocked"


def _normalize_required_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must not be blank")
    return value.strip()


def _normalize_required_tuple(name: str, values: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(_normalize_required_text(name, value) for value in values)
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    return normalized


def _normalize_optional_tuple(name: str, values: Iterable[str] = ()) -> tuple[str, ...]:
    return tuple(_normalize_required_text(name, value) for value in values)


@dataclass(frozen=True)
class ProjectRelationshipRefs:
    """Stable relationship refs tying a project to repo, venture, and sessions."""

    repo_refs: tuple[str, ...]
    venture_refs: tuple[str, ...]
    session_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "repo_refs",
            _normalize_required_tuple("repo_refs", self.repo_refs),
        )
        object.__setattr__(
            self,
            "venture_refs",
            _normalize_required_tuple("venture_refs", self.venture_refs),
        )
        object.__setattr__(
            self,
            "session_refs",
            _normalize_optional_tuple("session_refs", self.session_refs),
        )

    def to_dict(self) -> dict[str, tuple[str, ...]]:
        return {
            "repo_refs": self.repo_refs,
            "venture_refs": self.venture_refs,
            "session_refs": self.session_refs,
        }


@dataclass(frozen=True)
class ProjectDefinition:
    """Serializable Compass definition for one bounded project."""

    project_id: str
    title: str
    outcome: str
    context: tuple[str, ...]
    artifacts: tuple[str, ...]
    objectives: tuple[str, ...]
    tasks: tuple[str, ...]
    proof_trail: tuple[str, ...]
    relationship_refs: ProjectRelationshipRefs

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "project_id",
            _normalize_required_text("project_id", self.project_id),
        )
        object.__setattr__(self, "title", _normalize_required_text("title", self.title))
        object.__setattr__(
            self,
            "outcome",
            _normalize_required_text("outcome", self.outcome),
        )
        object.__setattr__(
            self,
            "context",
            _normalize_required_tuple("context", self.context),
        )
        object.__setattr__(
            self,
            "artifacts",
            _normalize_required_tuple("artifacts", self.artifacts),
        )
        object.__setattr__(
            self,
            "objectives",
            _normalize_required_tuple("objectives", self.objectives),
        )
        object.__setattr__(
            self,
            "tasks",
            _normalize_required_tuple("tasks", self.tasks),
        )
        object.__setattr__(
            self,
            "proof_trail",
            _normalize_required_tuple("proof_trail", self.proof_trail),
        )
        if not isinstance(self.relationship_refs, ProjectRelationshipRefs):
            raise ValueError("relationship_refs must be ProjectRelationshipRefs")

    def to_dict(self) -> dict[str, object]:
        """Return a stable, JSON-serializable dictionary."""
        return {
            "project_id": self.project_id,
            "title": self.title,
            "outcome": self.outcome,
            "context": self.context,
            "artifacts": self.artifacts,
            "objectives": self.objectives,
            "tasks": self.tasks,
            "proof_trail": self.proof_trail,
            "relationship_refs": self.relationship_refs.to_dict(),
        }

    def fingerprint(self) -> str:
        """Return a deterministic content fingerprint for proof references."""
        return project_definition_fingerprint(self)


@dataclass(frozen=True)
class ProjectScopeCandidate:
    """Summarized subject proposed for one project's context boundary."""

    project_id: str | None
    subject_kind: str
    subject_ref: str
    evidence_refs: tuple[str, ...]
    ambiguity_reason: str | None = None

    def __post_init__(self) -> None:
        if self.project_id is not None:
            object.__setattr__(
                self,
                "project_id",
                _normalize_required_text("project_id", self.project_id),
            )
        object.__setattr__(
            self,
            "subject_kind",
            _normalize_required_text("subject_kind", self.subject_kind),
        )
        object.__setattr__(
            self,
            "subject_ref",
            _normalize_required_text("subject_ref", self.subject_ref),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _normalize_optional_tuple("evidence_refs", self.evidence_refs),
        )
        if self.ambiguity_reason is not None:
            object.__setattr__(
                self,
                "ambiguity_reason",
                _normalize_required_text("ambiguity_reason", self.ambiguity_reason),
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "subject_kind": self.subject_kind,
            "subject_ref": self.subject_ref,
            "evidence_refs": self.evidence_refs,
            "ambiguity_reason": self.ambiguity_reason,
        }


@dataclass(frozen=True)
class ProjectScopeEvaluation:
    """Serializable Compass result for one project boundary check."""

    decision: ProjectScopeDecision
    project_id: str | None
    subject_kind: str
    subject_ref: str
    evidence_refs: tuple[str, ...]
    matched_refs: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    compass_question: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.decision, ProjectScopeDecision):
            raise ValueError("decision must be ProjectScopeDecision")
        if self.project_id is not None:
            object.__setattr__(
                self,
                "project_id",
                _normalize_required_text("project_id", self.project_id),
            )
        object.__setattr__(
            self,
            "subject_kind",
            _normalize_required_text("subject_kind", self.subject_kind),
        )
        object.__setattr__(
            self,
            "subject_ref",
            _normalize_required_text("subject_ref", self.subject_ref),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _normalize_optional_tuple("evidence_refs", self.evidence_refs),
        )
        object.__setattr__(
            self,
            "matched_refs",
            _normalize_optional_tuple("matched_refs", self.matched_refs),
        )
        object.__setattr__(
            self,
            "blockers",
            _normalize_optional_tuple("blockers", self.blockers),
        )
        if self.compass_question is not None:
            object.__setattr__(
                self,
                "compass_question",
                _normalize_required_text("compass_question", self.compass_question),
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision.value,
            "project_id": self.project_id,
            "subject_kind": self.subject_kind,
            "subject_ref": self.subject_ref,
            "evidence_refs": self.evidence_refs,
            "matched_refs": self.matched_refs,
            "blockers": self.blockers,
            "compass_question": self.compass_question,
            "execution_authorized": False,
        }


@dataclass(frozen=True)
class ProjectDifferenceProfile:
    """Primitive project-bearing summary used to compare project identity."""

    project_id: str | None
    mission_bearing: str | None
    objectives: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    memory_pins: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    proof_expectations: tuple[str, ...] = ()
    repo_refs: tuple[str, ...] = ()
    venture_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.project_id is not None:
            object.__setattr__(
                self,
                "project_id",
                _normalize_required_text("project_id", self.project_id),
            )
        if self.mission_bearing is not None:
            object.__setattr__(
                self,
                "mission_bearing",
                _normalize_required_text("mission_bearing", self.mission_bearing),
            )
        object.__setattr__(
            self,
            "objectives",
            _normalize_optional_tuple("objectives", self.objectives),
        )
        object.__setattr__(
            self,
            "artifacts",
            _normalize_optional_tuple("artifacts", self.artifacts),
        )
        object.__setattr__(
            self,
            "memory_pins",
            _normalize_optional_tuple("memory_pins", self.memory_pins),
        )
        object.__setattr__(
            self,
            "blockers",
            _normalize_optional_tuple("blockers", self.blockers),
        )
        object.__setattr__(
            self,
            "proof_expectations",
            _normalize_optional_tuple(
                "proof_expectations",
                self.proof_expectations,
            ),
        )
        object.__setattr__(
            self,
            "repo_refs",
            _normalize_optional_tuple("repo_refs", self.repo_refs),
        )
        object.__setattr__(
            self,
            "venture_refs",
            _normalize_optional_tuple("venture_refs", self.venture_refs),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "mission_bearing": self.mission_bearing,
            "objectives": self.objectives,
            "artifacts": self.artifacts,
            "memory_pins": self.memory_pins,
            "blockers": self.blockers,
            "proof_expectations": self.proof_expectations,
            "repo_refs": self.repo_refs,
            "venture_refs": self.venture_refs,
        }


@dataclass(frozen=True)
class ProjectDifferenceEvidence:
    """Visible evidence for one project-bearing difference field."""

    field: str
    left: tuple[str, ...]
    right: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "field", _normalize_required_text("field", self.field))
        object.__setattr__(
            self,
            "left",
            _normalize_optional_tuple("left", self.left),
        )
        object.__setattr__(
            self,
            "right",
            _normalize_optional_tuple("right", self.right),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "field": self.field,
            "left": self.left,
            "right": self.right,
        }


@dataclass(frozen=True)
class ProjectDifferenceEvaluation:
    """Serializable Compass result for a project-difference check."""

    decision: ProjectDifferenceDecision
    left_project_id: str | None
    right_project_id: str | None
    evidence_refs: tuple[str, ...]
    difference_evidence: tuple[ProjectDifferenceEvidence, ...] = ()
    shared_relationship_refs: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    compass_question: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.decision, ProjectDifferenceDecision):
            raise ValueError("decision must be ProjectDifferenceDecision")
        if self.left_project_id is not None:
            object.__setattr__(
                self,
                "left_project_id",
                _normalize_required_text("left_project_id", self.left_project_id),
            )
        if self.right_project_id is not None:
            object.__setattr__(
                self,
                "right_project_id",
                _normalize_required_text("right_project_id", self.right_project_id),
            )
        object.__setattr__(
            self,
            "evidence_refs",
            _normalize_optional_tuple("evidence_refs", self.evidence_refs),
        )
        if any(
            not isinstance(evidence, ProjectDifferenceEvidence)
            for evidence in self.difference_evidence
        ):
            raise ValueError("difference_evidence must be ProjectDifferenceEvidence")
        object.__setattr__(
            self,
            "shared_relationship_refs",
            _normalize_optional_tuple(
                "shared_relationship_refs",
                self.shared_relationship_refs,
            ),
        )
        object.__setattr__(
            self,
            "blockers",
            _normalize_optional_tuple("blockers", self.blockers),
        )
        if self.compass_question is not None:
            object.__setattr__(
                self,
                "compass_question",
                _normalize_required_text("compass_question", self.compass_question),
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision.value,
            "left_project_id": self.left_project_id,
            "right_project_id": self.right_project_id,
            "evidence_refs": self.evidence_refs,
            "difference_evidence": tuple(
                evidence.to_dict() for evidence in self.difference_evidence
            ),
            "shared_relationship_refs": self.shared_relationship_refs,
            "blockers": self.blockers,
            "compass_question": self.compass_question,
            "merge_authorized": False,
        }


@dataclass(frozen=True)
class ProjectHandoffRequest:
    """Primitive, display-safe request for cross-project handoff review."""

    source_project_id: str | None
    target_project_id: str | None
    reason_category: str
    payload_type: str
    payload_summary_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    approval_required: bool
    approval_refs: tuple[str, ...] = ()
    raw_context_blocked: bool = True

    def __post_init__(self) -> None:
        if self.source_project_id is not None:
            object.__setattr__(
                self,
                "source_project_id",
                _normalize_required_text(
                    "source_project_id",
                    self.source_project_id,
                ),
            )
        if self.target_project_id is not None:
            object.__setattr__(
                self,
                "target_project_id",
                _normalize_required_text(
                    "target_project_id",
                    self.target_project_id,
                ),
            )
        object.__setattr__(
            self,
            "reason_category",
            _normalize_required_text("reason_category", self.reason_category),
        )
        object.__setattr__(
            self,
            "payload_type",
            _normalize_required_text("payload_type", self.payload_type),
        )
        object.__setattr__(
            self,
            "payload_summary_refs",
            _normalize_optional_tuple(
                "payload_summary_refs",
                self.payload_summary_refs,
            ),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _normalize_optional_tuple("evidence_refs", self.evidence_refs),
        )
        if not isinstance(self.approval_required, bool):
            raise ValueError("approval_required must be bool")
        object.__setattr__(
            self,
            "approval_refs",
            _normalize_optional_tuple("approval_refs", self.approval_refs),
        )
        if not isinstance(self.raw_context_blocked, bool):
            raise ValueError("raw_context_blocked must be bool")

    def to_dict(self) -> dict[str, object]:
        return {
            "source_project_id": self.source_project_id,
            "target_project_id": self.target_project_id,
            "reason_category": self.reason_category,
            "payload_type": self.payload_type,
            "payload_summary_refs": self.payload_summary_refs,
            "evidence_refs": self.evidence_refs,
            "approval_required": self.approval_required,
            "approval_refs": self.approval_refs,
            "raw_context_blocked": self.raw_context_blocked,
        }


@dataclass(frozen=True)
class ProjectHandoffEvaluation:
    """Serializable Compass advisory result for cross-project handoff."""

    decision: ProjectHandoffDecision
    source_project_id: str | None
    target_project_id: str | None
    reason_category: str
    payload_type: str
    payload_summary_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    approval_required: bool
    approval_refs: tuple[str, ...] = ()
    project_difference_decision: ProjectDifferenceDecision | None = None
    shared_relationship_refs: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    compass_question: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.decision, ProjectHandoffDecision):
            raise ValueError("decision must be ProjectHandoffDecision")
        if self.source_project_id is not None:
            object.__setattr__(
                self,
                "source_project_id",
                _normalize_required_text(
                    "source_project_id",
                    self.source_project_id,
                ),
            )
        if self.target_project_id is not None:
            object.__setattr__(
                self,
                "target_project_id",
                _normalize_required_text(
                    "target_project_id",
                    self.target_project_id,
                ),
            )
        object.__setattr__(
            self,
            "reason_category",
            _normalize_required_text("reason_category", self.reason_category),
        )
        object.__setattr__(
            self,
            "payload_type",
            _normalize_required_text("payload_type", self.payload_type),
        )
        object.__setattr__(
            self,
            "payload_summary_refs",
            _normalize_optional_tuple(
                "payload_summary_refs",
                self.payload_summary_refs,
            ),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _normalize_optional_tuple("evidence_refs", self.evidence_refs),
        )
        if not isinstance(self.approval_required, bool):
            raise ValueError("approval_required must be bool")
        object.__setattr__(
            self,
            "approval_refs",
            _normalize_optional_tuple("approval_refs", self.approval_refs),
        )
        if self.project_difference_decision is not None and not isinstance(
            self.project_difference_decision,
            ProjectDifferenceDecision,
        ):
            raise ValueError("project_difference_decision must be ProjectDifferenceDecision")
        object.__setattr__(
            self,
            "shared_relationship_refs",
            _normalize_optional_tuple(
                "shared_relationship_refs",
                self.shared_relationship_refs,
            ),
        )
        object.__setattr__(
            self,
            "blockers",
            _normalize_optional_tuple("blockers", self.blockers),
        )
        if self.compass_question is not None:
            object.__setattr__(
                self,
                "compass_question",
                _normalize_required_text("compass_question", self.compass_question),
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision.value,
            "source_project_id": self.source_project_id,
            "target_project_id": self.target_project_id,
            "reason_category": self.reason_category,
            "payload_type": self.payload_type,
            "payload_summary_refs": self.payload_summary_refs,
            "evidence_refs": self.evidence_refs,
            "approval_required": self.approval_required,
            "approval_refs": self.approval_refs,
            "project_difference_decision": (
                self.project_difference_decision.value
                if self.project_difference_decision is not None
                else None
            ),
            "shared_relationship_refs": self.shared_relationship_refs,
            "blockers": self.blockers,
            "compass_question": self.compass_question,
            "review_ready": self.decision is ProjectHandoffDecision.REVIEW_READY,
            "execution_authorized": False,
        }


def define_project(
    *,
    project_id: str,
    title: str,
    outcome: str,
    context: Iterable[str],
    artifacts: Iterable[str],
    objectives: Iterable[str],
    tasks: Iterable[str],
    proof_trail: Iterable[str],
    repo_refs: Iterable[str],
    venture_refs: Iterable[str],
    session_refs: Iterable[str] = (),
) -> ProjectDefinition:
    """Create a validated Compass project definition from primitive fields."""
    return ProjectDefinition(
        project_id=project_id,
        title=title,
        outcome=outcome,
        context=tuple(context),
        artifacts=tuple(artifacts),
        objectives=tuple(objectives),
        tasks=tuple(tasks),
        proof_trail=tuple(proof_trail),
        relationship_refs=ProjectRelationshipRefs(
            repo_refs=tuple(repo_refs),
            venture_refs=tuple(venture_refs),
            session_refs=tuple(session_refs),
        ),
    )


def evaluate_project_scope(
    project: ProjectDefinition,
    candidate: ProjectScopeCandidate,
) -> ProjectScopeEvaluation:
    """Evaluate whether a summarized subject is inside a project boundary."""
    if candidate.project_id is None:
        return _scope_result(
            ProjectScopeDecision.BLOCKED,
            candidate,
            blockers=("missing_project_identity",),
        )
    if candidate.project_id != project.project_id:
        return _scope_result(
            ProjectScopeDecision.BLOCKED,
            candidate,
            blockers=("project_identity_mismatch",),
        )
    if not candidate.evidence_refs:
        return _scope_result(
            ProjectScopeDecision.BLOCKED,
            candidate,
            blockers=("missing_scope_evidence_refs",),
        )
    if candidate.subject_kind not in _SCOPE_SUBJECT_KINDS:
        return _scope_result(
            ProjectScopeDecision.AMBIGUOUS,
            candidate,
            compass_question=(
                "Compass needs a known subject kind before deciding project scope."
            ),
        )
    if candidate.subject_kind == "ambiguous":
        reason = candidate.ambiguity_reason or "subject kind is ambiguous"
        return _scope_result(
            ProjectScopeDecision.AMBIGUOUS,
            candidate,
            compass_question=f"Compass question: should {candidate.subject_ref!r} belong to {project.project_id}? {reason}",
        )

    matched_refs = _scope_matches(project, candidate)
    if matched_refs:
        return _scope_result(
            ProjectScopeDecision.IN_SCOPE,
            candidate,
            matched_refs=matched_refs,
        )
    return _scope_result(
        ProjectScopeDecision.OUT_OF_SCOPE,
        candidate,
        blockers=("subject_not_in_project_boundary",),
    )


def project_difference_profile_from_definition(
    project: ProjectDefinition,
    *,
    mission_bearing: str,
    memory_pins: Iterable[str],
    blockers: Iterable[str],
    proof_expectations: Iterable[str],
) -> ProjectDifferenceProfile:
    """Create a difference profile from a reviewed project definition."""
    return ProjectDifferenceProfile(
        project_id=project.project_id,
        mission_bearing=mission_bearing,
        objectives=project.objectives,
        artifacts=project.artifacts,
        memory_pins=tuple(memory_pins),
        blockers=tuple(blockers),
        proof_expectations=tuple(proof_expectations),
        repo_refs=project.relationship_refs.repo_refs,
        venture_refs=project.relationship_refs.venture_refs,
    )


def evaluate_project_difference(
    left: ProjectDifferenceProfile,
    right: ProjectDifferenceProfile,
    *,
    evidence_refs: Iterable[str],
) -> ProjectDifferenceEvaluation:
    """Evaluate whether two project-bearing summaries describe distinct work."""
    normalized_evidence_refs = _normalize_optional_tuple(
        "evidence_refs",
        tuple(evidence_refs),
    )
    shared_relationship_refs = _shared_relationship_refs(left, right)
    blockers = _project_difference_blockers(left, right, normalized_evidence_refs)
    if blockers:
        return ProjectDifferenceEvaluation(
            decision=ProjectDifferenceDecision.BLOCKED,
            left_project_id=left.project_id,
            right_project_id=right.project_id,
            evidence_refs=normalized_evidence_refs,
            shared_relationship_refs=shared_relationship_refs,
            blockers=blockers,
            compass_question=(
                "Compass needs complete project difference evidence before merging contexts."
            ),
        )

    difference_evidence = _project_difference_evidence(left, right)
    if difference_evidence:
        return ProjectDifferenceEvaluation(
            decision=ProjectDifferenceDecision.DISTINCT,
            left_project_id=left.project_id,
            right_project_id=right.project_id,
            evidence_refs=normalized_evidence_refs,
            difference_evidence=difference_evidence,
            shared_relationship_refs=shared_relationship_refs,
        )

    if left.project_id == right.project_id:
        return ProjectDifferenceEvaluation(
            decision=ProjectDifferenceDecision.SAME_PROJECT,
            left_project_id=left.project_id,
            right_project_id=right.project_id,
            evidence_refs=normalized_evidence_refs,
            shared_relationship_refs=shared_relationship_refs,
        )

    return ProjectDifferenceEvaluation(
        decision=ProjectDifferenceDecision.AMBIGUOUS,
        left_project_id=left.project_id,
        right_project_id=right.project_id,
        evidence_refs=normalized_evidence_refs,
        shared_relationship_refs=shared_relationship_refs,
        blockers=("ambiguous_project_difference_evidence",),
        compass_question=(
            "Compass needs explicit project-difference evidence before treating "
            "different project identities as the same project."
        ),
    )


def evaluate_cross_project_handoff(
    source_project: ProjectDifferenceProfile,
    target_project: ProjectDifferenceProfile,
    request: ProjectHandoffRequest,
) -> ProjectHandoffEvaluation:
    """Evaluate whether a cross-project handoff is ready for human review."""
    blockers = list(_handoff_request_blockers(source_project, target_project, request))
    difference_result: ProjectDifferenceEvaluation | None = None
    if request.evidence_refs:
        difference_result = evaluate_project_difference(
            source_project,
            target_project,
            evidence_refs=request.evidence_refs,
        )
        if difference_result.decision is ProjectDifferenceDecision.BLOCKED:
            blockers.append("project_difference_blocked")
            blockers.extend(difference_result.blockers)
        elif difference_result.decision is ProjectDifferenceDecision.SAME_PROJECT:
            blockers.append("source_target_not_distinct")
        elif difference_result.decision is ProjectDifferenceDecision.AMBIGUOUS:
            return _handoff_result(
                ProjectHandoffDecision.AMBIGUOUS,
                request,
                difference_result=difference_result,
                blockers=("ambiguous_project_difference_evidence",),
                compass_question=(
                    "Compass needs distinct project-difference evidence before "
                    "presenting a cross-project handoff for review."
                ),
            )

    if blockers:
        return _handoff_result(
            ProjectHandoffDecision.BLOCKED,
            request,
            difference_result=difference_result,
            blockers=_dedupe_preserve_order(blockers),
            compass_question=(
                "Compass needs safe handoff refs, distinct project identities, "
                "and required approval evidence before review."
            ),
        )

    if difference_result is None:
        return _handoff_result(
            ProjectHandoffDecision.BLOCKED,
            request,
            blockers=("missing_handoff_evidence_refs",),
            compass_question=(
                "Compass needs evidence refs before cross-project handoff review."
            ),
        )

    return _handoff_result(
        ProjectHandoffDecision.REVIEW_READY,
        request,
        difference_result=difference_result,
    )


def _scope_result(
    decision: ProjectScopeDecision,
    candidate: ProjectScopeCandidate,
    *,
    matched_refs: tuple[str, ...] = (),
    blockers: tuple[str, ...] = (),
    compass_question: str | None = None,
) -> ProjectScopeEvaluation:
    return ProjectScopeEvaluation(
        decision=decision,
        project_id=candidate.project_id,
        subject_kind=candidate.subject_kind,
        subject_ref=candidate.subject_ref,
        evidence_refs=candidate.evidence_refs,
        matched_refs=matched_refs,
        blockers=blockers,
        compass_question=compass_question,
    )


def _handoff_result(
    decision: ProjectHandoffDecision,
    request: ProjectHandoffRequest,
    *,
    difference_result: ProjectDifferenceEvaluation | None = None,
    blockers: tuple[str, ...] = (),
    compass_question: str | None = None,
) -> ProjectHandoffEvaluation:
    return ProjectHandoffEvaluation(
        decision=decision,
        source_project_id=request.source_project_id,
        target_project_id=request.target_project_id,
        reason_category=request.reason_category,
        payload_type=request.payload_type,
        payload_summary_refs=request.payload_summary_refs,
        evidence_refs=request.evidence_refs,
        approval_required=request.approval_required,
        approval_refs=request.approval_refs,
        project_difference_decision=(
            difference_result.decision if difference_result is not None else None
        ),
        shared_relationship_refs=(
            difference_result.shared_relationship_refs
            if difference_result is not None
            else ()
        ),
        blockers=blockers,
        compass_question=compass_question,
    )


def _scope_matches(
    project: ProjectDefinition,
    candidate: ProjectScopeCandidate,
) -> tuple[str, ...]:
    subject_map = {
        "context": project.context,
        "artifact": project.artifacts,
        "objective": project.objectives,
        "task": project.tasks,
        "proof": project.proof_trail,
        "repo": project.relationship_refs.repo_refs,
        "venture": project.relationship_refs.venture_refs,
        "session": project.relationship_refs.session_refs,
    }
    values = subject_map[candidate.subject_kind]
    return (candidate.subject_ref,) if candidate.subject_ref in values else ()


def _handoff_request_blockers(
    source_project: ProjectDifferenceProfile,
    target_project: ProjectDifferenceProfile,
    request: ProjectHandoffRequest,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if request.source_project_id is None:
        blockers.append("missing_source_project_id")
    if request.target_project_id is None:
        blockers.append("missing_target_project_id")
    if source_project.project_id is None:
        blockers.append("missing_source_project_profile_id")
    if target_project.project_id is None:
        blockers.append("missing_target_project_profile_id")
    if (
        request.source_project_id is not None
        and source_project.project_id is not None
        and request.source_project_id != source_project.project_id
    ):
        blockers.append("source_project_identity_mismatch")
    if (
        request.target_project_id is not None
        and target_project.project_id is not None
        and request.target_project_id != target_project.project_id
    ):
        blockers.append("target_project_identity_mismatch")
    if (
        request.source_project_id is not None
        and request.target_project_id is not None
        and request.source_project_id == request.target_project_id
    ):
        blockers.append("source_target_not_distinct")
    if not request.evidence_refs:
        blockers.append("missing_handoff_evidence_refs")
    if not request.payload_summary_refs:
        blockers.append("missing_payload_summary_refs")
    if request.reason_category not in _HANDOFF_REASON_CATEGORIES:
        blockers.append("unknown_handoff_reason_category")
    if request.payload_type in _RAW_CONTEXT_PAYLOAD_TYPES:
        blockers.append("raw_context_payload_type_blocked")
    elif request.payload_type not in _HANDOFF_PAYLOAD_TYPES:
        blockers.append("unknown_handoff_payload_type")
    if not request.raw_context_blocked:
        blockers.append("raw_context_bleed_not_blocked")
    if _has_raw_context_ref(request.evidence_refs):
        blockers.append("raw_context_evidence_ref_blocked")
    if _has_raw_context_ref(request.payload_summary_refs):
        blockers.append("raw_context_payload_summary_ref_blocked")
    if request.approval_required and not request.approval_refs:
        blockers.append("missing_required_approval_refs")
    if _has_raw_context_ref(request.approval_refs):
        blockers.append("raw_context_approval_ref_blocked")
    return tuple(blockers)


def _project_difference_blockers(
    left: ProjectDifferenceProfile,
    right: ProjectDifferenceProfile,
    evidence_refs: tuple[str, ...],
) -> tuple[str, ...]:
    blockers: list[str] = []
    if left.project_id is None:
        blockers.append("missing_left_project_id")
    if right.project_id is None:
        blockers.append("missing_right_project_id")
    if not evidence_refs:
        blockers.append("missing_project_difference_evidence_refs")

    for side_name, profile in (("left", left), ("right", right)):
        for field in _PROJECT_DIFFERENCE_REQUIRED_FIELDS:
            value = getattr(profile, field)
            if value is None or value == ():
                blockers.append(f"missing_{side_name}_{field}")
    return tuple(blockers)


def _project_difference_evidence(
    left: ProjectDifferenceProfile,
    right: ProjectDifferenceProfile,
) -> tuple[ProjectDifferenceEvidence, ...]:
    evidence: list[ProjectDifferenceEvidence] = []
    for field in _PROJECT_DIFFERENCE_REQUIRED_FIELDS:
        left_value = _difference_field_tuple(getattr(left, field))
        right_value = _difference_field_tuple(getattr(right, field))
        if left_value != right_value:
            evidence.append(
                ProjectDifferenceEvidence(
                    field=field,
                    left=left_value,
                    right=right_value,
                )
            )
    return tuple(evidence)


def _difference_field_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(value)  # type: ignore[arg-type]


def _shared_relationship_refs(
    left: ProjectDifferenceProfile,
    right: ProjectDifferenceProfile,
) -> tuple[str, ...]:
    shared_refs = set(left.repo_refs).intersection(right.repo_refs)
    shared_refs.update(set(left.venture_refs).intersection(right.venture_refs))
    return tuple(sorted(shared_refs))


def _has_raw_context_ref(refs: Iterable[str]) -> bool:
    return any(_is_raw_context_ref(ref) for ref in refs)


def _is_raw_context_ref(ref: str) -> bool:
    normalized = ref.strip().lower()
    return "\n" in ref or any(
        normalized.startswith(prefix) for prefix in _RAW_CONTEXT_REF_PREFIXES
    )


def _dedupe_preserve_order(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return tuple(deduped)


def project_definition_fingerprint(project: ProjectDefinition | Mapping[str, object]) -> str:
    """Return a stable SHA-256 fingerprint for a project definition."""
    payload = project.to_dict() if isinstance(project, ProjectDefinition) else dict(project)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def project_definition_dict_keys() -> tuple[str, ...]:
    """Expose the stable top-level serialization shape for tests/consumers."""
    return _PROJECT_DEFINITION_DICT_KEYS


def project_scope_result_dict_keys() -> tuple[str, ...]:
    """Expose the stable scope-evaluation serialization shape."""
    return _PROJECT_SCOPE_RESULT_DICT_KEYS


def project_difference_profile_dict_keys() -> tuple[str, ...]:
    """Expose the stable difference-profile serialization shape."""
    return _PROJECT_DIFFERENCE_PROFILE_KEYS


def project_difference_evidence_dict_keys() -> tuple[str, ...]:
    """Expose the stable difference-evidence serialization shape."""
    return _PROJECT_DIFFERENCE_EVIDENCE_KEYS


def project_difference_result_dict_keys() -> tuple[str, ...]:
    """Expose the stable difference-evaluation serialization shape."""
    return _PROJECT_DIFFERENCE_RESULT_DICT_KEYS


def project_handoff_request_dict_keys() -> tuple[str, ...]:
    """Expose the stable handoff-request serialization shape."""
    return _PROJECT_HANDOFF_REQUEST_KEYS


def project_handoff_result_dict_keys() -> tuple[str, ...]:
    """Expose the stable handoff-evaluation serialization shape."""
    return _PROJECT_HANDOFF_RESULT_DICT_KEYS
