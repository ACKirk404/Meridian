"""Backlog Authority: backend-owned backlog records and transitions.

This module owns durable backlog domain shape for BAK3-BAK11. It is a pure
backend authority slice: no UI bridge, no live session dispatch, no model calls,
and no writeback to Polaris or other external systems.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Optional


SHORT_TEXT_MAX = 240
BODY_SUMMARY_MAX = 1200
CRITERION_MAX = 320
EVIDENCE_REF_MAX = 160


class BacklogValidationError(ValueError):
    """Raised when backlog input would violate authority or display safety."""


class BacklogItemState(Enum):
    """Closed lifecycle states for backlog items."""

    CAPTURED = "captured"
    APPROVED = "approved"
    DEFERRED = "deferred"
    REJECTED = "rejected"
    TASK_DRAFTED = "task_drafted"
    ARCHIVED = "archived"


class BacklogSource(Enum):
    """Trusted source families for backlog records."""

    USER = "user"
    PRIME = "prime"
    POLARIS = "polaris"
    REVIEW_CONSOLE = "review_console"
    DOC = "doc"


class BacklogPriority(Enum):
    """Backlog priority labels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class BacklogOwner(Enum):
    """Owner lane or harness for a backlog item or task draft."""

    PRIME = "prime"
    BUILD = "build"
    REVIEW = "review"
    UI = "ui"
    AEGIS = "aegis"
    RELAY = "relay"
    HUMAN = "human"


class BacklogBlockedStatus(Enum):
    """Blocked-state filter field."""

    UNBLOCKED = "unblocked"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class BacklogAuditAction(Enum):
    """Audit actions that mutate backlog record state."""

    CAPTURE = "capture"
    MODIFY = "modify"
    APPROVE = "approve"
    REJECT = "reject"
    DEFER = "defer"
    LINK_SCOPE = "link_scope"
    CONVERT_TO_TASK = "convert_to_task"
    IMPORT_CANDIDATE = "import_candidate"
    ARCHIVE = "archive"


@dataclass(frozen=True)
class BacklogScope:
    """Project/initiative/venture attachment for a backlog item."""

    project_id: str
    project_name: str
    initiative_id: Optional[str] = None
    venture_id: Optional[str] = None

    def __post_init__(self) -> None:
        _safe_label(self.project_id, "BacklogScope.project_id")
        _safe_text(self.project_name, "BacklogScope.project_name", SHORT_TEXT_MAX)
        if self.initiative_id is not None:
            _safe_label(self.initiative_id, "BacklogScope.initiative_id")
        if self.venture_id is not None:
            _safe_label(self.venture_id, "BacklogScope.venture_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "initiative_id": self.initiative_id,
            "venture_id": self.venture_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BacklogScope":
        return cls(
            project_id=str(data["project_id"]),
            project_name=str(data["project_name"]),
            initiative_id=data.get("initiative_id"),
            venture_id=data.get("venture_id"),
        )


@dataclass(frozen=True)
class BacklogAuditEntry:
    """Display-safe audit record for a backlog transition."""

    action: BacklogAuditAction
    actor: str
    timestamp: datetime
    reason: Optional[str] = None
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.action, BacklogAuditAction):
            raise BacklogValidationError("audit action must be a BacklogAuditAction")
        _safe_label(self.actor, "BacklogAuditEntry.actor")
        _as_utc(self.timestamp)
        if self.reason is not None:
            _safe_text(self.reason, "BacklogAuditEntry.reason", SHORT_TEXT_MAX)
        object.__setattr__(
            self,
            "evidence_refs",
            _safe_refs(self.evidence_refs, "BacklogAuditEntry.evidence_refs"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "actor": self.actor,
            "timestamp": _as_utc(self.timestamp).isoformat(),
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BacklogAuditEntry":
        return cls(
            action=BacklogAuditAction(str(data["action"])),
            actor=str(data["actor"]),
            timestamp=_parse_datetime(str(data["timestamp"])),
            reason=data.get("reason"),
            evidence_refs=tuple(data.get("evidence_refs", ())),
        )


@dataclass(frozen=True)
class BacklogRevision:
    """Immutable revision record for editable backlog fields."""

    version: int
    title: str
    body_summary: str
    acceptance_criteria: tuple[str, ...]
    priority: BacklogPriority
    owner: BacklogOwner
    blocked_status: BacklogBlockedStatus
    updated_by: str
    updated_at: datetime
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.version < 1:
            raise BacklogValidationError("revision version must be >= 1")
        _safe_text(self.title, "BacklogRevision.title", SHORT_TEXT_MAX)
        _safe_text(self.body_summary, "BacklogRevision.body_summary", BODY_SUMMARY_MAX)
        object.__setattr__(
            self,
            "acceptance_criteria",
            _safe_criteria(self.acceptance_criteria),
        )
        if not isinstance(self.priority, BacklogPriority):
            raise BacklogValidationError("priority must be a BacklogPriority")
        if not isinstance(self.owner, BacklogOwner):
            raise BacklogValidationError("owner must be a BacklogOwner")
        if not isinstance(self.blocked_status, BacklogBlockedStatus):
            raise BacklogValidationError(
                "blocked_status must be a BacklogBlockedStatus"
            )
        _safe_label(self.updated_by, "BacklogRevision.updated_by")
        _as_utc(self.updated_at)
        object.__setattr__(
            self,
            "evidence_refs",
            _safe_refs(self.evidence_refs, "BacklogRevision.evidence_refs"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "title": self.title,
            "body_summary": self.body_summary,
            "acceptance_criteria": list(self.acceptance_criteria),
            "priority": self.priority.value,
            "owner": self.owner.value,
            "blocked_status": self.blocked_status.value,
            "updated_by": self.updated_by,
            "updated_at": _as_utc(self.updated_at).isoformat(),
            "evidence_refs": list(self.evidence_refs),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BacklogRevision":
        return cls(
            version=int(data["version"]),
            title=str(data["title"]),
            body_summary=str(data["body_summary"]),
            acceptance_criteria=tuple(data.get("acceptance_criteria", ())),
            priority=BacklogPriority(str(data["priority"])),
            owner=BacklogOwner(str(data["owner"])),
            blocked_status=BacklogBlockedStatus(str(data["blocked_status"])),
            updated_by=str(data["updated_by"]),
            updated_at=_parse_datetime(str(data["updated_at"])),
            evidence_refs=tuple(data.get("evidence_refs", ())),
        )


@dataclass(frozen=True)
class BacklogItem:
    """Durable backlog item with audit and revision history."""

    item_id: str
    title: str
    body_summary: str
    source: BacklogSource
    source_ref: str
    state: BacklogItemState
    scope: BacklogScope
    priority: BacklogPriority
    owner: BacklogOwner
    blocked_status: BacklogBlockedStatus
    acceptance_criteria: tuple[str, ...]
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
    revision: int
    revisions: tuple[BacklogRevision, ...]
    audit_trail: tuple[BacklogAuditEntry, ...]
    deferred_until: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    archived_by: Optional[str] = None
    archive_reason: Optional[str] = None

    def __post_init__(self) -> None:
        _safe_label(self.item_id, "BacklogItem.item_id")
        _safe_text(self.title, "BacklogItem.title", SHORT_TEXT_MAX)
        _safe_text(self.body_summary, "BacklogItem.body_summary", BODY_SUMMARY_MAX)
        if not isinstance(self.source, BacklogSource):
            raise BacklogValidationError("source must be a BacklogSource")
        _safe_ref(self.source_ref, "BacklogItem.source_ref")
        if not isinstance(self.state, BacklogItemState):
            raise BacklogValidationError("state must be a BacklogItemState")
        if not isinstance(self.scope, BacklogScope):
            raise BacklogValidationError("scope must be a BacklogScope")
        if not isinstance(self.priority, BacklogPriority):
            raise BacklogValidationError("priority must be a BacklogPriority")
        if not isinstance(self.owner, BacklogOwner):
            raise BacklogValidationError("owner must be a BacklogOwner")
        if not isinstance(self.blocked_status, BacklogBlockedStatus):
            raise BacklogValidationError(
                "blocked_status must be a BacklogBlockedStatus"
            )
        object.__setattr__(
            self,
            "acceptance_criteria",
            _safe_criteria(self.acceptance_criteria),
        )
        _as_utc(self.created_at)
        _as_utc(self.updated_at)
        _safe_label(self.created_by, "BacklogItem.created_by")
        _safe_label(self.updated_by, "BacklogItem.updated_by")
        if self.revision < 1:
            raise BacklogValidationError("revision must be >= 1")
        object.__setattr__(self, "revisions", tuple(self.revisions or ()))
        object.__setattr__(self, "audit_trail", tuple(self.audit_trail or ()))
        if not self.revisions:
            raise BacklogValidationError("backlog items require revision history")
        if self.revision != len(self.revisions):
            raise BacklogValidationError("revision must match revision history length")
        if not self.audit_trail:
            raise BacklogValidationError("backlog items require audit history")
        for revision in self.revisions:
            if not isinstance(revision, BacklogRevision):
                raise BacklogValidationError("revisions must be BacklogRevision")
        latest_revision = self.revisions[-1]
        if latest_revision.version != self.revision:
            raise BacklogValidationError("latest revision must match item revision")
        if (
            latest_revision.title != self.title
            or latest_revision.body_summary != self.body_summary
            or latest_revision.acceptance_criteria != self.acceptance_criteria
            or latest_revision.priority != self.priority
            or latest_revision.owner != self.owner
            or latest_revision.blocked_status != self.blocked_status
        ):
            raise BacklogValidationError(
                "latest revision must match editable backlog fields"
            )
        for entry in self.audit_trail:
            if not isinstance(entry, BacklogAuditEntry):
                raise BacklogValidationError("audit_trail must be BacklogAuditEntry")
        if self.deferred_until is not None:
            _as_utc(self.deferred_until)
        if self.archived_at is not None:
            _as_utc(self.archived_at)
        if self.archived_by is not None:
            _safe_label(self.archived_by, "BacklogItem.archived_by")
        if self.archive_reason is not None:
            _safe_text(self.archive_reason, "BacklogItem.archive_reason", SHORT_TEXT_MAX)
        if self.state == BacklogItemState.ARCHIVED and self.archived_at is None:
            raise BacklogValidationError("archived items require archived_at")
        if self.state == BacklogItemState.ARCHIVED and self.archived_by is None:
            raise BacklogValidationError("archived items require archived_by")
        if self.state == BacklogItemState.ARCHIVED and self.archive_reason is None:
            raise BacklogValidationError("archived items require archive_reason")

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "title": self.title,
            "body_summary": self.body_summary,
            "source": self.source.value,
            "source_ref": self.source_ref,
            "state": self.state.value,
            "scope": self.scope.to_dict(),
            "priority": self.priority.value,
            "owner": self.owner.value,
            "blocked_status": self.blocked_status.value,
            "acceptance_criteria": list(self.acceptance_criteria),
            "created_at": _as_utc(self.created_at).isoformat(),
            "created_by": self.created_by,
            "updated_at": _as_utc(self.updated_at).isoformat(),
            "updated_by": self.updated_by,
            "revision": self.revision,
            "revisions": [revision.to_dict() for revision in self.revisions],
            "audit_trail": [entry.to_dict() for entry in self.audit_trail],
            "deferred_until": (
                _as_utc(self.deferred_until).isoformat()
                if self.deferred_until
                else None
            ),
            "archived_at": (
                _as_utc(self.archived_at).isoformat() if self.archived_at else None
            ),
            "archived_by": self.archived_by,
            "archive_reason": self.archive_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BacklogItem":
        return cls(
            item_id=str(data["item_id"]),
            title=str(data["title"]),
            body_summary=str(data["body_summary"]),
            source=BacklogSource(str(data["source"])),
            source_ref=str(data["source_ref"]),
            state=BacklogItemState(str(data["state"])),
            scope=BacklogScope.from_dict(dict(data["scope"])),
            priority=BacklogPriority(str(data["priority"])),
            owner=BacklogOwner(str(data["owner"])),
            blocked_status=BacklogBlockedStatus(str(data["blocked_status"])),
            acceptance_criteria=tuple(data.get("acceptance_criteria", ())),
            created_at=_parse_datetime(str(data["created_at"])),
            created_by=str(data["created_by"]),
            updated_at=_parse_datetime(str(data["updated_at"])),
            updated_by=str(data["updated_by"]),
            revision=int(data["revision"]),
            revisions=tuple(
                BacklogRevision.from_dict(dict(revision))
                for revision in data.get("revisions", ())
            ),
            audit_trail=tuple(
                BacklogAuditEntry.from_dict(dict(entry))
                for entry in data.get("audit_trail", ())
            ),
            deferred_until=(
                _parse_datetime(str(data["deferred_until"]))
                if data.get("deferred_until")
                else None
            ),
            archived_at=(
                _parse_datetime(str(data["archived_at"]))
                if data.get("archived_at")
                else None
            ),
            archived_by=data.get("archived_by"),
            archive_reason=data.get("archive_reason"),
        )


@dataclass(frozen=True)
class BacklogTaskDraft:
    """Executable-task draft projection from an approved backlog item."""

    item_id: str
    task_id: str
    title: str
    owner: BacklogOwner
    project_id: str
    proof_expectation: str
    risk_tier: int
    acceptance_criteria: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _safe_label(self.item_id, "BacklogTaskDraft.item_id")
        _safe_label(self.task_id, "BacklogTaskDraft.task_id")
        _safe_text(self.title, "BacklogTaskDraft.title", SHORT_TEXT_MAX)
        if not isinstance(self.owner, BacklogOwner):
            raise BacklogValidationError("owner must be a BacklogOwner")
        _safe_label(self.project_id, "BacklogTaskDraft.project_id")
        _safe_text(
            self.proof_expectation,
            "BacklogTaskDraft.proof_expectation",
            SHORT_TEXT_MAX,
        )
        if self.risk_tier < 0 or self.risk_tier > 5:
            raise BacklogValidationError("risk_tier must be between 0 and 5")
        object.__setattr__(
            self,
            "acceptance_criteria",
            _safe_criteria(self.acceptance_criteria),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _safe_refs(self.evidence_refs, "BacklogTaskDraft.evidence_refs"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "task_id": self.task_id,
            "title": self.title,
            "owner": self.owner.value,
            "project_id": self.project_id,
            "proof_expectation": self.proof_expectation,
            "risk_tier": self.risk_tier,
            "acceptance_criteria": list(self.acceptance_criteria),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class BacklogImportCandidate:
    """Polaris/doc/user candidate before capture as a backlog item."""

    candidate_id: str
    title: str
    source: BacklogSource
    source_ref: str
    dedupe_key: str
    body_summary: str = ""

    def __post_init__(self) -> None:
        _safe_label(self.candidate_id, "BacklogImportCandidate.candidate_id")
        _safe_text(self.title, "BacklogImportCandidate.title", SHORT_TEXT_MAX)
        if not isinstance(self.source, BacklogSource):
            raise BacklogValidationError("source must be a BacklogSource")
        _safe_ref(self.source_ref, "BacklogImportCandidate.source_ref")
        _safe_label(self.dedupe_key, "BacklogImportCandidate.dedupe_key")
        _safe_text(
            self.body_summary,
            "BacklogImportCandidate.body_summary",
            BODY_SUMMARY_MAX,
            allow_empty=True,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "title": self.title,
            "source": self.source.value,
            "source_ref": self.source_ref,
            "dedupe_key": self.dedupe_key,
            "body_summary": self.body_summary,
        }


@dataclass(frozen=True)
class BacklogImportBatch:
    """Imported candidate batch with provenance and no source writeback."""

    batch_id: str
    imported_by: str
    imported_at: datetime
    source: BacklogSource
    candidates: tuple[BacklogImportCandidate, ...]
    writes_back_to_source: bool = False

    def __post_init__(self) -> None:
        _safe_label(self.batch_id, "BacklogImportBatch.batch_id")
        _safe_label(self.imported_by, "BacklogImportBatch.imported_by")
        _as_utc(self.imported_at)
        if not isinstance(self.source, BacklogSource):
            raise BacklogValidationError("source must be a BacklogSource")
        object.__setattr__(self, "candidates", tuple(self.candidates or ()))
        for candidate in self.candidates:
            if not isinstance(candidate, BacklogImportCandidate):
                raise BacklogValidationError(
                    "candidates must be BacklogImportCandidate"
                )
            if candidate.source != self.source:
                raise BacklogValidationError(
                    "candidate source must match import batch source"
                )
        if self.writes_back_to_source:
            raise BacklogValidationError("import batches cannot write back to source")

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "imported_by": self.imported_by,
            "imported_at": _as_utc(self.imported_at).isoformat(),
            "source": self.source.value,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "writes_back_to_source": self.writes_back_to_source,
        }


@dataclass(frozen=True)
class BacklogQuery:
    """Search/filter request over real backlog fields."""

    project_id: Optional[str] = None
    states: tuple[BacklogItemState, ...] = ()
    priorities: tuple[BacklogPriority, ...] = ()
    owners: tuple[BacklogOwner, ...] = ()
    blocked_statuses: tuple[BacklogBlockedStatus, ...] = ()
    include_archived: bool = False
    text: Optional[str] = None

    def __post_init__(self) -> None:
        if self.project_id is not None:
            _safe_label(self.project_id, "BacklogQuery.project_id")
        object.__setattr__(self, "states", tuple(self.states or ()))
        object.__setattr__(self, "priorities", tuple(self.priorities or ()))
        object.__setattr__(self, "owners", tuple(self.owners or ()))
        object.__setattr__(
            self,
            "blocked_statuses",
            tuple(self.blocked_statuses or ()),
        )
        for state in self.states:
            if not isinstance(state, BacklogItemState):
                raise BacklogValidationError("states must be BacklogItemState")
        for priority in self.priorities:
            if not isinstance(priority, BacklogPriority):
                raise BacklogValidationError("priorities must be BacklogPriority")
        for owner in self.owners:
            if not isinstance(owner, BacklogOwner):
                raise BacklogValidationError("owners must be BacklogOwner")
        for blocked in self.blocked_statuses:
            if not isinstance(blocked, BacklogBlockedStatus):
                raise BacklogValidationError(
                    "blocked_statuses must be BacklogBlockedStatus"
                )
        if self.text is not None:
            _safe_text(self.text, "BacklogQuery.text", SHORT_TEXT_MAX)


def capture_backlog_item(
    item_id: str,
    title: str,
    body_summary: str,
    source: BacklogSource,
    source_ref: str,
    created_by: str,
    scope: BacklogScope,
    priority: BacklogPriority = BacklogPriority.NORMAL,
    owner: BacklogOwner = BacklogOwner.PRIME,
    blocked_status: BacklogBlockedStatus = BacklogBlockedStatus.UNBLOCKED,
    acceptance_criteria: tuple[str, ...] | list[str] = (),
    timestamp: Optional[datetime] = None,
) -> BacklogItem:
    """Capture a new auditable backlog item."""
    observed_at = _as_utc(timestamp or datetime.now(timezone.utc))
    criteria = _safe_criteria(acceptance_criteria)
    revision = BacklogRevision(
        version=1,
        title=title,
        body_summary=body_summary,
        acceptance_criteria=criteria,
        priority=priority,
        owner=owner,
        blocked_status=blocked_status,
        updated_by=created_by,
        updated_at=observed_at,
        evidence_refs=(source_ref,),
    )
    audit = BacklogAuditEntry(
        action=BacklogAuditAction.CAPTURE,
        actor=created_by,
        timestamp=observed_at,
        reason="captured",
        evidence_refs=(source_ref,),
    )
    return BacklogItem(
        item_id=item_id,
        title=title,
        body_summary=body_summary,
        source=source,
        source_ref=source_ref,
        state=BacklogItemState.CAPTURED,
        scope=scope,
        priority=priority,
        owner=owner,
        blocked_status=blocked_status,
        acceptance_criteria=criteria,
        created_at=observed_at,
        created_by=created_by,
        updated_at=observed_at,
        updated_by=created_by,
        revision=1,
        revisions=(revision,),
        audit_trail=(audit,),
    )


def modify_backlog_item(
    item: BacklogItem,
    updated_by: str,
    title: Optional[str] = None,
    body_summary: Optional[str] = None,
    acceptance_criteria: Optional[tuple[str, ...] | list[str]] = None,
    priority: Optional[BacklogPriority] = None,
    owner: Optional[BacklogOwner] = None,
    blocked_status: Optional[BacklogBlockedStatus] = None,
    evidence_refs: tuple[str, ...] | list[str] = (),
    timestamp: Optional[datetime] = None,
) -> BacklogItem:
    """Modify editable fields while preserving revision history."""
    _assert_not_archived(item)
    observed_at = _as_utc(timestamp or datetime.now(timezone.utc))
    next_title = title if title is not None else item.title
    next_body = body_summary if body_summary is not None else item.body_summary
    next_criteria = (
        _safe_criteria(acceptance_criteria)
        if acceptance_criteria is not None
        else item.acceptance_criteria
    )
    next_priority = priority or item.priority
    next_owner = owner or item.owner
    next_blocked = blocked_status or item.blocked_status
    next_revision = item.revision + 1
    next_state = (
        BacklogItemState.CAPTURED
        if item.state == BacklogItemState.REJECTED
        else item.state
    )
    revision = BacklogRevision(
        version=next_revision,
        title=next_title,
        body_summary=next_body,
        acceptance_criteria=next_criteria,
        priority=next_priority,
        owner=next_owner,
        blocked_status=next_blocked,
        updated_by=updated_by,
        updated_at=observed_at,
        evidence_refs=tuple(evidence_refs),
    )
    audit = BacklogAuditEntry(
        action=BacklogAuditAction.MODIFY,
        actor=updated_by,
        timestamp=observed_at,
        reason="modified",
        evidence_refs=tuple(evidence_refs),
    )
    return _replace_item(
        item,
        title=next_title,
        body_summary=next_body,
        state=next_state,
        deferred_until=(
            None if next_state != BacklogItemState.DEFERRED else item.deferred_until
        ),
        priority=next_priority,
        owner=next_owner,
        blocked_status=next_blocked,
        acceptance_criteria=next_criteria,
        updated_at=observed_at,
        updated_by=updated_by,
        revision=next_revision,
        revisions=item.revisions + (revision,),
        audit_trail=item.audit_trail + (audit,),
    )


def approve_backlog_item(
    item: BacklogItem,
    approved_by: str,
    evidence_refs: tuple[str, ...] | list[str],
    timestamp: Optional[datetime] = None,
) -> BacklogItem:
    """Move an item into active planning/build consideration."""
    _assert_not_archived(item)
    if item.state not in (BacklogItemState.CAPTURED, BacklogItemState.DEFERRED):
        raise BacklogValidationError(
            "only captured or deferred items can be approved"
        )
    refs = _safe_refs(evidence_refs, "approve_backlog_item.evidence_refs")
    if not refs:
        raise BacklogValidationError("approval requires evidence_refs")
    return _transition_item(
        item,
        BacklogItemState.APPROVED,
        BacklogAuditAction.APPROVE,
        approved_by,
        "approved",
        refs,
        timestamp,
    )


def reject_backlog_item(
    item: BacklogItem,
    rejected_by: str,
    reason: str,
    timestamp: Optional[datetime] = None,
) -> BacklogItem:
    """Reject an item without deleting audit history."""
    _assert_not_archived(item)
    _assert_not_task_drafted(item)
    return _transition_item(
        item,
        BacklogItemState.REJECTED,
        BacklogAuditAction.REJECT,
        rejected_by,
        reason,
        (),
        timestamp,
    )


def deny_backlog_item(
    item: BacklogItem,
    denied_by: str,
    reason: str,
    timestamp: Optional[datetime] = None,
) -> BacklogItem:
    """Deny an item without deleting audit history."""
    return reject_backlog_item(
        item,
        rejected_by=denied_by,
        reason=reason,
        timestamp=timestamp,
    )


def defer_backlog_item(
    item: BacklogItem,
    deferred_by: str,
    reason: str,
    deferred_until: datetime,
    timestamp: Optional[datetime] = None,
) -> BacklogItem:
    """Defer an item without deleting audit history."""
    _assert_not_archived(item)
    _assert_not_task_drafted(item)
    observed_at = _as_utc(timestamp or datetime.now(timezone.utc))
    until = _as_utc(deferred_until)
    if until <= observed_at:
        raise BacklogValidationError("deferred_until must be after timestamp")
    audit = BacklogAuditEntry(
        action=BacklogAuditAction.DEFER,
        actor=deferred_by,
        timestamp=observed_at,
        reason=reason,
    )
    return _replace_item(
        item,
        state=BacklogItemState.DEFERRED,
        deferred_until=until,
        updated_at=observed_at,
        updated_by=deferred_by,
        audit_trail=item.audit_trail + (audit,),
    )


def link_backlog_item_scope(
    item: BacklogItem,
    scope: BacklogScope,
    linked_by: str,
    evidence_refs: tuple[str, ...] | list[str] = (),
    timestamp: Optional[datetime] = None,
) -> BacklogItem:
    """Attach a backlog item to a project, initiative, or venture."""
    _assert_not_archived(item)
    observed_at = _as_utc(timestamp or datetime.now(timezone.utc))
    audit = BacklogAuditEntry(
        action=BacklogAuditAction.LINK_SCOPE,
        actor=linked_by,
        timestamp=observed_at,
        reason="scope linked",
        evidence_refs=tuple(evidence_refs),
    )
    return _replace_item(
        item,
        scope=scope,
        updated_at=observed_at,
        updated_by=linked_by,
        audit_trail=item.audit_trail + (audit,),
    )


def convert_backlog_item_to_task_draft(
    item: BacklogItem,
    task_id: str,
    converted_by: str,
    proof_expectation: str,
    risk_tier: int,
    timestamp: Optional[datetime] = None,
) -> tuple[BacklogItem, BacklogTaskDraft]:
    """Convert an approved backlog item to a task draft without dispatching it."""
    _assert_not_archived(item)
    if item.state != BacklogItemState.APPROVED:
        raise BacklogValidationError("only approved items can become task drafts")
    observed_at = _as_utc(timestamp or datetime.now(timezone.utc))
    draft = BacklogTaskDraft(
        item_id=item.item_id,
        task_id=task_id,
        title=item.title,
        owner=item.owner,
        project_id=item.scope.project_id,
        proof_expectation=proof_expectation,
        risk_tier=risk_tier,
        acceptance_criteria=item.acceptance_criteria,
        evidence_refs=(f"backlog://{item.item_id}",),
    )
    audit = BacklogAuditEntry(
        action=BacklogAuditAction.CONVERT_TO_TASK,
        actor=converted_by,
        timestamp=observed_at,
        reason="task draft created",
        evidence_refs=draft.evidence_refs,
    )
    updated = _replace_item(
        item,
        state=BacklogItemState.TASK_DRAFTED,
        deferred_until=None,
        updated_at=observed_at,
        updated_by=converted_by,
        audit_trail=item.audit_trail + (audit,),
    )
    return updated, draft


def archive_backlog_item(
    item: BacklogItem,
    archived_by: str,
    reason: str,
    timestamp: Optional[datetime] = None,
) -> BacklogItem:
    """Archive an item intentionally without destructive deletion."""
    _assert_not_archived(item)
    observed_at = _as_utc(timestamp or datetime.now(timezone.utc))
    audit = BacklogAuditEntry(
        action=BacklogAuditAction.ARCHIVE,
        actor=archived_by,
        timestamp=observed_at,
        reason=reason,
    )
    return _replace_item(
        item,
        state=BacklogItemState.ARCHIVED,
        deferred_until=None,
        archived_at=observed_at,
        archived_by=archived_by,
        archive_reason=reason,
        updated_at=observed_at,
        updated_by=archived_by,
        audit_trail=item.audit_trail + (audit,),
    )


def import_backlog_candidates(
    batch_id: str,
    imported_by: str,
    source: BacklogSource,
    candidates: tuple[BacklogImportCandidate, ...] | list[BacklogImportCandidate],
    timestamp: Optional[datetime] = None,
) -> BacklogImportBatch:
    """Hold imported candidates for review without touching the source system."""
    return BacklogImportBatch(
        batch_id=batch_id,
        imported_by=imported_by,
        imported_at=_as_utc(timestamp or datetime.now(timezone.utc)),
        source=source,
        candidates=tuple(candidates),
        writes_back_to_source=False,
    )


def query_backlog(
    items: Iterable[BacklogItem],
    query: BacklogQuery,
) -> tuple[BacklogItem, ...]:
    """Filter backlog items by real backend fields."""
    results: list[BacklogItem] = []
    text = query.text.lower() if query.text else None
    for item in items:
        if item.state == BacklogItemState.ARCHIVED and not query.include_archived:
            continue
        if query.project_id is not None and item.scope.project_id != query.project_id:
            continue
        if query.states and item.state not in query.states:
            continue
        if query.priorities and item.priority not in query.priorities:
            continue
        if query.owners and item.owner not in query.owners:
            continue
        if query.blocked_statuses and item.blocked_status not in query.blocked_statuses:
            continue
        if text and text not in f"{item.title} {item.body_summary}".lower():
            continue
        results.append(item)
    return tuple(
        sorted(
            results,
            key=lambda item: (
                _PRIORITY_ORDER[item.priority],
                _as_utc(item.updated_at),
                item.item_id,
            ),
        )
    )


def to_goal_objective_ref(item: BacklogItem) -> Any:
    """Project a backlog item into the existing Goal Runtime objective ref."""
    from .goal_runtime import GoalObjectiveRef, SHORT_LABEL_MAX

    return GoalObjectiveRef(
        id=item.item_id,
        label=_bounded_label(item.title, SHORT_LABEL_MAX),
        source="backlog",
    )


def serialize_backlog(items: Iterable[BacklogItem]) -> dict[str, Any]:
    """Serialize backlog records to a JSON-ready document."""
    return {
        "tasks": [item.to_dict() for item in items],
        "schema": "meridian.backlog.v1",
    }


def deserialize_backlog(data: dict[str, Any]) -> tuple[BacklogItem, ...]:
    """Load backlog records from a JSON-ready document."""
    return tuple(BacklogItem.from_dict(dict(item)) for item in data.get("tasks", ()))


def save_backlog(path: str | Path, items: Iterable[BacklogItem]) -> None:
    """Persist backlog records to a caller-supplied JSON path."""
    target = Path(path)
    target.write_text(
        json.dumps(serialize_backlog(items), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def load_backlog(path: str | Path) -> tuple[BacklogItem, ...]:
    """Load backlog records from a caller-supplied JSON path."""
    source = Path(path)
    if not source.exists():
        return ()
    return deserialize_backlog(json.loads(source.read_text(encoding="utf-8")))


_PRIORITY_ORDER = {
    BacklogPriority.URGENT: 0,
    BacklogPriority.HIGH: 1,
    BacklogPriority.NORMAL: 2,
    BacklogPriority.LOW: 3,
}

_UNSAFE_NORMALIZED = (
    "secret",
    "credential",
    "password",
    "token",
    "apikey",
    "rawprompt",
    "workerchat",
    "providerresponse",
    "transcript",
    "localpath",
)


def _replace_item(item: BacklogItem, **changes: Any) -> BacklogItem:
    data = {**item.__dict__, **changes}
    return BacklogItem(**data)


def _transition_item(
    item: BacklogItem,
    state: BacklogItemState,
    action: BacklogAuditAction,
    actor: str,
    reason: str,
    evidence_refs: tuple[str, ...] | list[str],
    timestamp: Optional[datetime],
) -> BacklogItem:
    observed_at = _as_utc(timestamp or datetime.now(timezone.utc))
    audit = BacklogAuditEntry(
        action=action,
        actor=actor,
        timestamp=observed_at,
        reason=reason,
        evidence_refs=tuple(evidence_refs),
    )
    return _replace_item(
        item,
        state=state,
        deferred_until=None if state != BacklogItemState.DEFERRED else item.deferred_until,
        updated_at=observed_at,
        updated_by=actor,
        audit_trail=item.audit_trail + (audit,),
    )


def _assert_not_archived(item: BacklogItem) -> None:
    if item.state == BacklogItemState.ARCHIVED:
        raise BacklogValidationError("archived backlog items cannot be mutated")


def _assert_not_task_drafted(item: BacklogItem) -> None:
    if item.state == BacklogItemState.TASK_DRAFTED:
        raise BacklogValidationError("task-drafted backlog items cannot be rerouted")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_datetime(value: str) -> datetime:
    return _as_utc(datetime.fromisoformat(value))


def _normalized(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _looks_like_path(value: str) -> bool:
    if "://" in value:
        return not value.startswith(_ALLOWED_URI_PREFIXES)
    tokens = re.split(r"\s+", value.strip())
    for token in tokens:
        cleaned = token.strip(".,;:()[]{}'\"")
        if (
            "\\" in cleaned
            or cleaned.startswith("/")
            or cleaned.startswith("./")
            or cleaned.startswith("../")
            or (len(cleaned) > 2 and cleaned[1] == ":" and cleaned[0].isalpha())
            or _RELATIVE_PATH_PATTERN.search(cleaned)
        ):
            return True
    return False


def _assert_display_safe(value: str, field_name: str) -> None:
    normalized = _normalized(value)
    if any(fragment in normalized for fragment in _UNSAFE_NORMALIZED):
        raise BacklogValidationError(f"{field_name} contains unsafe content")
    if _looks_like_path(value):
        raise BacklogValidationError(f"{field_name} contains a local path")


def _safe_text(
    value: str,
    field_name: str,
    max_len: int,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        raise BacklogValidationError(f"{field_name} must be a string")
    text = value.strip()
    if not text and not allow_empty:
        raise BacklogValidationError(f"{field_name} is required")
    if len(text) > max_len:
        raise BacklogValidationError(f"{field_name} exceeds {max_len} chars")
    _assert_display_safe(text, field_name)
    return text


def _safe_label(value: str, field_name: str) -> str:
    text = _safe_text(value, field_name, SHORT_TEXT_MAX)
    if not all(ch.isalnum() or ch in "._:-" for ch in text):
        raise BacklogValidationError(f"{field_name} must be a safe label")
    return text


def _safe_ref(value: str, field_name: str) -> str:
    text = _safe_text(value, field_name, EVIDENCE_REF_MAX)
    if not all(ch.isalnum() or ch in "._:/#-" for ch in text):
        raise BacklogValidationError(f"{field_name} must be a safe ref")
    return text


def _safe_refs(refs: tuple[str, ...] | list[str], field_name: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_safe_ref(ref, field_name) for ref in refs or ()))


def _safe_criteria(criteria: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(
        _safe_text(criterion, "acceptance_criteria", CRITERION_MAX)
        for criterion in criteria or ()
    )


def _bounded_label(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 3].rstrip() + "..."


_ALLOWED_URI_PREFIXES = ("user://", "proof://", "polaris://", "backlog://")
_RELATIVE_PATH_PATTERN = re.compile(
    r"(?:^|[A-Za-z0-9_.-]/)[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\.[A-Za-z0-9]+$"
)
