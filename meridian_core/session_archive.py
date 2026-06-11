"""Backend-only session archive authority.

This module owns typed archive catalog/reload/run-again/transcript-access
metadata. It never replays raw transcripts, starts sessions, writes UI routes,
or performs filesystem/provider work.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable, Optional

from .session_lifecycle import (
    CloseArchiveWriteThroughAction,
    SessionCloseWriteThroughResult,
    SessionStatus,
)


SHORT_TEXT_MAX = 160
LONG_TEXT_MAX = 480
SAFE_REF_SCHEMES = (
    "archive://",
    "obsidian://",
    "proof://",
    "session://",
    "task://",
    "workflow://",
)
UNSAFE_TERMS = (
    "raw prompt",
    "serialized prompt",
    "provider response",
    "worker chat",
    "transcript excerpt",
    "full transcript",
    "api_key",
    "secret",
    "token=",
    "password",
)


class SessionArchiveValidationError(ValueError):
    """Raised when archive authority input would be unsafe or ambiguous."""


class SessionArchivePlanStatus(Enum):
    READY = "ready"
    BLOCKED = "blocked"


class TranscriptAccessMode(Enum):
    METADATA_ONLY = "metadata_only"
    AUTHORIZED_HANDLE = "authorized_handle"


@dataclass(frozen=True)
class ArchivedSessionRecord:
    archive_id: str
    session_id: str
    session_name: str
    final_status: SessionStatus
    archived_at: datetime
    close_request_id: str
    intended_action: CloseArchiveWriteThroughAction
    write_through_completed: bool
    obsidian_capture_completed: bool
    session_left_recoverable: bool
    proof_refs: tuple[str, ...]
    transcript_hash: Optional[str] = None
    transcript_length: Optional[int] = None
    raw_transcript_included: bool = False
    raw_prompt_included: bool = False

    def __post_init__(self) -> None:
        _safe_text(self.archive_id, "ArchivedSessionRecord.archive_id")
        _safe_text(self.session_id, "ArchivedSessionRecord.session_id")
        _safe_text(self.session_name, "ArchivedSessionRecord.session_name")
        if not isinstance(self.final_status, SessionStatus):
            raise SessionArchiveValidationError("final_status must be SessionStatus")
        _as_utc(self.archived_at)
        _safe_text(self.close_request_id, "ArchivedSessionRecord.close_request_id")
        if not isinstance(self.intended_action, CloseArchiveWriteThroughAction):
            raise SessionArchiveValidationError(
                "intended_action must be CloseArchiveWriteThroughAction"
            )
        object.__setattr__(
            self, "proof_refs", _safe_refs(self.proof_refs, "ArchivedSessionRecord.proof_refs")
        )
        if not self.proof_refs:
            raise SessionArchiveValidationError("proof_refs must not be empty")
        if self.transcript_hash is not None:
            _safe_hash(self.transcript_hash, "ArchivedSessionRecord.transcript_hash")
        if self.transcript_length is not None and self.transcript_length < 0:
            raise SessionArchiveValidationError("transcript_length must be non-negative")
        if self.raw_transcript_included or self.raw_prompt_included:
            raise SessionArchiveValidationError("raw transcript or prompt cannot be archived")

    def to_dict(self) -> dict[str, object]:
        return {
            "archive_id": self.archive_id,
            "session_id": self.session_id,
            "session_name": self.session_name,
            "final_status": self.final_status.value,
            "archived_at": _as_utc(self.archived_at).isoformat(),
            "close_request_id": self.close_request_id,
            "intended_action": self.intended_action.value,
            "write_through_completed": self.write_through_completed,
            "obsidian_capture_completed": self.obsidian_capture_completed,
            "session_left_recoverable": self.session_left_recoverable,
            "proof_refs": self.proof_refs,
            "transcript_hash": self.transcript_hash,
            "transcript_length": self.transcript_length,
            "raw_transcript_included": False,
            "raw_prompt_included": False,
        }


@dataclass(frozen=True)
class ArchiveCatalogEntry:
    archive_id: str
    session_id: str
    session_name: str
    archived_at: datetime
    final_status: SessionStatus
    reload_available: bool
    run_again_available: bool
    transcript_access_mode: TranscriptAccessMode
    proof_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _safe_text(self.archive_id, "ArchiveCatalogEntry.archive_id")
        _safe_text(self.session_id, "ArchiveCatalogEntry.session_id")
        _safe_text(self.session_name, "ArchiveCatalogEntry.session_name")
        _as_utc(self.archived_at)
        if not isinstance(self.final_status, SessionStatus):
            raise SessionArchiveValidationError("final_status must be SessionStatus")
        if not isinstance(self.transcript_access_mode, TranscriptAccessMode):
            raise SessionArchiveValidationError(
                "transcript_access_mode must be TranscriptAccessMode"
            )
        object.__setattr__(
            self, "proof_refs", _safe_refs(self.proof_refs, "ArchiveCatalogEntry.proof_refs")
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "archive_id": self.archive_id,
            "session_id": self.session_id,
            "session_name": self.session_name,
            "archived_at": _as_utc(self.archived_at).isoformat(),
            "final_status": self.final_status.value,
            "reload_available": self.reload_available,
            "run_again_available": self.run_again_available,
            "transcript_access_mode": self.transcript_access_mode.value,
            "proof_refs": self.proof_refs,
        }


@dataclass(frozen=True)
class ArchiveReloadPlan:
    plan_id: str
    archive_id: str
    session_id: str
    status: SessionArchivePlanStatus
    reload_authorized: bool
    execution_authorized: bool
    blockers: tuple[str, ...]
    proof_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _safe_text(self.plan_id, "ArchiveReloadPlan.plan_id")
        _safe_text(self.archive_id, "ArchiveReloadPlan.archive_id")
        _safe_text(self.session_id, "ArchiveReloadPlan.session_id")
        if not isinstance(self.status, SessionArchivePlanStatus):
            raise SessionArchiveValidationError("status must be SessionArchivePlanStatus")
        object.__setattr__(self, "blockers", tuple(_safe_label(v, "blocker") for v in self.blockers))
        object.__setattr__(self, "proof_refs", _safe_refs(self.proof_refs, "ArchiveReloadPlan.proof_refs"))
        if self.execution_authorized:
            raise SessionArchiveValidationError("archive reload execution is not authorized")

    def to_dict(self) -> dict[str, object]:
        return _plan_dict(self)


@dataclass(frozen=True)
class ArchiveRunAgainPlan:
    plan_id: str
    archive_id: str
    session_id: str
    status: SessionArchivePlanStatus
    run_again_authorized: bool
    execution_authorized: bool
    blockers: tuple[str, ...]
    proof_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _safe_text(self.plan_id, "ArchiveRunAgainPlan.plan_id")
        _safe_text(self.archive_id, "ArchiveRunAgainPlan.archive_id")
        _safe_text(self.session_id, "ArchiveRunAgainPlan.session_id")
        if not isinstance(self.status, SessionArchivePlanStatus):
            raise SessionArchiveValidationError("status must be SessionArchivePlanStatus")
        object.__setattr__(self, "blockers", tuple(_safe_label(v, "blocker") for v in self.blockers))
        object.__setattr__(self, "proof_refs", _safe_refs(self.proof_refs, "ArchiveRunAgainPlan.proof_refs"))
        if self.execution_authorized:
            raise SessionArchiveValidationError("archive run-again execution is not authorized")

    def to_dict(self) -> dict[str, object]:
        payload = _plan_dict(self)
        payload["run_again_authorized"] = self.run_again_authorized
        payload.pop("reload_authorized", None)
        return payload


@dataclass(frozen=True)
class TranscriptAccessHandle:
    handle_id: str
    archive_id: str
    session_id: str
    mode: TranscriptAccessMode
    authorized: bool
    transcript_hash: Optional[str]
    transcript_length: Optional[int]
    proof_refs: tuple[str, ...]
    raw_transcript_included: bool = False

    def __post_init__(self) -> None:
        _safe_text(self.handle_id, "TranscriptAccessHandle.handle_id")
        _safe_text(self.archive_id, "TranscriptAccessHandle.archive_id")
        _safe_text(self.session_id, "TranscriptAccessHandle.session_id")
        if not isinstance(self.mode, TranscriptAccessMode):
            raise SessionArchiveValidationError("mode must be TranscriptAccessMode")
        if self.transcript_hash is not None:
            _safe_hash(self.transcript_hash, "TranscriptAccessHandle.transcript_hash")
        if self.transcript_length is not None and self.transcript_length < 0:
            raise SessionArchiveValidationError("transcript_length must be non-negative")
        object.__setattr__(
            self, "proof_refs", _safe_refs(self.proof_refs, "TranscriptAccessHandle.proof_refs")
        )
        if self.raw_transcript_included:
            raise SessionArchiveValidationError("raw transcript cannot be included")

    def to_dict(self) -> dict[str, object]:
        return {
            "handle_id": self.handle_id,
            "archive_id": self.archive_id,
            "session_id": self.session_id,
            "mode": self.mode.value,
            "authorized": self.authorized,
            "transcript_hash": self.transcript_hash,
            "transcript_length": self.transcript_length,
            "proof_refs": self.proof_refs,
            "raw_transcript_included": False,
        }


def archive_record_from_close_result(
    result: SessionCloseWriteThroughResult,
    *,
    archive_id: str,
    session_name: Optional[str] = None,
    transcript_text: Optional[str] = None,
) -> ArchivedSessionRecord:
    if not result.close_authorized or not result.write_through_completed:
        raise SessionArchiveValidationError("close/write-through result is not archiveable")
    if (
        result.intended_action is not CloseArchiveWriteThroughAction.ARCHIVE
        or result.final_status is not SessionStatus.ARCHIVED
    ):
        raise SessionArchiveValidationError("archive records require archived final state")
    reviewed_session_name = result.final_state.session_name
    transcript_hash = None
    transcript_length = None
    if transcript_text is not None:
        _safe_text(transcript_text, "transcript_text")
        transcript_hash = hashlib.sha256(transcript_text.encode("utf-8")).hexdigest()
        transcript_length = len(transcript_text)
    record = ArchivedSessionRecord(
        archive_id=archive_id,
        session_id=result.target_session_id,
        session_name=reviewed_session_name,
        final_status=result.final_status,
        archived_at=result.timestamp,
        close_request_id=result.request_id,
        intended_action=result.intended_action,
        write_through_completed=result.write_through_completed,
        obsidian_capture_completed=result.obsidian_capture_completed,
        session_left_recoverable=result.session_left_recoverable,
        proof_refs=result.proof_refs,
        transcript_hash=transcript_hash,
        transcript_length=transcript_length,
        raw_transcript_included=result.raw_transcript_included,
        raw_prompt_included=result.raw_prompt_included,
    )
    if session_name is not None and _safe_text(session_name, "session_name") != reviewed_session_name:
        raise SessionArchiveValidationError("session_name must match reviewed lifecycle result")
    return record


def catalog_entry_from_record(record: ArchivedSessionRecord) -> ArchiveCatalogEntry:
    return ArchiveCatalogEntry(
        archive_id=record.archive_id,
        session_id=record.session_id,
        session_name=record.session_name,
        archived_at=record.archived_at,
        final_status=record.final_status,
        reload_available=record.final_status == SessionStatus.ARCHIVED,
        run_again_available=record.write_through_completed and record.session_left_recoverable,
        transcript_access_mode=TranscriptAccessMode.AUTHORIZED_HANDLE
        if record.transcript_hash
        else TranscriptAccessMode.METADATA_ONLY,
        proof_refs=record.proof_refs,
    )


def plan_archive_reload(
    record: ArchivedSessionRecord,
    *,
    plan_id: str,
    requested_by: str,
    evidence_refs: tuple[str, ...] = (),
) -> ArchiveReloadPlan:
    _safe_text(requested_by, "requested_by")
    refs = record.proof_refs + _safe_refs(evidence_refs, "evidence_refs")
    blockers: tuple[str, ...] = ()
    if record.final_status != SessionStatus.ARCHIVED:
        blockers = ("archive.not_archived",)
    return ArchiveReloadPlan(
        plan_id=plan_id,
        archive_id=record.archive_id,
        session_id=record.session_id,
        status=SessionArchivePlanStatus.BLOCKED if blockers else SessionArchivePlanStatus.READY,
        reload_authorized=not blockers,
        execution_authorized=False,
        blockers=blockers,
        proof_refs=refs,
    )


def plan_archive_run_again(
    record: ArchivedSessionRecord,
    *,
    plan_id: str,
    requested_by: str,
    evidence_refs: tuple[str, ...] = (),
) -> ArchiveRunAgainPlan:
    _safe_text(requested_by, "requested_by")
    refs = record.proof_refs + _safe_refs(evidence_refs, "evidence_refs")
    blockers: tuple[str, ...] = ()
    if not record.write_through_completed:
        blockers = ("archive.write_through_required",)
    elif not record.session_left_recoverable:
        blockers = ("archive.recoverable_session_required",)
    return ArchiveRunAgainPlan(
        plan_id=plan_id,
        archive_id=record.archive_id,
        session_id=record.session_id,
        status=SessionArchivePlanStatus.BLOCKED if blockers else SessionArchivePlanStatus.READY,
        run_again_authorized=not blockers,
        execution_authorized=False,
        blockers=blockers,
        proof_refs=refs,
    )


def authorize_transcript_access(
    record: ArchivedSessionRecord,
    *,
    handle_id: str,
    requested_by: str,
    human_gate_approved: bool,
    evidence_refs: tuple[str, ...] = (),
) -> TranscriptAccessHandle:
    _safe_text(requested_by, "requested_by")
    refs = record.proof_refs + _safe_refs(evidence_refs, "evidence_refs")
    authorized = bool(human_gate_approved and record.transcript_hash)
    return TranscriptAccessHandle(
        handle_id=handle_id,
        archive_id=record.archive_id,
        session_id=record.session_id,
        mode=TranscriptAccessMode.AUTHORIZED_HANDLE
        if authorized
        else TranscriptAccessMode.METADATA_ONLY,
        authorized=authorized,
        transcript_hash=record.transcript_hash,
        transcript_length=record.transcript_length,
        proof_refs=refs,
    )


def _plan_dict(plan: ArchiveReloadPlan | ArchiveRunAgainPlan) -> dict[str, object]:
    return {
        "plan_id": plan.plan_id,
        "archive_id": plan.archive_id,
        "session_id": plan.session_id,
        "status": plan.status.value,
        "reload_authorized": getattr(plan, "reload_authorized", False),
        "execution_authorized": False,
        "blockers": plan.blockers,
        "proof_refs": plan.proof_refs,
    }


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SessionArchiveValidationError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


def _safe_refs(values: Iterable[str], field: str) -> tuple[str, ...]:
    refs = tuple(_safe_ref(value, field) for value in values)
    if len(set(refs)) != len(refs):
        raise SessionArchiveValidationError(f"{field} must not contain duplicates")
    return refs


def _safe_ref(value: str, field: str) -> str:
    ref = str(value).strip()
    if not ref:
        raise SessionArchiveValidationError(f"{field} must not be empty")
    if len(ref) > LONG_TEXT_MAX:
        raise SessionArchiveValidationError(f"{field} is too long")
    if not ref.startswith(SAFE_REF_SCHEMES):
        return _safe_text(ref, field)
    _reject_unsafe_content(ref, field)
    payload = ref.split("://", 1)[1]
    if not payload or _looks_like_uri_path_payload(payload):
        raise SessionArchiveValidationError(f"{field} must not contain local paths")
    return ref


def _safe_text(value: str, field: str) -> str:
    text = str(value).strip()
    if not text:
        raise SessionArchiveValidationError(f"{field} must not be empty")
    if len(text) > SHORT_TEXT_MAX:
        raise SessionArchiveValidationError(f"{field} is too long")
    _reject_unsafe_content(text, field)
    if _looks_like_path(text):
        raise SessionArchiveValidationError(f"{field} must not contain local paths")
    return text


def _safe_label(value: str, field: str) -> str:
    return _safe_text(value, field)


def _reject_unsafe_content(value: str, field: str) -> None:
    lowered = str(value).lower()
    if any(term in lowered for term in UNSAFE_TERMS):
        raise SessionArchiveValidationError(f"{field} contains unsafe content")


def _safe_hash(value: str, field: str) -> str:
    if not re.fullmatch(r"[a-f0-9]{64}", value):
        raise SessionArchiveValidationError(f"{field} must be a sha256 hex digest")
    return value


def _looks_like_path(value: str) -> bool:
    if re.search(r"^[A-Za-z]:[\\/]", value):
        return True
    if value.startswith(("/", "\\", "./", ".\\", "../", "..\\")):
        return True
    if re.search(r"\b[\w.-]+[\\/][\w.-]+", value):
        return True
    return False


def _looks_like_uri_path_payload(value: str) -> bool:
    if value.startswith(("./", "../", ".\\", "..\\")):
        return True
    if re.search(r"^[A-Za-z]:[\\/]", value):
        return True
    if "\\" in value:
        return True
    if re.search(r"\.[A-Za-z0-9]{1,8}$", value):
        return True
    return False
