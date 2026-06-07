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
import re
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
    "execution_authorized",
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
_PROJECT_DIFFERENCE_RAW_CONTEXT_SCAN_FIELDS = (
    "mission_bearing",
    "objectives",
    "artifacts",
    "memory_pins",
    "blockers",
    "proof_expectations",
    "repo_refs",
    "venture_refs",
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
_PROJECT_IDENTITY_NEIGHBOR_KEYS = (
    "project_id",
    "mission_bearing",
    "title",
    "outcome",
    "context",
    "artifacts",
    "objectives",
    "tasks",
    "proof_trail",
    "repo_refs",
    "venture_refs",
    "session_refs",
)
_PROJECT_IDENTITY_CANDIDATE_KEYS = (
    "project_id",
    "title",
    "outcome",
    "mission_bearing",
    "context",
    "artifacts",
    "objectives",
    "tasks",
    "proof_trail",
    "repo_refs",
    "venture_refs",
    "session_refs",
    "evidence_refs",
    "neighbors",
)
_PROJECT_IDENTITY_BOUNDED_TUPLE_FIELDS = (
    "context",
    "artifacts",
    "objectives",
    "tasks",
    "proof_trail",
)
_PROJECT_IDENTITY_BOUNDED_TEXT_FIELDS = (
    "title",
    "outcome",
)
_BEARING_PUNCTUATION_STRIP = ".,;:!?-—–_'\"—–"
_BEARING_WHITESPACE_RE = re.compile(r"\s+")
_PROJECT_IDENTITY_RESULT_DICT_KEYS = (
    "decision",
    "project_id",
    "title",
    "outcome",
    "mission_bearing",
    "evidence_refs",
    "shared_repo_refs",
    "shared_venture_refs",
    "shared_session_refs",
    "distinguishing_neighbors",
    "collapsing_neighbors",
    "blockers",
    "compass_question",
    "execution_authorized",
)
_PROJECT_IDENTITY_REQUIRED_TEXT_FIELDS = (
    "project_id",
    "title",
    "outcome",
    "mission_bearing",
)
_PROJECT_BOUNDS_REQUEST_KEYS = (
    "project_id",
    "request_kind",
    "request_ref",
    "candidates",
    "repo_refs",
    "venture_refs",
    "session_refs",
    "evidence_refs",
    "ambiguity_reason",
)
_PROJECT_BOUNDS_RESULT_DICT_KEYS = (
    "decision",
    "project_id",
    "request_kind",
    "request_ref",
    "in_scope_refs",
    "out_of_scope_refs",
    "ambiguous_refs",
    "blocked_refs",
    "shared_relationship_refs",
    "evidence_refs",
    "candidate_decisions",
    "blockers",
    "compass_question",
    "execution_authorized",
)
_BOUNDS_REQUEST_KINDS = {
    "feature_change",
    "scope_inquiry",
    "boundary_extension",
    "context_load",
    "task_addition",
    "evidence_attach",
    "ambiguous",
}
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


class ProjectIdentityDecision(Enum):
    """Deterministic Compass decision for project identity definition."""

    DEFINED = "defined"
    AMBIGUOUS = "ambiguous"
    BLOCKED = "blocked"


class ProjectBoundsDecision(Enum):
    """Deterministic Compass decision for a multi-subject project bounds request."""

    IN_SCOPE = "in_scope"
    OUT_OF_SCOPE = "out_of_scope"
    PARTIAL_SCOPE = "partial_scope"
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
            "execution_authorized": False,
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


@dataclass(frozen=True)
class ProjectIdentityNeighbor:
    """Already-defined neighbor project that may share relationship refs.

    Optional bounded identity evidence (``title``, ``outcome``, ``context``,
    ``artifacts``, ``objectives``, ``tasks``, ``proof_trail``) is used during
    overlap evaluation to keep genuinely distinct projects distinct even when
    their mission bearings collide after normalization.
    """

    project_id: str
    mission_bearing: str
    title: str | None = None
    outcome: str | None = None
    context: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    objectives: tuple[str, ...] = ()
    tasks: tuple[str, ...] = ()
    proof_trail: tuple[str, ...] = ()
    repo_refs: tuple[str, ...] = ()
    venture_refs: tuple[str, ...] = ()
    session_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "project_id",
            _normalize_required_text("project_id", self.project_id),
        )
        object.__setattr__(
            self,
            "mission_bearing",
            _normalize_required_text("mission_bearing", self.mission_bearing),
        )
        if self.title is not None:
            object.__setattr__(
                self,
                "title",
                _normalize_required_text("title", self.title),
            )
        if self.outcome is not None:
            object.__setattr__(
                self,
                "outcome",
                _normalize_required_text("outcome", self.outcome),
            )
        object.__setattr__(
            self,
            "context",
            _normalize_optional_tuple("context", self.context),
        )
        object.__setattr__(
            self,
            "artifacts",
            _normalize_optional_tuple("artifacts", self.artifacts),
        )
        object.__setattr__(
            self,
            "objectives",
            _normalize_optional_tuple("objectives", self.objectives),
        )
        object.__setattr__(
            self,
            "tasks",
            _normalize_optional_tuple("tasks", self.tasks),
        )
        object.__setattr__(
            self,
            "proof_trail",
            _normalize_optional_tuple("proof_trail", self.proof_trail),
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
        object.__setattr__(
            self,
            "session_refs",
            _normalize_optional_tuple("session_refs", self.session_refs),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "mission_bearing": self.mission_bearing,
            "title": self.title,
            "outcome": self.outcome,
            "context": self.context,
            "artifacts": self.artifacts,
            "objectives": self.objectives,
            "tasks": self.tasks,
            "proof_trail": self.proof_trail,
            "repo_refs": self.repo_refs,
            "venture_refs": self.venture_refs,
            "session_refs": self.session_refs,
        }


@dataclass(frozen=True)
class ProjectIdentityCandidate:
    """Primitive identity inputs being considered as a Meridian project definition.

    Bounded identity evidence tuples (``context``, ``artifacts``, ``objectives``,
    ``tasks``, ``proof_trail``) are optional but, when populated, participate in
    neighbor comparison so a candidate whose mission bearing collides with a
    neighbor can still stay distinct if any of its bounded body of work differs.
    """

    project_id: str | None
    title: str | None
    outcome: str | None
    mission_bearing: str | None
    repo_refs: tuple[str, ...]
    venture_refs: tuple[str, ...]
    session_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    context: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    objectives: tuple[str, ...] = ()
    tasks: tuple[str, ...] = ()
    proof_trail: tuple[str, ...] = ()
    neighbors: tuple[ProjectIdentityNeighbor, ...] = ()

    def __post_init__(self) -> None:
        if self.project_id is not None:
            object.__setattr__(
                self,
                "project_id",
                _normalize_required_text("project_id", self.project_id),
            )
        if self.title is not None:
            object.__setattr__(
                self,
                "title",
                _normalize_required_text("title", self.title),
            )
        if self.outcome is not None:
            object.__setattr__(
                self,
                "outcome",
                _normalize_required_text("outcome", self.outcome),
            )
        if self.mission_bearing is not None:
            object.__setattr__(
                self,
                "mission_bearing",
                _normalize_required_text("mission_bearing", self.mission_bearing),
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
        object.__setattr__(
            self,
            "session_refs",
            _normalize_optional_tuple("session_refs", self.session_refs),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _normalize_optional_tuple("evidence_refs", self.evidence_refs),
        )
        object.__setattr__(
            self,
            "context",
            _normalize_optional_tuple("context", self.context),
        )
        object.__setattr__(
            self,
            "artifacts",
            _normalize_optional_tuple("artifacts", self.artifacts),
        )
        object.__setattr__(
            self,
            "objectives",
            _normalize_optional_tuple("objectives", self.objectives),
        )
        object.__setattr__(
            self,
            "tasks",
            _normalize_optional_tuple("tasks", self.tasks),
        )
        object.__setattr__(
            self,
            "proof_trail",
            _normalize_optional_tuple("proof_trail", self.proof_trail),
        )
        if any(
            not isinstance(neighbor, ProjectIdentityNeighbor)
            for neighbor in self.neighbors
        ):
            raise ValueError("neighbors must be ProjectIdentityNeighbor")
        object.__setattr__(self, "neighbors", tuple(self.neighbors))

    def to_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "title": self.title,
            "outcome": self.outcome,
            "mission_bearing": self.mission_bearing,
            "context": self.context,
            "artifacts": self.artifacts,
            "objectives": self.objectives,
            "tasks": self.tasks,
            "proof_trail": self.proof_trail,
            "repo_refs": self.repo_refs,
            "venture_refs": self.venture_refs,
            "session_refs": self.session_refs,
            "evidence_refs": self.evidence_refs,
            "neighbors": tuple(neighbor.to_dict() for neighbor in self.neighbors),
        }


@dataclass(frozen=True)
class ProjectIdentityEvaluation:
    """Serializable Compass result for a project identity definition check."""

    decision: ProjectIdentityDecision
    project_id: str | None
    title: str | None
    outcome: str | None
    mission_bearing: str | None
    evidence_refs: tuple[str, ...]
    shared_repo_refs: tuple[str, ...] = ()
    shared_venture_refs: tuple[str, ...] = ()
    shared_session_refs: tuple[str, ...] = ()
    distinguishing_neighbors: tuple[str, ...] = ()
    collapsing_neighbors: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    compass_question: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.decision, ProjectIdentityDecision):
            raise ValueError("decision must be ProjectIdentityDecision")
        if self.project_id is not None:
            object.__setattr__(
                self,
                "project_id",
                _normalize_required_text("project_id", self.project_id),
            )
        if self.title is not None:
            object.__setattr__(
                self,
                "title",
                _normalize_required_text("title", self.title),
            )
        if self.outcome is not None:
            object.__setattr__(
                self,
                "outcome",
                _normalize_required_text("outcome", self.outcome),
            )
        if self.mission_bearing is not None:
            object.__setattr__(
                self,
                "mission_bearing",
                _normalize_required_text("mission_bearing", self.mission_bearing),
            )
        object.__setattr__(
            self,
            "evidence_refs",
            _normalize_optional_tuple("evidence_refs", self.evidence_refs),
        )
        object.__setattr__(
            self,
            "shared_repo_refs",
            _normalize_optional_tuple("shared_repo_refs", self.shared_repo_refs),
        )
        object.__setattr__(
            self,
            "shared_venture_refs",
            _normalize_optional_tuple("shared_venture_refs", self.shared_venture_refs),
        )
        object.__setattr__(
            self,
            "shared_session_refs",
            _normalize_optional_tuple("shared_session_refs", self.shared_session_refs),
        )
        object.__setattr__(
            self,
            "distinguishing_neighbors",
            _normalize_optional_tuple(
                "distinguishing_neighbors",
                self.distinguishing_neighbors,
            ),
        )
        object.__setattr__(
            self,
            "collapsing_neighbors",
            _normalize_optional_tuple(
                "collapsing_neighbors",
                self.collapsing_neighbors,
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
            "project_id": self.project_id,
            "title": self.title,
            "outcome": self.outcome,
            "mission_bearing": self.mission_bearing,
            "evidence_refs": self.evidence_refs,
            "shared_repo_refs": self.shared_repo_refs,
            "shared_venture_refs": self.shared_venture_refs,
            "shared_session_refs": self.shared_session_refs,
            "distinguishing_neighbors": self.distinguishing_neighbors,
            "collapsing_neighbors": self.collapsing_neighbors,
            "blockers": self.blockers,
            "compass_question": self.compass_question,
            "execution_authorized": False,
        }


@dataclass(frozen=True)
class ProjectBoundsRequest:
    """Primitive multi-subject request proposed against a project's boundary.

    A bounds request bundles one or more ``ProjectScopeCandidate`` subjects
    along with the relationship envelope (repo/venture/session refs) and
    evidence refs that justify the request. The Compass bounds runtime then
    decides whether the bundle as a whole sits inside the project boundary,
    falls outside it, splits across the boundary, requires a Compass
    clarification, or is blocked.
    """

    project_id: str | None
    request_kind: str
    request_ref: str
    candidates: tuple[ProjectScopeCandidate, ...]
    repo_refs: tuple[str, ...] = ()
    venture_refs: tuple[str, ...] = ()
    session_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
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
            "request_kind",
            _normalize_required_text("request_kind", self.request_kind),
        )
        object.__setattr__(
            self,
            "request_ref",
            _normalize_required_text("request_ref", self.request_ref),
        )
        if any(
            not isinstance(candidate, ProjectScopeCandidate)
            for candidate in self.candidates
        ):
            raise ValueError("candidates must be ProjectScopeCandidate")
        object.__setattr__(self, "candidates", tuple(self.candidates))
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
        object.__setattr__(
            self,
            "session_refs",
            _normalize_optional_tuple("session_refs", self.session_refs),
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
            "request_kind": self.request_kind,
            "request_ref": self.request_ref,
            "candidates": tuple(candidate.to_dict() for candidate in self.candidates),
            "repo_refs": self.repo_refs,
            "venture_refs": self.venture_refs,
            "session_refs": self.session_refs,
            "evidence_refs": self.evidence_refs,
            "ambiguity_reason": self.ambiguity_reason,
        }


@dataclass(frozen=True)
class ProjectBoundsEvaluation:
    """Serializable Compass result for a multi-subject bounds request.

    The result always carries ``execution_authorized=False``. Shared
    relationship refs are surfaced rather than collapsed so the caller can
    see overlapping repo/venture/session refs without inferring the request
    has implicitly merged with the project.
    """

    decision: ProjectBoundsDecision
    project_id: str | None
    request_kind: str
    request_ref: str
    in_scope_refs: tuple[str, ...] = ()
    out_of_scope_refs: tuple[str, ...] = ()
    ambiguous_refs: tuple[str, ...] = ()
    blocked_refs: tuple[str, ...] = ()
    shared_relationship_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    candidate_decisions: tuple[Mapping[str, object], ...] = ()
    blockers: tuple[str, ...] = ()
    compass_question: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.decision, ProjectBoundsDecision):
            raise ValueError("decision must be ProjectBoundsDecision")
        if self.project_id is not None:
            object.__setattr__(
                self,
                "project_id",
                _normalize_required_text("project_id", self.project_id),
            )
        object.__setattr__(
            self,
            "request_kind",
            _normalize_required_text("request_kind", self.request_kind),
        )
        object.__setattr__(
            self,
            "request_ref",
            _normalize_required_text("request_ref", self.request_ref),
        )
        object.__setattr__(
            self,
            "in_scope_refs",
            _normalize_optional_tuple("in_scope_refs", self.in_scope_refs),
        )
        object.__setattr__(
            self,
            "out_of_scope_refs",
            _normalize_optional_tuple("out_of_scope_refs", self.out_of_scope_refs),
        )
        object.__setattr__(
            self,
            "ambiguous_refs",
            _normalize_optional_tuple("ambiguous_refs", self.ambiguous_refs),
        )
        object.__setattr__(
            self,
            "blocked_refs",
            _normalize_optional_tuple("blocked_refs", self.blocked_refs),
        )
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
            "evidence_refs",
            _normalize_optional_tuple("evidence_refs", self.evidence_refs),
        )
        normalized_decisions: list[dict[str, object]] = []
        for entry in self.candidate_decisions:
            if not isinstance(entry, Mapping):
                raise ValueError("candidate_decisions must contain mappings")
            normalized_decisions.append(dict(entry))
        object.__setattr__(self, "candidate_decisions", tuple(normalized_decisions))
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
            "request_kind": self.request_kind,
            "request_ref": self.request_ref,
            "in_scope_refs": self.in_scope_refs,
            "out_of_scope_refs": self.out_of_scope_refs,
            "ambiguous_refs": self.ambiguous_refs,
            "blocked_refs": self.blocked_refs,
            "shared_relationship_refs": self.shared_relationship_refs,
            "evidence_refs": self.evidence_refs,
            "candidate_decisions": self.candidate_decisions,
            "blockers": self.blockers,
            "compass_question": self.compass_question,
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
    """Evaluate whether a summarized subject is inside a project boundary.

    Raw-context evidence refs (``raw_prompt:``, ``raw_transcript:``,
    ``free_form_context:``, ``transcript:``, ``conversation:``,
    ``provider_response:``, anything containing a newline, etc.) fail closed
    as ``BLOCKED`` before any boundary match, and the serialized evidence is
    redacted so the raw payload never appears in ``to_dict()`` output. This
    keeps the no-raw-cross-project-transcript-injection invariant intact for
    direct callers of ``evaluate_project_scope``, not only for callers that
    reach scope through ``evaluate_project_bounds``.
    """
    if _has_raw_context_ref(candidate.evidence_refs):
        return ProjectScopeEvaluation(
            decision=ProjectScopeDecision.BLOCKED,
            project_id=candidate.project_id,
            subject_kind=candidate.subject_kind,
            subject_ref=_redact_raw_context_refs((candidate.subject_ref,))[0],
            blockers=("raw_context_evidence_ref_blocked",),
            evidence_refs=_redact_raw_context_refs(candidate.evidence_refs),
        )
    if _has_raw_context_ref((candidate.subject_ref,)) or (
        candidate.ambiguity_reason is not None
        and _has_raw_context_ref((candidate.ambiguity_reason,))
    ):
        return ProjectScopeEvaluation(
            decision=ProjectScopeDecision.BLOCKED,
            project_id=candidate.project_id,
            subject_kind=candidate.subject_kind,
            subject_ref=_redact_raw_context_refs((candidate.subject_ref,))[0],
            evidence_refs=_redact_raw_context_refs(candidate.evidence_refs),
            blockers=("raw_context_subject_field_blocked",),
        )
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
    """Evaluate whether two project-bearing summaries describe distinct work.

    Distinguishes projects by mission/bearing, objectives, artifacts, memory
    pins, blockers, proof expectations, and relationship refs. Same repo or
    venture does NOT imply same project: ``shared_relationship_refs`` is
    surfaced for review, but the difference decision depends on the bounded
    bearing fields, not on overlapping repo/venture/session labels.

    Uncertain or insufficient evidence surfaces as Compass questions/blockers
    (never silently merged). Raw-context evidence_refs and any raw-context
    payload smuggled through profile text/ref fields fail closed BEFORE the
    comparison runs; the serialized result redacts raw-context evidence_refs
    to the marker ``<redacted_raw_context>`` so no raw payload leaks.

    The result always serializes ``execution_authorized=False``.
    """
    normalized_evidence_refs = _normalize_optional_tuple(
        "evidence_refs",
        tuple(evidence_refs),
    )
    shared_relationship_refs = _shared_relationship_refs(left, right)

    safe_left_project_id = _redact_raw_context_scalar(left.project_id)
    safe_right_project_id = _redact_raw_context_scalar(right.project_id)

    raw_context_blockers = _project_difference_raw_context_blockers(
        left, right, normalized_evidence_refs
    )
    if raw_context_blockers:
        return ProjectDifferenceEvaluation(
            decision=ProjectDifferenceDecision.BLOCKED,
            left_project_id=safe_left_project_id,
            right_project_id=safe_right_project_id,
            evidence_refs=_redact_raw_context_refs(normalized_evidence_refs),
            shared_relationship_refs=_redact_raw_context_refs(
                shared_relationship_refs
            ),
            blockers=raw_context_blockers,
            compass_question=(
                "Compass cannot compare project bearings while raw prompt, "
                "transcript, free-form context, or provider-response payload "
                "is present in the difference inputs. Pass summarized refs "
                "and retry."
            ),
        )

    blockers = _project_difference_blockers(left, right, normalized_evidence_refs)
    if blockers:
        return ProjectDifferenceEvaluation(
            decision=ProjectDifferenceDecision.BLOCKED,
            left_project_id=safe_left_project_id,
            right_project_id=safe_right_project_id,
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
            left_project_id=safe_left_project_id,
            right_project_id=safe_right_project_id,
            evidence_refs=normalized_evidence_refs,
            difference_evidence=difference_evidence,
            shared_relationship_refs=shared_relationship_refs,
        )

    if left.project_id == right.project_id:
        return ProjectDifferenceEvaluation(
            decision=ProjectDifferenceDecision.SAME_PROJECT,
            left_project_id=safe_left_project_id,
            right_project_id=safe_right_project_id,
            evidence_refs=normalized_evidence_refs,
            shared_relationship_refs=shared_relationship_refs,
        )

    return ProjectDifferenceEvaluation(
        decision=ProjectDifferenceDecision.AMBIGUOUS,
        left_project_id=safe_left_project_id,
        right_project_id=safe_right_project_id,
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


def project_identity_candidate_from_definition(
    project: ProjectDefinition,
    *,
    mission_bearing: str,
    evidence_refs: Iterable[str],
    neighbors: Iterable[ProjectIdentityNeighbor] = (),
) -> ProjectIdentityCandidate:
    """Build a ProjectIdentityCandidate from an already-validated ProjectDefinition.

    The bounded body of work (context, artifacts, objectives, tasks, proof_trail)
    is forwarded so neighbor comparison can use richer identity evidence when a
    mission bearing collides with another project.
    """
    return ProjectIdentityCandidate(
        project_id=project.project_id,
        title=project.title,
        outcome=project.outcome,
        mission_bearing=mission_bearing,
        repo_refs=project.relationship_refs.repo_refs,
        venture_refs=project.relationship_refs.venture_refs,
        session_refs=project.relationship_refs.session_refs,
        evidence_refs=tuple(evidence_refs),
        context=project.context,
        artifacts=project.artifacts,
        objectives=project.objectives,
        tasks=project.tasks,
        proof_trail=project.proof_trail,
        neighbors=tuple(neighbors),
    )


def evaluate_project_identity(
    candidate: ProjectIdentityCandidate,
) -> ProjectIdentityEvaluation:
    """Decide whether a candidate is a complete, distinct project definition.

    Identity does not collapse merely because a candidate shares a repo path,
    venture, or session label with a neighbor — the candidate must also carry
    a distinguishing mission bearing. Shared refs without a distinguishing
    bearing surface as a Compass question rather than silently merging.

    Raw-context payload smuggled through scalar identity fields
    (``project_id``, ``title``, ``outcome``, ``mission_bearing``) or through
    relationship-ref / bounded body-of-work tuples fails closed BEFORE the
    neighbor-overlap comparison runs. Shared relationship refs that collide
    on raw-context payload are redacted to ``<redacted_raw_context>`` so the
    serialized result never preserves the raw prompt/transcript/free-form
    context payload.
    """
    blockers = _project_identity_blockers(candidate)
    safe_project_id = _redact_raw_context_scalar(candidate.project_id)
    safe_title = _redact_raw_context_scalar(candidate.title)
    safe_outcome = _redact_raw_context_scalar(candidate.outcome)
    safe_mission_bearing = _redact_raw_context_scalar(candidate.mission_bearing)
    safe_evidence_refs = _redact_raw_context_refs(candidate.evidence_refs)
    if blockers:
        return ProjectIdentityEvaluation(
            decision=ProjectIdentityDecision.BLOCKED,
            project_id=safe_project_id,
            title=safe_title,
            outcome=safe_outcome,
            mission_bearing=safe_mission_bearing,
            evidence_refs=safe_evidence_refs,
            blockers=blockers,
            compass_question=(
                "Compass needs complete project identity inputs before defining "
                "a project boundary."
            ),
        )

    (
        shared_repo_refs,
        shared_venture_refs,
        shared_session_refs,
        distinguishing,
        collapsing,
    ) = _project_identity_neighbor_overlap(candidate)

    safe_shared_repo_refs = _redact_raw_context_refs(shared_repo_refs)
    safe_shared_venture_refs = _redact_raw_context_refs(shared_venture_refs)
    safe_shared_session_refs = _redact_raw_context_refs(shared_session_refs)
    redacted_distinguishing = _redact_raw_context_refs(distinguishing)
    redacted_collapsing = _redact_raw_context_refs(collapsing)

    if collapsing:
        return ProjectIdentityEvaluation(
            decision=ProjectIdentityDecision.AMBIGUOUS,
            project_id=safe_project_id,
            title=safe_title,
            outcome=safe_outcome,
            mission_bearing=safe_mission_bearing,
            evidence_refs=safe_evidence_refs,
            shared_repo_refs=safe_shared_repo_refs,
            shared_venture_refs=safe_shared_venture_refs,
            shared_session_refs=safe_shared_session_refs,
            distinguishing_neighbors=redacted_distinguishing,
            collapsing_neighbors=redacted_collapsing,
            blockers=("project_identity_collapse_risk",),
            compass_question=(
                "Compass needs a distinguishing mission bearing before defining "
                "a project that shares repo, venture, or session refs with "
                f"{list(redacted_collapsing)}."
            ),
        )

    return ProjectIdentityEvaluation(
        decision=ProjectIdentityDecision.DEFINED,
        project_id=safe_project_id,
        title=safe_title,
        outcome=safe_outcome,
        mission_bearing=safe_mission_bearing,
        evidence_refs=safe_evidence_refs,
        shared_repo_refs=safe_shared_repo_refs,
        shared_venture_refs=safe_shared_venture_refs,
        shared_session_refs=safe_shared_session_refs,
        distinguishing_neighbors=redacted_distinguishing,
    )


def evaluate_project_bounds(
    project: ProjectDefinition,
    request: ProjectBoundsRequest,
) -> ProjectBoundsEvaluation:
    """Decide whether a multi-subject bounds request fits the project boundary.

    Builds on the reviewed project identity runtime: the request must name the
    same ``project_id`` as the reviewed ``ProjectDefinition`` and must carry
    its own evidence refs. Each ``ProjectScopeCandidate`` is evaluated through
    ``evaluate_project_scope`` and the per-subject decisions are aggregated:

    - any candidate ``BLOCKED`` -> bounds ``BLOCKED``.
    - any candidate ``AMBIGUOUS`` -> bounds ``AMBIGUOUS`` (Compass question).
    - all candidates ``IN_SCOPE`` -> bounds ``IN_SCOPE``.
    - all candidates ``OUT_OF_SCOPE`` -> bounds ``OUT_OF_SCOPE``.
    - mixed in/out -> bounds ``PARTIAL_SCOPE``.

    Shared repo/venture/session refs between the request envelope and the
    project's ``relationship_refs`` are surfaced rather than collapsed so that
    callers cannot silently infer the request has merged with the project.

    The result always serializes ``execution_authorized=False``.
    """
    request_blockers = _project_bounds_request_blockers(project, request)
    if request_blockers:
        return _bounds_result(
            ProjectBoundsDecision.BLOCKED,
            project,
            request,
            blockers=request_blockers,
            compass_question=(
                "Compass needs a valid project identity and evidence refs "
                "before deciding bounds."
            ),
        )

    if _has_raw_context_ref((request.request_ref,)) or (
        request.ambiguity_reason is not None
        and _has_raw_context_ref((request.ambiguity_reason,))
    ):
        return _bounds_result(
            ProjectBoundsDecision.BLOCKED,
            project,
            request,
            blockers=("raw_context_request_field_blocked",),
            compass_question=(
                "Compass cannot evaluate bounds while raw prompt, transcript, "
                "free-form context, conversation, or provider-response payload "
                "is present in the request_ref or ambiguity_reason. Pass "
                "summarized labels and retry."
            ),
        )

    if request.request_kind not in _BOUNDS_REQUEST_KINDS:
        return _bounds_result(
            ProjectBoundsDecision.AMBIGUOUS,
            project,
            request,
            blockers=("unknown_bounds_request_kind",),
            compass_question=(
                "Compass needs a known bounds request kind; received "
                f"{request.request_kind!r}."
            ),
        )

    if request.request_kind == "ambiguous":
        reason = request.ambiguity_reason or "request kind is ambiguous"
        return _bounds_result(
            ProjectBoundsDecision.AMBIGUOUS,
            project,
            request,
            blockers=("ambiguous_bounds_request",),
            compass_question=(
                f"Compass question: should request {request.request_ref!r} "
                f"be allowed for {project.project_id}? {reason}"
            ),
        )

    candidate_results = tuple(
        evaluate_project_scope(project, candidate) for candidate in request.candidates
    )
    candidate_decisions = tuple(
        {
            "subject_kind": result.subject_kind,
            "subject_ref": result.subject_ref,
            "decision": result.decision.value,
        }
        for result in candidate_results
    )

    in_scope_refs = tuple(
        result.subject_ref
        for result in candidate_results
        if result.decision is ProjectScopeDecision.IN_SCOPE
    )
    out_of_scope_refs = tuple(
        result.subject_ref
        for result in candidate_results
        if result.decision is ProjectScopeDecision.OUT_OF_SCOPE
    )
    ambiguous_refs = tuple(
        result.subject_ref
        for result in candidate_results
        if result.decision is ProjectScopeDecision.AMBIGUOUS
    )
    blocked_refs = tuple(
        result.subject_ref
        for result in candidate_results
        if result.decision is ProjectScopeDecision.BLOCKED
    )

    if blocked_refs:
        return _bounds_result(
            ProjectBoundsDecision.BLOCKED,
            project,
            request,
            in_scope_refs=in_scope_refs,
            out_of_scope_refs=out_of_scope_refs,
            ambiguous_refs=ambiguous_refs,
            blocked_refs=blocked_refs,
            candidate_decisions=candidate_decisions,
            blockers=("candidate_blocked",),
            compass_question=(
                "Compass cannot decide bounds while subjects "
                f"{list(blocked_refs)} are blocked."
            ),
        )

    if ambiguous_refs:
        return _bounds_result(
            ProjectBoundsDecision.AMBIGUOUS,
            project,
            request,
            in_scope_refs=in_scope_refs,
            out_of_scope_refs=out_of_scope_refs,
            ambiguous_refs=ambiguous_refs,
            candidate_decisions=candidate_decisions,
            blockers=("candidate_ambiguous",),
            compass_question=(
                "Compass needs clarification on subjects "
                f"{list(ambiguous_refs)} before deciding bounds."
            ),
        )

    if in_scope_refs and out_of_scope_refs:
        return _bounds_result(
            ProjectBoundsDecision.PARTIAL_SCOPE,
            project,
            request,
            in_scope_refs=in_scope_refs,
            out_of_scope_refs=out_of_scope_refs,
            candidate_decisions=candidate_decisions,
            compass_question=(
                "Compass observes mixed scope: "
                f"{list(in_scope_refs)} in-scope, "
                f"{list(out_of_scope_refs)} out-of-scope. Should the "
                "out-of-scope subjects be split off?"
            ),
        )

    if in_scope_refs:
        return _bounds_result(
            ProjectBoundsDecision.IN_SCOPE,
            project,
            request,
            in_scope_refs=in_scope_refs,
            candidate_decisions=candidate_decisions,
        )

    return _bounds_result(
        ProjectBoundsDecision.OUT_OF_SCOPE,
        project,
        request,
        out_of_scope_refs=out_of_scope_refs,
        candidate_decisions=candidate_decisions,
        compass_question=(
            "Compass question: should request "
            f"{request.request_ref!r} be redirected to a different project?"
        ),
    )


def _scope_result(
    decision: ProjectScopeDecision,
    candidate: ProjectScopeCandidate,
    *,
    matched_refs: tuple[str, ...] = (),
    blockers: tuple[str, ...] = (),
    compass_question: str | None = None,
    evidence_refs_override: tuple[str, ...] | None = None,
) -> ProjectScopeEvaluation:
    return ProjectScopeEvaluation(
        decision=decision,
        project_id=candidate.project_id,
        subject_kind=candidate.subject_kind,
        subject_ref=candidate.subject_ref,
        evidence_refs=(
            evidence_refs_override
            if evidence_refs_override is not None
            else candidate.evidence_refs
        ),
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
        source_project_id=_redact_raw_context_scalar(request.source_project_id),
        target_project_id=_redact_raw_context_scalar(request.target_project_id),
        reason_category=_redact_raw_context_scalar(request.reason_category),
        payload_type=_redact_raw_context_scalar(request.payload_type),
        payload_summary_refs=_redact_raw_context_refs(request.payload_summary_refs),
        evidence_refs=_redact_raw_context_refs(request.evidence_refs),
        approval_required=request.approval_required,
        approval_refs=_redact_raw_context_refs(request.approval_refs),
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
    if _is_raw_context_ref(request.reason_category):
        blockers.append("raw_context_reason_category_blocked")
    elif request.reason_category not in _HANDOFF_REASON_CATEGORIES:
        blockers.append("unknown_handoff_reason_category")
    if request.payload_type in _RAW_CONTEXT_PAYLOAD_TYPES:
        blockers.append("raw_context_payload_type_blocked")
    elif _is_raw_context_ref(request.payload_type):
        blockers.append("raw_context_payload_type_blocked")
    elif request.payload_type not in _HANDOFF_PAYLOAD_TYPES:
        blockers.append("unknown_handoff_payload_type")
    if request.source_project_id is not None and _is_raw_context_ref(
        request.source_project_id
    ):
        blockers.append("raw_context_source_project_id_blocked")
    if request.target_project_id is not None and _is_raw_context_ref(
        request.target_project_id
    ):
        blockers.append("raw_context_target_project_id_blocked")
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


def _bounds_result(
    decision: ProjectBoundsDecision,
    project: ProjectDefinition,
    request: ProjectBoundsRequest,
    *,
    in_scope_refs: tuple[str, ...] = (),
    out_of_scope_refs: tuple[str, ...] = (),
    ambiguous_refs: tuple[str, ...] = (),
    blocked_refs: tuple[str, ...] = (),
    candidate_decisions: tuple[Mapping[str, object], ...] = (),
    blockers: tuple[str, ...] = (),
    compass_question: str | None = None,
) -> ProjectBoundsEvaluation:
    return ProjectBoundsEvaluation(
        decision=decision,
        project_id=request.project_id,
        request_kind=request.request_kind,
        request_ref=_redact_raw_context_refs((request.request_ref,))[0],
        in_scope_refs=in_scope_refs,
        out_of_scope_refs=out_of_scope_refs,
        ambiguous_refs=ambiguous_refs,
        blocked_refs=blocked_refs,
        shared_relationship_refs=_redact_raw_context_refs(
            _project_bounds_shared_relationship_refs(project, request)
        ),
        evidence_refs=_redact_raw_context_refs(request.evidence_refs),
        candidate_decisions=candidate_decisions,
        blockers=blockers,
        compass_question=compass_question,
    )


def _project_bounds_request_blockers(
    project: ProjectDefinition,
    request: ProjectBoundsRequest,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if request.project_id is None:
        blockers.append("missing_request_project_id")
    elif request.project_id != project.project_id:
        blockers.append("project_identity_mismatch")
    if not request.candidates:
        blockers.append("missing_request_candidates")
    if not request.evidence_refs:
        blockers.append("missing_request_evidence_refs")
    if _has_raw_context_ref(request.evidence_refs):
        blockers.append("raw_context_evidence_ref_blocked")
    for candidate in request.candidates:
        if _has_raw_context_ref(candidate.evidence_refs):
            blockers.append("raw_context_candidate_evidence_ref_blocked")
            break
    return tuple(blockers)


def _project_bounds_shared_relationship_refs(
    project: ProjectDefinition,
    request: ProjectBoundsRequest,
) -> tuple[str, ...]:
    shared: set[str] = set()
    shared.update(
        set(request.repo_refs) & set(project.relationship_refs.repo_refs)
    )
    shared.update(
        set(request.venture_refs) & set(project.relationship_refs.venture_refs)
    )
    shared.update(
        set(request.session_refs) & set(project.relationship_refs.session_refs)
    )
    return tuple(sorted(shared))


def _project_identity_blockers(
    candidate: ProjectIdentityCandidate,
) -> tuple[str, ...]:
    blockers: list[str] = []
    for field_name in _PROJECT_IDENTITY_REQUIRED_TEXT_FIELDS:
        if getattr(candidate, field_name) is None:
            blockers.append(f"missing_{field_name}")
    if not candidate.repo_refs:
        blockers.append("missing_repo_refs")
    if not candidate.venture_refs:
        blockers.append("missing_venture_refs")
    if not candidate.evidence_refs:
        blockers.append("missing_evidence_refs")
    if _has_raw_context_ref(candidate.evidence_refs):
        blockers.append("raw_context_evidence_ref_blocked")
    for field_name in ("project_id", "title", "outcome", "mission_bearing"):
        value = getattr(candidate, field_name)
        if value is not None and _is_raw_context_ref(value):
            blockers.append(f"raw_context_{field_name}_blocked")
    for field_name in ("repo_refs", "venture_refs", "session_refs"):
        if _has_raw_context_ref(getattr(candidate, field_name)):
            blockers.append(f"raw_context_{field_name}_blocked")
    for field_name in _PROJECT_IDENTITY_BOUNDED_TUPLE_FIELDS:
        if _has_raw_context_ref(getattr(candidate, field_name)):
            blockers.append(f"raw_context_{field_name}_blocked")
    return tuple(blockers)


def _normalize_bearing_text(value: str | None) -> str:
    """Normalize bearing-like text so trivial variants do not slip past comparison.

    Lowercases, strips leading/trailing whitespace, collapses internal whitespace
    runs to single spaces, and trims surrounding punctuation. Used to detect
    case/formatting/punctuation collisions between candidate and neighbor
    mission bearings (and analogous bounded text fields).
    """
    if value is None:
        return ""
    normalized = _BEARING_WHITESPACE_RE.sub(" ", value.strip().lower())
    return normalized.strip(_BEARING_PUNCTUATION_STRIP).strip()


def _bounded_identity_distinguishes(
    candidate: ProjectIdentityCandidate,
    neighbor: ProjectIdentityNeighbor,
) -> bool:
    """Return True if candidate vs neighbor bounded identity evidence differs.

    Only fields populated on both sides participate. Text fields are compared
    after the same normalization used for mission bearings; tuple fields are
    compared as order-insensitive sets so storage order does not cause spurious
    distinction.
    """
    for field_name in _PROJECT_IDENTITY_BOUNDED_TEXT_FIELDS:
        candidate_value = getattr(candidate, field_name, None)
        neighbor_value = getattr(neighbor, field_name, None)
        if candidate_value is None or neighbor_value is None:
            continue
        if _normalize_bearing_text(candidate_value) != _normalize_bearing_text(
            neighbor_value
        ):
            return True

    for field_name in _PROJECT_IDENTITY_BOUNDED_TUPLE_FIELDS:
        candidate_value = getattr(candidate, field_name, ())
        neighbor_value = getattr(neighbor, field_name, ())
        if not candidate_value or not neighbor_value:
            continue
        if set(candidate_value) != set(neighbor_value):
            return True
    return False


def _project_identity_neighbor_overlap(
    candidate: ProjectIdentityCandidate,
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
]:
    candidate_repo = set(candidate.repo_refs)
    candidate_venture = set(candidate.venture_refs)
    candidate_session = set(candidate.session_refs)
    candidate_bearing = _normalize_bearing_text(candidate.mission_bearing)

    shared_repo: set[str] = set()
    shared_venture: set[str] = set()
    shared_session: set[str] = set()
    distinguishing: list[str] = []
    collapsing: list[str] = []
    seen_neighbors: set[str] = set()

    for neighbor in candidate.neighbors:
        if neighbor.project_id in seen_neighbors:
            continue
        n_repo = set(neighbor.repo_refs) & candidate_repo
        n_venture = set(neighbor.venture_refs) & candidate_venture
        n_session = set(neighbor.session_refs) & candidate_session
        if not (n_repo or n_venture or n_session):
            continue

        seen_neighbors.add(neighbor.project_id)
        shared_repo |= n_repo
        shared_venture |= n_venture
        shared_session |= n_session

        neighbor_bearing = _normalize_bearing_text(neighbor.mission_bearing)
        same_project_id = (
            candidate.project_id is not None
            and neighbor.project_id == candidate.project_id
        )
        same_bearing = neighbor_bearing == candidate_bearing
        bounded_distinguishes = _bounded_identity_distinguishes(candidate, neighbor)

        if same_project_id:
            collapsing.append(neighbor.project_id)
        elif not same_bearing:
            distinguishing.append(neighbor.project_id)
        elif bounded_distinguishes:
            distinguishing.append(neighbor.project_id)
        else:
            collapsing.append(neighbor.project_id)

    return (
        tuple(sorted(shared_repo)),
        tuple(sorted(shared_venture)),
        tuple(sorted(shared_session)),
        tuple(distinguishing),
        tuple(collapsing),
    )


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


def _project_difference_raw_context_blockers(
    left: ProjectDifferenceProfile,
    right: ProjectDifferenceProfile,
    evidence_refs: tuple[str, ...],
) -> tuple[str, ...]:
    """Detect raw-context bleed across the difference inputs.

    Mirrors the scope/bounds-layer pattern: if the difference evidence_refs or
    any profile text/ref field carries a raw-prompt / raw-transcript /
    free-form-context / provider-response / embedded-newline payload, the
    runtime must fail closed BEFORE comparing the two profiles, and the
    serialized result must not preserve the raw payload. Includes the scalar
    ``project_id`` on each side so a raw payload smuggled through the id
    label is blocked before it can be copied into the difference result.
    """
    blockers: list[str] = []
    if _has_raw_context_ref(evidence_refs):
        blockers.append("raw_context_evidence_ref_blocked")
    for side_name, profile in (("left", left), ("right", right)):
        if profile.project_id is not None and _is_raw_context_ref(profile.project_id):
            blockers.append(f"raw_context_in_{side_name}_project_id_blocked")
        for field in _PROJECT_DIFFERENCE_RAW_CONTEXT_SCAN_FIELDS:
            value = _difference_field_tuple(getattr(profile, field))
            if _has_raw_context_ref(value):
                blockers.append(f"raw_context_in_{side_name}_{field}_blocked")
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


def _redact_raw_context_refs(refs: Iterable[str]) -> tuple[str, ...]:
    """Replace each raw-context ref with a redaction marker.

    Safe (non-raw) refs pass through unchanged so a serialized scope/bounds
    result still carries the legitimate evidence trail while never preserving
    the raw prompt/transcript/free-form-context payload that triggered the
    block.
    """
    return tuple(
        "<redacted_raw_context>" if _is_raw_context_ref(ref) else ref
        for ref in refs
    )


def _redact_raw_context_scalar(value: str | None) -> str | None:
    """Replace a single raw-context scalar with a redaction marker.

    ``None`` is preserved so optional-id fields stay nullable. Safe scalars
    pass through unchanged so identity/difference/handoff results still
    carry legitimate project ids, titles, outcomes, bearings, reason
    categories, and payload types without preserving any raw-prompt /
    raw-transcript / free-form-context payload that smuggled into a scalar
    metadata field.
    """
    if value is None:
        return None
    if _is_raw_context_ref(value):
        return "<redacted_raw_context>"
    return value


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


def project_identity_neighbor_dict_keys() -> tuple[str, ...]:
    """Expose the stable identity-neighbor serialization shape."""
    return _PROJECT_IDENTITY_NEIGHBOR_KEYS


def project_identity_candidate_dict_keys() -> tuple[str, ...]:
    """Expose the stable identity-candidate serialization shape."""
    return _PROJECT_IDENTITY_CANDIDATE_KEYS


def project_identity_result_dict_keys() -> tuple[str, ...]:
    """Expose the stable identity-evaluation serialization shape."""
    return _PROJECT_IDENTITY_RESULT_DICT_KEYS


def project_bounds_request_dict_keys() -> tuple[str, ...]:
    """Expose the stable bounds-request serialization shape."""
    return _PROJECT_BOUNDS_REQUEST_KEYS


def project_bounds_result_dict_keys() -> tuple[str, ...]:
    """Expose the stable bounds-evaluation serialization shape."""
    return _PROJECT_BOUNDS_RESULT_DICT_KEYS


def project_bounds_request_kinds() -> frozenset[str]:
    """Expose the known bounds request kinds as a frozen set."""
    return frozenset(_BOUNDS_REQUEST_KINDS)
