"""Display-safe backend diagnostics for the V2.5 harness surface.

This module is intentionally pure: it performs no process inspection, IO,
model calls, or automatic intervention. Callers provide already-observed
counts and version labels; the diagnostics only classify them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


SNAPSHOT_VERSION = "harness-diagnostics-v1"


class HeartbeatAnomaly(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    STALE = "stale"
    MISSING = "missing"
    FAILED = "failed"
    BLOCKED = "blocked"


class StaleWorkerClassification(Enum):
    ACTIVE = "active"
    WATCH = "watch"
    STALE = "stale"
    MISSING = "missing"
    FAILED = "failed"
    BLOCKED = "blocked"
    UNDER_PROVEN = "under_proven"


class SnapshotDriftClassification(Enum):
    ALIGNED = "aligned"
    DIVERGENT = "divergent"
    MISSING_BACKEND = "missing_backend"
    MISSING_DISPLAY = "missing_display"
    UNPROVEN = "unproven"


@dataclass(frozen=True)
class HarnessDiagnosticInput:
    """Already-observed facts about one harness worker."""

    harness_id: str
    heartbeat_status: str
    heartbeat_age_seconds: int | None
    expected_heartbeat_seconds: int
    proof_count: int = 0
    required_proof_count: int = 1
    blocker_count: int = 0
    current_work_present: bool = False
    raw_event_text: str | None = None

    def __post_init__(self) -> None:
        if self.expected_heartbeat_seconds < 0:
            raise ValueError("expected_heartbeat_seconds must be non-negative")
        if self.heartbeat_age_seconds is not None and self.heartbeat_age_seconds < 0:
            raise ValueError("heartbeat_age_seconds must be non-negative")
        if self.proof_count < 0:
            raise ValueError("proof_count must be non-negative")
        if self.required_proof_count < 0:
            raise ValueError("required_proof_count must be non-negative")
        if self.blocker_count < 0:
            raise ValueError("blocker_count must be non-negative")


@dataclass(frozen=True)
class BackendSnapshotProof:
    """Version/proof comparison between backend truth and displayed snapshot."""

    backend_snapshot_id: str | None
    displayed_snapshot_id: str | None
    backend_proof_count: int = 0
    required_proof_count: int = 1

    def __post_init__(self) -> None:
        if self.backend_proof_count < 0:
            raise ValueError("backend_proof_count must be non-negative")
        if self.required_proof_count < 0:
            raise ValueError("required_proof_count must be non-negative")


@dataclass(frozen=True)
class HarnessDiagnosticRecord:
    harness_id: str
    heartbeat_anomaly: HeartbeatAnomaly
    stale_worker_classification: StaleWorkerClassification
    heartbeat_age_seconds: int | None
    expected_heartbeat_seconds: int
    proof_count: int
    required_proof_count: int
    blocker_count: int
    current_work_present: bool

    @property
    def under_proven(self) -> bool:
        return self.proof_count < self.required_proof_count

    def to_display_dict(self) -> dict[str, object]:
        return {
            "harness_id": _display_token(self.harness_id),
            "heartbeat_anomaly": self.heartbeat_anomaly.value,
            "stale_worker_classification": self.stale_worker_classification.value,
            "heartbeat_age_seconds": self.heartbeat_age_seconds,
            "expected_heartbeat_seconds": self.expected_heartbeat_seconds,
            "proof_count": self.proof_count,
            "required_proof_count": self.required_proof_count,
            "under_proven": self.under_proven,
            "blocker_count": self.blocker_count,
            "current_work_present": self.current_work_present,
            "raw_event_visible": False,
            "raw_filesystem_paths_visible": False,
        }


@dataclass(frozen=True)
class BackendSnapshotDrift:
    classification: SnapshotDriftClassification
    backend_snapshot_present: bool
    displayed_snapshot_present: bool
    backend_proof_count: int
    required_proof_count: int

    @property
    def under_proven(self) -> bool:
        return self.backend_proof_count < self.required_proof_count

    def to_display_dict(self) -> dict[str, object]:
        return {
            "classification": self.classification.value,
            "backend_snapshot_present": self.backend_snapshot_present,
            "displayed_snapshot_present": self.displayed_snapshot_present,
            "backend_proof_count": self.backend_proof_count,
            "required_proof_count": self.required_proof_count,
            "under_proven": self.under_proven,
            "snapshot_ids_visible": False,
            "raw_backend_payload_visible": False,
            "raw_display_payload_visible": False,
        }


@dataclass(frozen=True)
class ReliabilityScore:
    score: int
    total_workers: int
    healthy_count: int
    stale_count: int
    failed_count: int
    missing_count: int
    blocked_count: int
    under_proven_count: int
    divergent_snapshot_count: int

    def to_display_dict(self) -> dict[str, int]:
        return {
            "score": self.score,
            "total_workers": self.total_workers,
            "healthy_count": self.healthy_count,
            "stale_count": self.stale_count,
            "failed_count": self.failed_count,
            "missing_count": self.missing_count,
            "blocked_count": self.blocked_count,
            "under_proven_count": self.under_proven_count,
            "divergent_snapshot_count": self.divergent_snapshot_count,
        }


@dataclass(frozen=True)
class HarnessDiagnosticSnapshot:
    version: str
    generated_at: str
    records: tuple[HarnessDiagnosticRecord, ...]
    backend_drift: BackendSnapshotDrift
    reliability: ReliabilityScore
    escalation_recommendation: str

    def to_display_dict(self) -> dict[str, object]:
        return {
            "version": _display_safe_text(self.version),
            "generated_at": _display_safe_text(self.generated_at),
            "display_only": True,
            "mutation_authorized": False,
            "automatic_intervention_authorized": False,
            "process_inspection_authorized": False,
            "model_calls_authorized": False,
            "raw_worker_chat_visible": False,
            "raw_logs_visible": False,
            "raw_filesystem_paths_visible": False,
            "records": tuple(record.to_display_dict() for record in self.records),
            "backend_drift": self.backend_drift.to_display_dict(),
            "reliability": self.reliability.to_display_dict(),
            "escalation_recommendation": _display_safe_text(self.escalation_recommendation),
            "guardrails": (
                "display_only",
                "no_process_inspection",
                "no_io",
                "no_model_calls",
                "no_automatic_intervention",
                "no_raw_paths",
                "no_raw_logs",
            ),
        }


def classify_heartbeat_anomaly(
    heartbeat_status: str,
    heartbeat_age_seconds: int | None,
    expected_heartbeat_seconds: int,
    blocker_count: int = 0,
) -> HeartbeatAnomaly:
    """Classify heartbeat health from provided status and age only."""
    status = heartbeat_status.strip().lower()
    if status in {"failed", "error"}:
        return HeartbeatAnomaly.FAILED
    if status == "blocked" or blocker_count > 0:
        return HeartbeatAnomaly.BLOCKED
    if status in {"missing", "unknown"} or heartbeat_age_seconds is None:
        return HeartbeatAnomaly.MISSING
    if status == "stale" or heartbeat_age_seconds > expected_heartbeat_seconds:
        return HeartbeatAnomaly.STALE
    if expected_heartbeat_seconds and heartbeat_age_seconds > expected_heartbeat_seconds * 0.8:
        return HeartbeatAnomaly.WARNING
    return HeartbeatAnomaly.HEALTHY


def classify_stale_worker(
    heartbeat_anomaly: HeartbeatAnomaly,
    proof_count: int,
    required_proof_count: int,
) -> StaleWorkerClassification:
    """Map heartbeat and proof counts into a worker-facing classification."""
    if heartbeat_anomaly is HeartbeatAnomaly.FAILED:
        return StaleWorkerClassification.FAILED
    if heartbeat_anomaly is HeartbeatAnomaly.MISSING:
        return StaleWorkerClassification.MISSING
    if heartbeat_anomaly is HeartbeatAnomaly.BLOCKED:
        return StaleWorkerClassification.BLOCKED
    if heartbeat_anomaly is HeartbeatAnomaly.STALE:
        return StaleWorkerClassification.STALE
    if proof_count < required_proof_count:
        return StaleWorkerClassification.UNDER_PROVEN
    if heartbeat_anomaly is HeartbeatAnomaly.WARNING:
        return StaleWorkerClassification.WATCH
    return StaleWorkerClassification.ACTIVE


def detect_backend_snapshot_drift(proof: BackendSnapshotProof) -> BackendSnapshotDrift:
    backend_present = bool(proof.backend_snapshot_id)
    display_present = bool(proof.displayed_snapshot_id)
    if not backend_present:
        classification = SnapshotDriftClassification.MISSING_BACKEND
    elif not display_present:
        classification = SnapshotDriftClassification.MISSING_DISPLAY
    elif proof.backend_snapshot_id != proof.displayed_snapshot_id:
        classification = SnapshotDriftClassification.DIVERGENT
    elif proof.backend_proof_count < proof.required_proof_count:
        classification = SnapshotDriftClassification.UNPROVEN
    else:
        classification = SnapshotDriftClassification.ALIGNED
    return BackendSnapshotDrift(
        classification=classification,
        backend_snapshot_present=backend_present,
        displayed_snapshot_present=display_present,
        backend_proof_count=proof.backend_proof_count,
        required_proof_count=proof.required_proof_count,
    )


def build_harness_diagnostic_snapshot(
    observations: tuple[HarnessDiagnosticInput, ...] | list[HarnessDiagnosticInput],
    backend_snapshot_proof: BackendSnapshotProof,
    *,
    generated_at: str = "2026-06-11T00:00:00+00:00",
) -> HarnessDiagnosticSnapshot:
    records = tuple(_record_from_observation(observation) for observation in observations)
    drift = detect_backend_snapshot_drift(backend_snapshot_proof)
    reliability = _reliability_score(records, drift)
    return HarnessDiagnosticSnapshot(
        version=SNAPSHOT_VERSION,
        generated_at=generated_at,
        records=records,
        backend_drift=drift,
        reliability=reliability,
        escalation_recommendation=_escalation_recommendation(records, drift, reliability),
    )


def _record_from_observation(
    observation: HarnessDiagnosticInput,
) -> HarnessDiagnosticRecord:
    anomaly = classify_heartbeat_anomaly(
        observation.heartbeat_status,
        observation.heartbeat_age_seconds,
        observation.expected_heartbeat_seconds,
        observation.blocker_count,
    )
    worker_classification = classify_stale_worker(
        anomaly,
        observation.proof_count,
        observation.required_proof_count,
    )
    return HarnessDiagnosticRecord(
        harness_id=observation.harness_id,
        heartbeat_anomaly=anomaly,
        stale_worker_classification=worker_classification,
        heartbeat_age_seconds=observation.heartbeat_age_seconds,
        expected_heartbeat_seconds=observation.expected_heartbeat_seconds,
        proof_count=observation.proof_count,
        required_proof_count=observation.required_proof_count,
        blocker_count=observation.blocker_count,
        current_work_present=observation.current_work_present,
    )


def _reliability_score(
    records: tuple[HarnessDiagnosticRecord, ...],
    drift: BackendSnapshotDrift,
) -> ReliabilityScore:
    healthy_count = sum(
        1
        for record in records
        if record.heartbeat_anomaly is HeartbeatAnomaly.HEALTHY
        and not record.under_proven
    )
    stale_count = sum(1 for record in records if record.heartbeat_anomaly is HeartbeatAnomaly.STALE)
    failed_count = sum(1 for record in records if record.heartbeat_anomaly is HeartbeatAnomaly.FAILED)
    missing_count = sum(1 for record in records if record.heartbeat_anomaly is HeartbeatAnomaly.MISSING)
    blocked_count = sum(1 for record in records if record.heartbeat_anomaly is HeartbeatAnomaly.BLOCKED)
    under_proven_count = sum(1 for record in records if record.under_proven)
    divergent_snapshot_count = (
        0 if drift.classification is SnapshotDriftClassification.ALIGNED else 1
    )
    score = 100
    score -= stale_count * 20
    score -= failed_count * 35
    score -= missing_count * 30
    score -= blocked_count * 25
    score -= under_proven_count * 10
    score -= divergent_snapshot_count * 25
    score = max(0, min(100, score))
    return ReliabilityScore(
        score=score,
        total_workers=len(records),
        healthy_count=healthy_count,
        stale_count=stale_count,
        failed_count=failed_count,
        missing_count=missing_count,
        blocked_count=blocked_count,
        under_proven_count=under_proven_count,
        divergent_snapshot_count=divergent_snapshot_count,
    )


def _escalation_recommendation(
    records: tuple[HarnessDiagnosticRecord, ...],
    drift: BackendSnapshotDrift,
    reliability: ReliabilityScore,
) -> str:
    if drift.classification is SnapshotDriftClassification.DIVERGENT:
        return "Read-only guidance: escalate for backend/display snapshot drift review before trusting the visible harness."
    if drift.classification in {
        SnapshotDriftClassification.MISSING_BACKEND,
        SnapshotDriftClassification.MISSING_DISPLAY,
    }:
        return "Read-only guidance: escalate for missing snapshot proof; do not infer live state from this panel."
    if any(
        record.heartbeat_anomaly
        in {HeartbeatAnomaly.FAILED, HeartbeatAnomaly.MISSING, HeartbeatAnomaly.BLOCKED}
        for record in records
    ):
        return "Read-only guidance: escalate to the coordinator for manual worker triage; no automatic recovery is authorized."
    if reliability.under_proven_count:
        return "Read-only guidance: request additional proof before changing harness confidence."
    if reliability.stale_count:
        return "Read-only guidance: watch stale workers and request human review if the condition persists."
    return "Read-only guidance: harness diagnostics are healthy; continue passive monitoring."


def _display_token(value: str) -> str:
    clean = value.strip()
    if not clean:
        return "harness:unknown"
    if _looks_like_local_path(clean):
        return "harness:unsafe-id"
    return clean


def _display_safe_text(value: str) -> str:
    clean = re.sub(r"\s+", " ", str(value).strip())
    if not clean:
        return "[redacted]"
    if _looks_unsafe_text(clean):
        return "[redacted]"
    return clean[:240]


def _looks_like_local_path(value: str) -> bool:
    return bool(
        re.search(
            r"(?i)(?:[A-Z]:\\|\\\\[^\\\s]+\\[^\\\s]+\\|/(?:Users|home|var|tmp|mnt|Volumes)/)",
            value,
        )
    )


def _looks_unsafe_text(value: str) -> bool:
    return bool(
        re.search(
            r"(?i)(?:[A-Z]:\\|\\\\[^\\\s]+\\[^\\\s]+\\|/(?:Users|home|var|tmp|mnt|Volumes)/|"
            r"traceback|exception:|raw\s+(?:prompt|transcript|content|log)|"
            r"provider\s+(?:response|output)|model\s+(?:response|output)|"
            r"api[_-]?key|secret|token|password|sk-(?:proj-)?[A-Za-z0-9_-]{16,})",
            value,
        )
    )
