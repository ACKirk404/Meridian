"""Display-safe Prime/Compass decision transparency records.

This module is pure backend projection logic: no model calls, no IO, and no
execution authority. It turns already-known decision facts into deterministic
records suitable for UI or CLI display.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping

from .evidence_safety import EvidenceSafetyStatus, scan_evidence_artifact


DISPLAY_TEXT_MAX = 160


class TransparencyStatus(Enum):
    COMPLETE = "complete"
    WARNING = "warning"
    BLOCKED = "blocked"


class EdgeKind(Enum):
    INTENT = "intent"
    DEPENDS_ON = "depends_on"
    BLOCKED_BY = "blocked_by"
    EVIDENCED_BY = "evidenced_by"


class EdgeStatus(Enum):
    ACTIVE = "active"
    SATISFIED = "satisfied"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class DriftStatus(Enum):
    ALIGNED = "aligned"
    DRIFT = "drift"
    MISSING_BASELINE = "missing_baseline"
    MISSING_CURRENT = "missing_current"


class ProjectHealth(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class ProjectTrajectory(Enum):
    ACCELERATING = "accelerating"
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    STALLED = "stalled"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class EvidenceRef:
    """A stable, display-safe pointer to evidence without evidence body text."""

    ref_id: str
    label: str = ""

    def to_display_dict(self) -> dict[str, str]:
        return {
            "ref_id": _safe_id(self.ref_id, fallback="evidence:unsafe-id"),
            "label": _safe_text(self.label or self.ref_id),
        }


@dataclass(frozen=True)
class EvidenceBackedRationale:
    rationale: str
    evidence_refs: tuple[EvidenceRef, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def status(self) -> TransparencyStatus:
        if self.evidence_refs and not self.warnings:
            return TransparencyStatus.COMPLETE
        return TransparencyStatus.WARNING

    def to_display_dict(self) -> dict[str, object]:
        warnings = list(self.warnings)
        if not self.evidence_refs:
            _append_unique(warnings, "missing_evidence")

        rationale, safety_warnings = _safe_text_with_warnings(self.rationale)
        for warning in safety_warnings:
            _append_unique(warnings, warning)

        return {
            "status": TransparencyStatus.COMPLETE.value if not warnings else TransparencyStatus.WARNING.value,
            "rationale": rationale,
            "evidence_refs": tuple(ref.to_display_dict() for ref in self.evidence_refs),
            "warnings": tuple(warnings),
        }


@dataclass(frozen=True)
class IntentDependencyEdge:
    source_ref: str
    target_ref: str
    kind: EdgeKind
    status: EdgeStatus = EdgeStatus.ACTIVE
    evidence_refs: tuple[EvidenceRef, ...] = ()
    label: str = ""
    warnings: tuple[str, ...] = ()

    def to_display_dict(self) -> dict[str, object]:
        warnings = list(self.warnings)
        label, safety_warnings = _safe_text_with_warnings(self.label)
        for warning in safety_warnings:
            _append_unique(warnings, warning)

        return {
            "source_ref": _safe_id(self.source_ref, fallback="edge:unsafe-source"),
            "target_ref": _safe_id(self.target_ref, fallback="edge:unsafe-target"),
            "kind": self.kind.value,
            "status": self.status.value,
            "label": label,
            "evidence_refs": tuple(ref.to_display_dict() for ref in self.evidence_refs),
            "warnings": tuple(warnings),
        }


@dataclass(frozen=True)
class ObjectiveDriftAlert:
    status: DriftStatus
    expected_objective_refs: tuple[str, ...]
    current_objective_refs: tuple[str, ...]
    missing_refs: tuple[str, ...] = ()
    added_refs: tuple[str, ...] = ()
    warning: str = ""

    @property
    def has_alert(self) -> bool:
        return self.status is not DriftStatus.ALIGNED

    def to_display_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "has_alert": self.has_alert,
            "expected_objective_refs": tuple(_safe_id(ref, "objective:unsafe") for ref in self.expected_objective_refs),
            "current_objective_refs": tuple(_safe_id(ref, "objective:unsafe") for ref in self.current_objective_refs),
            "missing_refs": tuple(_safe_id(ref, "objective:unsafe") for ref in self.missing_refs),
            "added_refs": tuple(_safe_id(ref, "objective:unsafe") for ref in self.added_refs),
            "warning": _safe_text(self.warning),
        }


@dataclass(frozen=True)
class ProjectHealthTrajectory:
    project_ref: str
    health: ProjectHealth
    trajectory: ProjectTrajectory
    blocker_count: int = 0
    warning_count: int = 0
    stale_dependency_count: int = 0
    evidence_refs: tuple[EvidenceRef, ...] = ()

    def to_display_dict(self) -> dict[str, object]:
        return {
            "project_ref": _safe_id(self.project_ref, fallback="project:unsafe"),
            "health": self.health.value,
            "trajectory": self.trajectory.value,
            "blocker_count": max(0, int(self.blocker_count)),
            "warning_count": max(0, int(self.warning_count)),
            "stale_dependency_count": max(0, int(self.stale_dependency_count)),
            "evidence_refs": tuple(ref.to_display_dict() for ref in self.evidence_refs),
        }


@dataclass(frozen=True)
class NextActionRationale:
    action_ref: str
    action_label: str
    decision_label: str
    rationale: EvidenceBackedRationale
    edges: tuple[IntentDependencyEdge, ...] = ()
    drift_alert: ObjectiveDriftAlert | None = None
    health: ProjectHealthTrajectory | None = None
    warnings: tuple[str, ...] = ()
    execution_authorized: bool = False

    def to_display_dict(self) -> dict[str, object]:
        rationale_display = self.rationale.to_display_dict()
        warnings = list(self.warnings)
        for warning in rationale_display["warnings"]:
            _append_unique(warnings, str(warning))
        if self.drift_alert and self.drift_alert.has_alert:
            _append_unique(warnings, "objective_drift")

        action_label, action_warnings = _safe_text_with_warnings(self.action_label)
        decision_label, decision_warnings = _safe_text_with_warnings(self.decision_label)
        for warning in (*action_warnings, *decision_warnings):
            _append_unique(warnings, warning)

        status = TransparencyStatus.COMPLETE
        if warnings:
            status = TransparencyStatus.WARNING
        if self.health and self.health.health is ProjectHealth.BLOCKED:
            status = TransparencyStatus.BLOCKED

        return {
            "status": status.value,
            "action_ref": _safe_id(self.action_ref, fallback="action:unsafe"),
            "action_label": action_label,
            "decision_label": decision_label,
            "rationale": rationale_display,
            "edges": tuple(edge.to_display_dict() for edge in self.edges),
            "drift_alert": None if self.drift_alert is None else self.drift_alert.to_display_dict(),
            "health": None if self.health is None else self.health.to_display_dict(),
            "warnings": tuple(warnings),
            "execution_authorized": False,
        }


def build_evidence_backed_rationale(
    rationale: str,
    evidence_refs: Iterable[str | EvidenceRef],
) -> EvidenceBackedRationale:
    return EvidenceBackedRationale(
        rationale=rationale,
        evidence_refs=tuple(_coerce_evidence_ref(ref) for ref in evidence_refs),
    )


def build_next_action_rationale(
    *,
    action_ref: str,
    action_label: str,
    decision_label: str,
    rationale: str,
    evidence_refs: Iterable[str | EvidenceRef],
    edges: Iterable[IntentDependencyEdge] = (),
    drift_alert: ObjectiveDriftAlert | None = None,
    health: ProjectHealthTrajectory | None = None,
) -> NextActionRationale:
    return NextActionRationale(
        action_ref=action_ref,
        action_label=action_label,
        decision_label=decision_label,
        rationale=build_evidence_backed_rationale(rationale, evidence_refs),
        edges=tuple(edges),
        drift_alert=drift_alert,
        health=health,
    )


def detect_objective_drift(
    expected_objective_refs: Iterable[str],
    current_objective_refs: Iterable[str],
) -> ObjectiveDriftAlert:
    expected = _stable_unique_safe_ids(expected_objective_refs, fallback="objective:unsafe-expected")
    current = _stable_unique_safe_ids(current_objective_refs, fallback="objective:unsafe-current")

    if not expected:
        status = DriftStatus.MISSING_BASELINE
        warning = "objective baseline is missing"
    elif not current:
        status = DriftStatus.MISSING_CURRENT
        warning = "current objectives are missing"
    else:
        missing = tuple(ref for ref in expected if ref not in current)
        added = tuple(ref for ref in current if ref not in expected)
        if missing or added:
            status = DriftStatus.DRIFT
            warning = "current objectives differ from the reviewed baseline"
        else:
            status = DriftStatus.ALIGNED
            warning = ""
        return ObjectiveDriftAlert(
            status=status,
            expected_objective_refs=expected,
            current_objective_refs=current,
            missing_refs=missing,
            added_refs=added,
            warning=warning,
        )

    return ObjectiveDriftAlert(
        status=status,
        expected_objective_refs=expected,
        current_objective_refs=current,
        missing_refs=expected if status is DriftStatus.MISSING_CURRENT else (),
        warning=warning,
    )


def label_project_health(
    *,
    project_ref: str,
    blocker_count: int = 0,
    warning_count: int = 0,
    stale_dependency_count: int = 0,
    completed_step_count: int = 0,
    active_step_count: int = 0,
    evidence_refs: Iterable[str | EvidenceRef] = (),
) -> ProjectHealthTrajectory:
    blockers = max(0, int(blocker_count))
    warnings = max(0, int(warning_count))
    stale = max(0, int(stale_dependency_count))
    completed = max(0, int(completed_step_count))
    active = max(0, int(active_step_count))

    if blockers:
        health = ProjectHealth.BLOCKED
        trajectory = ProjectTrajectory.STALLED
    elif stale:
        health = ProjectHealth.DEGRADED
        trajectory = ProjectTrajectory.AT_RISK
    elif warnings:
        health = ProjectHealth.DEGRADED
        trajectory = ProjectTrajectory.ON_TRACK if active else ProjectTrajectory.AT_RISK
    elif completed > active and active > 0:
        health = ProjectHealth.HEALTHY
        trajectory = ProjectTrajectory.ACCELERATING
    elif active or completed:
        health = ProjectHealth.HEALTHY
        trajectory = ProjectTrajectory.ON_TRACK
    else:
        health = ProjectHealth.UNKNOWN
        trajectory = ProjectTrajectory.UNKNOWN

    return ProjectHealthTrajectory(
        project_ref=project_ref,
        health=health,
        trajectory=trajectory,
        blocker_count=blockers,
        warning_count=warnings,
        stale_dependency_count=stale,
        evidence_refs=tuple(_coerce_evidence_ref(ref) for ref in evidence_refs),
    )


def build_dependency_graph_display(
    edges: Iterable[IntentDependencyEdge],
) -> tuple[Mapping[str, object], ...]:
    return tuple(edge.to_display_dict() for edge in edges)


def _coerce_evidence_ref(ref: str | EvidenceRef) -> EvidenceRef:
    if isinstance(ref, EvidenceRef):
        return ref
    return EvidenceRef(ref_id=str(ref))


def _safe_text(value: object, fallback: str = "[redacted]") -> str:
    text, _warnings = _safe_text_with_warnings(value, fallback=fallback)
    return text


def _safe_text_with_warnings(value: object, fallback: str = "[redacted]") -> tuple[str, tuple[str, ...]]:
    if value is None:
        return "", ()

    text = _collapse_whitespace(str(value))
    if not text:
        return "", ()

    proof = scan_evidence_artifact("display:text", text)
    warnings: list[str] = []
    if proof.status is EvidenceSafetyStatus.FAIL or _looks_like_raw_model_prose(text):
        for finding in proof.findings:
            _append_unique(warnings, f"unsafe_{finding.category.value}")
        if _looks_like_raw_model_prose(text):
            _append_unique(warnings, "unsafe_raw_model_prose")
        return fallback, tuple(warnings)

    if len(text) > DISPLAY_TEXT_MAX:
        return f"{text[: DISPLAY_TEXT_MAX - 3].rstrip()}...", ()
    return text, ()


def _safe_id(value: object, fallback: str) -> str:
    text = _collapse_whitespace(str(value or ""))
    if not text:
        return fallback
    proof = scan_evidence_artifact("display:id", text)
    if proof.status is EvidenceSafetyStatus.FAIL or _looks_like_raw_model_prose(text):
        return fallback
    return text[:DISPLAY_TEXT_MAX]


def _stable_unique_safe_ids(values: Iterable[str], fallback: str) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for index, value in enumerate(values, start=1):
        safe = _safe_id(value, fallback=f"{fallback}-{index}")
        if safe not in seen:
            seen.add(safe)
            out.append(safe)
    return tuple(out)


def _looks_like_raw_model_prose(text: str) -> bool:
    return bool(
        re.search(
            r"(?i)\b("
            r"as an ai language model|"
            r"provider response|"
            r"model output|"
            r"raw completion|"
            r"assistant message|"
            r"chain[- ]of[- ]thought"
            r")\b",
            text,
        )
    )


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)
