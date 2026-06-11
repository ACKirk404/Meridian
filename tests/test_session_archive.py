"""Tests for backend session archive authority."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from meridian_core.session_archive import (
    SessionArchivePlanStatus,
    SessionArchiveValidationError,
    TranscriptAccessMode,
    archive_record_from_close_result,
    authorize_transcript_access,
    catalog_entry_from_record,
    plan_archive_reload,
    plan_archive_run_again,
)
from meridian_core.session_lifecycle import (
    CloseArchiveWriteThroughAction,
    HarnessRole,
    HealthState,
    OperationScope,
    PermissionContext,
    PermissionState,
    ProofState,
    ReviewCadenceState,
    SessionCloseWriteThroughResult,
    SessionLifecycleState,
    SessionStatus,
)


NOW = datetime(2026, 6, 10, 23, 15, tzinfo=timezone.utc)


def close_result(**overrides) -> SessionCloseWriteThroughResult:
    permissions = PermissionContext(
        approved_by="scott",
        approval_scope=frozenset({OperationScope.ARCHIVE}),
        escalation_gate=False,
        escalation_reason=None,
        branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
        approved_by_secondary=None,
        unlock_expiry=datetime(2026, 6, 11, tzinfo=timezone.utc),
        task_scope="session-archive-authority",
        last_permission_change=NOW,
    )
    state = SessionLifecycleState(
        session_id="session-archive-source",
        session_name="Archive source",
        project_name="Meridian",
        project_path=None,
        harness_role=HarnessRole.COORDINATOR,
        assigned_queue_file="queue://archive",
        model_provider="codex",
        model_name="gpt-5-codex",
        status=SessionStatus.ARCHIVED,
        worktree_path="worktree://archive",
        branch_name="codex/archive-authority",
        current_task_id="session-archive-authority",
        last_queue_read_at=NOW,
        last_queue_write_at=NOW,
        last_prompt_sent_at=NOW,
        last_prompt_payload_size=0,
        review_cadence_state=ReviewCadenceState.CLEARED,
        proof_state=ProofState.EXECUTED,
        health_state=HealthState.HEALTHY,
        blocker_summary=None,
        permission_context=permissions,
    )
    data = {
        "request_id": "close-request-archive",
        "target_session_id": "session-archive-source",
        "intended_action": CloseArchiveWriteThroughAction.ARCHIVE,
        "initial_status": SessionStatus.STOPPED,
        "final_status": SessionStatus.ARCHIVED,
        "close_authorized": True,
        "write_through_attempted": True,
        "write_through_completed": True,
        "obsidian_capture_attempted": True,
        "obsidian_capture_completed": True,
        "session_left_recoverable": True,
        "failure_reason": None,
        "blockers": (),
        "proof_refs": ("proof://archive/sk9", "obsidian://capture/session-archive"),
        "final_state": state,
        "raw_transcript_included": False,
        "raw_prompt_included": False,
        "timestamp": NOW,
    }
    data.update(overrides)
    return SessionCloseWriteThroughResult(**data)


def archive_record():
    return archive_record_from_close_result(
        close_result(),
        archive_id="archive-session-source",
        session_name="Archive source",
        transcript_text="safe bounded session summary",
    )


def test_archive_record_from_close_result_uses_metadata_only():
    record = archive_record()
    payload = record.to_dict()

    assert record.final_status is SessionStatus.ARCHIVED
    assert record.write_through_completed is True
    assert record.obsidian_capture_completed is True
    assert payload["transcript_hash"]
    assert payload["transcript_length"] == len("safe bounded session summary")
    assert payload["raw_transcript_included"] is False
    assert payload["raw_prompt_included"] is False
    assert "safe bounded session summary" not in repr(payload)


def test_archive_record_rejects_unfinished_or_raw_close_results():
    with pytest.raises(SessionArchiveValidationError, match="not archiveable"):
        archive_record_from_close_result(
            close_result(close_authorized=False),
            archive_id="archive-failed",
            session_name="Failed",
        )

    with pytest.raises(SessionArchiveValidationError, match="raw transcript"):
        archive_record_from_close_result(
            close_result(raw_transcript_included=True),
            archive_id="archive-raw",
            session_name="Archive source",
        )


def test_archive_record_requires_archive_action_and_archived_status():
    with pytest.raises(SessionArchiveValidationError, match="archived final state"):
        archive_record_from_close_result(
            close_result(
                intended_action=CloseArchiveWriteThroughAction.CLOSE,
                final_status=SessionStatus.STOPPED,
            ),
            archive_id="archive-close-result",
            session_name="Archive source",
        )


def test_archive_record_rejects_session_name_drift_from_reviewed_result():
    with pytest.raises(SessionArchiveValidationError, match="session_name"):
        archive_record_from_close_result(
            close_result(),
            archive_id="archive-name-drift",
            session_name="Different name",
        )


def test_catalog_entry_exposes_reload_and_transcript_posture():
    entry = catalog_entry_from_record(archive_record())
    payload = entry.to_dict()

    assert payload["reload_available"] is True
    assert payload["run_again_available"] is True
    assert payload["transcript_access_mode"] == "authorized_handle"
    assert "proof://archive/sk9" in payload["proof_refs"]


def test_reload_and_run_again_are_non_executable_plans():
    record = archive_record()
    reload_plan = plan_archive_reload(
        record,
        plan_id="archive-reload-plan",
        requested_by="prime",
        evidence_refs=("proof://archive/reload",),
    )
    run_again_plan = plan_archive_run_again(
        record,
        plan_id="archive-run-again-plan",
        requested_by="prime",
        evidence_refs=("proof://archive/run-again",),
    )

    assert reload_plan.status is SessionArchivePlanStatus.READY
    assert reload_plan.reload_authorized is True
    assert reload_plan.execution_authorized is False
    assert run_again_plan.status is SessionArchivePlanStatus.READY
    assert run_again_plan.run_again_authorized is True
    assert run_again_plan.execution_authorized is False


def test_run_again_blocks_unrecoverable_archives():
    record = archive_record_from_close_result(
        close_result(session_left_recoverable=False),
        archive_id="archive-unrecoverable",
        session_name="Archive source",
    )
    entry = catalog_entry_from_record(record)
    plan = plan_archive_run_again(
        record,
        plan_id="archive-run-again-blocked",
        requested_by="prime",
    )

    assert entry.run_again_available is False
    assert plan.status is SessionArchivePlanStatus.BLOCKED
    assert plan.run_again_authorized is False
    assert "archive.recoverable_session_required" in plan.blockers
    assert plan.execution_authorized is False


def test_transcript_access_requires_human_gate_and_returns_handle_only():
    record = archive_record()
    denied = authorize_transcript_access(
        record,
        handle_id="transcript-handle-denied",
        requested_by="prime",
        human_gate_approved=False,
    )
    allowed = authorize_transcript_access(
        record,
        handle_id="transcript-handle-allowed",
        requested_by="prime",
        human_gate_approved=True,
        evidence_refs=("proof://archive/transcript-access",),
    )

    assert denied.mode is TranscriptAccessMode.METADATA_ONLY
    assert denied.authorized is False
    assert allowed.mode is TranscriptAccessMode.AUTHORIZED_HANDLE
    assert allowed.authorized is True
    assert allowed.to_dict()["raw_transcript_included"] is False
    assert "safe bounded session summary" not in repr(allowed.to_dict())


@pytest.mark.parametrize(
    "unsafe_value",
    (
        "raw prompt contents",
        "provider response body",
        "worker chat transcript",
        "token=abc123",
        r"C:\Users\scott\archive.json",
        "../private/archive.json",
        "docs/archive.md",
    ),
)
def test_archive_rejects_unsafe_text_and_refs(unsafe_value):
    with pytest.raises(SessionArchiveValidationError):
        archive_record_from_close_result(
            close_result(proof_refs=(unsafe_value,)),
            archive_id="archive-unsafe",
            session_name="Unsafe",
        )


@pytest.mark.parametrize(
    "unsafe_transcript",
    (
        "../private/transcript.md",
        "docs/transcript.md",
        r"C:\Users\scott\transcript.txt",
    ),
)
def test_archive_rejects_path_shaped_transcript_inputs(unsafe_transcript):
    with pytest.raises(SessionArchiveValidationError, match="local paths"):
        archive_record_from_close_result(
            close_result(),
            archive_id="archive-unsafe-transcript",
            session_name="Archive source",
            transcript_text=unsafe_transcript,
        )


@pytest.mark.parametrize(
    "unsafe_ref",
    (
        "archive://../private/session.json",
        "proof://./runtime/archive.json",
        r"obsidian://C:\Users\scott\transcript.md",
    ),
)
def test_archive_safe_uri_refs_reject_path_payloads(unsafe_ref):
    with pytest.raises(SessionArchiveValidationError, match="local paths"):
        archive_record_from_close_result(
            close_result(proof_refs=(unsafe_ref,)),
            archive_id="archive-unsafe-ref",
            session_name="Archive source",
        )
