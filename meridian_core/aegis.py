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

import re
from dataclasses import dataclass, field
from enum import Enum

from .review_console import (
    ReviewConsoleAction,
    ReviewConsoleItem,
    ReviewConsoleResponse,
    ReviewConsoleSeverity,
    ReviewConsoleQueue,
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
        clean_reason = reason.strip()
        if not clean_reason:
            raise ValueError("waiver reason must not be empty or whitespace-only")
        self.status = EvidenceStatus.WAIVED
        self.waiver_reason = clean_reason

    def escalate(self) -> None:
        """Escalate this evidence; it will remain proof-blocking until resolved."""
        self.status = EvidenceStatus.ESCALATED

    def apply_console_response(self, response: ReviewConsoleResponse) -> None:
        """
        Apply a Review Console response to this evidence record.

        APPROVE resolves the evidence.
        REJECT and MODIFY escalate it — finding is unacceptable, needs rework.
        ACKNOWLEDGE is a visibility-only action; evidence status is unchanged.
          The Review Console item transitions to ACKNOWLEDGED on its own;
          Aegis evidence must be explicitly resolved or waived by Prime.

        Raises ValueError if no console item has been created for this evidence
        (call to_console_item() first) or if the response targets a different item.
        """
        if self.console_item_id is None:
            raise ValueError(
                "cannot apply a console response: this evidence has no console item yet; "
                "call to_console_item() first"
            )
        if response.item_id != self.console_item_id:
            raise ValueError(
                f"response item {response.item_id!r} does not match evidence console item "
                f"{self.console_item_id!r}"
            )

        if response.action is ReviewConsoleAction.APPROVE:
            self.resolve()
            return
        if response.action in {ReviewConsoleAction.REJECT, ReviewConsoleAction.MODIFY}:
            self.escalate()
            return
        if response.action is ReviewConsoleAction.ACKNOWLEDGE:
            return  # visibility only; evidence status is unchanged

        raise ValueError(f"Unsupported Review Console action: {response.action.value!r}")

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
        self.console_item_id = item_id

        content = f"Source: {self.source} | Target: {self.target}"
        if self.status is not EvidenceStatus.OPEN:
            content = f"{content} | Status: {self.status.value}"
        if self.status is EvidenceStatus.WAIVED:
            content = f"{content} | Waiver: {self.waiver_reason}"

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

    def to_console_items(self) -> list[ReviewConsoleItem]:
        """Convert all evidence to ReviewConsoleItems in insertion order.

        Each call sets console_item_id on the source evidence record.
        """
        return [e.to_console_item() for e in self.evidence]

    def enqueue_to_review_console(self, queue: ReviewConsoleQueue) -> list[str]:
        """Enqueue all evidence as ReviewConsoleItems and return their ids.

        Items are enqueued in insertion order. Each source evidence record
        has its console_item_id set as a side effect.
        """
        items = self.to_console_items()
        for item in items:
            queue.enqueue(item)
        return [item.id for item in items]


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


# ---------------------------------------------------------------------------
# Aegis Route Validation Gates
# ---------------------------------------------------------------------------


class GateDecision(Enum):
    """Outcome of a single Aegis gate evaluation."""
    ALLOW = "allow"
    DEMOTE = "demote"
    BLOCK = "block"


@dataclass
class GateResult:
    """Result of evaluating a single gate."""
    gate_name: str
    decision: GateDecision
    reason: str = ""
    demote_to_tier: int | None = None


@dataclass
class WaiverRecord:
    """Waiver record for policy exceptions — must include required evidence fields."""
    waiver_id: str
    actor: str
    scope: str
    timestamp: str
    reason: str
    expiration: str | None = None
    evidence_url: str | None = None

    def is_valid(self) -> bool:
        """Check that all required fields are present and non-empty."""
        return bool(
            self.waiver_id.strip()
            and self.actor.strip()
            and self.scope.strip()
            and self.timestamp.strip()
            and self.reason.strip()
        )


@dataclass
class ApprovalRecord:
    """Approval record for user consent — must include required evidence fields."""
    approval_id: str
    actor: str
    scope: str
    timestamp: str
    reason: str
    expiration: str | None = None

    def is_valid(self) -> bool:
        """Check that all required fields are present and non-empty."""
        return bool(
            self.approval_id.strip()
            and self.actor.strip()
            and self.scope.strip()
            and self.timestamp.strip()
            and self.reason.strip()
        )


def gate_unknown_route_class(
    route_class: str | None,
) -> GateResult:
    """
    Gate 1: Unknown Route Class Gate.

    Trigger: route_class is missing, unknown, or ambiguous.
    Allowed values: account_session | local_cli | direct_api | aggregator_api
    Logic: If route_class is not declared, block unconditionally.
    """
    allowed = {"account_session", "local_cli", "direct_api", "aggregator_api"}
    if route_class is None or route_class not in allowed:
        return GateResult(
            gate_name="unknown_route_class",
            decision=GateDecision.BLOCK,
            reason=f"route_class unknown or missing; got {route_class!r}",
        )
    return GateResult(
        gate_name="unknown_route_class",
        decision=GateDecision.ALLOW,
        reason=f"route_class valid: {route_class!r}",
    )


def gate_missing_exact_model_id(
    model_id: str | None,
    risk_tier: int,
) -> GateResult:
    """
    Gate 2: Missing Exact Model ID Gate.

    Trigger: model_id is missing, empty, or unversioned.
    Allowed for: Tier 0, Tier 1 only (with cost/latency pressure noted).
    Logic:
    - For Tier 0, gate passes (no model ID needed).
    - For Tier 1, if model_id missing/unversioned, allow with warning.
    - For Tier 2+, if model_id missing/unversioned, block.

    Heuristic for "unversioned": missing, ends with generic label like
    'latest', 'pro', 'next', 'standard', or lacks date/version patterns
    (YYYY-MM-DD, YYYY-MM, or consecutive digits 2+).
    """
    if risk_tier == 0:
        return GateResult(
            gate_name="missing_exact_model_id",
            decision=GateDecision.ALLOW,
            reason="Tier 0: no model call needed",
        )

    is_missing = model_id is None or model_id == ""

    # Check if unversioned: generic labels or no version pattern
    is_unversioned = False
    if is_missing:
        is_unversioned = True
    elif model_id:
        # Unversioned if it ends with generic labels
        generic_labels = {"latest", "pro", "next", "standard", "preview"}
        if any(model_id.lower().endswith(label) for label in generic_labels):
            is_unversioned = True
        # Or if no date/version pattern found
        elif not any(c.isdigit() for c in model_id):
            is_unversioned = True
        else:
            # Has digits but check for version patterns
            # Look for: YYYY-MM-DD, YYYY-MM, 2+ consecutive digits, or dash-separated numeric components
            has_version = bool(re.search(r'\d{4}-\d{2}|\d{2,}|-\d+', model_id))
            is_unversioned = not has_version

    if is_missing or is_unversioned:
        if risk_tier == 1:
            return GateResult(
                gate_name="missing_exact_model_id",
                decision=GateDecision.ALLOW,
                reason=f"Tier 1: unversioned allowed with warning; model_id={model_id!r}",
            )
        else:
            return GateResult(
                gate_name="missing_exact_model_id",
                decision=GateDecision.BLOCK,
                reason=f"Tier {risk_tier}: exact model ID required; got {model_id!r}",
            )

    return GateResult(
        gate_name="missing_exact_model_id",
        decision=GateDecision.ALLOW,
        reason=f"model_id exact: {model_id!r}",
    )


def gate_tier3_dual_lane_requirement(
    risk_tier: int,
    dual_lane_required: bool,
    waiver_record: WaiverRecord | None = None,
) -> GateResult:
    """
    Gate 3: Tier 3 Dual-Lane Requirement Gate.

    Trigger: risk_tier is 3 and dual_lane_required is not True.
    Logic:
    - If Tier 3 and dual_lane_required=False:
      - If valid waiver_record exists (with actor, scope, timestamp, reason),
        demote to Tier 2.
      - If no valid waiver_record, block.
    - If Tier 3 and dual_lane_required=True, gate passes.
    - Bare boolean waivers are not accepted; structured evidence required.
    """
    if risk_tier != 3:
        return GateResult(
            gate_name="tier3_dual_lane_requirement",
            decision=GateDecision.ALLOW,
            reason=f"Tier {risk_tier}: dual-lane not required",
        )

    if dual_lane_required:
        return GateResult(
            gate_name="tier3_dual_lane_requirement",
            decision=GateDecision.ALLOW,
            reason="Tier 3: dual-lane required and provided",
        )

    if waiver_record is not None and waiver_record.is_valid():
        return GateResult(
            gate_name="tier3_dual_lane_requirement",
            decision=GateDecision.DEMOTE,
            reason=f"Tier 3 without dual-lane; valid waiver permits demotion (waiver_id={waiver_record.waiver_id})",
            demote_to_tier=2,
        )

    return GateResult(
        gate_name="tier3_dual_lane_requirement",
        decision=GateDecision.BLOCK,
        reason="Tier 3 single-lane blocked; dual-lane required or valid waiver record needed (actor, scope, timestamp, reason)",
    )


def gate_unknown_proof_requirement(
    proof_required: str | None,
    risk_tier: int,
) -> GateResult:
    """
    Gate 4: Unknown Proof Requirement Gate.

    Trigger: proof_required is missing or unknown.
    Allowed values per tier:
    - Tier 0: none
    - Tier 1: none | artifact | telemetry
    - Tier 2: artifact | telemetry | code_review
    - Tier 3: code_review | security_review | dual_review
    - Tier 4: human_gate | security_review

    Logic:
    - If proof_required unknown, block.
    - If mismatch (insufficient for tier), demote or block.
    """
    valid_by_tier = {
        0: {"none"},
        1: {"none", "artifact", "telemetry"},
        2: {"artifact", "telemetry", "code_review"},
        3: {"code_review", "security_review", "dual_review"},
        4: {"human_gate", "security_review"},
    }

    allowed = valid_by_tier.get(risk_tier, set())

    if proof_required is None or proof_required not in allowed:
        if proof_required is None:
            return GateResult(
                gate_name="unknown_proof_requirement",
                decision=GateDecision.BLOCK,
                reason=f"Tier {risk_tier}: proof_required is missing",
            )
        return GateResult(
            gate_name="unknown_proof_requirement",
            decision=GateDecision.BLOCK,
            reason=f"Tier {risk_tier}: proof_required={proof_required!r} not allowed (allowed: {allowed})",
        )

    return GateResult(
        gate_name="unknown_proof_requirement",
        decision=GateDecision.ALLOW,
        reason=f"Tier {risk_tier}: proof_required={proof_required!r} valid",
    )


def gate_unsafe_fallback(
    fallback_allowed: bool,
    fallback_blockers: list[str] | None,
    risk_tier: int,
) -> GateResult:
    """
    Gate 5: Unsafe Fallback Gate.

    Trigger: fallback_allowed is True but fallback_blockers contains risk flags.
    Logic:
    - If fallback_allowed=False, gate passes (no fallback to validate).
    - If blocker is "silent_fallback", block unconditionally.
    - If blocker is "trust_downgrade" and Tier >= 2, allow with warning.
    - If blocker is "cost_increase" and cost_posture=PREMIUM, allow but warn.
    - If blocker is "model_mismatch" and Tier >= 3, block.
    """
    if not fallback_allowed:
        return GateResult(
            gate_name="unsafe_fallback",
            decision=GateDecision.ALLOW,
            reason="no fallback configured",
        )

    blockers = fallback_blockers or []

    if "silent_fallback" in blockers:
        return GateResult(
            gate_name="unsafe_fallback",
            decision=GateDecision.BLOCK,
            reason="silent fallback not allowed for Tier 2+",
        )

    if "model_mismatch" in blockers and risk_tier >= 3:
        return GateResult(
            gate_name="unsafe_fallback",
            decision=GateDecision.BLOCK,
            reason="fallback model mismatch not allowed for Tier 3+",
        )

    return GateResult(
        gate_name="unsafe_fallback",
        decision=GateDecision.ALLOW,
        reason=f"fallback blockers acceptable: {blockers}",
    )


def gate_unvalidated_deepseek(
    provider: str | None,
    trust_mode: str,
    external_review_status: str | None,
    risk_tier: int,
) -> GateResult:
    """
    Gate 6: Unvalidated DeepSeek Gate.

    Trigger: provider=="deepseek" and external_review_status is not PASSED.
    Logic:
    - If provider != deepseek, gate passes.
    - If provider==deepseek:
      - If trust_mode != DIRECT, block.
      - If external_review_status==PENDING, allow Tier 0-1 only.
      - If external_review_status==PASSED (within 30 days), gate passes.
      - If external_review_status==FAILED or EXPIRED, block.
    """
    if provider != "deepseek":
        return GateResult(
            gate_name="unvalidated_deepseek",
            decision=GateDecision.ALLOW,
            reason=f"provider={provider!r}; no DeepSeek validation needed",
        )

    if trust_mode != "DIRECT":
        return GateResult(
            gate_name="unvalidated_deepseek",
            decision=GateDecision.BLOCK,
            reason="DeepSeek through aggregator not allowed; use direct API",
        )

    if external_review_status == "PENDING":
        if risk_tier <= 1:
            return GateResult(
                gate_name="unvalidated_deepseek",
                decision=GateDecision.ALLOW,
                reason=f"Tier {risk_tier}: DeepSeek validation pending, allowed for Tier 0-1",
            )
        return GateResult(
            gate_name="unvalidated_deepseek",
            decision=GateDecision.DEMOTE,
            reason=f"Tier {risk_tier}: DeepSeek validation pending, demoting to Tier 1",
            demote_to_tier=1,
        )

    if external_review_status == "PASSED":
        return GateResult(
            gate_name="unvalidated_deepseek",
            decision=GateDecision.ALLOW,
            reason=f"Tier {risk_tier}: DeepSeek validation passed",
        )

    if external_review_status in ("FAILED", "EXPIRED", "NOT_REQUIRED"):
        return GateResult(
            gate_name="unvalidated_deepseek",
            decision=GateDecision.BLOCK,
            reason=f"DeepSeek validation not available: {external_review_status!r}",
        )

    return GateResult(
        gate_name="unvalidated_deepseek",
        decision=GateDecision.BLOCK,
        reason=f"DeepSeek validation status unknown: {external_review_status!r}",
    )


def gate_aggregator_authority(
    trust_mode: str,
    risk_tier: int,
    proof_strength: str = "WEAK",
    selected_model_evidence: str | None = None,
) -> GateResult:
    """
    Gate 7: Aggregator Authority Gate.

    Trigger: trust_mode==AGGREGATOR and risk_tier >= 3.
    Logic:
    - If Tier >= 3 and aggregator, block.
    - If Tier 2 and aggregator, require explicit selected model/vendor evidence.
    - If Tier 0-1 and aggregator and proof_strength=WEAK, allow with warning.
    - If proof_strength=NONE, block.
    """
    if trust_mode != "AGGREGATOR":
        return GateResult(
            gate_name="aggregator_authority",
            decision=GateDecision.ALLOW,
            reason=f"trust_mode={trust_mode!r}; not aggregator",
        )

    if risk_tier >= 3:
        return GateResult(
            gate_name="aggregator_authority",
            decision=GateDecision.BLOCK,
            reason=f"Tier {risk_tier}: aggregator not authorized",
        )

    if proof_strength == "NONE":
        return GateResult(
            gate_name="aggregator_authority",
            decision=GateDecision.BLOCK,
            reason="aggregator route with no proof not allowed",
        )

    # Tier 2 aggregator routes require explicit selected model/vendor evidence
    if risk_tier == 2:
        if not selected_model_evidence or selected_model_evidence.strip() == "":
            return GateResult(
                gate_name="aggregator_authority",
                decision=GateDecision.BLOCK,
                reason="Tier 2: aggregator route requires explicit selected model/vendor evidence",
            )
        return GateResult(
            gate_name="aggregator_authority",
            decision=GateDecision.ALLOW,
            reason=f"Tier 2: aggregator allowed with explicit model evidence ({selected_model_evidence!r})",
        )

    # Tier 0-1 aggregator routes
    return GateResult(
        gate_name="aggregator_authority",
        decision=GateDecision.ALLOW,
        reason=f"Tier {risk_tier}: aggregator allowed for Tier 0-1",
    )


def gate_account_session_risk(
    route_class: str,
    account_risk_level: str | None,
    session_health_status: str | None,
    risk_tier: int,
) -> GateResult:
    """
    Gate 8: Account/Session Risk Gate.

    Trigger: route_class==account_session.
    Logic:
    - If route_class != account_session, gate passes.
    - If account_risk_level missing, assume UNKNOWN and demote to Tier 1.
    - If account_risk_level==HIGH and Tier >= 2, block.
    - If session_health_status in (POLLUTED, STALE, WRONG_PROJECT), block.
    """
    if route_class != "account_session":
        return GateResult(
            gate_name="account_session_risk",
            decision=GateDecision.ALLOW,
            reason=f"route_class={route_class!r}; not account_session",
        )

    if session_health_status in ("POLLUTED", "STALE", "WRONG_PROJECT"):
        return GateResult(
            gate_name="account_session_risk",
            decision=GateDecision.BLOCK,
            reason=f"session context invalid: {session_health_status!r}",
        )

    if account_risk_level is None:
        return GateResult(
            gate_name="account_session_risk",
            decision=GateDecision.DEMOTE,
            reason="account_risk_level unknown; demoting to Tier 1",
            demote_to_tier=1,
        )

    if account_risk_level == "HIGH" and risk_tier >= 2:
        return GateResult(
            gate_name="account_session_risk",
            decision=GateDecision.BLOCK,
            reason=f"account risk level HIGH not allowed for Tier {risk_tier}",
        )

    return GateResult(
        gate_name="account_session_risk",
        decision=GateDecision.ALLOW,
        reason=f"account_risk_level={account_risk_level!r}; session={session_health_status!r}",
    )


def gate_cost_exposure(
    cost_posture: str,
    cost_justified: bool,
    risk_tier: int,
    cost_pressure: str | None = None,
    approval_record: ApprovalRecord | None = None,
) -> GateResult:
    """
    Gate 9: Cost Exposure Gate.

    Trigger: cost_posture==PREMIUM or risk_tier==4.
    Logic:
    - If cost_posture==PREMIUM and cost_justified=False:
      - For Tier <= 1, allow with warning.
      - For Tier >= 2, block unless valid approval_record exists
        (with actor, scope, timestamp, reason).
    - If risk_tier==4 and cost_pressure in (QUOTA_LIMITED, EXHAUSTED), block.
    - Bare boolean approvals are not accepted; structured evidence required.
    """
    if risk_tier == 4:
        if cost_pressure in ("QUOTA_LIMITED", "EXHAUSTED"):
            return GateResult(
                gate_name="cost_exposure",
                decision=GateDecision.BLOCK,
                reason=f"Tier 4: cost limit reached ({cost_pressure!r})",
            )

    if cost_posture != "PREMIUM":
        return GateResult(
            gate_name="cost_exposure",
            decision=GateDecision.ALLOW,
            reason=f"cost_posture={cost_posture!r}",
        )

    if cost_justified:
        return GateResult(
            gate_name="cost_exposure",
            decision=GateDecision.ALLOW,
            reason="premium cost justified",
        )

    if risk_tier <= 1:
        return GateResult(
            gate_name="cost_exposure",
            decision=GateDecision.ALLOW,
            reason=f"Tier {risk_tier}: premium cost allowed with warning",
        )

    # Tier >= 2: premium cost requires explicit user approval
    if approval_record is not None and approval_record.is_valid():
        return GateResult(
            gate_name="cost_exposure",
            decision=GateDecision.ALLOW,
            reason=f"Tier {risk_tier}: premium cost approved by user (approval_id={approval_record.approval_id})",
        )

    return GateResult(
        gate_name="cost_exposure",
        decision=GateDecision.BLOCK,
        reason=f"Tier {risk_tier}: premium cost requires valid user approval record (actor, scope, timestamp, reason)",
    )


# ---------------------------------------------------------------------------
# Aegis Gate Summary Helpers for Relay/Bifrost Display
# ---------------------------------------------------------------------------


# Gate metadata: human-readable labels and proof requirements per gate
_GATE_METADATA = {
    "unknown_route_class": {
        "label": "Route Class Validation",
        "proof_type": "route metadata",
    },
    "missing_exact_model_id": {
        "label": "Model ID Exactness",
        "proof_type": "model version audit trail",
    },
    "tier3_dual_lane_requirement": {
        "label": "Tier 3 Dual-Lane Requirement",
        "proof_type": "dual-lane evidence or waiver record",
    },
    "unknown_proof_requirement": {
        "label": "Proof Requirement",
        "proof_type": "proof artifacts per risk tier",
    },
    "unsafe_fallback": {
        "label": "Fallback Safety",
        "proof_type": "fallback blockers analysis",
    },
    "unvalidated_deepseek": {
        "label": "DeepSeek Validation",
        "proof_type": "external review status",
    },
    "aggregator_authority": {
        "label": "Aggregator Authority",
        "proof_type": "proof strength and selected model evidence",
    },
    "account_session_risk": {
        "label": "Account/Session Risk",
        "proof_type": "account risk level and session health",
    },
    "cost_exposure": {
        "label": "Cost Exposure",
        "proof_type": "cost justification or user approval record",
    },
}


def _decision_to_severity(decision: GateDecision) -> str:
    """Map GateDecision to display severity level."""
    if decision == GateDecision.ALLOW:
        return "info"
    if decision == GateDecision.DEMOTE:
        return "warning"
    return "error"  # BLOCK


def _extract_waiver_approval_status(gate_name: str, reason: str) -> str:
    """Extract waiver/approval status from gate result reason if present."""
    if "waiver" in reason.lower() and "valid" in reason.lower():
        return "waiver_present"
    if "approval" in reason.lower() and "valid" in reason.lower():
        return "approval_present"
    if "waiver" in reason.lower() or "approval" in reason.lower():
        return "waiver_approval_missing"
    return "none"


def _downstream_action(gate_name: str, decision: GateDecision, demote_to_tier: int | None) -> str:
    """Describe the downstream action based on gate decision."""
    if decision == GateDecision.ALLOW:
        return "route_allowed"
    if decision == GateDecision.DEMOTE:
        tier_label = f"tier_{demote_to_tier}" if demote_to_tier is not None else "lower_tier"
        return f"route_demoted_to_{tier_label}"
    return "route_blocked"


@dataclass
class GateSummary:
    """Display-friendly summary of a single gate result for Relay/Bifrost."""
    gate_id: str
    gate_label: str
    decision: str
    severity: str
    reason: str
    required_evidence: str
    waiver_approval_status: str
    downstream_action: str


def summarize_gate_result(result: GateResult) -> GateSummary:
    """
    Produce a Relay/Bifrost-friendly summary of a gate result.

    Pure, deterministic function: no model calls, no account inspection.
    Output is display-safe for both system and human consumption.
    """
    gate_name = result.gate_name
    metadata = _GATE_METADATA.get(gate_name, {
        "label": gate_name.replace("_", " ").title(),
        "proof_type": "gate-specific evidence",
    })

    return GateSummary(
        gate_id=gate_name,
        gate_label=metadata["label"],
        decision=result.decision.value,
        severity=_decision_to_severity(result.decision),
        reason=result.reason,
        required_evidence=metadata["proof_type"],
        waiver_approval_status=_extract_waiver_approval_status(gate_name, result.reason),
        downstream_action=_downstream_action(gate_name, result.decision, result.demote_to_tier),
    )


def summarize_gate_results(results: list[GateResult]) -> list[GateSummary]:
    """Summarize multiple gate results in order."""
    return [summarize_gate_result(r) for r in results]


def format_gate_summary_for_display(summary: GateSummary) -> str:
    """Format a GateSummary for human-readable display."""
    return (
        f"{summary.gate_label}: {summary.decision.upper()} "
        f"(severity={summary.severity})\n"
        f"  reason: {summary.reason}\n"
        f"  evidence: {summary.required_evidence}\n"
        f"  waiver/approval: {summary.waiver_approval_status}\n"
        f"  action: {summary.downstream_action}"
    )
