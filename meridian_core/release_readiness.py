"""Display-safe internal release readiness packaging proof for V2.5.

This module is pure backend classification. It never writes packages, touches
git, performs deploy work, or exposes raw proof/log contents.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ProofPackageStatus(Enum):
    PRESENT = "present"
    MISSING = "missing"
    STALE = "stale"


class RollbackGateState(Enum):
    CLOSED = "closed"
    OPEN = "open"


class ReleaseReadinessClassification(Enum):
    READY = "ready"
    NOT_READY = "not_ready"


@dataclass(frozen=True)
class ProofPackageEvidence:
    proof_ref: str
    requirement: str
    captured_at_seconds: int | None
    max_age_seconds: int
    content_digest: str
    present: bool = True
    raw_log: str | None = None
    source_path: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.proof_ref, str) or not self.proof_ref.strip():
            raise ValueError("proof_ref must not be empty")
        if not isinstance(self.requirement, str) or not self.requirement.strip():
            raise ValueError("requirement must not be empty")
        if self.captured_at_seconds is not None and not isinstance(
            self.captured_at_seconds, int
        ):
            raise ValueError("captured_at_seconds must be an integer or None")
        if not isinstance(self.max_age_seconds, int) or self.max_age_seconds < 0:
            raise ValueError("max_age_seconds must be a non-negative integer")
        if not isinstance(self.content_digest, str):
            raise ValueError("content_digest must be a string")
        if not isinstance(self.present, bool):
            raise ValueError("present must be a boolean")


@dataclass(frozen=True)
class RollbackGate:
    gate_id: str
    label: str
    state: RollbackGateState
    summary: str

    def __post_init__(self) -> None:
        if not isinstance(self.gate_id, str) or not self.gate_id.strip():
            raise ValueError("gate_id must not be empty")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("label must not be empty")
        if not isinstance(self.state, RollbackGateState):
            raise ValueError("state must be a RollbackGateState")
        if not isinstance(self.summary, str) or not self.summary.strip():
            raise ValueError("summary must not be empty")


@dataclass(frozen=True)
class ProofPackageRecord:
    manifest_id: str
    requirement: str
    proof_ref: str
    status: ProofPackageStatus
    captured_at_seconds: int | None
    age_seconds: int | None
    max_age_seconds: int
    content_digest: str | None
    reason_tags: tuple[str, ...]

    def to_display_dict(self) -> dict[str, object]:
        return {
            "manifest_id": _display_safe_text(self.manifest_id),
            "requirement": _display_safe_text(self.requirement),
            "proof_ref": _display_safe_text(self.proof_ref),
            "status": self.status.value,
            "captured_at_seconds": self.captured_at_seconds,
            "age_seconds": self.age_seconds,
            "max_age_seconds": self.max_age_seconds,
            "content_digest": (
                None if self.content_digest is None else _display_safe_text(self.content_digest)
            ),
            "reason_tags": tuple(_display_safe_text(tag) for tag in self.reason_tags),
        }


@dataclass(frozen=True)
class ProofPackageManifest:
    records: tuple[ProofPackageRecord, ...]

    @property
    def required_count(self) -> int:
        return len(self.records)

    @property
    def present_count(self) -> int:
        return sum(1 for record in self.records if record.status is ProofPackageStatus.PRESENT)

    @property
    def missing_count(self) -> int:
        return sum(1 for record in self.records if record.status is ProofPackageStatus.MISSING)

    @property
    def stale_count(self) -> int:
        return sum(1 for record in self.records if record.status is ProofPackageStatus.STALE)

    @property
    def summary(self) -> str:
        return (
            f"proof package manifest: {self.present_count}/{self.required_count} "
            f"present, {self.missing_count} missing, {self.stale_count} stale"
        )

    def to_display_dict(self) -> dict[str, object]:
        return {
            "summary": self.summary,
            "required_count": self.required_count,
            "present_count": self.present_count,
            "missing_count": self.missing_count,
            "stale_count": self.stale_count,
            "records": tuple(record.to_display_dict() for record in self.records),
        }


@dataclass(frozen=True)
class RollbackGateRecord:
    gate_id: str
    label: str
    state: RollbackGateState
    blocking: bool
    summary: str

    def to_display_dict(self) -> dict[str, object]:
        return {
            "gate_id": _display_safe_text(self.gate_id),
            "label": _display_safe_text(self.label),
            "state": self.state.value,
            "blocking": self.blocking,
            "summary": _display_safe_text(self.summary),
        }


@dataclass(frozen=True)
class RollbackGateSummary:
    records: tuple[RollbackGateRecord, ...]

    @property
    def open_gate_count(self) -> int:
        return sum(1 for record in self.records if record.blocking)

    @property
    def closed_gate_count(self) -> int:
        return len(self.records) - self.open_gate_count

    @property
    def status(self) -> str:
        if self.open_gate_count:
            return "rollback gates open"
        return "rollback gates closed"

    def to_display_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "open_gate_count": self.open_gate_count,
            "closed_gate_count": self.closed_gate_count,
            "records": tuple(record.to_display_dict() for record in self.records),
        }


@dataclass(frozen=True)
class ReleaseReadinessSnapshot:
    release_id: str
    generated_at_seconds: int
    classification: ReleaseReadinessClassification
    ready: bool
    proof_package_manifest: ProofPackageManifest
    rollback_gate_summary: RollbackGateSummary
    cannot_release_because: tuple[str, ...]
    reason_tags: tuple[str, ...]
    display_only: bool = True
    mutation_authorized: bool = False

    def to_display_dict(self) -> dict[str, object]:
        return {
            "release_id": _display_safe_text(self.release_id),
            "generated_at_seconds": self.generated_at_seconds,
            "classification": self.classification.value,
            "ready": self.ready,
            "display_only": self.display_only,
            "mutation_authorized": self.mutation_authorized,
            "cannot_release_because": tuple(
                _display_safe_text(reason) for reason in self.cannot_release_because
            ),
            "reason_tags": tuple(_display_safe_text(tag) for tag in self.reason_tags),
            "proof_package_manifest": self.proof_package_manifest.to_display_dict(),
            "rollback_gate_summary": self.rollback_gate_summary.to_display_dict(),
        }


def build_release_readiness_snapshot(
    *,
    release_id: str,
    proof_evidence: tuple[ProofPackageEvidence, ...],
    rollback_gates: tuple[RollbackGate, ...],
    now_seconds: int,
) -> ReleaseReadinessSnapshot:
    """Build an internal display-safe release readiness snapshot."""
    if not isinstance(release_id, str) or not release_id.strip():
        raise ValueError("release_id must not be empty")
    if not isinstance(now_seconds, int):
        raise ValueError("now_seconds must be an integer")

    manifest = ProofPackageManifest(
        records=tuple(
            sorted(
                (_proof_record(evidence, now_seconds) for evidence in proof_evidence),
                key=lambda record: record.manifest_id,
            )
        )
    )
    rollback_summary = RollbackGateSummary(
        records=tuple(
            sorted(
                (_rollback_record(gate) for gate in rollback_gates),
                key=lambda record: record.gate_id,
            )
        )
    )
    blockers, reason_tags = _readiness_blockers(manifest, rollback_summary)
    ready = not blockers

    return ReleaseReadinessSnapshot(
        release_id=_display_safe_text(release_id),
        generated_at_seconds=now_seconds,
        classification=(
            ReleaseReadinessClassification.READY
            if ready
            else ReleaseReadinessClassification.NOT_READY
        ),
        ready=ready,
        proof_package_manifest=manifest,
        rollback_gate_summary=rollback_summary,
        cannot_release_because=tuple(blockers),
        reason_tags=tuple(reason_tags) if reason_tags else ("release_ready",),
    )


def _proof_record(
    evidence: ProofPackageEvidence, now_seconds: int
) -> ProofPackageRecord:
    captured_at = evidence.captured_at_seconds
    age_seconds = None if captured_at is None else max(0, now_seconds - captured_at)
    requirement = _display_safe_text(evidence.requirement)
    proof_ref = _display_safe_text(evidence.proof_ref)
    digest = evidence.content_digest.strip()

    if not evidence.present or captured_at is None or not digest:
        status = ProofPackageStatus.MISSING
        tags = ("proof_missing",)
        content_digest = None
    elif age_seconds is not None and age_seconds > evidence.max_age_seconds:
        status = ProofPackageStatus.STALE
        tags = ("proof_stale",)
        content_digest = _display_safe_text(digest)
    else:
        status = ProofPackageStatus.PRESENT
        tags = ("proof_present", "proof_fresh")
        content_digest = _display_safe_text(digest)

    return ProofPackageRecord(
        manifest_id=f"proof-package:{_stable_key(requirement)}",
        requirement=requirement,
        proof_ref=proof_ref,
        status=status,
        captured_at_seconds=captured_at,
        age_seconds=age_seconds,
        max_age_seconds=evidence.max_age_seconds,
        content_digest=content_digest,
        reason_tags=tags,
    )


def _rollback_record(gate: RollbackGate) -> RollbackGateRecord:
    return RollbackGateRecord(
        gate_id=_display_safe_text(gate.gate_id),
        label=_display_safe_text(gate.label),
        state=gate.state,
        blocking=gate.state is RollbackGateState.OPEN,
        summary=_display_safe_text(gate.summary),
    )


def _readiness_blockers(
    manifest: ProofPackageManifest, rollback_summary: RollbackGateSummary
) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    reason_tags: list[str] = []

    for record in manifest.records:
        if record.status is ProofPackageStatus.MISSING:
            blockers.append(f"missing required proof: {record.requirement}")
            reason_tags.append("proof_missing")
        elif record.status is ProofPackageStatus.STALE:
            blockers.append(f"stale required proof: {record.requirement}")
            reason_tags.append("proof_stale")

    for record in rollback_summary.records:
        if record.blocking:
            blockers.append(f"open rollback gate: {record.label}")
            reason_tags.append("rollback_gate_open")

    return blockers, _dedupe(reason_tags)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _display_safe_text(value: str) -> str:
    clean = " ".join(value.strip().split())
    if not clean:
        return "[redacted]"
    if _looks_unsafe(clean):
        return "[redacted]"
    return clean[:120]


def _stable_key(value: str) -> str:
    clean = value.lower()
    clean = re.sub(r"[^a-z0-9]+", "-", clean).strip("-")
    return clean or "redacted"


def _looks_unsafe(value: str) -> bool:
    lowered = value.lower()
    unsafe_markers = (
        "raw prompt:",
        "full prompt:",
        "complete prompt:",
        "raw transcript:",
        "full transcript:",
        "complete transcript:",
        "provider response:",
        "provider output:",
        "model response:",
        "model output:",
        "traceback",
        "exception:",
    )
    if any(marker in lowered for marker in unsafe_markers):
        return True
    if re.search(r"(?i)(?:[A-Z]:\\|\\\\[^\\\s]+\\[^\\\s]+\\|/(?:Users|home|var|tmp|mnt|Volumes)/)", value):
        return True
    if re.search(
        r"(?i)\b(?:api[_-]?key|secret|token|password|credential)\s*[:=]\s*\S{8,}",
        value,
    ):
        return True
    if re.search(r"sk-(?:proj-)?[A-Za-z0-9_-]{16,}", value):
        return True
    if re.search(r"gh[pousr]_[A-Za-z0-9_]{20,}", value):
        return True
    return bool(re.search(r"github_pat_[A-Za-z0-9_]{20,}", value))
