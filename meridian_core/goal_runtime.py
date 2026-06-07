"""Goal Runtime domain — V3 first minimal slice.

Pure-Python, deterministic, dependency-free domain objects and validation
helpers authorized by ``docs/v3-goal-runtime-contract.md``. No persistence,
no model calls, no network, no UI, no FileMap entry. Implementation slice
ships only the typed records, the closed enums, the transition validator,
the proof-reference requirement helper, and a display-safe serializer.

The runtime split below is normative (see contract §"Harness Ownership"):

* ``Prime``    — creation; ``ACTIVE -> COMPLETE``.
* ``Compass``  — every transition among ``ACTIVE``, ``BLOCKED``,
                 ``USAGE_LIMITED``; ``continuation_policy`` edits after
                 creation.
* ``Echo``     — ``lineage`` appends.
* ``Beacon``   — ``telemetry`` snapshot appends.
* ``Aegis``    — ``proof_trail_ref``; never writes ``status``.

Multi-writer fields are a contract bug. The validator in this module is
the runtime expression of "single writer per transition".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Field caps (from the contract)
# ---------------------------------------------------------------------------

OBJECTIVE_TEXT_MAX = 280
COMPLETION_SUMMARY_MAX = 200
BLOCKED_SUMMARY_MAX = 200
SNAPSHOT_NOTE_MAX = 200
SHORT_LABEL_MAX = 120


# ---------------------------------------------------------------------------
# Closed enums
# ---------------------------------------------------------------------------


class GoalStatus(Enum):
    """Closed lifecycle of a goal record."""

    ACTIVE = "active"
    BLOCKED = "blocked"
    USAGE_LIMITED = "usage_limited"
    COMPLETE = "complete"


class HarnessWriter(Enum):
    """Harnesses authorized to write goal fields under the contract."""

    PRIME = "Prime"
    COMPASS = "Compass"
    ECHO = "Echo"
    BEACON = "Beacon"
    AEGIS = "Aegis"
    SESSION_LIFECYCLE = "SessionLifecycle"


class GoalBlockedReasonKind(Enum):
    """Closed enum of blocker kinds (contract §`GoalBlockedReason`)."""

    MISSING_PROOF = "missing_proof"
    FAILED_PROOF = "failed_proof"
    HUMAN_GATE = "human_gate"
    BRANCH_PERMISSION_REQUIRED = "branch_permission_required"
    WORKTREE_COLLISION = "worktree_collision"
    OPEN_REVIEW_GATE = "open_review_gate"
    MISSING_FILEMAP_ENTRY = "missing_filemap_entry"
    MISSING_ECHO_CONTEXT = "missing_echo_context"
    MISSING_ATLAS_CONTEXT = "missing_atlas_context"
    POLICY_DENIED = "policy_denied"
    DEPENDENCY_INCOMPLETE = "dependency_incomplete"
    OPERATOR_HOLD = "operator_hold"
    EXTERNAL_DEPENDENCY = "external_dependency"


class UsageLimitResumeKind(Enum):
    WAIT_FOR_SIGNAL = "wait_for_signal"
    WAIT_FOR_TIMEOUT = "wait_for_timeout"
    MANUAL = "manual"


class BlockResumeKind(Enum):
    MANUAL = "manual"
    AUTO_ON_DEPENDENCY_CLEAR = "auto_on_dependency_clear"
    EXTERNAL_SIGNAL = "external_signal"


# Allowed status transitions: source -> frozenset of permitted targets.
# COMPLETE is terminal (absent from the map).
_ALLOWED_TRANSITIONS: dict[GoalStatus, frozenset[GoalStatus]] = {
    GoalStatus.ACTIVE: frozenset(
        {GoalStatus.BLOCKED, GoalStatus.USAGE_LIMITED, GoalStatus.COMPLETE}
    ),
    GoalStatus.BLOCKED: frozenset({GoalStatus.ACTIVE, GoalStatus.USAGE_LIMITED}),
    GoalStatus.USAGE_LIMITED: frozenset({GoalStatus.ACTIVE, GoalStatus.BLOCKED}),
    GoalStatus.COMPLETE: frozenset(),
}

# Authoring matrix: (from, to) -> the single harness allowed to write the
# transition. Creation (None -> ACTIVE) is Prime. ACTIVE -> COMPLETE is
# Prime. Every other transition among non-terminal states is Compass.
_TRANSITION_AUTHOR: dict[tuple[GoalStatus | None, GoalStatus], HarnessWriter] = {
    (None, GoalStatus.ACTIVE): HarnessWriter.PRIME,
    (GoalStatus.ACTIVE, GoalStatus.COMPLETE): HarnessWriter.PRIME,
    (GoalStatus.ACTIVE, GoalStatus.BLOCKED): HarnessWriter.COMPASS,
    (GoalStatus.ACTIVE, GoalStatus.USAGE_LIMITED): HarnessWriter.COMPASS,
    (GoalStatus.BLOCKED, GoalStatus.ACTIVE): HarnessWriter.COMPASS,
    (GoalStatus.BLOCKED, GoalStatus.USAGE_LIMITED): HarnessWriter.COMPASS,
    (GoalStatus.USAGE_LIMITED, GoalStatus.ACTIVE): HarnessWriter.COMPASS,
    (GoalStatus.USAGE_LIMITED, GoalStatus.BLOCKED): HarnessWriter.COMPASS,
}

# Kinds that always require a human gate before resume regardless of policy.
_ALWAYS_HUMAN_GATE_KINDS: frozenset[GoalBlockedReasonKind] = frozenset(
    {
        GoalBlockedReasonKind.HUMAN_GATE,
        GoalBlockedReasonKind.BRANCH_PERMISSION_REQUIRED,
        GoalBlockedReasonKind.WORKTREE_COLLISION,
        GoalBlockedReasonKind.POLICY_DENIED,
    }
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class GoalRuntimeError(ValueError):
    """Domain error for the Goal Runtime."""


class DisplaySafetyError(GoalRuntimeError):
    """Raised when a field would carry display-unsafe content."""


class TransitionError(GoalRuntimeError):
    """Raised for forbidden transitions or wrong-author transitions."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_utc(ts: datetime, field_name: str) -> datetime:
    if not isinstance(ts, datetime):
        raise GoalRuntimeError(f"{field_name} must be a datetime, got {type(ts).__name__}")
    if ts.tzinfo is None:
        raise GoalRuntimeError(f"{field_name} must be timezone-aware (UTC)")
    return ts.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Deterministic unsafe-content patterns
# ---------------------------------------------------------------------------
#
# Contract §"Display-Safety Rule" and §"Safety Constraints" require that no
# field carries "free-form model output, embedded prompts, executable
# payload, or HTML", and §"What Telemetry Does Not Do" forbids
# session-private data (transcripts, prompt bodies, model output). These
# regexes are a deterministic, dependency-free reject list applied to every
# free-text and short-label field. They never rewrite input — they raise
# DisplaySafetyError. The list is intentionally conservative and biased
# toward rejecting unfamiliar content rather than guessing intent.

_UNSAFE_HTML_TAG = re.compile(r"<[A-Za-z!/]")  # <tag, </tag, <!doctype
_CHAT_TEMPLATE_TOKEN = re.compile(
    r"<\|(?:im_start|im_end|endoftext|system|user|assistant)\|>",
    re.IGNORECASE,
)
_CHAT_ROLE_LINE = re.compile(
    r"(?:^|\s)(?:system|user|assistant)\s*:\s+\S",
    re.IGNORECASE,
)
_PROMPT_OVERRIDE = re.compile(
    r"\bignore\s+(?:prior|previous|all\s+prior|the\s+above)\s+instructions?\b",
    re.IGNORECASE,
)
_CODE_FENCE = re.compile(r"```")
_JAVASCRIPT_URI = re.compile(r"\bjavascript\s*:", re.IGNORECASE)
_JS_HANDLER_ATTR = re.compile(r"\bon[a-z]{3,15}\s*=", re.IGNORECASE)
_API_KEY_ASSIGN = re.compile(
    r"\b(?:api[_\-]?key|password|secret|access[_\-]?token)\s*[:=]",
    re.IGNORECASE,
)
_AUTHZ_BEARER = re.compile(r"\bauthorization\s*:\s*bearer\b", re.IGNORECASE)
_BEARER_TOKEN = re.compile(r"\bbearer\s+[A-Za-z0-9._\-]{12,}", re.IGNORECASE)
_OPENAI_KEY = re.compile(r"\bsk-[A-Za-z0-9]{16,}")
_GITHUB_TOKEN = re.compile(r"\b(?:ghp_|ghs_|gho_)[A-Za-z0-9]{16,}")
_GITHUB_PAT = re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}")
_AWS_ACCESS_KEY = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_PRIVATE_KEY_BLOCK = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
_JWT_LIKE = re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}")

_UNSAFE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (_UNSAFE_HTML_TAG, "HTML markup"),
    (_CHAT_TEMPLATE_TOKEN, "chat-template role token"),
    (_CHAT_ROLE_LINE, "transcript role line"),
    (_PROMPT_OVERRIDE, "prompt-override phrase"),
    (_CODE_FENCE, "code fence"),
    (_JAVASCRIPT_URI, "javascript: URI"),
    (_JS_HANDLER_ATTR, "javascript handler attribute"),
    (_API_KEY_ASSIGN, "credential assignment"),
    (_AUTHZ_BEARER, "Authorization header"),
    (_BEARER_TOKEN, "Bearer token"),
    (_OPENAI_KEY, "OpenAI-style API key"),
    (_GITHUB_TOKEN, "GitHub token"),
    (_GITHUB_PAT, "GitHub PAT"),
    (_AWS_ACCESS_KEY, "AWS access key id"),
    (_PRIVATE_KEY_BLOCK, "PEM private key block"),
    (_JWT_LIKE, "JWT-shaped token"),
)


def _assert_display_safe_content(value: str, field_name: str) -> None:
    """Reject strings that look like prompts, transcripts, HTML, executable
    payloads, or credentials.

    Deterministic and offline: no model calls, no network. Rewriting is
    explicitly out of scope per the contract — unsafe content raises
    ``DisplaySafetyError`` rather than being silently sanitized.
    """
    for ch in value:
        code = ord(ch)
        if code < 0x20 or code == 0x7F:
            raise DisplaySafetyError(
                f"{field_name} must not contain control characters"
            )
    for pattern, label in _UNSAFE_PATTERNS:
        if pattern.search(value):
            raise DisplaySafetyError(
                f"{field_name} appears to carry unsafe content ({label})"
            )


def _enforce_short_text(value: str, field_name: str, max_len: int) -> str:
    if not isinstance(value, str):
        raise DisplaySafetyError(f"{field_name} must be a string")
    if len(value) > max_len:
        raise DisplaySafetyError(
            f"{field_name} exceeds {max_len} chars (got {len(value)})"
        )
    _assert_display_safe_content(value, field_name)
    return value


def _enforce_short_label(value: str, field_name: str) -> str:
    return _enforce_short_text(value, field_name, SHORT_LABEL_MAX)


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GoalObjectiveRef:
    """Structured reference to a backlog / doc / contract record."""

    id: str
    label: str
    source: str  # short tag: backlog, doc, contract, ...

    def __post_init__(self) -> None:
        _enforce_short_label(self.id, "GoalObjectiveRef.id")
        _enforce_short_label(self.label, "GoalObjectiveRef.label")
        _enforce_short_label(self.source, "GoalObjectiveRef.source")

    def to_safe_dict(self) -> dict[str, str]:
        return {"id": self.id, "label": self.label, "source": self.source}


@dataclass(frozen=True)
class ProofTrailRef:
    """Reference to an Aegis ProofTrail handle. Never carries proof contents."""

    id: str
    label: str

    def __post_init__(self) -> None:
        _enforce_short_label(self.id, "ProofTrailRef.id")
        _enforce_short_label(self.label, "ProofTrailRef.label")

    def to_safe_dict(self) -> dict[str, str]:
        return {"id": self.id, "label": self.label}


@dataclass(frozen=True)
class GoalBlockedReason:
    """Display-safe blocker record."""

    kind: GoalBlockedReasonKind
    summary: str
    recorded_at: datetime
    recorded_by: HarnessWriter
    reference: GoalObjectiveRef | ProofTrailRef | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, GoalBlockedReasonKind):
            raise DisplaySafetyError("GoalBlockedReason.kind must be a closed enum value")
        _enforce_short_text(self.summary, "GoalBlockedReason.summary", BLOCKED_SUMMARY_MAX)
        # Contract §"GoalBlockedReason": for status-write-induced blocks
        # `recorded_by` is always Compass. Goals never enter BLOCKED or
        # USAGE_LIMITED at creation — Prime creates into ACTIVE only — so
        # there is no Prime-authored blocker case to preserve.
        if self.recorded_by is not HarnessWriter.COMPASS:
            raise DisplaySafetyError(
                "GoalBlockedReason.recorded_by must be Compass (sole writer of "
                "status-write-induced blocks)"
            )
        if self.reference is not None and not isinstance(
            self.reference, (GoalObjectiveRef, ProofTrailRef)
        ):
            raise DisplaySafetyError(
                "GoalBlockedReason.reference must be None, GoalObjectiveRef, "
                "or ProofTrailRef"
            )
        object.__setattr__(
            self, "recorded_at", _ensure_utc(self.recorded_at, "GoalBlockedReason.recorded_at")
        )

    def to_safe_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "kind": self.kind.value,
            "summary": self.summary,
            "recorded_at": self.recorded_at.isoformat(),
            "recorded_by": self.recorded_by.value,
        }
        if self.reference is not None:
            out["reference"] = self.reference.to_safe_dict()
        return out


# ----- telemetry windows ----------------------------------------------------


@dataclass(frozen=True)
class GoalTokenWindow:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    provider_label: str

    def __post_init__(self) -> None:
        for name in ("prompt_tokens", "completion_tokens", "total_tokens"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise DisplaySafetyError(
                    f"GoalTokenWindow.{name} must be a non-negative int"
                )
        _enforce_short_label(self.provider_label, "GoalTokenWindow.provider_label")

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "provider_label": self.provider_label,
        }


@dataclass(frozen=True)
class GoalTimeWindow:
    wall_seconds_active: float
    wall_seconds_blocked: float
    wall_seconds_usage_limited: float

    def __post_init__(self) -> None:
        for name in (
            "wall_seconds_active",
            "wall_seconds_blocked",
            "wall_seconds_usage_limited",
        ):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                raise DisplaySafetyError(
                    f"GoalTimeWindow.{name} must be a non-negative number"
                )

    def to_safe_dict(self) -> dict[str, float]:
        return {
            "wall_seconds_active": float(self.wall_seconds_active),
            "wall_seconds_blocked": float(self.wall_seconds_blocked),
            "wall_seconds_usage_limited": float(self.wall_seconds_usage_limited),
        }


@dataclass(frozen=True)
class GoalBudgetWindow:
    cost_units: float
    cost_currency: str
    provider_label: str

    def __post_init__(self) -> None:
        if not isinstance(self.cost_units, (int, float)) or isinstance(
            self.cost_units, bool
        ) or self.cost_units < 0:
            raise DisplaySafetyError("GoalBudgetWindow.cost_units must be non-negative")
        _enforce_short_label(self.cost_currency, "GoalBudgetWindow.cost_currency")
        _enforce_short_label(self.provider_label, "GoalBudgetWindow.provider_label")

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "cost_units": float(self.cost_units),
            "cost_currency": self.cost_currency,
            "provider_label": self.provider_label,
        }


@dataclass(frozen=True)
class GoalSessionWindow:
    dispatched_sessions: int
    completed_sessions: int
    failed_sessions: int

    def __post_init__(self) -> None:
        for name in (
            "dispatched_sessions",
            "completed_sessions",
            "failed_sessions",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise DisplaySafetyError(
                    f"GoalSessionWindow.{name} must be a non-negative int"
                )

    def to_safe_dict(self) -> dict[str, int]:
        return {
            "dispatched_sessions": self.dispatched_sessions,
            "completed_sessions": self.completed_sessions,
            "failed_sessions": self.failed_sessions,
        }


@dataclass(frozen=True)
class GoalTelemetrySnapshot:
    """Beacon-authored, append-only telemetry snapshot."""

    snapshot_id: str
    recorded_at: datetime
    token_source: str
    cost_source: str
    token_window: GoalTokenWindow
    time_window: GoalTimeWindow
    budget_window: GoalBudgetWindow
    session_window: GoalSessionWindow
    recorded_by: HarnessWriter = HarnessWriter.BEACON
    note: str | None = None

    def __post_init__(self) -> None:
        if self.recorded_by is not HarnessWriter.BEACON:
            raise DisplaySafetyError(
                "GoalTelemetrySnapshot.recorded_by must be Beacon (sole appender)"
            )
        _enforce_short_label(self.snapshot_id, "GoalTelemetrySnapshot.snapshot_id")
        _enforce_short_label(self.token_source, "GoalTelemetrySnapshot.token_source")
        _enforce_short_label(self.cost_source, "GoalTelemetrySnapshot.cost_source")
        if self.note is not None:
            _enforce_short_text(self.note, "GoalTelemetrySnapshot.note", SNAPSHOT_NOTE_MAX)
        object.__setattr__(
            self,
            "recorded_at",
            _ensure_utc(self.recorded_at, "GoalTelemetrySnapshot.recorded_at"),
        )

    def to_safe_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "snapshot_id": self.snapshot_id,
            "recorded_at": self.recorded_at.isoformat(),
            "recorded_by": self.recorded_by.value,
            "token_source": self.token_source,
            "cost_source": self.cost_source,
            "token_window": self.token_window.to_safe_dict(),
            "time_window": self.time_window.to_safe_dict(),
            "budget_window": self.budget_window.to_safe_dict(),
            "session_window": self.session_window.to_safe_dict(),
        }
        if self.note is not None:
            out["note"] = self.note
        return out


# ----- continuation policy --------------------------------------------------


@dataclass(frozen=True)
class GoalContinuationPolicy:
    max_active_attempts: int
    cooldown_seconds: int
    usage_limit_resume_kind: UsageLimitResumeKind
    block_resume_kind: BlockResumeKind
    proof_required_for_resume: bool
    human_gate_on_resume_kinds: tuple[GoalBlockedReasonKind, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.max_active_attempts, int)
            or isinstance(self.max_active_attempts, bool)
            or self.max_active_attempts < 1
        ):
            raise GoalRuntimeError(
                "GoalContinuationPolicy.max_active_attempts must be a positive int"
            )
        if (
            not isinstance(self.cooldown_seconds, int)
            or isinstance(self.cooldown_seconds, bool)
            or self.cooldown_seconds < 0
        ):
            raise GoalRuntimeError(
                "GoalContinuationPolicy.cooldown_seconds must be a non-negative int"
            )
        if not isinstance(self.usage_limit_resume_kind, UsageLimitResumeKind):
            raise GoalRuntimeError("usage_limit_resume_kind must be a closed enum value")
        if not isinstance(self.block_resume_kind, BlockResumeKind):
            raise GoalRuntimeError("block_resume_kind must be a closed enum value")
        for kind in self.human_gate_on_resume_kinds:
            if not isinstance(kind, GoalBlockedReasonKind):
                raise GoalRuntimeError(
                    "human_gate_on_resume_kinds entries must be GoalBlockedReasonKind values"
                )
        # Always-human-gate kinds must be present.
        missing = _ALWAYS_HUMAN_GATE_KINDS.difference(self.human_gate_on_resume_kinds)
        if missing:
            object.__setattr__(
                self,
                "human_gate_on_resume_kinds",
                tuple(
                    sorted(
                        set(self.human_gate_on_resume_kinds) | _ALWAYS_HUMAN_GATE_KINDS,
                        key=lambda k: k.value,
                    )
                ),
            )

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "max_active_attempts": self.max_active_attempts,
            "cooldown_seconds": self.cooldown_seconds,
            "usage_limit_resume_kind": self.usage_limit_resume_kind.value,
            "block_resume_kind": self.block_resume_kind.value,
            "proof_required_for_resume": self.proof_required_for_resume,
            "human_gate_on_resume_kinds": [
                k.value for k in self.human_gate_on_resume_kinds
            ],
        }


# ----- lineage --------------------------------------------------------------


@dataclass(frozen=True)
class GoalLineageEntry:
    """Echo-authored audit entry for a goal-record write."""

    entry_id: str
    recorded_at: datetime
    prior_status: GoalStatus | None
    new_status: GoalStatus
    written_by: HarnessWriter
    note: str | None = None
    recorded_by: HarnessWriter = HarnessWriter.ECHO

    def __post_init__(self) -> None:
        if self.recorded_by is not HarnessWriter.ECHO:
            raise DisplaySafetyError(
                "GoalLineageEntry.recorded_by must be Echo (sole appender of lineage)"
            )
        _enforce_short_label(self.entry_id, "GoalLineageEntry.entry_id")
        if self.note is not None:
            _enforce_short_text(self.note, "GoalLineageEntry.note", SNAPSHOT_NOTE_MAX)
        if self.prior_status is not None and not isinstance(self.prior_status, GoalStatus):
            raise DisplaySafetyError("GoalLineageEntry.prior_status must be a GoalStatus")
        if not isinstance(self.new_status, GoalStatus):
            raise DisplaySafetyError("GoalLineageEntry.new_status must be a GoalStatus")
        if not isinstance(self.written_by, HarnessWriter):
            raise DisplaySafetyError("GoalLineageEntry.written_by must be a HarnessWriter")
        object.__setattr__(
            self, "recorded_at", _ensure_utc(self.recorded_at, "GoalLineageEntry.recorded_at")
        )

    def to_safe_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "entry_id": self.entry_id,
            "recorded_at": self.recorded_at.isoformat(),
            "prior_status": self.prior_status.value if self.prior_status else None,
            "new_status": self.new_status.value,
            "written_by": self.written_by.value,
            "recorded_by": self.recorded_by.value,
        }
        if self.note is not None:
            out["note"] = self.note
        return out


# ----- goal record ----------------------------------------------------------


@dataclass(frozen=True)
class GoalRecord:
    """Durable, display-safe goal object."""

    goal_id: str
    project: str
    objective_text: str
    owners: tuple[HarnessWriter, ...]
    status: GoalStatus
    risk_tier: int
    continuation_policy: GoalContinuationPolicy
    created_at: datetime
    updated_at: datetime
    contract_version: str
    objective_ref: GoalObjectiveRef | None = None
    telemetry: tuple[GoalTelemetrySnapshot, ...] = ()
    lineage: tuple[GoalLineageEntry, ...] = ()
    proof_trail_ref: ProofTrailRef | None = None
    blocked_reason: GoalBlockedReason | None = None
    completion_summary: str | None = None
    final_proof_ref: ProofTrailRef | None = None
    dispatched_sessions: int = 0
    blocked_occurrences: int = 0
    usage_limited_occurrences: int = 0

    def __post_init__(self) -> None:
        _enforce_short_label(self.goal_id, "GoalRecord.goal_id")
        _enforce_short_label(self.project, "GoalRecord.project")
        _enforce_short_text(
            self.objective_text, "GoalRecord.objective_text", OBJECTIVE_TEXT_MAX
        )
        _enforce_short_label(self.contract_version, "GoalRecord.contract_version")

        if not isinstance(self.status, GoalStatus):
            raise DisplaySafetyError("GoalRecord.status must be a GoalStatus enum value")
        if not isinstance(self.risk_tier, int) or isinstance(self.risk_tier, bool):
            raise GoalRuntimeError("GoalRecord.risk_tier must be an int")
        if not 1 <= self.risk_tier <= 4:
            raise GoalRuntimeError("GoalRecord.risk_tier must be in 1..4")
        if not self.owners or HarnessWriter.PRIME not in self.owners:
            raise GoalRuntimeError("GoalRecord.owners must always include Prime")
        for owner in self.owners:
            if not isinstance(owner, HarnessWriter):
                raise DisplaySafetyError("GoalRecord.owners must contain HarnessWriter values")
        if self.objective_ref is not None and not isinstance(
            self.objective_ref, GoalObjectiveRef
        ):
            raise DisplaySafetyError("GoalRecord.objective_ref must be a GoalObjectiveRef")
        if self.proof_trail_ref is not None and not isinstance(
            self.proof_trail_ref, ProofTrailRef
        ):
            raise DisplaySafetyError(
                "GoalRecord.proof_trail_ref must be a ProofTrailRef"
            )
        if self.final_proof_ref is not None and not isinstance(
            self.final_proof_ref, ProofTrailRef
        ):
            raise DisplaySafetyError(
                "GoalRecord.final_proof_ref must be a ProofTrailRef"
            )

        # status-coupled fields
        in_blocked_states = self.status in {GoalStatus.BLOCKED, GoalStatus.USAGE_LIMITED}
        if in_blocked_states and self.blocked_reason is None:
            raise GoalRuntimeError(
                f"GoalRecord.blocked_reason is required when status is {self.status.value}"
            )
        if not in_blocked_states and self.blocked_reason is not None:
            raise GoalRuntimeError(
                "GoalRecord.blocked_reason is only valid when status is BLOCKED or USAGE_LIMITED"
            )
        if (
            self.status is GoalStatus.USAGE_LIMITED
            and self.blocked_reason is not None
            and self.blocked_reason.kind is not GoalBlockedReasonKind.EXTERNAL_DEPENDENCY
        ):
            raise GoalRuntimeError(
                "USAGE_LIMITED goals must carry blocked_reason kind EXTERNAL_DEPENDENCY"
            )

        if self.status is GoalStatus.COMPLETE:
            if self.completion_summary is None:
                raise GoalRuntimeError(
                    "GoalRecord.completion_summary is required when status is COMPLETE"
                )
            _enforce_short_text(
                self.completion_summary,
                "GoalRecord.completion_summary",
                COMPLETION_SUMMARY_MAX,
            )
        else:
            if self.completion_summary is not None:
                raise GoalRuntimeError(
                    "GoalRecord.completion_summary is only valid when status is COMPLETE"
                )

        for snap in self.telemetry:
            if not isinstance(snap, GoalTelemetrySnapshot):
                raise DisplaySafetyError(
                    "GoalRecord.telemetry must contain GoalTelemetrySnapshot values"
                )
        for entry in self.lineage:
            if not isinstance(entry, GoalLineageEntry):
                raise DisplaySafetyError(
                    "GoalRecord.lineage must contain GoalLineageEntry values"
                )

        for name in ("dispatched_sessions", "blocked_occurrences", "usage_limited_occurrences"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise GoalRuntimeError(f"GoalRecord.{name} must be a non-negative int")

        object.__setattr__(
            self, "created_at", _ensure_utc(self.created_at, "GoalRecord.created_at")
        )
        object.__setattr__(
            self, "updated_at", _ensure_utc(self.updated_at, "GoalRecord.updated_at")
        )

        # Proof-reference requirements (single source of truth).
        if proof_trail_ref_required(self) and self.proof_trail_ref is None:
            raise GoalRuntimeError(
                "GoalRecord.proof_trail_ref is required (risk_tier>=2, "
                "dispatched, blocked, usage-limited, or COMPLETE)"
            )
        if final_proof_ref_required(self) and self.final_proof_ref is None:
            raise GoalRuntimeError(
                "GoalRecord.final_proof_ref is required when COMPLETE and risk_tier >= 2"
            )

    def to_safe_dict(self) -> dict[str, Any]:
        """Serialize the record using only display-safe, typed fields.

        Raw prompt/model/session-private text is structurally impossible to
        emit because no field accepts it; this serializer simply walks the
        typed value objects.
        """
        out: dict[str, Any] = {
            "goal_id": self.goal_id,
            "project": self.project,
            "objective_text": self.objective_text,
            "owners": [w.value for w in self.owners],
            "status": self.status.value,
            "risk_tier": self.risk_tier,
            "continuation_policy": self.continuation_policy.to_safe_dict(),
            "telemetry": [t.to_safe_dict() for t in self.telemetry],
            "lineage": [entry.to_safe_dict() for entry in self.lineage],
            "dispatched_sessions": self.dispatched_sessions,
            "blocked_occurrences": self.blocked_occurrences,
            "usage_limited_occurrences": self.usage_limited_occurrences,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "contract_version": self.contract_version,
        }
        if self.objective_ref is not None:
            out["objective_ref"] = self.objective_ref.to_safe_dict()
        if self.proof_trail_ref is not None:
            out["proof_trail_ref"] = self.proof_trail_ref.to_safe_dict()
        if self.blocked_reason is not None:
            out["blocked_reason"] = self.blocked_reason.to_safe_dict()
        if self.completion_summary is not None:
            out["completion_summary"] = self.completion_summary
        if self.final_proof_ref is not None:
            out["final_proof_ref"] = self.final_proof_ref.to_safe_dict()
        return out


# ---------------------------------------------------------------------------
# Transition validator
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransitionDecision:
    """Outcome of validating a proposed status write."""

    allowed: bool
    expected_writer: HarnessWriter | None
    reason: str

    @property
    def ok(self) -> bool:
        return self.allowed


def expected_writer_for(
    from_status: GoalStatus | None, to_status: GoalStatus
) -> HarnessWriter | None:
    """Return the single harness authorized to write the given transition.

    ``from_status=None`` represents creation (None -> ACTIVE). Returns
    ``None`` if the transition is not allowed at all.
    """
    return _TRANSITION_AUTHOR.get((from_status, to_status))


def allowed_transitions_from(status: GoalStatus) -> frozenset[GoalStatus]:
    """Targets reachable from ``status`` (empty for terminal states)."""
    return _ALLOWED_TRANSITIONS[status]


def validate_transition(
    from_status: GoalStatus | None,
    to_status: GoalStatus,
    writer: HarnessWriter,
) -> TransitionDecision:
    """Validate a proposed status write against the closed lifecycle and
    single-writer authorship rules.

    The validator never performs the write. Callers do.
    """
    if not isinstance(to_status, GoalStatus):
        return TransitionDecision(False, None, "to_status must be a GoalStatus")
    if from_status is not None and not isinstance(from_status, GoalStatus):
        return TransitionDecision(False, None, "from_status must be GoalStatus or None")
    if not isinstance(writer, HarnessWriter):
        return TransitionDecision(False, None, "writer must be a HarnessWriter")

    if from_status is None:
        # Creation: only Prime, only into ACTIVE.
        if to_status is not GoalStatus.ACTIVE:
            return TransitionDecision(
                False, HarnessWriter.PRIME, "creation must enter ACTIVE"
            )
        if writer is not HarnessWriter.PRIME:
            return TransitionDecision(
                False, HarnessWriter.PRIME, "creation must be written by Prime"
            )
        return TransitionDecision(True, HarnessWriter.PRIME, "creation by Prime")

    if from_status is GoalStatus.COMPLETE:
        return TransitionDecision(
            False, None, "COMPLETE is terminal; no transitions allowed"
        )

    if to_status not in _ALLOWED_TRANSITIONS[from_status]:
        return TransitionDecision(
            False,
            None,
            f"forbidden transition {from_status.value} -> {to_status.value}",
        )

    expected = _TRANSITION_AUTHOR[(from_status, to_status)]
    if writer is not expected:
        return TransitionDecision(
            False,
            expected,
            f"{from_status.value} -> {to_status.value} must be written by "
            f"{expected.value}, not {writer.value}",
        )
    return TransitionDecision(True, expected, "transition allowed")


def assert_transition(
    from_status: GoalStatus | None,
    to_status: GoalStatus,
    writer: HarnessWriter,
) -> None:
    """Raise ``TransitionError`` if the transition is not allowed."""
    decision = validate_transition(from_status, to_status, writer)
    if not decision.allowed:
        raise TransitionError(decision.reason)


# ---------------------------------------------------------------------------
# Proof-reference requirement helpers
# ---------------------------------------------------------------------------


def proof_trail_ref_required(record: "GoalRecord") -> bool:
    """Return True if the contract requires ``proof_trail_ref`` on ``record``.

    Conditions (any one is sufficient): risk_tier >= 2, at least one Session
    Lifecycle dispatch, at least one BLOCKED occurrence, at least one
    USAGE_LIMITED occurrence, or status == COMPLETE.
    """
    return (
        record.risk_tier >= 2
        or record.dispatched_sessions > 0
        or record.blocked_occurrences > 0
        or record.usage_limited_occurrences > 0
        or record.status is GoalStatus.COMPLETE
    )


def final_proof_ref_required(record: "GoalRecord") -> bool:
    """Return True iff ``status == COMPLETE`` and ``risk_tier >= 2``."""
    return record.status is GoalStatus.COMPLETE and record.risk_tier >= 2


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

__all__ = [
    "OBJECTIVE_TEXT_MAX",
    "COMPLETION_SUMMARY_MAX",
    "BLOCKED_SUMMARY_MAX",
    "SNAPSHOT_NOTE_MAX",
    "GoalStatus",
    "HarnessWriter",
    "GoalBlockedReasonKind",
    "UsageLimitResumeKind",
    "BlockResumeKind",
    "GoalRuntimeError",
    "DisplaySafetyError",
    "TransitionError",
    "GoalObjectiveRef",
    "ProofTrailRef",
    "GoalBlockedReason",
    "GoalTokenWindow",
    "GoalTimeWindow",
    "GoalBudgetWindow",
    "GoalSessionWindow",
    "GoalTelemetrySnapshot",
    "GoalContinuationPolicy",
    "GoalLineageEntry",
    "GoalRecord",
    "TransitionDecision",
    "expected_writer_for",
    "allowed_transitions_from",
    "validate_transition",
    "assert_transition",
    "proof_trail_ref_required",
    "final_proof_ref_required",
]
