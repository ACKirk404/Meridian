"""Tests for backend routine authority."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from meridian_core.routines import (
    RoutineDefinition,
    RoutineRunPlanStatus,
    RoutineState,
    RoutineTrigger,
    RoutineTriggerKind,
    RoutineValidationError,
    create_routine,
    plan_routine_run,
    set_routine_enabled,
)


NOW = datetime(2026, 6, 10, 22, 45, tzinfo=timezone.utc)


def make_trigger() -> RoutineTrigger:
    return RoutineTrigger(
        trigger_id="routine-trigger-manual",
        kind=RoutineTriggerKind.MANUAL,
        label="Manual review checkpoint",
        evidence_refs=("proof://routine/trigger",),
    )


def make_routine(enabled: bool = False) -> RoutineDefinition:
    return create_routine(
        routine_id="routine-review-checkpoint",
        name="Review checkpoint",
        owner="prime",
        scope_refs=("workflow://review/checkpoint",),
        triggers=(make_trigger(),),
        created_by="prime",
        created_at=NOW,
        enabled=enabled,
        evidence_refs=("proof://routine/create",),
    )


def test_create_routine_records_definition_without_execution_authority():
    routine = make_routine()
    payload = routine.to_dict()

    assert routine.state is RoutineState.DISABLED
    assert payload["routine_id"] == "routine-review-checkpoint"
    assert payload["scheduler_mutation_authorized"] is False
    assert payload["execution_authorized"] is False
    assert payload["triggers"][0]["kind"] == "manual"


def test_set_routine_enabled_toggles_state_with_safe_evidence():
    routine = make_routine()
    enabled = set_routine_enabled(
        routine,
        enabled=True,
        actor="prime",
        timestamp=NOW,
        evidence_refs=("proof://routine/enabled",),
    )
    disabled = set_routine_enabled(
        enabled,
        enabled=False,
        actor="prime",
        timestamp=NOW,
        evidence_refs=("proof://routine/disabled",),
    )

    assert enabled.state is RoutineState.ENABLED
    assert enabled.evidence_refs[-1] == "proof://routine/enabled"
    assert disabled.state is RoutineState.DISABLED
    assert disabled.evidence_refs[-1] == "proof://routine/disabled"


def test_plan_routine_run_blocks_disabled_routine():
    plan = plan_routine_run(
        make_routine(enabled=False),
        plan_id="routine-plan-1",
        trigger_id="routine-trigger-manual",
        requested_by="prime",
        requested_at=NOW,
        evidence_refs=("proof://routine/run-request",),
    )
    payload = plan.to_dict()

    assert plan.status is RoutineRunPlanStatus.BLOCKED_DISABLED
    assert payload["execution_authorized"] is False
    assert payload["scheduler_mutation_authorized"] is False


def test_plan_routine_run_for_enabled_routine_is_non_executable_plan():
    plan = plan_routine_run(
        make_routine(enabled=True),
        plan_id="routine-plan-2",
        trigger_id="routine-trigger-manual",
        requested_by="prime",
        requested_at=NOW,
        evidence_refs=("proof://routine/run-request",),
    )

    assert plan.status is RoutineRunPlanStatus.PLANNED
    assert plan.to_dict()["execution_authorized"] is False


def test_plan_routine_run_requires_registered_trigger():
    with pytest.raises(RoutineValidationError, match="trigger_id"):
        plan_routine_run(
            make_routine(enabled=True),
            plan_id="routine-plan-3",
            trigger_id="routine-trigger-other",
            requested_by="prime",
            requested_at=NOW,
        )


def test_create_routine_rejects_duplicate_trigger_ids():
    duplicate = RoutineTrigger(
        trigger_id="routine-trigger-manual",
        kind=RoutineTriggerKind.CADENCE,
        label="Scheduled review checkpoint",
        evidence_refs=("proof://routine/trigger/scheduled",),
    )

    with pytest.raises(RoutineValidationError, match="trigger_id values must be unique"):
        create_routine(
            routine_id="routine-duplicate-triggers",
            name="Duplicate trigger ids",
            owner="prime",
            scope_refs=("workflow://review/checkpoint",),
            triggers=(make_trigger(), duplicate),
            created_by="prime",
            created_at=NOW,
        )


def test_create_routine_requires_scope_and_trigger():
    with pytest.raises(RoutineValidationError, match="scope_refs"):
        create_routine(
            routine_id="routine-no-scope",
            name="No scope",
            owner="prime",
            scope_refs=(),
            triggers=(make_trigger(),),
            created_by="prime",
            created_at=NOW,
        )

    with pytest.raises(RoutineValidationError, match="triggers"):
        create_routine(
            routine_id="routine-no-trigger",
            name="No trigger",
            owner="prime",
            scope_refs=("workflow://review/checkpoint",),
            triggers=(),
            created_by="prime",
            created_at=NOW,
        )


@pytest.mark.parametrize(
    "unsafe_value",
    (
        "raw prompt contents",
        "provider response body",
        "worker chat transcript",
        "token=abc123",
        r"C:\Users\scott\routine.json",
        "../private/routine.json",
        "docs/routine.md",
    ),
)
def test_routines_reject_unsafe_text_and_refs(unsafe_value):
    with pytest.raises(RoutineValidationError):
        RoutineTrigger(
            trigger_id="routine-trigger-unsafe",
            kind=RoutineTriggerKind.MANUAL,
            label=unsafe_value,
        )

    with pytest.raises(RoutineValidationError):
        create_routine(
            routine_id="routine-unsafe",
            name="Unsafe",
            owner="prime",
            scope_refs=(unsafe_value,),
            triggers=(make_trigger(),),
            created_by="prime",
            created_at=NOW,
        )


@pytest.mark.parametrize(
    "unsafe_ref",
    (
        "routine://../private/routine.json",
        "workflow://./runtime/queue.json",
        r"proof://C:\Users\scott\routine.txt",
    ),
)
def test_routine_safe_uri_refs_reject_path_payloads(unsafe_ref):
    with pytest.raises(RoutineValidationError, match="local paths"):
        create_routine(
            routine_id="routine-unsafe-ref",
            name="Unsafe ref",
            owner="prime",
            scope_refs=(unsafe_ref,),
            triggers=(make_trigger(),),
            created_by="prime",
            created_at=NOW,
        )
