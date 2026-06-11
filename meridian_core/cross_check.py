"""Backend cross-check authority for Meridian V2.

This module owns typed cross-check execution, repair routing, finding
disposition, and verification reruns. It is pure backend domain logic: no UI,
bridge route, persistence store, process/session control, model calls, network
calls, or filesystem reads/writes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Iterable, Optional

from .aegis import AegisEvidence, EvidenceSeverity, evidence_from_cross_check
from .review_console import ReviewConsoleItem


SHORT_TEXT_MAX = 160
SUMMARY_MAX = 420
SAFE_REF_SCHEMES = (
    "aegis://",
    "backlog://",
    "crosscheck://",
    "proof://",
    "review://",
    "task://",
    "xck://",
)
UNSAFE_TERMS = (
    "raw prompt",
    "serialized prompt",
    "provider response",
    "worker chat",
    "transcript",
    "api key",
    "secret",
    "credential",
    "token=",
)


class CrossCheckValidationError(ValueError):
    """Raised when cross-check authority input is unsafe or inconsistent."""


class CrossCheckSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class CrossCheckFindingStatus(Enum):
    OPEN = "open"
    APPROVED = "approved"
    DISMISSED = "dismissed"
    WAIVED = "waived"
    ROUTED_FOR_REPAIR = "routed_for_repair"
    VERIFIED = "verified"
    VERIFICATION_FAILED = "verification_failed"


class CrossCheckRunStatus(Enum):
    PASSED = "passed"
    FINDINGS_OPEN = "findings_open"


class CrossCheckDispositionAction(Enum):
    APPROVE = "approve"
    DISMISS = "dismiss"
    WAIVE = "waive"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CrossCheckValidationError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


def _looks_like_path(value: str) -> bool:
    if re.search(r"^[A-Za-z]:[\\/]", value):
        return True
    if value.startswith(("/", "\\", "./", ".\\", "../", "..\\")):
        return True
    if re.search(r"\b[\w.-]+[\\/][\w.-]+", value):
        return True
    return False


def _looks_like_uri_path_payload(value: str) -> bool:
    if re.search(r"^[A-Za-z]:[\\/]", value):
        return True
    if value.startswith(("/", "\\", "./", ".\\", "../", "..\\")):
        return True
    if "\\" in value:
        return True
    segments = [segment for segment in value.split("/") if segment]
    if any(segment in (".", "..") for segment in segments):
        return True
    if any(re.search(r"\.[A-Za-z0-9]{1,8}$", segment) for segment in segments):
        return True
    return False


def _safe_text(value: str, field: str, max_length: int = SHORT_TEXT_MAX) -> str:
    text = str(value).strip()
    if not text:
        raise CrossCheckValidationError(f"{field} must not be empty")
    if len(text) > max_length:
        raise CrossCheckValidationError(f"{field} is too long")
    lowered = text.lower()
    if any(term in lowered for term in UNSAFE_TERMS):
        raise CrossCheckValidationError(f"{field} contains unsafe content")
    if _looks_like_path(text):
        raise CrossCheckValidationError(f"{field} must not contain local paths")
    return text


def _safe_uri_ref(value: str, field: str) -> str:
    ref = str(value).strip()
    if not ref:
        raise CrossCheckValidationError(f"{field} must not be empty")
    if len(ref) > SHORT_TEXT_MAX:
        raise CrossCheckValidationError(f"{field} is too long")
    lowered = ref.lower()
    if any(term in lowered for term in UNSAFE_TERMS):
        raise CrossCheckValidationError(f"{field} contains unsafe content")
    scheme = next((safe_scheme for safe_scheme in SAFE_REF_SCHEMES if ref.startswith(safe_scheme)), None)
    if scheme is None:
        raise CrossCheckValidationError(f"{field} uses an unsupported URI scheme")
    payload = ref[len(scheme) :]
    if not payload:
        raise CrossCheckValidationError(f"{field} must include a safe ref payload")
    if _looks_like_uri_path_payload(payload):
        raise CrossCheckValidationError(f"{field} must not contain local paths")
    return ref


def _safe_ref(value: str, field: str) -> str:
    ref = str(value).strip()
    if ref.startswith(SAFE_REF_SCHEMES):
        return _safe_uri_ref(ref, field)
    ref = _safe_text(ref, field, SHORT_TEXT_MAX)
    if "://" in ref:
        raise CrossCheckValidationError(f"{field} uses an unsupported URI scheme")
    return ref


def _safe_refs(values: Iterable[str], field: str) -> tuple[str, ...]:
    refs = tuple(_safe_ref(str(value), field) for value in values)
    if len(set(refs)) != len(refs):
        raise CrossCheckValidationError(f"{field} must not contain duplicates")
    return refs


def _blocking(severity: CrossCheckSeverity) -> bool:
    return severity in (CrossCheckSeverity.ERROR, CrossCheckSeverity.CRITICAL)


def _aegis_severity(severity: CrossCheckSeverity) -> EvidenceSeverity:
    return {
        CrossCheckSeverity.INFO: EvidenceSeverity.INFO,
        CrossCheckSeverity.WARNING: EvidenceSeverity.WARNING,
        CrossCheckSeverity.ERROR: EvidenceSeverity.ERROR,
        CrossCheckSeverity.CRITICAL: EvidenceSeverity.CRITICAL,
    }[severity]


@dataclass(frozen=True)
class CrossCheckRunRequest:
    run_id: str
    objective: str
    scope_refs: tuple[str, ...]
    requested_by: str
    requested_at: datetime
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _safe_text(self.run_id, "CrossCheckRunRequest.run_id")
        _safe_text(self.objective, "CrossCheckRunRequest.objective", SUMMARY_MAX)
        object.__setattr__(self, "scope_refs", _safe_refs(self.scope_refs, "CrossCheckRunRequest.scope_refs"))
        _safe_text(self.requested_by, "CrossCheckRunRequest.requested_by")
        _as_utc(self.requested_at)
        object.__setattr__(self, "evidence_refs", _safe_refs(self.evidence_refs, "CrossCheckRunRequest.evidence_refs"))


@dataclass(frozen=True)
class CrossCheckFinding:
    finding_id: str
    source: str
    target_ref: str
    summary: str
    severity: CrossCheckSeverity
    status: CrossCheckFindingStatus = CrossCheckFindingStatus.OPEN
    evidence_refs: tuple[str, ...] = ()
    repair_route_id: Optional[str] = None
    disposition_id: Optional[str] = None
    verification_id: Optional[str] = None

    def __post_init__(self) -> None:
        _safe_text(self.finding_id, "CrossCheckFinding.finding_id")
        _safe_text(self.source, "CrossCheckFinding.source")
        _safe_ref(self.target_ref, "CrossCheckFinding.target_ref")
        _safe_text(self.summary, "CrossCheckFinding.summary", SUMMARY_MAX)
        if not isinstance(self.severity, CrossCheckSeverity):
            raise CrossCheckValidationError("severity must be a CrossCheckSeverity")
        if not isinstance(self.status, CrossCheckFindingStatus):
            raise CrossCheckValidationError("status must be a CrossCheckFindingStatus")
        object.__setattr__(self, "evidence_refs", _safe_refs(self.evidence_refs, "CrossCheckFinding.evidence_refs"))
        if self.repair_route_id is not None:
            _safe_text(self.repair_route_id, "CrossCheckFinding.repair_route_id")
        if self.disposition_id is not None:
            _safe_text(self.disposition_id, "CrossCheckFinding.disposition_id")
        if self.verification_id is not None:
            _safe_text(self.verification_id, "CrossCheckFinding.verification_id")

    def is_blocking(self) -> bool:
        return self.status in (
            CrossCheckFindingStatus.OPEN,
            CrossCheckFindingStatus.ROUTED_FOR_REPAIR,
            CrossCheckFindingStatus.VERIFICATION_FAILED,
        ) and _blocking(self.severity)

    def to_aegis_evidence(self) -> AegisEvidence:
        evidence = evidence_from_cross_check(
            id=self.finding_id,
            source=self.source,
            target=self.target_ref,
            summary=self.summary,
            severity=_aegis_severity(self.severity),
        )
        if self.status is CrossCheckFindingStatus.APPROVED:
            evidence.resolve()
        elif self.status is CrossCheckFindingStatus.WAIVED:
            evidence.waive("waived by cross-check disposition")
        elif self.status is CrossCheckFindingStatus.VERIFIED:
            evidence.resolve()
        elif self.status is CrossCheckFindingStatus.DISMISSED:
            evidence.resolve()
        return evidence

    def to_review_console_item(self) -> ReviewConsoleItem:
        return self.to_aegis_evidence().to_console_item()


@dataclass(frozen=True)
class CrossCheckRunResult:
    run_id: str
    status: CrossCheckRunStatus
    findings: tuple[CrossCheckFinding, ...]
    executed_by: str
    executed_at: datetime
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _safe_text(self.run_id, "CrossCheckRunResult.run_id")
        if not isinstance(self.status, CrossCheckRunStatus):
            raise CrossCheckValidationError("status must be a CrossCheckRunStatus")
        object.__setattr__(self, "findings", tuple(self.findings))
        for finding in self.findings:
            if not isinstance(finding, CrossCheckFinding):
                raise CrossCheckValidationError("findings must be CrossCheckFinding")
        _safe_text(self.executed_by, "CrossCheckRunResult.executed_by")
        _as_utc(self.executed_at)
        object.__setattr__(self, "evidence_refs", _safe_refs(self.evidence_refs, "CrossCheckRunResult.evidence_refs"))


@dataclass(frozen=True)
class CrossCheckRepairRoute:
    route_id: str
    finding_id: str
    owner: str
    reason: str
    routed_by: str
    routed_at: datetime
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _safe_text(self.route_id, "CrossCheckRepairRoute.route_id")
        _safe_text(self.finding_id, "CrossCheckRepairRoute.finding_id")
        _safe_text(self.owner, "CrossCheckRepairRoute.owner")
        _safe_text(self.reason, "CrossCheckRepairRoute.reason", SUMMARY_MAX)
        _safe_text(self.routed_by, "CrossCheckRepairRoute.routed_by")
        _as_utc(self.routed_at)
        object.__setattr__(self, "evidence_refs", _safe_refs(self.evidence_refs, "CrossCheckRepairRoute.evidence_refs"))


@dataclass(frozen=True)
class CrossCheckDisposition:
    disposition_id: str
    finding_id: str
    action: CrossCheckDispositionAction
    actor: str
    reason: str
    scope: str
    timestamp: datetime
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _safe_text(self.disposition_id, "CrossCheckDisposition.disposition_id")
        _safe_text(self.finding_id, "CrossCheckDisposition.finding_id")
        if not isinstance(self.action, CrossCheckDispositionAction):
            raise CrossCheckValidationError("action must be a CrossCheckDispositionAction")
        _safe_text(self.actor, "CrossCheckDisposition.actor")
        _safe_text(self.reason, "CrossCheckDisposition.reason", SUMMARY_MAX)
        _safe_text(self.scope, "CrossCheckDisposition.scope")
        _as_utc(self.timestamp)
        object.__setattr__(self, "evidence_refs", _safe_refs(self.evidence_refs, "CrossCheckDisposition.evidence_refs"))
        if self.action is CrossCheckDispositionAction.WAIVE and not self.evidence_refs:
            raise CrossCheckValidationError("waive disposition requires evidence_refs")


@dataclass(frozen=True)
class CrossCheckVerificationRequest:
    verification_id: str
    finding_id: str
    repaired_evidence_refs: tuple[str, ...]
    requested_by: str
    requested_at: datetime

    def __post_init__(self) -> None:
        _safe_text(self.verification_id, "CrossCheckVerificationRequest.verification_id")
        _safe_text(self.finding_id, "CrossCheckVerificationRequest.finding_id")
        object.__setattr__(
            self,
            "repaired_evidence_refs",
            _safe_refs(self.repaired_evidence_refs, "CrossCheckVerificationRequest.repaired_evidence_refs"),
        )
        if not self.repaired_evidence_refs:
            raise CrossCheckValidationError("verification requires repaired_evidence_refs")
        _safe_text(self.requested_by, "CrossCheckVerificationRequest.requested_by")
        _as_utc(self.requested_at)


@dataclass(frozen=True)
class CrossCheckVerificationResult:
    verification_id: str
    finding_id: str
    passed: bool
    verifier: str
    verified_at: datetime
    evidence_refs: tuple[str, ...]
    followup_findings: tuple[CrossCheckFinding, ...] = ()

    def __post_init__(self) -> None:
        _safe_text(self.verification_id, "CrossCheckVerificationResult.verification_id")
        _safe_text(self.finding_id, "CrossCheckVerificationResult.finding_id")
        if not isinstance(self.passed, bool):
            raise CrossCheckValidationError("passed must be bool")
        _safe_text(self.verifier, "CrossCheckVerificationResult.verifier")
        _as_utc(self.verified_at)
        object.__setattr__(self, "evidence_refs", _safe_refs(self.evidence_refs, "CrossCheckVerificationResult.evidence_refs"))
        if not self.evidence_refs:
            raise CrossCheckValidationError("verification result requires evidence_refs")
        object.__setattr__(self, "followup_findings", tuple(self.followup_findings))
        for finding in self.followup_findings:
            if not isinstance(finding, CrossCheckFinding):
                raise CrossCheckValidationError("followup_findings must be CrossCheckFinding")
        if self.passed and self.followup_findings:
            raise CrossCheckValidationError("passed verification cannot include followup_findings")


CrossCheckRunner = Callable[[CrossCheckRunRequest], Iterable[CrossCheckFinding]]
CrossCheckVerifier = Callable[[CrossCheckFinding, CrossCheckVerificationRequest], CrossCheckVerificationResult]


def execute_cross_check(
    request: CrossCheckRunRequest,
    runner: CrossCheckRunner,
    *,
    executed_by: str,
    executed_at: datetime,
) -> CrossCheckRunResult:
    """Run a backend-authorized cross-check through an injected runner."""
    if not isinstance(request, CrossCheckRunRequest):
        raise CrossCheckValidationError("request must be CrossCheckRunRequest")
    if not callable(runner):
        raise CrossCheckValidationError("runner must be callable")
    findings = tuple(runner(request))
    for finding in findings:
        if not isinstance(finding, CrossCheckFinding):
            raise CrossCheckValidationError("runner must return CrossCheckFinding records")
        if finding.status is not CrossCheckFindingStatus.OPEN:
            raise CrossCheckValidationError("runner findings must be open")
        if finding.repair_route_id or finding.disposition_id or finding.verification_id:
            raise CrossCheckValidationError("runner findings must not include authority ids")
    status = (
        CrossCheckRunStatus.FINDINGS_OPEN
        if any(finding.is_blocking() for finding in findings)
        else CrossCheckRunStatus.PASSED
    )
    return CrossCheckRunResult(
        run_id=request.run_id,
        status=status,
        findings=findings,
        executed_by=executed_by,
        executed_at=executed_at,
        evidence_refs=request.evidence_refs,
    )


def route_finding_for_repair(
    finding: CrossCheckFinding,
    *,
    route_id: str,
    owner: str,
    reason: str,
    routed_by: str,
    routed_at: datetime,
    evidence_refs: tuple[str, ...] = (),
) -> tuple[CrossCheckFinding, CrossCheckRepairRoute]:
    """Route an open finding to a backend repair owner without executing repair."""
    if finding.status not in (
        CrossCheckFindingStatus.OPEN,
        CrossCheckFindingStatus.VERIFICATION_FAILED,
    ):
        raise CrossCheckValidationError("only open or failed-verification findings can be routed for repair")
    route = CrossCheckRepairRoute(
        route_id=route_id,
        finding_id=finding.finding_id,
        owner=owner,
        reason=reason,
        routed_by=routed_by,
        routed_at=routed_at,
        evidence_refs=evidence_refs,
    )
    updated = replace(
        finding,
        status=CrossCheckFindingStatus.ROUTED_FOR_REPAIR,
        repair_route_id=route.route_id,
        verification_id=None,
        evidence_refs=finding.evidence_refs + route.evidence_refs,
    )
    return updated, route


def dispose_finding(
    finding: CrossCheckFinding,
    disposition: CrossCheckDisposition,
) -> CrossCheckFinding:
    """Apply an approve, dismiss, or waive disposition to a finding."""
    if finding.finding_id != disposition.finding_id:
        raise CrossCheckValidationError("disposition finding_id does not match")
    if finding.status in (
        CrossCheckFindingStatus.APPROVED,
        CrossCheckFindingStatus.DISMISSED,
        CrossCheckFindingStatus.WAIVED,
        CrossCheckFindingStatus.VERIFIED,
    ):
        raise CrossCheckValidationError("finding is already closed")
    next_status = {
        CrossCheckDispositionAction.APPROVE: CrossCheckFindingStatus.APPROVED,
        CrossCheckDispositionAction.DISMISS: CrossCheckFindingStatus.DISMISSED,
        CrossCheckDispositionAction.WAIVE: CrossCheckFindingStatus.WAIVED,
    }[disposition.action]
    return replace(
        finding,
        status=next_status,
        disposition_id=disposition.disposition_id,
        evidence_refs=finding.evidence_refs + disposition.evidence_refs,
    )


def rerun_verification(
    finding: CrossCheckFinding,
    request: CrossCheckVerificationRequest,
    verifier: CrossCheckVerifier,
) -> tuple[CrossCheckFinding, CrossCheckVerificationResult]:
    """Rerun verification for a repaired finding through an injected verifier."""
    if finding.finding_id != request.finding_id:
        raise CrossCheckValidationError("verification finding_id does not match")
    if finding.status is not CrossCheckFindingStatus.ROUTED_FOR_REPAIR:
        raise CrossCheckValidationError("only repair-routed findings can be verified")
    if not finding.repair_route_id:
        raise CrossCheckValidationError("repair-routed findings require repair_route_id")
    if not callable(verifier):
        raise CrossCheckValidationError("verifier must be callable")
    result = verifier(finding, request)
    if not isinstance(result, CrossCheckVerificationResult):
        raise CrossCheckValidationError("verifier must return CrossCheckVerificationResult")
    if result.verification_id != request.verification_id:
        raise CrossCheckValidationError("verification result id does not match request")
    if result.finding_id != finding.finding_id:
        raise CrossCheckValidationError("verification result finding_id does not match")
    next_status = (
        CrossCheckFindingStatus.VERIFIED
        if result.passed
        else CrossCheckFindingStatus.VERIFICATION_FAILED
    )
    updated = replace(
        finding,
        status=next_status,
        verification_id=result.verification_id,
        evidence_refs=finding.evidence_refs + request.repaired_evidence_refs + result.evidence_refs,
    )
    return updated, result
