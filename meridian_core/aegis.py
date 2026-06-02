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

    if risk_tier <= 1:
        # Tier 0-1: premium cost allowed if cost_justified or by default
        if cost_justified:
            return GateResult(
                gate_name="cost_exposure",
                decision=GateDecision.ALLOW,
                reason="premium cost justified",
            )
        return GateResult(
            gate_name="cost_exposure",
            decision=GateDecision.ALLOW,
            reason=f"Tier {risk_tier}: premium cost allowed with warning",
        )

    # Tier >= 2: premium cost requires explicit user approval, not cost_justified alone
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


# ---------------------------------------------------------------------------
# Aegis Aggregate Route-Gate Summary Helpers
# ---------------------------------------------------------------------------


def _highest_severity(severities: list[str]) -> str:
    """Determine highest severity from a list: error > warning > info."""
    severity_order = {"error": 3, "warning": 2, "info": 1}
    return max(severities, key=lambda s: severity_order.get(s, 0))


def _aggregate_downstream_action(summaries: list[GateSummary]) -> str:
    """
    Determine aggregate downstream action from multiple gates.

    Priority: route_blocked > route_demoted > route_allowed
    """
    actions = [s.downstream_action for s in summaries]

    # If any gate blocks, the route is blocked
    if any("blocked" in action for action in actions):
        return "route_blocked"

    # If any gate demotes, find the lowest tier demotion
    demote_actions = [a for a in actions if "demoted" in a]
    if demote_actions:
        # Extract tier numbers and return the lowest
        tiers = []
        for action in demote_actions:
            try:
                tier = int(action.split("_")[-1])
                tiers.append(tier)
            except (ValueError, IndexError):
                pass
        if tiers:
            return f"route_demoted_to_tier_{min(tiers)}"
        return "route_demoted"

    return "route_allowed"


def _aggregate_evidence_status(summaries: list[GateSummary]) -> dict[str, list[str]]:
    """
    Aggregate evidence/waiver/approval status across gates.

    Returns dict with keys: evidence_required, waivers_present, approvals_present
    """
    evidence_required = []
    waivers_present = []
    approvals_present = []

    for summary in summaries:
        evidence_required.append(f"{summary.gate_id}: {summary.required_evidence}")
        if summary.waiver_approval_status == "waiver_present":
            waivers_present.append(summary.gate_id)
        elif summary.waiver_approval_status == "approval_present":
            approvals_present.append(summary.gate_id)

    return {
        "evidence_required": evidence_required,
        "waivers_present": waivers_present,
        "approvals_present": approvals_present,
    }


@dataclass
class AggregateGateSummary:
    """Aggregate summary of multiple gate results for route decisions."""
    gate_count: int
    highest_severity: str
    aggregate_action: str
    blocked_gates: list[str]
    demoted_gates: list[str]
    allowed_gates: list[str]
    evidence_required: list[str]
    waivers_present: list[str]
    approvals_present: list[str]
    gate_details: list[GateSummary]


def summarize_aggregate_route_gates(summaries: list[GateSummary]) -> AggregateGateSummary:
    """
    Produce an aggregate summary of multiple gate results.

    Pure, deterministic function for route-level decision display.
    Combines individual gate results to show:
    - Highest severity across all gates
    - Aggregate downstream action (blocked > demoted > allowed)
    - Which gates block/demote/allow
    - Evidence/waiver/approval requirements across all gates
    """
    if not summaries:
        return AggregateGateSummary(
            gate_count=0,
            highest_severity="info",
            aggregate_action="route_allowed",
            blocked_gates=[],
            demoted_gates=[],
            allowed_gates=[],
            evidence_required=[],
            waivers_present=[],
            approvals_present=[],
            gate_details=[],
        )

    # Determine highest severity
    severities = [s.severity for s in summaries]
    highest_sev = _highest_severity(severities)

    # Determine aggregate action
    agg_action = _aggregate_downstream_action(summaries)

    # Categorize gates by decision
    blocked = [s.gate_id for s in summaries if "blocked" in s.downstream_action]
    demoted = [s.gate_id for s in summaries if "demoted" in s.downstream_action]
    allowed = [s.gate_id for s in summaries if "allowed" in s.downstream_action]

    # Aggregate evidence/waiver/approval status
    evidence_status = _aggregate_evidence_status(summaries)

    return AggregateGateSummary(
        gate_count=len(summaries),
        highest_severity=highest_sev,
        aggregate_action=agg_action,
        blocked_gates=blocked,
        demoted_gates=demoted,
        allowed_gates=allowed,
        evidence_required=evidence_status["evidence_required"],
        waivers_present=evidence_status["waivers_present"],
        approvals_present=evidence_status["approvals_present"],
        gate_details=summaries,
    )


def format_aggregate_summary_for_display(aggregate: AggregateGateSummary) -> str:
    """Format an AggregateGateSummary for human-readable display."""
    lines = [
        f"Route-Gate Aggregate Summary ({aggregate.gate_count} gates)",
        f"  highest severity: {aggregate.highest_severity}",
        f"  aggregate action: {aggregate.aggregate_action}",
    ]

    if aggregate.blocked_gates:
        lines.append(f"  blocked gates: {', '.join(aggregate.blocked_gates)}")
    if aggregate.demoted_gates:
        lines.append(f"  demoted gates: {', '.join(aggregate.demoted_gates)}")
    if aggregate.allowed_gates:
        lines.append(f"  allowed gates: {', '.join(aggregate.allowed_gates)}")

    if aggregate.evidence_required:
        lines.append("  evidence required:")
        for ev in aggregate.evidence_required:
            lines.append(f"    - {ev}")

    if aggregate.waivers_present:
        lines.append(f"  waivers present: {', '.join(aggregate.waivers_present)}")
    if aggregate.approvals_present:
        lines.append(f"  approvals present: {', '.join(aggregate.approvals_present)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# PromptPacket Proof Policy Evaluator
# ---------------------------------------------------------------------------


class PromptPacketProofDecision(Enum):
    """Route-level outcome for PromptPacket proof metadata evaluation."""
    ALLOW = "allow"
    WARN = "warn"
    DEMOTE = "demote"
    BLOCK = "block"
    HUMAN_GATE = "human_gate"


class ProviderResultValidationDecision(Enum):
    """Aegis advisory outcome for post-transport provider-result metadata."""
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


class PromptPayloadMeterDecision(Enum):
    """Aegis advisory outcome for visible prompt payload meter metadata."""
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


@dataclass(frozen=True)
class PromptPacketProofMetadata:
    """Display-safe PromptPacket proof metadata evaluated by Aegis."""
    packet_id: str | None
    packet_hash_status: str
    prompt_tokens: int
    max_context_tokens: int
    source_lineage: dict[str, int]
    allowed_sources: tuple[str, ...]
    aegis_evidence_ids: tuple[str, ...]
    risk_tier: int
    proof_requirement: str = "none"
    packet_hash: str | None = None
    budget_ref: str | None = None
    selected_model_id: str | None = None
    model_trust_state: str = "trusted"
    snapshot_requirement: str = "not_required"
    snapshot_status: str = "not_required"
    human_gate_required: bool = False
    human_approval_present: bool = False
    dual_lane_required: bool = False
    dual_lane_proof_present: bool = False
    demotion_target_tier: int | None = None


@dataclass(frozen=True)
class PromptPacketProofPolicyResult:
    """Deterministic Aegis decision for PromptPacket proof metadata."""
    decision: PromptPacketProofDecision
    severity: str
    reason: str
    evidence_ids: tuple[str, ...]
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    demote_to_tier: int | None = None

    def to_display_dict(self) -> dict[str, object]:
        """Return a display-safe serialization for Relay/Bifrost consumers."""
        return serialize_prompt_packet_policy_result(self)


@dataclass(frozen=True)
class ProviderResultValidationInput:
    """Display-safe post-transport validation summary evaluated by Aegis."""
    validation_status: str
    warning_tags: tuple[str, ...]
    blocker_tags: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    telemetry_available: bool
    external_review_state: str = "not_required"


@dataclass(frozen=True)
class ProviderResultValidationPolicyResult:
    """Deterministic Aegis advisory for provider-result validation metadata."""
    decision: ProviderResultValidationDecision
    severity: str
    reason: str
    validation_status: str
    external_review_state: str
    telemetry_available: bool
    evidence_refs: tuple[str, ...]
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_advisory_dict(self) -> dict[str, object]:
        """Return display-safe advisory metadata for future Relay/Bifrost use."""
        return serialize_provider_result_validation_policy_result(self)


@dataclass(frozen=True)
class PromptPayloadMeterInput:
    """Display-safe prompt payload meter summary evaluated by Aegis."""
    label_bucket: str
    budget_percent: float | None
    growth_delta_tokens: int | None
    payload_status: str
    q_mode_prompt_drag_state: str
    route_continuity_refs: tuple[str, ...]
    blocker_tags: tuple[str, ...]
    warning_tags: tuple[str, ...]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class PromptPayloadMeterPolicyResult:
    """Deterministic Aegis advisory for visible prompt payload meter metadata."""
    decision: PromptPayloadMeterDecision
    severity: str
    reason: str
    label_bucket: str
    budget_percent: float | None
    growth_delta_tokens: int | None
    payload_status: str
    q_mode_prompt_drag_state: str
    route_continuity_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_advisory_dict(self) -> dict[str, object]:
        """Return display-safe advisory metadata for future Relay/Bifrost use."""
        return serialize_prompt_payload_meter_policy_result(self)


_PROMPT_PACKET_HASH_STATUSES = {
    "present",
    "not_required",
    "unavailable",
    "missing",
    "mismatch",
}
_PROMPT_PACKET_SNAPSHOT_STATUSES = {
    "present",
    "not_required",
    "unavailable",
    "missing",
    "stale",
}
_PROMPT_PACKET_PROOF_REQUIREMENTS = {
    "none",
    "artifact",
    "telemetry",
    "code_review",
    "security_review",
    "dual_review",
    "human_gate",
}
_DIRECT_SNAPSHOT_REQUIREMENTS = {"direct_provider", "exact_model", "required"}
_PROMPT_PACKET_UNSAFE_EVIDENCE_PATTERNS = (
    "prompt:",
    "raw_prompt",
    "api_key",
    "secret",
    "credential",
    "token=",
)
_PROMPT_PACKET_UNSAFE_DISPLAY_PATTERNS = _PROMPT_PACKET_UNSAFE_EVIDENCE_PATTERNS + (
    "bearer ",
    "oauth",
    "cookie",
    "authorization",
    "provider_request",
    "provider_response",
    "process_id",
    "pid=",
    "pid:",
)
_PROMPT_PACKET_REDACTED = "[redacted]"

_PROVIDER_RESULT_VALIDATION_STATUSES = {
    "valid",
    "warning",
    "blocked",
    "invalid",
    "unavailable",
    "transport_error",
}
_PROVIDER_RESULT_EXTERNAL_REVIEW_STATES = {
    "not_required",
    "passed",
    "pending",
    "failed",
    "expired",
    "required",
    "unknown",
}
_PROVIDER_RESULT_EXTERNAL_REVIEW_BLOCKING_STATES = {
    "pending",
    "failed",
    "expired",
    "required",
    "unknown",
}
_PROVIDER_RESULT_UNSAFE_DISPLAY_PATTERNS = _PROMPT_PACKET_UNSAFE_DISPLAY_PATTERNS + (
    "raw_response",
    "raw response",
    "raw_output",
    "raw output",
    "raw_model",
    "model_output:",
    "provider_body",
    "http_header",
    "account_id",
    "billing",
    "quota",
)
_PROMPT_PAYLOAD_METER_LABEL_BUCKETS = {
    "0",
    "under-1k",
    "n.nk",
    "unknown",
    "over_budget",
}
_PROMPT_PAYLOAD_METER_STATUSES = {
    "ok",
    "watch",
    "over_budget",
    "unknown",
    "blocked",
    "missing",
    "unavailable",
}
_PROMPT_PAYLOAD_METER_BLOCKING_STATUSES = {
    "over_budget",
    "unknown",
    "blocked",
    "missing",
    "unavailable",
}
_PROMPT_PAYLOAD_Q_MODE_STATES = {
    "not_applicable",
    "flat",
    "bounded",
    "growing_expected",
    "growing_unexpected",
    "degraded",
    "blocked",
    "unknown",
}
_PROMPT_PAYLOAD_Q_MODE_BLOCKING_STATES = {
    "growing_unexpected",
    "degraded",
    "blocked",
    "unknown",
}


def _prompt_packet_severity(decision: PromptPacketProofDecision) -> str:
    if decision is PromptPacketProofDecision.BLOCK:
        return "error"
    if decision in {
        PromptPacketProofDecision.WARN,
        PromptPacketProofDecision.DEMOTE,
        PromptPacketProofDecision.HUMAN_GATE,
    }:
        return "warning"
    return "info"


def _provider_result_severity(decision: ProviderResultValidationDecision) -> str:
    if decision is ProviderResultValidationDecision.BLOCK:
        return "error"
    if decision is ProviderResultValidationDecision.WARN:
        return "warning"
    return "info"


def _prompt_payload_meter_severity(decision: PromptPayloadMeterDecision) -> str:
    if decision is PromptPayloadMeterDecision.BLOCK:
        return "error"
    if decision is PromptPayloadMeterDecision.WARN:
        return "warning"
    return "info"


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _has_prompt_packet_evidence(metadata: PromptPacketProofMetadata) -> bool:
    if not metadata.aegis_evidence_ids:
        return False
    return all(
        isinstance(evidence_id, str) and evidence_id.strip()
        for evidence_id in metadata.aegis_evidence_ids
    )


def _has_unsafe_prompt_packet_evidence(metadata: PromptPacketProofMetadata) -> bool:
    for evidence_id in metadata.aegis_evidence_ids:
        lowered = evidence_id.lower()
        if any(pattern in lowered for pattern in _PROMPT_PACKET_UNSAFE_EVIDENCE_PATTERNS):
            return True
    return False


def _is_prompt_packet_display_safe(value: str) -> bool:
    lowered = value.lower()
    return not any(pattern in lowered for pattern in _PROMPT_PACKET_UNSAFE_DISPLAY_PATTERNS)


def _display_safe_prompt_packet_value(value: object) -> str:
    text = str(value)
    if not _is_prompt_packet_display_safe(text):
        return _PROMPT_PACKET_REDACTED
    return text


def _display_safe_prompt_packet_tuple(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(_display_safe_prompt_packet_value(value) for value in values)


def _is_provider_result_display_safe(value: str) -> bool:
    lowered = value.lower()
    return not any(pattern in lowered for pattern in _PROVIDER_RESULT_UNSAFE_DISPLAY_PATTERNS)


def _display_safe_provider_result_value(value: object) -> str:
    text = str(value)
    if not _is_provider_result_display_safe(text):
        return _PROMPT_PACKET_REDACTED
    return text


def _display_safe_provider_result_tuple(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(_display_safe_provider_result_value(value) for value in values)


def _display_safe_prompt_payload_meter_value(value: object) -> str:
    return _display_safe_provider_result_value(value)


def _display_safe_prompt_payload_meter_tuple(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(_display_safe_prompt_payload_meter_value(value) for value in values)


def _prompt_packet_missing_field_from_tag(tag: str) -> str | None:
    if tag.startswith("missing_"):
        return tag.removeprefix("missing_")
    if tag == "packet_hash_missing":
        return "packet_hash"
    if tag == "snapshot_missing":
        return "snapshot"
    return None


def _prompt_packet_missing_fields(result: PromptPacketProofPolicyResult) -> tuple[str, ...]:
    fields: list[str] = []
    for tag in result.blockers:
        field = _prompt_packet_missing_field_from_tag(tag)
        if field is not None:
            _append_unique(fields, _display_safe_prompt_packet_value(field))
    return tuple(fields)


def _prompt_packet_reason_tags(result: PromptPacketProofPolicyResult) -> tuple[str, ...]:
    tags: list[str] = []
    for tag in result.blockers:
        _append_unique(tags, _display_safe_prompt_packet_value(tag))
    for tag in result.warnings:
        _append_unique(tags, _display_safe_prompt_packet_value(tag))
    if tags:
        return tuple(tags)
    if result.decision is PromptPacketProofDecision.ALLOW:
        return ("policy_allowed",)
    if result.decision is PromptPacketProofDecision.HUMAN_GATE:
        return ("human_gate_required",)
    if result.decision is PromptPacketProofDecision.DEMOTE:
        return ("policy_demote",)
    if result.decision is PromptPacketProofDecision.WARN:
        return ("policy_warn",)
    return ("policy_block",)


def _provider_result_reason_tags(
    result: ProviderResultValidationPolicyResult,
) -> tuple[str, ...]:
    tags: list[str] = []
    for tag in result.blockers:
        _append_unique(tags, _display_safe_provider_result_value(tag))
    for tag in result.warnings:
        _append_unique(tags, _display_safe_provider_result_value(tag))
    if tags:
        return tuple(tags)
    if result.decision is ProviderResultValidationDecision.ALLOW:
        return ("provider_result_allowed",)
    if result.decision is ProviderResultValidationDecision.WARN:
        return ("provider_result_warn",)
    return ("provider_result_block",)


def _prompt_payload_meter_reason_tags(
    result: PromptPayloadMeterPolicyResult,
) -> tuple[str, ...]:
    tags: list[str] = []
    for tag in result.blockers:
        _append_unique(tags, _display_safe_prompt_payload_meter_value(tag))
    for tag in result.warnings:
        _append_unique(tags, _display_safe_prompt_payload_meter_value(tag))
    if tags:
        return tuple(tags)
    if result.decision is PromptPayloadMeterDecision.ALLOW:
        return ("prompt_payload_meter_allowed",)
    if result.decision is PromptPayloadMeterDecision.WARN:
        return ("prompt_payload_meter_warn",)
    return ("prompt_payload_meter_block",)


def serialize_prompt_packet_policy_result(
    result: PromptPacketProofPolicyResult,
) -> dict[str, object]:
    """
    Serialize Aegis PromptPacket policy results for Relay/Bifrost display.

    The output is deterministic, plain-data, and display-safe. It does not
    include raw prompt text, credentials, provider request/response bodies,
    process ids, or live-control data.
    """
    return {
        "decision": result.decision.value,
        "severity": _display_safe_prompt_packet_value(result.severity),
        "reason": _display_safe_prompt_packet_value(result.reason),
        "evidence_ids": _display_safe_prompt_packet_tuple(result.evidence_ids),
        "blockers": _display_safe_prompt_packet_tuple(result.blockers),
        "warnings": _display_safe_prompt_packet_tuple(result.warnings),
        "missing_fields": _prompt_packet_missing_fields(result),
        "reason_tags": _prompt_packet_reason_tags(result),
        "demote_to_tier": result.demote_to_tier,
    }


def serialize_provider_result_validation_policy_result(
    result: ProviderResultValidationPolicyResult,
) -> dict[str, object]:
    """
    Serialize provider-result validation policy metadata for Relay/Bifrost.

    The result is primitive, deterministic, and display-safe. It contains only
    summarized validation state, advisory tags, telemetry availability, and
    evidence refs; it never includes raw prompts, provider responses,
    credentials, provider accounts, transport payloads, or live-call data.
    """
    return {
        "decision": result.decision.value,
        "severity": _display_safe_provider_result_value(result.severity),
        "reason": _display_safe_provider_result_value(result.reason),
        "validation_status": _display_safe_provider_result_value(result.validation_status),
        "external_review_state": _display_safe_provider_result_value(
            result.external_review_state
        ),
        "telemetry_available": result.telemetry_available,
        "evidence_refs": _display_safe_provider_result_tuple(result.evidence_refs),
        "blockers": _display_safe_provider_result_tuple(result.blockers),
        "warnings": _display_safe_provider_result_tuple(result.warnings),
        "reason_tags": _provider_result_reason_tags(result),
        "relay_advisory": result.decision.value,
        "bifrost_advisory": _provider_result_bifrost_advisory(result),
    }


def serialize_prompt_payload_meter_policy_result(
    result: PromptPayloadMeterPolicyResult,
) -> dict[str, object]:
    """
    Serialize visible prompt payload meter advisory metadata.

    The result is primitive, deterministic, and display-safe. It contains only
    summarized meter labels/statuses, budget/growth numbers, route continuity
    refs, evidence refs, and advisory tags; it never includes raw prompts,
    provider responses, credentials, account data, process/session control, or
    Relay/Bifrost runtime objects.
    """
    return {
        "decision": result.decision.value,
        "severity": _display_safe_prompt_payload_meter_value(result.severity),
        "reason": _display_safe_prompt_payload_meter_value(result.reason),
        "label_bucket": _display_safe_prompt_payload_meter_value(result.label_bucket),
        "budget_percent": result.budget_percent,
        "growth_delta_tokens": result.growth_delta_tokens,
        "payload_status": _display_safe_prompt_payload_meter_value(result.payload_status),
        "q_mode_prompt_drag_state": _display_safe_prompt_payload_meter_value(
            result.q_mode_prompt_drag_state
        ),
        "route_continuity_refs": _display_safe_prompt_payload_meter_tuple(
            result.route_continuity_refs
        ),
        "evidence_refs": _display_safe_prompt_payload_meter_tuple(result.evidence_refs),
        "blockers": _display_safe_prompt_payload_meter_tuple(result.blockers),
        "warnings": _display_safe_prompt_payload_meter_tuple(result.warnings),
        "reason_tags": _prompt_payload_meter_reason_tags(result),
        "relay_advisory": result.decision.value,
        "bifrost_advisory": _prompt_payload_meter_bifrost_advisory(result),
    }


def _prompt_payload_meter_bifrost_advisory(
    result: PromptPayloadMeterPolicyResult,
) -> str:
    if result.decision is PromptPayloadMeterDecision.BLOCK:
        return "display_blocked"
    if result.decision is PromptPayloadMeterDecision.WARN:
        return "display_warning"
    return "display_allowed"


def _provider_result_bifrost_advisory(
    result: ProviderResultValidationPolicyResult,
) -> str:
    if result.decision is ProviderResultValidationDecision.BLOCK:
        return "display_blocked"
    if result.decision is ProviderResultValidationDecision.WARN:
        return "display_warning"
    return "display_allowed"


def _prompt_packet_result(
    decision: PromptPacketProofDecision,
    reason: str,
    evidence_ids: tuple[str, ...],
    blockers: list[str],
    warnings: list[str],
    demote_to_tier: int | None = None,
) -> PromptPacketProofPolicyResult:
    return PromptPacketProofPolicyResult(
        decision=decision,
        severity=_prompt_packet_severity(decision),
        reason=reason,
        evidence_ids=evidence_ids,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        demote_to_tier=demote_to_tier,
    )


def _provider_result_policy_result(
    decision: ProviderResultValidationDecision,
    reason: str,
    metadata: ProviderResultValidationInput,
    blockers: list[str],
    warnings: list[str],
) -> ProviderResultValidationPolicyResult:
    return ProviderResultValidationPolicyResult(
        decision=decision,
        severity=_provider_result_severity(decision),
        reason=reason,
        validation_status=metadata.validation_status,
        external_review_state=metadata.external_review_state,
        telemetry_available=metadata.telemetry_available,
        evidence_refs=metadata.evidence_refs,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
    )


def _prompt_payload_meter_policy_result(
    decision: PromptPayloadMeterDecision,
    reason: str,
    metadata: PromptPayloadMeterInput,
    blockers: list[str],
    warnings: list[str],
) -> PromptPayloadMeterPolicyResult:
    return PromptPayloadMeterPolicyResult(
        decision=decision,
        severity=_prompt_payload_meter_severity(decision),
        reason=reason,
        label_bucket=metadata.label_bucket,
        budget_percent=metadata.budget_percent,
        growth_delta_tokens=metadata.growth_delta_tokens,
        payload_status=metadata.payload_status,
        q_mode_prompt_drag_state=metadata.q_mode_prompt_drag_state,
        route_continuity_refs=metadata.route_continuity_refs,
        evidence_refs=metadata.evidence_refs,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
    )


def _append_safe_ref_blockers(
    values: tuple[str, ...],
    missing_tag: str,
    invalid_tag: str,
    unsafe_tag: str,
    blockers: list[str],
) -> None:
    if not values:
        _append_unique(blockers, missing_tag)
    for value in values:
        if not isinstance(value, str) or not value.strip():
            _append_unique(blockers, invalid_tag)
        elif not _is_provider_result_display_safe(value):
            _append_unique(blockers, unsafe_tag)


def evaluate_prompt_payload_meter_advisory(
    metadata: PromptPayloadMeterInput,
) -> PromptPayloadMeterPolicyResult:
    """
    Evaluate summarized prompt payload meter metadata before display/promotion.

    Pure Aegis helper: accepts primitive, already-summarized inputs only. It
    does not import Relay/Bifrost types, call providers, inspect accounts,
    read raw prompts/responses, touch FileMap, or control processes/sessions.
    """
    blockers: list[str] = []
    warnings: list[str] = []

    if not isinstance(metadata.label_bucket, str) or not metadata.label_bucket.strip():
        _append_unique(blockers, "missing_prompt_payload_label_bucket")
    elif metadata.label_bucket not in _PROMPT_PAYLOAD_METER_LABEL_BUCKETS:
        _append_unique(blockers, "unknown_prompt_payload_label_bucket")
    elif metadata.label_bucket in {"unknown", "over_budget"}:
        _append_unique(blockers, f"prompt_payload_label_{metadata.label_bucket}")

    if not isinstance(metadata.payload_status, str) or not metadata.payload_status.strip():
        _append_unique(blockers, "missing_prompt_payload_status")
    elif metadata.payload_status not in _PROMPT_PAYLOAD_METER_STATUSES:
        _append_unique(blockers, "unknown_prompt_payload_status")
    elif metadata.payload_status in _PROMPT_PAYLOAD_METER_BLOCKING_STATUSES:
        _append_unique(blockers, f"prompt_payload_{metadata.payload_status}")

    if (
        not isinstance(metadata.q_mode_prompt_drag_state, str)
        or not metadata.q_mode_prompt_drag_state.strip()
    ):
        _append_unique(blockers, "missing_q_mode_prompt_drag_state")
    elif metadata.q_mode_prompt_drag_state not in _PROMPT_PAYLOAD_Q_MODE_STATES:
        _append_unique(blockers, "unknown_q_mode_prompt_drag_state")
    elif metadata.q_mode_prompt_drag_state in _PROMPT_PAYLOAD_Q_MODE_BLOCKING_STATES:
        _append_unique(blockers, f"q_mode_prompt_drag_{metadata.q_mode_prompt_drag_state}")

    if metadata.budget_percent is None:
        _append_unique(blockers, "missing_prompt_payload_budget_percent")
    elif metadata.budget_percent < 0:
        _append_unique(blockers, "invalid_prompt_payload_budget_percent")
    elif metadata.budget_percent > 100:
        _append_unique(blockers, "prompt_payload_budget_over_limit")
    elif metadata.budget_percent >= 90:
        _append_unique(warnings, "prompt_payload_budget_watch")

    if metadata.growth_delta_tokens is None:
        _append_unique(blockers, "missing_prompt_payload_growth_delta")
    elif metadata.growth_delta_tokens < 0:
        _append_unique(blockers, "invalid_prompt_payload_growth_delta")
    elif (
        metadata.growth_delta_tokens > 0
        and metadata.q_mode_prompt_drag_state not in {"not_applicable", "growing_expected"}
    ):
        _append_unique(blockers, "prompt_payload_growth_unexplained")

    _append_safe_ref_blockers(
        metadata.route_continuity_refs,
        "missing_route_continuity_refs",
        "invalid_route_continuity_ref",
        "unsafe_route_continuity_ref",
        blockers,
    )
    _append_safe_ref_blockers(
        metadata.evidence_refs,
        "missing_prompt_payload_meter_evidence_refs",
        "invalid_prompt_payload_meter_evidence_ref",
        "unsafe_prompt_payload_meter_evidence_ref",
        blockers,
    )

    for tag in metadata.blocker_tags:
        if not isinstance(tag, str) or not tag.strip():
            _append_unique(blockers, "invalid_prompt_payload_meter_blocker_tag")
        elif not _is_provider_result_display_safe(tag):
            _append_unique(blockers, "unsafe_prompt_payload_meter_blocker_tag")
        else:
            _append_unique(blockers, tag)

    for tag in metadata.warning_tags:
        if not isinstance(tag, str) or not tag.strip():
            _append_unique(warnings, "invalid_prompt_payload_meter_warning_tag")
        elif not _is_provider_result_display_safe(tag):
            _append_unique(warnings, "unsafe_prompt_payload_meter_warning_tag")
        else:
            _append_unique(warnings, tag)

    if blockers:
        return _prompt_payload_meter_policy_result(
            PromptPayloadMeterDecision.BLOCK,
            "; ".join(blockers),
            metadata,
            blockers,
            warnings,
        )
    if warnings:
        return _prompt_payload_meter_policy_result(
            PromptPayloadMeterDecision.WARN,
            "; ".join(warnings),
            metadata,
            blockers,
            warnings,
        )
    return _prompt_payload_meter_policy_result(
        PromptPayloadMeterDecision.ALLOW,
        "prompt payload meter metadata satisfies Aegis advisory policy",
        metadata,
        blockers,
        warnings,
    )


def evaluate_provider_result_validation_advisory(
    metadata: ProviderResultValidationInput,
) -> ProviderResultValidationPolicyResult:
    """
    Evaluate summarized provider-result validation metadata after transport.

    Pure Aegis helper: accepts primitive, already-summarized inputs only. It
    does not import Relay types, inspect accounts, call providers, read raw
    prompts/responses, mutate runtime state, or render Bifrost UI.
    """
    blockers: list[str] = []
    warnings: list[str] = []

    if not isinstance(metadata.validation_status, str) or not metadata.validation_status.strip():
        _append_unique(blockers, "missing_validation_status")
    elif metadata.validation_status not in _PROVIDER_RESULT_VALIDATION_STATUSES:
        _append_unique(blockers, "unknown_validation_status")
    elif metadata.validation_status in {"blocked", "invalid", "unavailable", "transport_error"}:
        _append_unique(blockers, f"provider_result_{metadata.validation_status}")

    if not isinstance(metadata.external_review_state, str) or not metadata.external_review_state.strip():
        _append_unique(blockers, "missing_external_review_state")
    elif metadata.external_review_state not in _PROVIDER_RESULT_EXTERNAL_REVIEW_STATES:
        _append_unique(blockers, "unknown_external_review_state")
    elif metadata.external_review_state in _PROVIDER_RESULT_EXTERNAL_REVIEW_BLOCKING_STATES:
        _append_unique(blockers, f"external_review_{metadata.external_review_state}")

    if not metadata.evidence_refs:
        _append_unique(blockers, "missing_provider_result_evidence_refs")
    for evidence_ref in metadata.evidence_refs:
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            _append_unique(blockers, "invalid_provider_result_evidence_ref")
        elif not _is_provider_result_display_safe(evidence_ref):
            _append_unique(blockers, "unsafe_provider_result_evidence_ref")

    for tag in metadata.blocker_tags:
        if not isinstance(tag, str) or not tag.strip():
            _append_unique(blockers, "invalid_provider_result_blocker_tag")
        elif not _is_provider_result_display_safe(tag):
            _append_unique(blockers, "unsafe_provider_result_blocker_tag")
        else:
            _append_unique(blockers, tag)

    for tag in metadata.warning_tags:
        if not isinstance(tag, str) or not tag.strip():
            _append_unique(warnings, "invalid_provider_result_warning_tag")
        elif not _is_provider_result_display_safe(tag):
            _append_unique(warnings, "unsafe_provider_result_warning_tag")
        else:
            _append_unique(warnings, tag)

    if metadata.validation_status == "warning" and not metadata.warning_tags:
        _append_unique(warnings, "provider_result_validation_warning")
    if not metadata.telemetry_available:
        _append_unique(warnings, "provider_result_telemetry_unavailable")

    if blockers:
        return _provider_result_policy_result(
            ProviderResultValidationDecision.BLOCK,
            "; ".join(blockers),
            metadata,
            blockers,
            warnings,
        )
    if warnings:
        return _provider_result_policy_result(
            ProviderResultValidationDecision.WARN,
            "; ".join(warnings),
            metadata,
            blockers,
            warnings,
        )
    return _provider_result_policy_result(
        ProviderResultValidationDecision.ALLOW,
        "provider result validation metadata satisfies Aegis advisory policy",
        metadata,
        blockers,
        warnings,
    )


def evaluate_prompt_packet_proof_policy(
    metadata: PromptPacketProofMetadata,
) -> PromptPacketProofPolicyResult:
    """
    Evaluate PromptPacket proof metadata before Relay dispatch.

    Pure, deterministic Aegis helper: no Relay mutation, no model calls, no
    account inspection, no Bifrost rendering, and no persistence side effects.
    """
    blockers: list[str] = []
    warnings: list[str] = []
    evidence_ids = metadata.aegis_evidence_ids

    if not isinstance(metadata.packet_id, str) or not metadata.packet_id.strip():
        _append_unique(blockers, "missing_packet_id")

    if metadata.packet_hash_status not in _PROMPT_PACKET_HASH_STATUSES:
        _append_unique(blockers, "unknown_packet_hash_status")
    elif metadata.packet_hash_status in {"missing", "mismatch"}:
        _append_unique(blockers, f"packet_hash_{metadata.packet_hash_status}")
    elif metadata.packet_hash_status == "present" and not (
        isinstance(metadata.packet_hash, str) and metadata.packet_hash.strip()
    ):
        _append_unique(blockers, "packet_hash_value_missing")

    if metadata.prompt_tokens < 0:
        _append_unique(blockers, "negative_prompt_tokens")
    if metadata.max_context_tokens <= 0:
        _append_unique(blockers, "invalid_budget_limit")
    if metadata.max_context_tokens > 0 and metadata.prompt_tokens > metadata.max_context_tokens:
        _append_unique(blockers, "prompt_packet_over_budget")
    if not isinstance(metadata.budget_ref, str) or not metadata.budget_ref.strip():
        _append_unique(blockers, "missing_budget_ref")

    if not metadata.allowed_sources:
        _append_unique(blockers, "missing_allowed_sources")
    if not metadata.source_lineage:
        _append_unique(blockers, "missing_source_lineage")

    allowed_sources = set(metadata.allowed_sources)
    lineage_total = 0
    for source, token_count in metadata.source_lineage.items():
        if not isinstance(source, str) or not source.strip():
            _append_unique(blockers, "invalid_source_lineage_key")
        elif source not in allowed_sources:
            _append_unique(blockers, f"disallowed_source:{source}")
        if not isinstance(token_count, int) or token_count < 0:
            _append_unique(blockers, f"invalid_source_lineage:{source}")
        elif token_count >= 0:
            lineage_total += token_count
    if lineage_total > metadata.prompt_tokens:
        _append_unique(blockers, "source_lineage_exceeds_prompt_tokens")

    if not _has_prompt_packet_evidence(metadata):
        _append_unique(blockers, "missing_aegis_evidence_ids")
    if len(set(evidence_ids)) != len(evidence_ids):
        _append_unique(blockers, "duplicate_aegis_evidence_ids")
    if _has_unsafe_prompt_packet_evidence(metadata):
        _append_unique(blockers, "unsafe_aegis_evidence_id")

    if not isinstance(metadata.proof_requirement, str) or not metadata.proof_requirement.strip():
        _append_unique(blockers, "missing_proof_requirement")
    elif metadata.proof_requirement not in _PROMPT_PACKET_PROOF_REQUIREMENTS:
        _append_unique(blockers, "unknown_proof_requirement")
    if metadata.proof_requirement == "human_gate" and not metadata.human_gate_required:
        _append_unique(blockers, "human_gate_requirement_conflict")
    if metadata.human_approval_present and not metadata.human_gate_required:
        _append_unique(blockers, "human_approval_without_gate")
    if metadata.proof_requirement == "dual_review" and not metadata.dual_lane_required:
        _append_unique(blockers, "dual_lane_requirement_conflict")
    if metadata.dual_lane_proof_present and not metadata.dual_lane_required:
        _append_unique(blockers, "dual_lane_proof_without_requirement")

    if metadata.snapshot_status not in _PROMPT_PACKET_SNAPSHOT_STATUSES:
        _append_unique(blockers, "unknown_snapshot_status")
    elif (
        metadata.snapshot_requirement in _DIRECT_SNAPSHOT_REQUIREMENTS
        and metadata.snapshot_status in {"missing", "stale", "unavailable"}
    ):
        _append_unique(blockers, f"snapshot_{metadata.snapshot_status}")
    elif metadata.snapshot_status == "unavailable" and metadata.risk_tier >= 2:
        _append_unique(blockers, "snapshot_unavailable_for_tier")
    elif metadata.snapshot_status == "unavailable":
        _append_unique(warnings, "snapshot_unavailable")

    if metadata.packet_hash_status == "unavailable":
        if (
            metadata.risk_tier >= 3
            or metadata.human_gate_required
            or metadata.dual_lane_required
            or metadata.snapshot_requirement in _DIRECT_SNAPSHOT_REQUIREMENTS
        ):
            _append_unique(blockers, "packet_hash_required_unavailable")
        elif metadata.risk_tier == 2:
            _append_unique(warnings, "packet_hash_unavailable_demote")
        else:
            _append_unique(warnings, "packet_hash_unavailable")

    if metadata.model_trust_state == "candidate" and metadata.risk_tier >= 3:
        _append_unique(blockers, "candidate_model_trust_for_high_tier")

    if metadata.dual_lane_required and not metadata.dual_lane_proof_present:
        _append_unique(blockers, "dual_lane_proof_missing")

    if blockers:
        return _prompt_packet_result(
            PromptPacketProofDecision.BLOCK,
            "; ".join(blockers),
            evidence_ids,
            blockers,
            warnings,
        )

    if metadata.human_gate_required and not metadata.human_approval_present:
        return _prompt_packet_result(
            PromptPacketProofDecision.HUMAN_GATE,
            "human approval required before dispatch",
            evidence_ids,
            blockers,
            warnings,
        )

    if "packet_hash_unavailable_demote" in warnings:
        demote_to_tier = metadata.demotion_target_tier
        if demote_to_tier is None:
            _append_unique(blockers, "missing_demotion_target")
        elif demote_to_tier < 0 or demote_to_tier >= metadata.risk_tier:
            _append_unique(blockers, "invalid_demotion_target")
        if blockers:
            return _prompt_packet_result(
                PromptPacketProofDecision.BLOCK,
                "; ".join(blockers),
                evidence_ids,
                blockers,
                warnings,
            )
        return _prompt_packet_result(
            PromptPacketProofDecision.DEMOTE,
            "packet hash unavailable; demoting to lower proof tier",
            evidence_ids,
            blockers,
            warnings,
            demote_to_tier=demote_to_tier,
        )

    if warnings:
        return _prompt_packet_result(
            PromptPacketProofDecision.WARN,
            "; ".join(warnings),
            evidence_ids,
            blockers,
            warnings,
        )

    return _prompt_packet_result(
        PromptPacketProofDecision.ALLOW,
        "PromptPacket proof metadata satisfies Aegis policy",
        evidence_ids,
        blockers,
        warnings,
    )
