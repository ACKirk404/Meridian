"""Pure review intelligence records for V2.5 backend hardening.

This module accepts already-collected review finding metadata and produces
deterministic, display-safe summaries. It performs no IO, no model calls, and
does not expose raw finding bodies or logs in display dictionaries.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class ReviewFindingSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RepairVerificationState(Enum):
    FIXED = "fixed"
    NOT_FIXED = "not_fixed"
    WAIVED = "waived"


class RegressionRiskLabel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


_SEVERITY_RANK: dict[ReviewFindingSeverity, int] = {
    ReviewFindingSeverity.INFO: 0,
    ReviewFindingSeverity.WARNING: 1,
    ReviewFindingSeverity.ERROR: 2,
    ReviewFindingSeverity.CRITICAL: 3,
}

_RISKY_COMPONENTS: frozenset[str] = frozenset(
    {
        "api",
        "bridge",
        "core",
        "dispatch",
        "evidence",
        "model",
        "policy",
        "proof",
        "repair",
        "runtime",
        "security",
        "state",
    }
)


@dataclass(frozen=True)
class ReviewFindingInput:
    """Raw finding metadata used only as analysis input."""

    source_id: str
    artifact_id: str
    rule_id: str
    severity: ReviewFindingSeverity | str
    finding_body: str = ""
    log_excerpt: str = ""
    location: str = ""
    repair_state: RepairVerificationState | str = RepairVerificationState.NOT_FIXED
    waiver_id: str = ""
    waiver_reason: str = ""
    repair_evidence_refs: tuple[str, ...] = ()
    changed_components: tuple[str, ...] = ()
    blocker_tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReviewFindingFingerprint:
    """Stable finding identity without raw finding text."""

    fingerprint: str
    source_ref: str
    artifact_ref: str
    rule_ref: str

    def to_display_dict(self) -> dict[str, str]:
        return {
            "fingerprint": self.fingerprint,
            "source_ref": self.source_ref,
            "artifact_ref": self.artifact_ref,
            "rule_ref": self.rule_ref,
        }


@dataclass(frozen=True)
class SeverityCalibration:
    severity: ReviewFindingSeverity
    rationale: str

    def to_display_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity.value,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class RepairVerification:
    state: RepairVerificationState
    evidence_refs: tuple[str, ...] = ()

    @property
    def is_closed(self) -> bool:
        return self.state in {
            RepairVerificationState.FIXED,
            RepairVerificationState.WAIVED,
        }

    def to_display_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "is_closed": self.is_closed,
            "evidence_refs": self.evidence_refs,
        }


@dataclass(frozen=True)
class WaiverVisibility:
    present: bool
    waiver_ref: str = ""
    reason_visible: bool = False

    def to_display_dict(self) -> dict[str, object]:
        return {
            "present": self.present,
            "waiver_ref": self.waiver_ref,
            "reason_visible": self.reason_visible,
        }


@dataclass(frozen=True)
class DuplicateFindingGroup:
    fingerprint: ReviewFindingFingerprint
    duplicate_count: int
    sources: tuple[str, ...]
    severity: SeverityCalibration
    repair: RepairVerification
    waiver: WaiverVisibility
    regression_risk: RegressionRiskLabel

    def to_display_dict(self) -> dict[str, object]:
        return {
            "fingerprint": self.fingerprint.to_display_dict(),
            "duplicate_count": self.duplicate_count,
            "sources": self.sources,
            "severity": self.severity.to_display_dict(),
            "repair": self.repair.to_display_dict(),
            "waiver": self.waiver.to_display_dict(),
            "regression_risk": self.regression_risk.value,
        }


@dataclass(frozen=True)
class ReviewIntelligenceReport:
    groups: tuple[DuplicateFindingGroup, ...]

    @property
    def open_count(self) -> int:
        return sum(
            1
            for group in self.groups
            if group.repair.state is RepairVerificationState.NOT_FIXED
        )

    def to_display_dict(self) -> dict[str, object]:
        return {
            "group_count": len(self.groups),
            "open_count": self.open_count,
            "groups": tuple(group.to_display_dict() for group in self.groups),
        }


def fingerprint_finding(finding: ReviewFindingInput) -> ReviewFindingFingerprint:
    """Create a deterministic fingerprint from finding identity and raw text."""
    source_ref = _safe_ref(finding.source_id, "source:unsafe")
    artifact_ref = _safe_ref(finding.artifact_id, "artifact:unsafe")
    rule_ref = _safe_ref(finding.rule_id, "rule:unsafe")
    parts = (
        _normalize_for_hash(artifact_ref),
        _normalize_for_hash(rule_ref),
        _normalize_for_hash(finding.location),
        _normalize_for_hash(finding.finding_body),
        _normalize_for_hash(finding.log_excerpt),
    )
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]
    return ReviewFindingFingerprint(
        fingerprint=f"rfp:{digest}",
        source_ref=source_ref,
        artifact_ref=artifact_ref,
        rule_ref=rule_ref,
    )


def build_review_intelligence(
    findings: Iterable[ReviewFindingInput],
) -> ReviewIntelligenceReport:
    """Collapse duplicate findings into display-safe review intelligence."""
    buckets: dict[str, list[ReviewFindingInput]] = {}
    fingerprints: dict[str, ReviewFindingFingerprint] = {}

    for finding in findings:
        fingerprint = fingerprint_finding(finding)
        buckets.setdefault(fingerprint.fingerprint, []).append(finding)
        fingerprints[fingerprint.fingerprint] = fingerprint

    groups = tuple(
        _group_from_findings(fingerprints[key], buckets[key])
        for key in sorted(buckets)
    )
    return ReviewIntelligenceReport(groups=groups)


def _group_from_findings(
    fingerprint: ReviewFindingFingerprint,
    findings: list[ReviewFindingInput],
) -> DuplicateFindingGroup:
    highest = _highest_severity(f.severity for f in findings)
    repair = _repair_verification(findings)
    waiver = _waiver_visibility(findings)
    sources = tuple(sorted({_safe_ref(f.source_id, "source:unsafe") for f in findings}))
    severity = SeverityCalibration(
        severity=highest,
        rationale=_severity_rationale(highest, len(findings), repair.state),
    )
    return DuplicateFindingGroup(
        fingerprint=fingerprint,
        duplicate_count=len(findings),
        sources=sources,
        severity=severity,
        repair=repair,
        waiver=waiver,
        regression_risk=_regression_risk(highest, repair.state, findings),
    )


def _highest_severity(
    severities: Iterable[ReviewFindingSeverity | str],
) -> ReviewFindingSeverity:
    normalized = tuple(_severity(value) for value in severities)
    if not normalized:
        return ReviewFindingSeverity.INFO
    return max(normalized, key=lambda sev: _SEVERITY_RANK[sev])


def _repair_verification(findings: list[ReviewFindingInput]) -> RepairVerification:
    states = tuple(_repair_state(f.repair_state) for f in findings)
    if RepairVerificationState.NOT_FIXED in states:
        state = RepairVerificationState.NOT_FIXED
    elif RepairVerificationState.WAIVED in states:
        state = RepairVerificationState.WAIVED
    else:
        state = RepairVerificationState.FIXED

    refs: list[str] = []
    for finding in findings:
        refs.extend(_safe_ref(ref, "evidence:unsafe") for ref in finding.repair_evidence_refs)
    return RepairVerification(state=state, evidence_refs=tuple(sorted(set(refs))))


def _waiver_visibility(findings: list[ReviewFindingInput]) -> WaiverVisibility:
    waived = [f for f in findings if _repair_state(f.repair_state) is RepairVerificationState.WAIVED]
    if not waived:
        return WaiverVisibility(present=False)

    waiver_ref = next(
        (_safe_ref(f.waiver_id, "waiver:unsafe") for f in waived if f.waiver_id.strip()),
        "waiver:present",
    )
    return WaiverVisibility(
        present=True,
        waiver_ref=waiver_ref,
        reason_visible=any(bool(f.waiver_reason.strip()) for f in waived),
    )


def _regression_risk(
    severity: ReviewFindingSeverity,
    repair_state: RepairVerificationState,
    findings: list[ReviewFindingInput],
) -> RegressionRiskLabel:
    if repair_state is RepairVerificationState.WAIVED:
        return RegressionRiskLabel.HIGH
    if severity is ReviewFindingSeverity.CRITICAL:
        return RegressionRiskLabel.HIGH
    if severity is ReviewFindingSeverity.ERROR:
        if len(findings) > 1 or _has_risky_component(findings) or _has_blocker_tag(findings):
            return RegressionRiskLabel.HIGH
        return RegressionRiskLabel.MEDIUM
    if severity is ReviewFindingSeverity.WARNING:
        if len(findings) > 1 or _has_risky_component(findings):
            return RegressionRiskLabel.MEDIUM
        return RegressionRiskLabel.LOW
    if _has_risky_component(findings) and repair_state is RepairVerificationState.NOT_FIXED:
        return RegressionRiskLabel.MEDIUM
    return RegressionRiskLabel.LOW


def _severity_rationale(
    severity: ReviewFindingSeverity,
    duplicate_count: int,
    repair_state: RepairVerificationState,
) -> str:
    parts = [f"highest observed severity is {severity.value}"]
    if duplicate_count > 1:
        parts.append(f"collapsed {duplicate_count} duplicate observations")
    parts.append(f"repair verification is {repair_state.value}")
    return "; ".join(parts)


def _severity(value: ReviewFindingSeverity | str) -> ReviewFindingSeverity:
    if isinstance(value, ReviewFindingSeverity):
        return value
    clean = str(value).strip().lower()
    try:
        return ReviewFindingSeverity(clean)
    except ValueError:
        return ReviewFindingSeverity.INFO


def _repair_state(value: RepairVerificationState | str) -> RepairVerificationState:
    if isinstance(value, RepairVerificationState):
        return value
    clean = str(value).strip().lower()
    try:
        return RepairVerificationState(clean)
    except ValueError:
        return RepairVerificationState.NOT_FIXED


def _has_risky_component(findings: list[ReviewFindingInput]) -> bool:
    return any(
        str(component).strip().lower() in _RISKY_COMPONENTS
        for finding in findings
        for component in finding.changed_components
    )


def _has_blocker_tag(findings: list[ReviewFindingInput]) -> bool:
    return any(
        bool(str(tag).strip())
        for finding in findings
        for tag in finding.blocker_tags
    )


def _normalize_for_hash(value: object) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def _safe_ref(value: str, fallback: str) -> str:
    clean = value.strip()
    if not clean:
        return fallback
    if _looks_like_path_or_log(clean):
        digest = hashlib.sha256(clean.encode("utf-8")).hexdigest()[:10]
        return f"{fallback}:{digest}"
    return clean


def _looks_like_path_or_log(value: str) -> bool:
    return bool(
        re.search(
            r"(?i)(?:[A-Z]:\\|\\\\[^\\\s]+\\[^\\\s]+\\|/(?:Users|home|var|tmp|mnt|Volumes)/|"
            r"\n|traceback|exception:|api[_-]?key|secret|token|password)",
            value,
        )
    )
