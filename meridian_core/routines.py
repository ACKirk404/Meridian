"""Backend routine authority for Meridian V2.

This module owns routine definitions, enable/disable state, and non-executable
run plans. It does not schedule automation, execute workflows, mutate queues,
call providers, or wire UI controls.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable


SHORT_TEXT_MAX = 160
SUMMARY_MAX = 420
SAFE_REF_SCHEMES = (
    "goal://",
    "proof://",
    "routine://",
    "task://",
    "workflow://",
)
UNSAFE_TERMS = (
    "raw prompt",
    "serialized prompt",
    "provider response",
    "worker chat",
    "transcript",
    "api key",
    "secret",
    "credential",
    "token=",
)


class RoutineValidationError(ValueError):
    """Raised when routine authority input is unsafe or inconsistent."""


class RoutineState(Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class RoutineTriggerKind(Enum):
    MANUAL = "manual"
    CADENCE = "cadence"
    EVENT = "event"


class RoutineRunPlanStatus(Enum):
    PLANNED = "planned"
    BLOCKED_DISABLED = "blocked_disabled"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RoutineValidationError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


def _looks_like_path(value: str) -> bool:
    if re.search(r"^[A-Za-z]:[\\/]", value):
        return True
    if value.startswith(("/", "\\", "./", ".\\", "../", "..\\")):
        return True
    if re.search(r"\b[\w.-]+[\\/][\w.-]+", value):
        return True
    return False


def _looks_like_uri_path_payload(value: str) -> bool:
    if re.search(r"^[A-Za-z]:[\\/]", value):
        return True
    if value.startswith(("/", "\\", "./", ".\\", "../", "..\\")):
        return True
    if "\\" in value:
        return True
    segments = [segment for segment in value.split("/") if segment]
    if any(segment in (".", "..") for segment in segments):
        return True
    if any(re.search(r"\.[A-Za-z0-9]{1,8}$", segment) for segment in segments):
        return True
    return False


def _safe_text(value: str, field: str, max_length: int = SHORT_TEXT_MAX) -> str:
    text = str(value).strip()
    if not text:
        raise RoutineValidationError(f"{field} must not be empty")
    if len(text) > max_length:
        raise RoutineValidationError(f"{field} is too long")
    lowered = text.lower()
    if any(term in lowered for term in UNSAFE_TERMS):
        raise RoutineValidationError(f"{field} contains unsafe content")
    if _looks_like_path(text):
        raise RoutineValidationError(f"{field} must not contain local paths")
    return text


def _safe_ref(value: str, field: str) -> str:
    ref = str(value).strip()
    if not ref:
        raise RoutineValidationError(f"{field} must not be empty")
    if len(ref) > SHORT_TEXT_MAX:
        raise RoutineValidationError(f"{field} is too long")
    if not ref.startswith(SAFE_REF_SCHEMES):
        ref = _safe_text(ref, field)
        if "://" in ref:
            raise RoutineValidationError(f"{field} uses an unsupported URI scheme")
        return ref
    lowered = ref.lower()
    if any(term in lowered for term in UNSAFE_TERMS):
        raise RoutineValidationError(f"{field} contains unsafe content")
    payload = ref.split("://", 1)[1]
    if not payload or _looks_like_uri_path_payload(payload):
        raise RoutineValidationError(f"{field} must not contain local paths")
    return ref


def _safe_refs(values: Iterable[str], field: str) -> tuple[str, ...]:
    refs = tuple(_safe_ref(value, field) for value in values)
    if len(set(refs)) != len(refs):
        raise RoutineValidationError(f"{field} must not contain duplicates")
    return refs


@dataclass(frozen=True)
class RoutineTrigger:
    trigger_id: str
    kind: RoutineTriggerKind
    label: str
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _safe_text(self.trigger_id, "RoutineTrigger.trigger_id")
        if not isinstance(self.kind, RoutineTriggerKind):
            raise RoutineValidationError("kind must be RoutineTriggerKind")
        _safe_text(self.label, "RoutineTrigger.label")
        object.__setattr__(self, "evidence_refs", _safe_refs(self.evidence_refs, "RoutineTrigger.evidence_refs"))

    def to_dict(self) -> dict[str, object]:
        return {
            "trigger_id": self.trigger_id,
            "kind": self.kind.value,
            "label": self.label,
            "evidence_refs": self.evidence_refs,
        }


@dataclass(frozen=True)
class RoutineDefinition:
    routine_id: str
    name: str
    owner: str
    scope_refs: tuple[str, ...]
    triggers: tuple[RoutineTrigger, ...]
    created_by: str
    created_at: datetime
    state: RoutineState = RoutineState.DISABLED
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _safe_text(self.routine_id, "RoutineDefinition.routine_id")
        _safe_text(self.name, "RoutineDefinition.name")
        _safe_text(self.owner, "RoutineDefinition.owner")
        object.__setattr__(self, "scope_refs", _safe_refs(self.scope_refs, "RoutineDefinition.scope_refs"))
        if not self.scope_refs:
            raise RoutineValidationError("RoutineDefinition.scope_refs must not be empty")
        object.__setattr__(self, "triggers", tuple(self.triggers))
        if not self.triggers:
            raise RoutineValidationError("RoutineDefinition.triggers must not be empty")
        trigger_ids: set[str] = set()
        for trigger in self.triggers:
            if not isinstance(trigger, RoutineTrigger):
                raise RoutineValidationError("triggers must be RoutineTrigger")
            if trigger.trigger_id in trigger_ids:
                raise RoutineValidationError("RoutineDefinition.triggers trigger_id values must be unique")
            trigger_ids.add(trigger.trigger_id)
        _safe_text(self.created_by, "RoutineDefinition.created_by")
        _as_utc(self.created_at)
        if not isinstance(self.state, RoutineState):
            raise RoutineValidationError("state must be RoutineState")
        object.__setattr__(self, "evidence_refs", _safe_refs(self.evidence_refs, "RoutineDefinition.evidence_refs"))

    def to_dict(self) -> dict[str, object]:
        return {
            "routine_id": self.routine_id,
            "name": self.name,
            "owner": self.owner,
            "scope_refs": self.scope_refs,
            "triggers": tuple(trigger.to_dict() for trigger in self.triggers),
            "created_by": self.created_by,
            "created_at": _as_utc(self.created_at).isoformat(),
            "state": self.state.value,
            "evidence_refs": self.evidence_refs,
            "scheduler_mutation_authorized": False,
            "execution_authorized": False,
        }


def create_routine(
    *,
    routine_id: str,
    name: str,
    owner: str,
    scope_refs: tuple[str, ...],
    triggers: tuple[RoutineTrigger, ...],
    created_by: str,
    created_at: datetime,
    enabled: bool = False,
    evidence_refs: tuple[str, ...] = (),
) -> RoutineDefinition:
    return RoutineDefinition(
        routine_id=routine_id,
        name=name,
        owner=owner,
        scope_refs=scope_refs,
        triggers=triggers,
        created_by=created_by,
        created_at=created_at,
        state=RoutineState.ENABLED if enabled else RoutineState.DISABLED,
        evidence_refs=evidence_refs,
    )


def set_routine_enabled(
    routine: RoutineDefinition,
    *,
    enabled: bool,
    actor: str,
    timestamp: datetime,
    evidence_refs: tuple[str, ...] = (),
) -> RoutineDefinition:
    if not isinstance(routine, RoutineDefinition):
        raise RoutineValidationError("routine must be RoutineDefinition")
    _safe_text(actor, "actor")
    _as_utc(timestamp)
    refs = _safe_refs(evidence_refs, "set_routine_enabled.evidence_refs")
    return replace(
        routine,
        state=RoutineState.ENABLED if enabled else RoutineState.DISABLED,
        evidence_refs=routine.evidence_refs + refs,
    )


@dataclass(frozen=True)
class RoutineRunPlan:
    plan_id: str
    routine_id: str
    trigger_id: str
    requested_by: str
    requested_at: datetime
    status: RoutineRunPlanStatus
    reason: str
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _safe_text(self.plan_id, "RoutineRunPlan.plan_id")
        _safe_text(self.routine_id, "RoutineRunPlan.routine_id")
        _safe_text(self.trigger_id, "RoutineRunPlan.trigger_id")
        _safe_text(self.requested_by, "RoutineRunPlan.requested_by")
        _as_utc(self.requested_at)
        if not isinstance(self.status, RoutineRunPlanStatus):
            raise RoutineValidationError("status must be RoutineRunPlanStatus")
        _safe_text(self.reason, "RoutineRunPlan.reason", SUMMARY_MAX)
        object.__setattr__(self, "evidence_refs", _safe_refs(self.evidence_refs, "RoutineRunPlan.evidence_refs"))

    def to_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "routine_id": self.routine_id,
            "trigger_id": self.trigger_id,
            "requested_by": self.requested_by,
            "requested_at": _as_utc(self.requested_at).isoformat(),
            "status": self.status.value,
            "reason": self.reason,
            "evidence_refs": self.evidence_refs,
            "execution_authorized": False,
            "scheduler_mutation_authorized": False,
        }


def plan_routine_run(
    routine: RoutineDefinition,
    *,
    plan_id: str,
    trigger_id: str,
    requested_by: str,
    requested_at: datetime,
    evidence_refs: tuple[str, ...] = (),
) -> RoutineRunPlan:
    if not isinstance(routine, RoutineDefinition):
        raise RoutineValidationError("routine must be RoutineDefinition")
    if trigger_id not in {trigger.trigger_id for trigger in routine.triggers}:
        raise RoutineValidationError("trigger_id is not registered on routine")
    if routine.state is RoutineState.DISABLED:
        return RoutineRunPlan(
            plan_id=plan_id,
            routine_id=routine.routine_id,
            trigger_id=trigger_id,
            requested_by=requested_by,
            requested_at=requested_at,
            status=RoutineRunPlanStatus.BLOCKED_DISABLED,
            reason="Routine is disabled; no execution is authorized.",
            evidence_refs=evidence_refs,
        )
    return RoutineRunPlan(
        plan_id=plan_id,
        routine_id=routine.routine_id,
        trigger_id=trigger_id,
        requested_by=requested_by,
        requested_at=requested_at,
        status=RoutineRunPlanStatus.PLANNED,
        reason="Routine run plan is display-safe and non-executable.",
        evidence_refs=evidence_refs,
    )
