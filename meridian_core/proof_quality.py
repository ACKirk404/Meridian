"""Display-safe proof sufficiency and freshness checks for V2.5.

This module is pure and deterministic: callers provide all timestamps and
snapshot metadata, and results never expose raw proof contents.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ProofQualityStatus(Enum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    STALE = "stale"
    WAIVED = "waived"
    MISSING = "missing"


class ProofFreshnessState(Enum):
    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class ProofRef:
    proof_ref: str
    requirement: str
    max_age_seconds: int

    def __post_init__(self) -> None:
        if not isinstance(self.proof_ref, str) or not self.proof_ref.strip():
            raise ValueError("proof_ref must not be empty")
        if not isinstance(self.requirement, str) or not self.requirement.strip():
            raise ValueError("requirement must not be empty")
        if not isinstance(self.max_age_seconds, int) or self.max_age_seconds < 0:
            raise ValueError("max_age_seconds must be a non-negative integer")

    def display_ref(self) -> str:
        return _display_safe_ref(self.proof_ref)


@dataclass(frozen=True)
class ProofSnapshot:
    proof_ref: str
    captured_at_seconds: int | None
    content_digest: str
    sufficient: bool
    waiver_ref: str | None = None
    raw_text: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.proof_ref, str) or not self.proof_ref.strip():
            raise ValueError("proof_ref must not be empty")
        if self.captured_at_seconds is not None and not isinstance(
            self.captured_at_seconds, int
        ):
            raise ValueError("captured_at_seconds must be an integer or None")
        if not isinstance(self.content_digest, str) or not self.content_digest.strip():
            raise ValueError("content_digest must not be empty")
        if not isinstance(self.sufficient, bool):
            raise ValueError("sufficient must be a boolean")
        if self.waiver_ref is not None and (
            not isinstance(self.waiver_ref, str) or not self.waiver_ref.strip()
        ):
            raise ValueError("waiver_ref must be a non-empty string or None")

    def display_digest(self) -> str:
        return _display_safe_ref(self.content_digest)

    def display_waiver_ref(self) -> str | None:
        if self.waiver_ref is None:
            return None
        return _display_safe_ref(self.waiver_ref)


@dataclass(frozen=True)
class ProofQualityResult:
    proof_ref: str
    requirement: str
    status: ProofQualityStatus
    freshness: ProofFreshnessState
    passed: bool
    age_seconds: int | None
    content_digest: str | None
    waiver_ref: str | None
    reason_tags: tuple[str, ...]

    def to_display_dict(self) -> dict[str, object]:
        return {
            "proof_ref": _display_safe_ref(self.proof_ref),
            "requirement": _display_safe_ref(self.requirement),
            "status": self.status.value,
            "freshness": self.freshness.value,
            "passed": self.passed,
            "age_seconds": self.age_seconds,
            "content_digest": (
                None if self.content_digest is None else _display_safe_ref(self.content_digest)
            ),
            "waiver_ref": (
                None if self.waiver_ref is None else _display_safe_ref(self.waiver_ref)
            ),
            "reason_tags": tuple(_display_safe_ref(tag) for tag in self.reason_tags),
        }


def evaluate_proof_quality(
    proof_ref: ProofRef,
    snapshot: ProofSnapshot | None,
    *,
    now_seconds: int,
) -> ProofQualityResult:
    """Classify proof metadata without exposing proof contents."""
    if not isinstance(now_seconds, int):
        raise ValueError("now_seconds must be an integer")

    display_ref = proof_ref.display_ref()
    requirement = _display_safe_ref(proof_ref.requirement)

    if snapshot is None:
        return ProofQualityResult(
            proof_ref=display_ref,
            requirement=requirement,
            status=ProofQualityStatus.MISSING,
            freshness=ProofFreshnessState.UNKNOWN,
            passed=False,
            age_seconds=None,
            content_digest=None,
            waiver_ref=None,
            reason_tags=("proof_snapshot_missing",),
        )

    age_seconds = _proof_age_seconds(snapshot.captured_at_seconds, now_seconds)
    freshness = _freshness_state(age_seconds, proof_ref.max_age_seconds)
    content_digest = snapshot.display_digest()
    waiver_ref = snapshot.display_waiver_ref()

    if snapshot.proof_ref != proof_ref.proof_ref:
        return ProofQualityResult(
            proof_ref=display_ref,
            requirement=requirement,
            status=ProofQualityStatus.MISSING,
            freshness=freshness,
            passed=False,
            age_seconds=age_seconds,
            content_digest=content_digest,
            waiver_ref=waiver_ref,
            reason_tags=("proof_ref_mismatch",),
        )

    if waiver_ref is not None:
        return ProofQualityResult(
            proof_ref=display_ref,
            requirement=requirement,
            status=ProofQualityStatus.WAIVED,
            freshness=ProofFreshnessState.NOT_APPLICABLE,
            passed=False,
            age_seconds=age_seconds,
            content_digest=content_digest,
            waiver_ref=waiver_ref,
            reason_tags=("proof_waived",),
        )

    if not snapshot.sufficient:
        return ProofQualityResult(
            proof_ref=display_ref,
            requirement=requirement,
            status=ProofQualityStatus.INSUFFICIENT,
            freshness=freshness,
            passed=False,
            age_seconds=age_seconds,
            content_digest=content_digest,
            waiver_ref=None,
            reason_tags=("proof_insufficient",),
        )

    if freshness is not ProofFreshnessState.FRESH:
        return ProofQualityResult(
            proof_ref=display_ref,
            requirement=requirement,
            status=ProofQualityStatus.STALE,
            freshness=freshness,
            passed=False,
            age_seconds=age_seconds,
            content_digest=content_digest,
            waiver_ref=None,
            reason_tags=("proof_stale",),
        )

    return ProofQualityResult(
        proof_ref=display_ref,
        requirement=requirement,
        status=ProofQualityStatus.SUFFICIENT,
        freshness=freshness,
        passed=True,
        age_seconds=age_seconds,
        content_digest=content_digest,
        waiver_ref=None,
        reason_tags=("proof_sufficient", "proof_fresh"),
    )


def _proof_age_seconds(captured_at_seconds: int | None, now_seconds: int) -> int | None:
    if captured_at_seconds is None:
        return None
    return max(0, now_seconds - captured_at_seconds)


def _freshness_state(
    age_seconds: int | None, max_age_seconds: int
) -> ProofFreshnessState:
    if age_seconds is None:
        return ProofFreshnessState.UNKNOWN
    if age_seconds > max_age_seconds:
        return ProofFreshnessState.STALE
    return ProofFreshnessState.FRESH


def _display_safe_ref(value: str) -> str:
    clean = value.strip()
    if _looks_like_raw_payload(clean):
        return "[redacted]"
    return clean


def _looks_like_raw_payload(value: str) -> bool:
    return bool(
        re.search(
            r"(?is)(?:"
            r"[A-Z]:\\|\\\\[^\\\s]+\\[^\\\s]+\\|/(?:Users|home|var|tmp|mnt|Volumes)/|"
            r"\b(?:raw|full|complete)\s+prompt\s*:|"
            r"\b(?:raw|full|complete)\s+transcript\s*:|"
            r"\b(?:provider|model)\s+(?:response|output)\s*:|"
            r"\b(?:api[_-]?key|secret|token|password|credential)\s*[:=]\s*\S{8,}|"
            r"sk-(?:proj-)?[A-Za-z0-9_-]{16,}|"
            r"gh[pousr]_[A-Za-z0-9_]{20,}"
            r")",
            value,
        )
    )
