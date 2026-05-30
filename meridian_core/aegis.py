"""
Aegis -- Proof harness. Evidence records and proof trails for Meridian.

Automatic cross-check findings are evidence. Evidence flows:

    cross-check finding
      -> AegisEvidence record
      -> ReviewConsoleItem (via to_console_item())
      -> Prime adjudication

Domain-only: no model calls, no UI, no persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .review_console import (
    ReviewConsoleItem,
    ReviewConsoleSeverity,
    make_approval_gate,
    make_cross_check_item,
)


class EvidenceType(Enum):
    CROSS_CHECK = "cross_check"
    TEST_RESULT = "test_result"
    BUILD_OUTPUT = "build_output"
    REVIEW_VERDICT = "review_verdict"
    SCREENSHOT = "screenshot"
    API_CHECK = "api_check"
    DIFF_INSPECTION = "diff_inspection"
    MANUAL_WAIVER = "manual_waiver"


class EvidenceStatus(Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    WAIVED = "waived"
    ESCALATED = "escalated"


class EvidenceSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# Severities that make open evidence proof-blocking
_BLOCKING_SEVERITIES: frozenset[EvidenceSeverity] = frozenset({
    EvidenceSeverity.ERROR,
    EvidenceSeverity.CRITICAL,
})


@dataclass
class AegisEvidence:
    id: str
    evidence_type: EvidenceType
    severity: EvidenceSeverity
    status: EvidenceStatus
    source: str          # where the finding originated (file, module, check name)
    target: str          # artifact, session, or output that was checked
    summary: str         # human-readable description
    waiver_reason: str = ""
    console_item_id: str | None = None

    # ------------------------------------------------------------------
    # Proof-blocking logic
    # ------------------------------------------------------------------

    def is_proof_blocking(self) -> bool:
        """
        True when this evidence prevents a completion claim.

        - RESOLVED and WAIVED are never blocking.
        - ESCALATED is always blocking (requires human resolution).
        - OPEN is blocking only at ERROR or CRITICAL severity.
        """
        if self.status is EvidenceStatus.RESOLVED:
            return False
        if self.status is EvidenceStatus.WAIVED:
            return False
        if self.status is EvidenceStatus.ESCALATED:
            return True
        return self.severity in _BLOCKING_SEVERITIES  # OPEN

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def resolve(self) -> None:
        """Mark this evidence as resolved."""
        self.status = EvidenceStatus.RESOLVED

    def waive(self, reason: str) -> None:
        """Waive this evidence with an explicit reason on record."""
        self.status = EvidenceStatus.WAIVED
        self.waiver_reason = reason

    def escalate(self) -> None:
        """Escalate this evidence; it will remain proof-blocking until resolved."""
        self.status = EvidenceStatus.ESCALATED

    # ------------------------------------------------------------------
    # Review Console bridge
    # ------------------------------------------------------------------

    def to_console_item(self) -> ReviewConsoleItem:
        """
        Produce a ReviewConsoleItem from this evidence record.

        Proof-blocking evidence becomes an approval gate (requires user response).
        Non-blocking evidence becomes an informational cross-check item.
        """
        rc_severity = _SEVERITY_MAP[self.severity]
        item_id = f"aegis-{self.id}"
        content = f"Source: {self.source} | Target: {self.target}"

        if self.is_proof_blocking():
            return make_approval_gate(
                id=item_id,
                title=f"Proof-blocking finding: {self.summary}",
                content=content,
                severity=rc_severity,
            )
        return make_cross_check_item(
            id=item_id,
            title=self.summary,
            content=content,
            severity=rc_severity,
            is_automatic=True,
        )


_SEVERITY_MAP: dict[EvidenceSeverity, ReviewConsoleSeverity] = {
    EvidenceSeverity.INFO: ReviewConsoleSeverity.INFO,
    EvidenceSeverity.WARNING: ReviewConsoleSeverity.WARNING,
    EvidenceSeverity.ERROR: ReviewConsoleSeverity.ERROR,
    EvidenceSeverity.CRITICAL: ReviewConsoleSeverity.CRITICAL,
}


@dataclass
class ProofTrail:
    """Ordered collection of AegisEvidence for a given work unit."""
    evidence: list[AegisEvidence] = field(default_factory=list)

    def add(self, ev: AegisEvidence) -> None:
        """Append evidence to the trail."""
        self.evidence.append(ev)

    def blocking(self) -> list[AegisEvidence]:
        """All proof-blocking evidence in insertion order."""
        return [e for e in self.evidence if e.is_proof_blocking()]

    def is_clean(self) -> bool:
        """True if no evidence is currently proof-blocking."""
        return len(self.blocking()) == 0

    def open_findings(self) -> list[AegisEvidence]:
        """All evidence with OPEN status."""
        return [e for e in self.evidence if e.status is EvidenceStatus.OPEN]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def evidence_from_cross_check(
    id: str,
    source: str,
    target: str,
    summary: str,
    severity: EvidenceSeverity = EvidenceSeverity.INFO,
) -> AegisEvidence:
    """Create an Aegis evidence record from an automatic cross-check finding."""
    return AegisEvidence(
        id=id,
        evidence_type=EvidenceType.CROSS_CHECK,
        severity=severity,
        status=EvidenceStatus.OPEN,
        source=source,
        target=target,
        summary=summary,
    )
