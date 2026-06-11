"""Pure workflow intelligence records for V2.5 backend capacity planning.

Callers provide task, lane, and result metadata. This module performs no IO,
does not dispatch workers, and returns deterministic display-safe records.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class WorkflowTaskReadiness(Enum):
    READY = "ready"
    BLOCKED = "blocked"


class LaneCapacityStatus(Enum):
    AVAILABLE = "available"
    FULL = "full"
    OVER_CAPACITY = "over_capacity"


class TaskResultOutcome(Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class FailureRecoveryAction(Enum):
    NONE = "none"
    RETRY = "retry"
    REPLAN = "replan"
    UNBLOCK_DEPENDENCY = "unblock_dependency"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class WorkflowTaskDefinition:
    task_id: str
    lane: str
    title: str = ""
    depends_on: tuple[str, ...] = field(default_factory=tuple)
    capacity_units: int = 1
    priority: int = 0

    def __post_init__(self) -> None:
        _require_non_empty(self.task_id, "task_id")
        _require_non_empty(self.lane, "lane")
        if not isinstance(self.capacity_units, int) or self.capacity_units < 1:
            raise ValueError("capacity_units must be a positive integer")
        if not isinstance(self.priority, int):
            raise ValueError("priority must be an integer")


@dataclass(frozen=True)
class WorkflowTaskPlan:
    task_ref: str
    lane: str
    title: str
    dependency_refs: tuple[str, ...]
    readiness: WorkflowTaskReadiness
    sequence: int | None
    capacity_units: int
    blocking_refs: tuple[str, ...] = ()
    reason_tags: tuple[str, ...] = ()

    def to_display_dict(self) -> dict[str, object]:
        return {
            "task_ref": _safe_ref(self.task_ref, "task:unsafe"),
            "lane": _display_safe_text(self.lane),
            "title": _display_safe_text(self.title),
            "dependency_refs": tuple(
                _safe_ref(ref, "task:unsafe") for ref in self.dependency_refs
            ),
            "readiness": self.readiness.value,
            "sequence": self.sequence,
            "capacity_units": self.capacity_units,
            "blocking_refs": tuple(
                _safe_ref(ref, "task:unsafe") for ref in self.blocking_refs
            ),
            "reason_tags": tuple(_display_safe_text(tag) for tag in self.reason_tags),
        }


@dataclass(frozen=True)
class LaneCapacitySummary:
    lane: str
    capacity_limit: int
    active_units: int
    planned_units: int
    blocked_count: int
    status: LaneCapacityStatus

    @property
    def available_units(self) -> int:
        return max(0, self.capacity_limit - self.active_units - self.planned_units)

    def to_display_dict(self) -> dict[str, object]:
        return {
            "lane": _display_safe_text(self.lane),
            "capacity_limit": self.capacity_limit,
            "active_units": self.active_units,
            "planned_units": self.planned_units,
            "available_units": self.available_units,
            "blocked_count": self.blocked_count,
            "status": self.status.value,
        }


@dataclass(frozen=True)
class BlockedLaneSummary:
    lane: str
    blocked_count: int
    blocking_refs: tuple[str, ...]
    reason_tags: tuple[str, ...]

    def to_display_dict(self) -> dict[str, object]:
        return {
            "lane": _display_safe_text(self.lane),
            "blocked_count": self.blocked_count,
            "blocking_refs": tuple(
                _safe_ref(ref, "task:unsafe") for ref in self.blocking_refs
            ),
            "reason_tags": tuple(_display_safe_text(tag) for tag in self.reason_tags),
        }


@dataclass(frozen=True)
class TaskResultInput:
    task_id: str
    lane: str
    status: str
    summary: str = ""
    transcript: str = ""
    log_excerpt: str = ""
    artifact_refs: tuple[str, ...] = ()
    failure_kind: str = ""
    retryable: bool | None = None
    duration_seconds: int | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.task_id, "task_id")
        _require_non_empty(self.lane, "lane")
        if self.duration_seconds is not None and (
            not isinstance(self.duration_seconds, int) or self.duration_seconds < 0
        ):
            raise ValueError("duration_seconds must be a non-negative integer or None")


@dataclass(frozen=True)
class TaskResultSummary:
    task_ref: str
    lane: str
    outcome: TaskResultOutcome
    headline: str
    artifact_refs: tuple[str, ...]
    failure_kind: str
    retryable: bool
    duration_seconds: int | None
    reason_tags: tuple[str, ...]

    def to_display_dict(self) -> dict[str, object]:
        return {
            "task_ref": _safe_ref(self.task_ref, "task:unsafe"),
            "lane": _display_safe_text(self.lane),
            "outcome": self.outcome.value,
            "headline": _display_safe_text(self.headline),
            "artifact_refs": tuple(_safe_ref(ref, "artifact:unsafe") for ref in self.artifact_refs),
            "failure_kind": _display_safe_text(self.failure_kind),
            "retryable": self.retryable,
            "duration_seconds": self.duration_seconds,
            "reason_tags": tuple(_display_safe_text(tag) for tag in self.reason_tags),
        }


@dataclass(frozen=True)
class FailureRecoveryRecommendation:
    task_ref: str
    action: FailureRecoveryAction
    reason_tags: tuple[str, ...]
    message: str

    def to_display_dict(self) -> dict[str, object]:
        return {
            "task_ref": _safe_ref(self.task_ref, "task:unsafe"),
            "action": self.action.value,
            "reason_tags": tuple(_display_safe_text(tag) for tag in self.reason_tags),
            "message": _display_safe_text(self.message),
        }


@dataclass(frozen=True)
class WorkflowIntelligenceReport:
    task_plans: tuple[WorkflowTaskPlan, ...]
    lane_capacity: tuple[LaneCapacitySummary, ...]
    blocked_lanes: tuple[BlockedLaneSummary, ...]

    def to_display_dict(self) -> dict[str, object]:
        return {
            "task_plans": tuple(plan.to_display_dict() for plan in self.task_plans),
            "lane_capacity": tuple(summary.to_display_dict() for summary in self.lane_capacity),
            "blocked_lanes": tuple(summary.to_display_dict() for summary in self.blocked_lanes),
        }


def plan_workflow_tasks(
    tasks: Iterable[WorkflowTaskDefinition],
    *,
    lane_capacity_limits: dict[str, int] | None = None,
    active_units_by_lane: dict[str, int] | None = None,
    completed_task_ids: Iterable[str] = (),
) -> WorkflowIntelligenceReport:
    """Build dependency-aware task plans constrained by caller-supplied capacity."""
    task_list = tuple(tasks)
    completed = frozenset(str(task_id) for task_id in completed_task_ids)
    limits = lane_capacity_limits or {}
    active = active_units_by_lane or {}

    ordered_tasks = _topological_task_order(task_list, completed)
    planned_units_by_lane: dict[str, int] = {}
    plans: list[WorkflowTaskPlan] = []
    sequence = 1

    for task in ordered_tasks:
        missing = tuple(dep for dep in task.depends_on if dep not in completed)
        blocking_refs = tuple(dep for dep in missing if dep not in {p.task_ref for p in plans if p.sequence})
        reason_tags: list[str] = []
        if blocking_refs:
            reason_tags.append("dependency_blocked")

        lane_limit = max(0, int(limits.get(task.lane, 1)))
        lane_active = max(0, int(active.get(task.lane, 0)))
        lane_planned = planned_units_by_lane.get(task.lane, 0)
        capacity_available = lane_active + lane_planned + task.capacity_units <= lane_limit
        if not capacity_available:
            reason_tags.append("lane_capacity_exhausted")

        if reason_tags:
            plans.append(
                WorkflowTaskPlan(
                    task_ref=task.task_id,
                    lane=task.lane,
                    title=task.title,
                    dependency_refs=tuple(sorted(task.depends_on)),
                    readiness=WorkflowTaskReadiness.BLOCKED,
                    sequence=None,
                    capacity_units=task.capacity_units,
                    blocking_refs=tuple(sorted(blocking_refs)),
                    reason_tags=tuple(reason_tags),
                )
            )
            continue

        planned_units_by_lane[task.lane] = lane_planned + task.capacity_units
        plans.append(
            WorkflowTaskPlan(
                task_ref=task.task_id,
                lane=task.lane,
                title=task.title,
                dependency_refs=tuple(sorted(task.depends_on)),
                readiness=WorkflowTaskReadiness.READY,
                sequence=sequence,
                capacity_units=task.capacity_units,
                reason_tags=("dependency_ready", "capacity_available"),
            )
        )
        sequence += 1

    return WorkflowIntelligenceReport(
        task_plans=tuple(sorted(plans, key=lambda plan: (plan.sequence is None, plan.sequence or 0, plan.task_ref))),
        lane_capacity=summarize_lane_capacity(
            plans,
            lane_capacity_limits=limits,
            active_units_by_lane=active,
        ),
        blocked_lanes=summarize_blocked_lanes(plans),
    )


def summarize_lane_capacity(
    plans: Iterable[WorkflowTaskPlan],
    *,
    lane_capacity_limits: dict[str, int] | None = None,
    active_units_by_lane: dict[str, int] | None = None,
) -> tuple[LaneCapacitySummary, ...]:
    limits = lane_capacity_limits or {}
    active = active_units_by_lane or {}
    plan_list = tuple(plans)
    lanes = sorted({*limits.keys(), *active.keys(), *(plan.lane for plan in plan_list)})
    summaries: list[LaneCapacitySummary] = []
    for lane in lanes:
        capacity_limit = max(0, int(limits.get(lane, 1)))
        active_units = max(0, int(active.get(lane, 0)))
        planned_units = sum(
            plan.capacity_units
            for plan in plan_list
            if plan.lane == lane and plan.readiness is WorkflowTaskReadiness.READY
        )
        blocked_count = sum(
            1
            for plan in plan_list
            if plan.lane == lane and plan.readiness is WorkflowTaskReadiness.BLOCKED
        )
        used = active_units + planned_units
        if used > capacity_limit:
            status = LaneCapacityStatus.OVER_CAPACITY
        elif used == capacity_limit:
            status = LaneCapacityStatus.FULL
        else:
            status = LaneCapacityStatus.AVAILABLE
        summaries.append(
            LaneCapacitySummary(
                lane=lane,
                capacity_limit=capacity_limit,
                active_units=active_units,
                planned_units=planned_units,
                blocked_count=blocked_count,
                status=status,
            )
        )
    return tuple(summaries)


def summarize_blocked_lanes(
    plans: Iterable[WorkflowTaskPlan],
) -> tuple[BlockedLaneSummary, ...]:
    blocked = [plan for plan in plans if plan.readiness is WorkflowTaskReadiness.BLOCKED]
    lanes = sorted({plan.lane for plan in blocked})
    summaries: list[BlockedLaneSummary] = []
    for lane in lanes:
        lane_plans = [plan for plan in blocked if plan.lane == lane]
        summaries.append(
            BlockedLaneSummary(
                lane=lane,
                blocked_count=len(lane_plans),
                blocking_refs=tuple(sorted({ref for plan in lane_plans for ref in plan.blocking_refs})),
                reason_tags=tuple(sorted({tag for plan in lane_plans for tag in plan.reason_tags})),
            )
        )
    return tuple(summaries)


def ingest_task_results(
    results: Iterable[TaskResultInput],
) -> tuple[TaskResultSummary, ...]:
    """Normalize worker-reported task results into display-safe summaries."""
    summaries = [_summarize_task_result(result) for result in results]
    return tuple(sorted(summaries, key=lambda summary: (summary.lane, summary.task_ref)))


def recommend_failure_recovery(
    result: TaskResultSummary,
) -> FailureRecoveryRecommendation:
    """Recommend deterministic recovery guidance without dispatching anything."""
    if result.outcome is TaskResultOutcome.SUCCEEDED:
        return FailureRecoveryRecommendation(
            task_ref=result.task_ref,
            action=FailureRecoveryAction.NONE,
            reason_tags=("task_succeeded",),
            message="No recovery action is needed.",
        )
    if result.outcome is TaskResultOutcome.BLOCKED or result.failure_kind == "dependency":
        return FailureRecoveryRecommendation(
            task_ref=result.task_ref,
            action=FailureRecoveryAction.UNBLOCK_DEPENDENCY,
            reason_tags=("dependency_blocked",),
            message="Resolve the blocking dependency before rerunning the task.",
        )
    if result.retryable:
        return FailureRecoveryRecommendation(
            task_ref=result.task_ref,
            action=FailureRecoveryAction.RETRY,
            reason_tags=("retryable_failure", result.failure_kind or "failure"),
            message="Retry after preserving the normalized failure summary.",
        )
    if result.failure_kind in {"capacity", "planning"}:
        return FailureRecoveryRecommendation(
            task_ref=result.task_ref,
            action=FailureRecoveryAction.REPLAN,
            reason_tags=(f"{result.failure_kind}_failure",),
            message="Replan lane capacity and dependencies before retrying.",
        )
    return FailureRecoveryRecommendation(
        task_ref=result.task_ref,
        action=FailureRecoveryAction.ESCALATE,
        reason_tags=("non_retryable_failure", result.failure_kind or "failure"),
        message="Escalate with sanitized evidence references and no raw logs.",
    )


def _summarize_task_result(result: TaskResultInput) -> TaskResultSummary:
    outcome = _normalize_outcome(result.status)
    failure_kind = _normalize_failure_kind(result.failure_kind, outcome)
    retryable = _normalize_retryable(result.retryable, outcome, failure_kind)
    headline = _headline_for_result(result, outcome)
    reason_tags = [f"outcome_{outcome.value}"]
    if failure_kind:
        reason_tags.append(f"failure_{failure_kind}")
    if retryable:
        reason_tags.append("retryable")

    return TaskResultSummary(
        task_ref=result.task_id,
        lane=result.lane,
        outcome=outcome,
        headline=headline,
        artifact_refs=tuple(sorted({_safe_ref(ref, "artifact:unsafe") for ref in result.artifact_refs})),
        failure_kind=failure_kind,
        retryable=retryable,
        duration_seconds=result.duration_seconds,
        reason_tags=tuple(reason_tags),
    )


def _topological_task_order(
    tasks: tuple[WorkflowTaskDefinition, ...],
    completed: frozenset[str],
) -> tuple[WorkflowTaskDefinition, ...]:
    remaining = {task.task_id: task for task in tasks}
    ordered: list[WorkflowTaskDefinition] = []
    available = set(completed)

    while remaining:
        ready = [
            task
            for task in remaining.values()
            if all(dep in available for dep in task.depends_on if dep in remaining or dep in completed)
        ]
        if not ready:
            ordered.extend(sorted(remaining.values(), key=_task_sort_key))
            break
        for task in sorted(ready, key=_task_sort_key):
            ordered.append(task)
            available.add(task.task_id)
            remaining.pop(task.task_id)
    return tuple(ordered)


def _task_sort_key(task: WorkflowTaskDefinition) -> tuple[int, str, str]:
    return (-task.priority, task.lane, task.task_id)


def _headline_for_result(result: TaskResultInput, outcome: TaskResultOutcome) -> str:
    summary = _display_safe_text(result.summary)
    if summary and summary != "[redacted]":
        return summary
    if result.transcript.strip() or result.log_excerpt.strip():
        return f"Task {outcome.value}; raw execution details redacted."
    return f"Task {outcome.value}."


def _normalize_outcome(status: str) -> TaskResultOutcome:
    clean = status.strip().lower().replace("-", "_")
    if clean in {"success", "succeeded", "complete", "completed", "pass", "passed"}:
        return TaskResultOutcome.SUCCEEDED
    if clean in {"fail", "failed", "failure", "error", "errored"}:
        return TaskResultOutcome.FAILED
    if clean in {"blocked", "waiting", "dependency_blocked"}:
        return TaskResultOutcome.BLOCKED
    if clean in {"cancelled", "canceled", "aborted"}:
        return TaskResultOutcome.CANCELLED
    return TaskResultOutcome.UNKNOWN


def _normalize_failure_kind(
    failure_kind: str,
    outcome: TaskResultOutcome,
) -> str:
    clean = _display_safe_text(failure_kind).strip().lower().replace("-", "_").replace(" ", "_")
    if clean == "[redacted]":
        return "redacted"
    if clean in {"dependency", "capacity", "timeout", "validation", "planning", "redacted"}:
        return clean
    if outcome is TaskResultOutcome.BLOCKED:
        return "dependency"
    if outcome is TaskResultOutcome.FAILED:
        return "unknown"
    return ""


def _normalize_retryable(
    retryable: bool | None,
    outcome: TaskResultOutcome,
    failure_kind: str,
) -> bool:
    if retryable is not None:
        return bool(retryable)
    if outcome is not TaskResultOutcome.FAILED:
        return False
    return failure_kind in {"capacity", "timeout", "unknown"}


def _safe_ref(value: str, fallback: str) -> str:
    clean = str(value).strip()
    if not clean:
        return fallback
    if _looks_unsafe(clean):
        digest = hashlib.sha256(clean.encode("utf-8")).hexdigest()[:10]
        return f"{fallback}:{digest}"
    return clean


def _display_safe_text(value: str | None) -> str:
    if value is None:
        return ""
    clean = str(value).strip()
    if _looks_unsafe(clean):
        return "[redacted]"
    return clean


def _looks_unsafe(value: str) -> bool:
    return bool(
        re.search(
            r"(?i)(?:[A-Z]:\\|\\\\[^\\\s]+\\[^\\\s]+\\|/(?:Users|home|var|tmp|mnt|Volumes)/|"
            r"\n|traceback|exception:|api[_-]?key|secret|token|password|"
            r"sk-(?:proj-)?[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{20,}|"
            r"github_pat_[A-Za-z0-9_]{20,}|"
            r"(?:raw|full|complete)\s+(?:prompt|transcript|content|log)\s*:|"
            r"(?:provider|model)\s+(?:response|output)\s*:)",
            value,
        )
    )


def _require_non_empty(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must not be empty")
