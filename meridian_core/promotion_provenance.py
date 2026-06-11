"""Display-safe session and promotion provenance for V2.5.

This module is intentionally pure: it plans and summarizes provenance records
from caller-provided metadata only. It does not run git commands, touch the
filesystem, inspect sessions, or mutate input state.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Optional


class BranchLeaseStatus(Enum):
    """Display-safe branch lease state for promotion review."""

    ACTIVE = "active"
    EXPIRED = "expired"
    MISSING = "missing"
    CONFLICTED = "conflicted"


class CommitIntentVerificationStatus(Enum):
    """Whether the intended promotion diff matches the observed diff summary."""

    VERIFIED = "verified"
    MISMATCH = "mismatch"
    MISSING = "missing"


class SessionFreshnessStatus(Enum):
    """Display-safe session freshness state."""

    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"


class PromotionStage(Enum):
    """Ordered promotion chain stages."""

    CANDIDATE = "candidate"
    REVIEW = "review"
    INTENT = "intent"
    MAIN = "main"


_REDACTED = "[redacted]"
_MISSING = "missing"
_CHAIN_ORDER: tuple[PromotionStage, ...] = (
    PromotionStage.CANDIDATE,
    PromotionStage.REVIEW,
    PromotionStage.INTENT,
    PromotionStage.MAIN,
)
_UNSAFE_DISPLAY_PATTERNS: tuple[str, ...] = (
    "raw prompt",
    "raw_prompt",
    "full prompt",
    "raw transcript",
    "raw_transcript",
    "full transcript",
    "raw log",
    "raw_log",
    "provider response",
    "model response",
    "secret",
    "password",
    "api_key",
    "apikey",
    "token=",
    "sk-",
    "c:\\",
    "\\users\\",
    "/users/",
    "/home/",
    "/tmp/",
    "/var/",
    "../",
    "..\\",
)
_SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@-]{0,119}$")


@dataclass(frozen=True)
class RollbackBundlePlan:
    """Display-safe rollback planning artifact for a promotion."""

    artifact_id: str
    strategy: str
    target_ref: str
    restore_ref: str
    evidence_refs: tuple[str, ...] = ()
    human_gate_required: bool = True
    executable_now: bool = False

    def to_display_dict(self) -> dict[str, object]:
        return {
            "artifact_id": _safe_ref(self.artifact_id, "rollback:plan"),
            "strategy": _safe_token(self.strategy, "manual_review"),
            "target_ref": _safe_ref(self.target_ref, "target_ref_missing"),
            "restore_ref": _safe_ref(self.restore_ref, "restore_ref_missing"),
            "evidence_refs": _safe_refs(self.evidence_refs),
            "human_gate_required": self.human_gate_required,
            "executable_now": False,
            "planning_only": True,
        }


@dataclass(frozen=True)
class SessionProvenance:
    """Display-safe provenance record for the session proposing promotion."""

    session_id: str
    session_label: str
    branch_name: str
    branch_lease_status: BranchLeaseStatus
    session_freshness: SessionFreshnessStatus
    stale_session_recommendation: str
    lease_holder: Optional[str] = None
    lease_expires_at: Optional[datetime] = None
    observed_at: Optional[datetime] = None
    evidence_refs: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()

    def to_display_dict(self) -> dict[str, object]:
        return {
            "session_id": _safe_ref(self.session_id, "session:unknown"),
            "session_label": _safe_label(self.session_label, "session_label_present"),
            "branch_name": _safe_ref(self.branch_name, "branch:unknown"),
            "branch_lease_status": self.branch_lease_status.value,
            "lease_holder": _safe_optional_ref(self.lease_holder, "lease_holder_missing"),
            "lease_expires_at": _safe_datetime(self.lease_expires_at),
            "session_freshness": self.session_freshness.value,
            "stale_session_recommendation": _safe_token(
                self.stale_session_recommendation,
                "refresh_session_before_promotion",
            ),
            "observed_at": _safe_datetime(self.observed_at),
            "evidence_refs": _safe_refs(self.evidence_refs),
            "warnings": _safe_tags(self.warnings),
            "blockers": _safe_tags(self.blockers),
        }


@dataclass(frozen=True)
class PromotionProvenance:
    """Display-safe promotion provenance from candidate through main."""

    provenance_id: str
    session: SessionProvenance
    candidate_ref: str
    review_ref: str
    intent_ref: str
    main_ref: str
    commit_intent_verification: CommitIntentVerificationStatus
    intended_diff_fingerprint: str
    observed_diff_fingerprint: str
    rollback_plan: RollbackBundlePlan
    observed_at: Optional[datetime] = None
    evidence_refs: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()

    @property
    def promotion_chain_summary(self) -> str:
        chain = (
            _safe_ref(self.candidate_ref, "candidate:missing"),
            _safe_ref(self.review_ref, "review:missing"),
            _safe_ref(self.intent_ref, "intent:missing"),
            _safe_ref(self.main_ref, "main:missing"),
        )
        return "candidate:{0}->review:{1}->intent:{2}->main:{3}".format(*chain)

    @property
    def is_clean(self) -> bool:
        return (
            self.session.branch_lease_status is BranchLeaseStatus.ACTIVE
            and self.session.session_freshness is SessionFreshnessStatus.FRESH
            and self.commit_intent_verification
            is CommitIntentVerificationStatus.VERIFIED
            and not self.warnings
            and not self.blockers
            and not self.session.warnings
            and not self.session.blockers
        )

    def to_display_dict(self) -> dict[str, object]:
        return {
            "provenance_id": _safe_ref(self.provenance_id, "promotion:provenance"),
            "session": self.session.to_display_dict(),
            "promotion_chain": {
                stage.value: _safe_ref(
                    getattr(self, f"{stage.value}_ref"),
                    f"{stage.value}:missing",
                )
                for stage in _CHAIN_ORDER
            },
            "promotion_chain_summary": self.promotion_chain_summary,
            "branch_lease_status": self.session.branch_lease_status.value,
            "commit_intent_verification": self.commit_intent_verification.value,
            "intended_diff_fingerprint": _safe_ref(
                self.intended_diff_fingerprint,
                "intent_diff_missing",
            ),
            "observed_diff_fingerprint": _safe_ref(
                self.observed_diff_fingerprint,
                "observed_diff_missing",
            ),
            "stale_session_recommendation": (
                self.session.to_display_dict()["stale_session_recommendation"]
            ),
            "rollback_plan": self.rollback_plan.to_display_dict(),
            "is_clean": self.is_clean,
            "observed_at": _safe_datetime(self.observed_at),
            "evidence_refs": _safe_refs(self.evidence_refs),
            "warnings": _safe_tags(self.warnings),
            "blockers": _safe_tags(self.blockers),
        }


def build_session_provenance(
    *,
    session_id: str,
    session_label: str,
    branch_name: str,
    branch_lease_status: BranchLeaseStatus | str,
    session_freshness: SessionFreshnessStatus | str,
    lease_holder: Optional[str] = None,
    lease_expires_at: Optional[datetime] = None,
    observed_at: Optional[datetime] = None,
    evidence_refs: Iterable[str] = (),
) -> SessionProvenance:
    """Build a deterministic, display-safe session provenance record."""

    lease_status = _coerce_enum(BranchLeaseStatus, branch_lease_status)
    freshness = _coerce_enum(SessionFreshnessStatus, session_freshness)
    warnings: list[str] = []
    blockers: list[str] = []

    if lease_status is not BranchLeaseStatus.ACTIVE:
        warnings.append(f"branch_lease.{lease_status.value}")
    if lease_status is BranchLeaseStatus.MISSING:
        blockers.append("branch_lease.missing")
    elif lease_status is BranchLeaseStatus.CONFLICTED:
        blockers.append("branch_lease.conflicted")

    if freshness is SessionFreshnessStatus.STALE:
        warnings.append("session.stale.advisory")
        recommendation = "refresh_session_before_promotion"
    elif freshness is SessionFreshnessStatus.UNKNOWN:
        warnings.append("session.freshness_unknown")
        recommendation = "verify_session_before_promotion"
    else:
        recommendation = "continue_current_session"

    return SessionProvenance(
        session_id=session_id,
        session_label=session_label,
        branch_name=branch_name,
        branch_lease_status=lease_status,
        session_freshness=freshness,
        stale_session_recommendation=recommendation,
        lease_holder=lease_holder,
        lease_expires_at=lease_expires_at,
        observed_at=observed_at,
        evidence_refs=tuple(evidence_refs),
        warnings=tuple(dict.fromkeys(warnings)),
        blockers=tuple(dict.fromkeys(blockers)),
    )


def build_promotion_provenance(
    *,
    provenance_id: str,
    session: SessionProvenance,
    candidate_ref: str,
    review_ref: str,
    intent_ref: str,
    main_ref: str,
    intended_diff_fingerprint: str,
    observed_diff_fingerprint: str,
    rollback_plan: RollbackBundlePlan,
    observed_at: Optional[datetime] = None,
    evidence_refs: Iterable[str] = (),
) -> PromotionProvenance:
    """Build display-safe promotion provenance and intent/diff warnings."""

    verification = _commit_intent_verification(
        intent_ref=intent_ref,
        intended_diff_fingerprint=intended_diff_fingerprint,
        observed_diff_fingerprint=observed_diff_fingerprint,
    )
    warnings: list[str] = []
    blockers: list[str] = []

    if verification is CommitIntentVerificationStatus.MISSING:
        blockers.append("commit_intent.missing")
    elif verification is CommitIntentVerificationStatus.MISMATCH:
        warnings.append("commit_intent.diff_mismatch")

    if session.branch_lease_status is not BranchLeaseStatus.ACTIVE:
        warnings.append(f"promotion.branch_lease.{session.branch_lease_status.value}")
    if session.session_freshness is SessionFreshnessStatus.STALE:
        warnings.append("promotion.session_stale")

    return PromotionProvenance(
        provenance_id=provenance_id,
        session=session,
        candidate_ref=candidate_ref,
        review_ref=review_ref,
        intent_ref=intent_ref,
        main_ref=main_ref,
        commit_intent_verification=verification,
        intended_diff_fingerprint=intended_diff_fingerprint,
        observed_diff_fingerprint=observed_diff_fingerprint,
        rollback_plan=rollback_plan,
        observed_at=observed_at,
        evidence_refs=tuple(evidence_refs),
        warnings=tuple(dict.fromkeys(warnings)),
        blockers=tuple(dict.fromkeys(blockers)),
    )


def _commit_intent_verification(
    *,
    intent_ref: str,
    intended_diff_fingerprint: str,
    observed_diff_fingerprint: str,
) -> CommitIntentVerificationStatus:
    if not intent_ref or not intended_diff_fingerprint or not observed_diff_fingerprint:
        return CommitIntentVerificationStatus.MISSING
    if intended_diff_fingerprint == observed_diff_fingerprint:
        return CommitIntentVerificationStatus.VERIFIED
    return CommitIntentVerificationStatus.MISMATCH


def _coerce_enum(enum_type: type[Enum], value: Enum | str) -> Any:
    if isinstance(value, enum_type):
        return value
    return enum_type(str(value))


def _safe_datetime(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    timestamp = value
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.isoformat()


def _safe_optional_ref(value: Optional[str], fallback: str) -> str:
    if value is None or not str(value).strip():
        return _MISSING
    return _safe_ref(value, fallback)


def _safe_ref(value: object, fallback: str) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return fallback
    if not _is_display_safe(candidate):
        return fallback
    if not _SAFE_TOKEN_RE.match(candidate):
        return fallback
    return candidate


def _safe_token(value: object, fallback: str) -> str:
    candidate = str(value or "").strip().lower().replace(" ", "_")
    if not candidate:
        return fallback
    if not _is_display_safe(candidate):
        return fallback
    candidate = "".join(
        char for char in candidate if char.isalnum() or char in ("_", "-", ".")
    )
    if not candidate or len(candidate) > 80:
        return fallback
    return candidate


def _safe_label(value: object, fallback: str) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return _MISSING
    return _safe_token(candidate, fallback)


def _safe_refs(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_safe_ref(value, _REDACTED) for value in values))


def _safe_tags(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_safe_token(value, _REDACTED) for value in values))


def _is_display_safe(value: str) -> bool:
    if "\n" in value or "\r" in value:
        return False
    lowered = value.lower()
    return not any(pattern in lowered for pattern in _UNSAFE_DISPLAY_PATTERNS)
