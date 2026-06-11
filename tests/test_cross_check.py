"""Tests for backend cross-check authority."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from meridian_core.cross_check import (
    CrossCheckDisposition,
    CrossCheckDispositionAction,
    CrossCheckFinding,
    CrossCheckFindingStatus,
    CrossCheckRepairRoute,
    CrossCheckRunRequest,
    CrossCheckRunStatus,
    CrossCheckSeverity,
    CrossCheckValidationError,
    CrossCheckVerificationRequest,
    CrossCheckVerificationResult,
    dispose_finding,
    execute_cross_check,
    rerun_verification,
    route_finding_for_repair,
)
from meridian_core.review_console import ReviewConsoleItemType


NOW = datetime(2026, 6, 10, 9, 0, tzinfo=timezone.utc)


def make_request() -> CrossCheckRunRequest:
    return CrossCheckRunRequest(
        run_id="xck-run-1",
        objective="Verify review and proof posture for backend authority.",
        scope_refs=("xck://slice/backend-authority",),
        requested_by="prime",
        requested_at=NOW,
        evidence_refs=("proof://xck/request",),
    )


def make_finding(
    finding_id: str = "xck-find-1",
    severity: CrossCheckSeverity = CrossCheckSeverity.ERROR,
) -> CrossCheckFinding:
    return CrossCheckFinding(
        finding_id=finding_id,
        source="codex-review-a",
        target_ref="xck://candidate/backend-authority",
        summary="Finding needs a repair route before V2 promotion.",
        severity=severity,
        evidence_refs=("review://finding/xck-find-1",),
    )


def test_execute_cross_check_runs_injected_runner_and_records_findings():
    seen = []

    def runner(request):
        seen.append(request.run_id)
        return (make_finding(),)

    result = execute_cross_check(
        make_request(),
        runner,
        executed_by="aegis",
        executed_at=NOW + timedelta(minutes=1),
    )

    assert seen == ["xck-run-1"]
    assert result.status is CrossCheckRunStatus.FINDINGS_OPEN
    assert result.findings[0].finding_id == "xck-find-1"
    assert result.evidence_refs == ("proof://xck/request",)


def test_execute_cross_check_passes_when_runner_returns_no_blocking_findings():
    result = execute_cross_check(
        make_request(),
        lambda request: (make_finding(severity=CrossCheckSeverity.INFO),),
        executed_by="aegis",
        executed_at=NOW + timedelta(minutes=1),
    )

    assert result.status is CrossCheckRunStatus.PASSED
    assert result.findings[0].is_blocking() is False


def test_execute_cross_check_requires_callable_runner():
    with pytest.raises(CrossCheckValidationError, match="runner"):
        execute_cross_check(
            make_request(),
            None,
            executed_by="aegis",
            executed_at=NOW,
        )


def test_execute_cross_check_rejects_non_finding_runner_output():
    with pytest.raises(CrossCheckValidationError, match="CrossCheckFinding"):
        execute_cross_check(
            make_request(),
            lambda request: ("not-a-finding",),
            executed_by="aegis",
            executed_at=NOW,
        )


@pytest.mark.parametrize(
    "finding",
    (
        CrossCheckFinding(
            finding_id="xck-pre-waived",
            source="codex-review-a",
            target_ref="xck://candidate/backend-authority",
            summary="Runner must not pre-close this finding.",
            severity=CrossCheckSeverity.ERROR,
            status=CrossCheckFindingStatus.WAIVED,
            disposition_id="xck-disp-preclosed",
        ),
        CrossCheckFinding(
            finding_id="xck-pre-verified",
            source="codex-review-a",
            target_ref="xck://candidate/backend-authority",
            summary="Runner must not pre-verify this finding.",
            severity=CrossCheckSeverity.ERROR,
            status=CrossCheckFindingStatus.VERIFIED,
            verification_id="xck-verify-preclosed",
        ),
    ),
)
def test_execute_cross_check_rejects_preclosed_runner_findings(finding):
    with pytest.raises(CrossCheckValidationError, match="runner findings"):
        execute_cross_check(
            make_request(),
            lambda request: (finding,),
            executed_by="aegis",
            executed_at=NOW,
        )


def test_execute_cross_check_rejects_runner_findings_with_authority_ids():
    finding = CrossCheckFinding(
        finding_id="xck-pre-routed",
        source="codex-review-a",
        target_ref="xck://candidate/backend-authority",
        summary="Runner must not attach authority ids.",
        severity=CrossCheckSeverity.ERROR,
        repair_route_id="xck-route-preexisting",
    )

    with pytest.raises(CrossCheckValidationError, match="authority ids"):
        execute_cross_check(
            make_request(),
            lambda request: (finding,),
            executed_by="aegis",
            executed_at=NOW,
        )


def test_finding_converts_to_aegis_evidence_and_review_console_item():
    finding = make_finding(severity=CrossCheckSeverity.CRITICAL)
    evidence = finding.to_aegis_evidence()
    item = finding.to_review_console_item()

    assert evidence.is_proof_blocking() is True
    assert item.item_type is ReviewConsoleItemType.APPROVAL_GATE
    assert item.requires_response is True


def test_route_finding_for_repair_records_owner_and_status():
    routed, route = route_finding_for_repair(
        make_finding(),
        route_id="xck-route-1",
        owner="backend",
        reason="Repair backend invariant before promotion.",
        routed_by="prime",
        routed_at=NOW + timedelta(minutes=2),
        evidence_refs=("task://xck/repair",),
    )

    assert isinstance(route, CrossCheckRepairRoute)
    assert routed.status is CrossCheckFindingStatus.ROUTED_FOR_REPAIR
    assert routed.repair_route_id == "xck-route-1"
    assert routed.evidence_refs[-1] == "task://xck/repair"


def test_route_finding_for_repair_requires_open_finding():
    approved = dispose_finding(
        make_finding(),
        CrossCheckDisposition(
            disposition_id="xck-disp-1",
            finding_id="xck-find-1",
            action=CrossCheckDispositionAction.APPROVE,
            actor="prime",
            reason="Reviewed and accepted.",
            scope="candidate",
            timestamp=NOW,
            evidence_refs=("proof://xck/approve",),
        ),
    )

    with pytest.raises(CrossCheckValidationError, match="open"):
        route_finding_for_repair(
            approved,
            route_id="xck-route-2",
            owner="backend",
            reason="cannot route closed",
            routed_by="prime",
            routed_at=NOW,
        )


@pytest.mark.parametrize(
    ("action", "expected"),
    (
        (CrossCheckDispositionAction.APPROVE, CrossCheckFindingStatus.APPROVED),
        (CrossCheckDispositionAction.DISMISS, CrossCheckFindingStatus.DISMISSED),
        (CrossCheckDispositionAction.WAIVE, CrossCheckFindingStatus.WAIVED),
    ),
)
def test_dispose_finding_records_approve_dismiss_and_waive(action, expected):
    refs = ("proof://xck/disposition",)
    disposition = CrossCheckDisposition(
        disposition_id=f"xck-disp-{action.value}",
        finding_id="xck-find-1",
        action=action,
        actor="prime",
        reason="Disposition is reviewed.",
        scope="candidate",
        timestamp=NOW,
        evidence_refs=refs,
    )

    updated = dispose_finding(make_finding(), disposition)

    assert updated.status is expected
    assert updated.disposition_id == disposition.disposition_id
    assert updated.evidence_refs[-1] == "proof://xck/disposition"


def test_waive_disposition_requires_evidence_refs():
    with pytest.raises(CrossCheckValidationError, match="requires evidence_refs"):
        CrossCheckDisposition(
            disposition_id="xck-waive-1",
            finding_id="xck-find-1",
            action=CrossCheckDispositionAction.WAIVE,
            actor="prime",
            reason="Accepted risk.",
            scope="candidate",
            timestamp=NOW,
            evidence_refs=(),
        )


def test_dispose_finding_rejects_mismatched_finding_id():
    disposition = CrossCheckDisposition(
        disposition_id="xck-disp-mismatch",
        finding_id="other",
        action=CrossCheckDispositionAction.APPROVE,
        actor="prime",
        reason="Reviewed.",
        scope="candidate",
        timestamp=NOW,
        evidence_refs=("proof://xck/approve",),
    )

    with pytest.raises(CrossCheckValidationError, match="does not match"):
        dispose_finding(make_finding(), disposition)


def test_rerun_verification_updates_status_when_verifier_passes():
    routed, _ = route_finding_for_repair(
        make_finding(),
        route_id="xck-route-1",
        owner="backend",
        reason="Repair and rerun.",
        routed_by="prime",
        routed_at=NOW,
        evidence_refs=("task://xck/repair",),
    )
    request = CrossCheckVerificationRequest(
        verification_id="xck-verify-1",
        finding_id="xck-find-1",
        repaired_evidence_refs=("proof://xck/repair-complete",),
        requested_by="prime",
        requested_at=NOW + timedelta(minutes=3),
    )

    def verifier(finding, verification_request):
        return CrossCheckVerificationResult(
            verification_id=verification_request.verification_id,
            finding_id=finding.finding_id,
            passed=True,
            verifier="aegis",
            verified_at=NOW + timedelta(minutes=4),
            evidence_refs=("proof://xck/rerun-pass",),
        )

    updated, result = rerun_verification(routed, request, verifier)

    assert result.passed is True
    assert updated.status is CrossCheckFindingStatus.VERIFIED
    assert updated.verification_id == "xck-verify-1"
    assert "proof://xck/rerun-pass" in updated.evidence_refs


def test_rerun_verification_records_followup_findings_when_failed():
    routed, _ = route_finding_for_repair(
        make_finding(),
        route_id="xck-route-1",
        owner="backend",
        reason="Repair and rerun.",
        routed_by="prime",
        routed_at=NOW,
    )
    request = CrossCheckVerificationRequest(
        verification_id="xck-verify-2",
        finding_id="xck-find-1",
        repaired_evidence_refs=("proof://xck/repair-complete",),
        requested_by="prime",
        requested_at=NOW + timedelta(minutes=3),
    )

    def verifier(finding, verification_request):
        return CrossCheckVerificationResult(
            verification_id=verification_request.verification_id,
            finding_id=finding.finding_id,
            passed=False,
            verifier="aegis",
            verified_at=NOW + timedelta(minutes=4),
            evidence_refs=("proof://xck/rerun-fail",),
            followup_findings=(make_finding("xck-followup-1"),),
        )

    updated, result = rerun_verification(routed, request, verifier)

    assert result.passed is False
    assert updated.status is CrossCheckFindingStatus.VERIFICATION_FAILED
    assert result.followup_findings[0].finding_id == "xck-followup-1"


def test_failed_verification_can_be_routed_and_verified_again():
    routed, _ = route_finding_for_repair(
        make_finding(),
        route_id="xck-route-1",
        owner="backend",
        reason="Repair and rerun.",
        routed_by="prime",
        routed_at=NOW,
    )
    failed_request = CrossCheckVerificationRequest(
        verification_id="xck-verify-failed",
        finding_id="xck-find-1",
        repaired_evidence_refs=("proof://xck/repair-first",),
        requested_by="prime",
        requested_at=NOW + timedelta(minutes=3),
    )

    failed, _ = rerun_verification(
        routed,
        failed_request,
        lambda finding, verification_request: CrossCheckVerificationResult(
            verification_id=verification_request.verification_id,
            finding_id=finding.finding_id,
            passed=False,
            verifier="aegis",
            verified_at=NOW + timedelta(minutes=4),
            evidence_refs=("proof://xck/rerun-fail",),
            followup_findings=(make_finding("xck-followup-1"),),
        ),
    )

    rerouted, route = route_finding_for_repair(
        failed,
        route_id="xck-route-2",
        owner="backend",
        reason="Repair failed verification.",
        routed_by="prime",
        routed_at=NOW + timedelta(minutes=5),
        evidence_refs=("task://xck/repair-second",),
    )
    assert rerouted.status is CrossCheckFindingStatus.ROUTED_FOR_REPAIR
    assert rerouted.repair_route_id == route.route_id
    assert rerouted.verification_id is None

    pass_request = CrossCheckVerificationRequest(
        verification_id="xck-verify-pass",
        finding_id="xck-find-1",
        repaired_evidence_refs=("proof://xck/repair-second",),
        requested_by="prime",
        requested_at=NOW + timedelta(minutes=6),
    )
    verified, _ = rerun_verification(
        rerouted,
        pass_request,
        lambda finding, verification_request: CrossCheckVerificationResult(
            verification_id=verification_request.verification_id,
            finding_id=finding.finding_id,
            passed=True,
            verifier="aegis",
            verified_at=NOW + timedelta(minutes=7),
            evidence_refs=("proof://xck/rerun-pass",),
        ),
    )

    assert verified.status is CrossCheckFindingStatus.VERIFIED
    assert verified.verification_id == "xck-verify-pass"


def test_rerun_verification_requires_repair_routed_finding():
    request = CrossCheckVerificationRequest(
        verification_id="xck-verify-3",
        finding_id="xck-find-1",
        repaired_evidence_refs=("proof://xck/repair-complete",),
        requested_by="prime",
        requested_at=NOW,
    )

    with pytest.raises(CrossCheckValidationError, match="repair-routed"):
        rerun_verification(
            make_finding(),
            request,
            lambda finding, verification_request: CrossCheckVerificationResult(
                verification_id=verification_request.verification_id,
                finding_id=finding.finding_id,
                passed=True,
                verifier="aegis",
                verified_at=NOW,
                evidence_refs=("proof://xck/rerun-pass",),
            ),
        )


def test_rerun_verification_requires_actual_repair_route_id():
    status_only_routed = CrossCheckFinding(
        finding_id="xck-find-1",
        source="codex-review-a",
        target_ref="xck://candidate/backend-authority",
        summary="Status-only routed findings must fail closed.",
        severity=CrossCheckSeverity.ERROR,
        status=CrossCheckFindingStatus.ROUTED_FOR_REPAIR,
    )
    request = CrossCheckVerificationRequest(
        verification_id="xck-verify-status-only",
        finding_id="xck-find-1",
        repaired_evidence_refs=("proof://xck/repair-complete",),
        requested_by="prime",
        requested_at=NOW,
    )

    with pytest.raises(CrossCheckValidationError, match="repair_route_id"):
        rerun_verification(
            status_only_routed,
            request,
            lambda finding, verification_request: CrossCheckVerificationResult(
                verification_id=verification_request.verification_id,
                finding_id=finding.finding_id,
                passed=True,
                verifier="aegis",
                verified_at=NOW,
                evidence_refs=("proof://xck/rerun-pass",),
            ),
        )


@pytest.mark.parametrize(
    "unsafe_value",
    (
        "raw prompt excerpt",
        "provider response body",
        "worker chat transcript",
        "token=abc123",
        r"C:\Users\scott\Meridian",
        "./runtime/queue.json",
        "../private/evidence.json",
        "docs/review.md",
    ),
)
def test_display_safety_rejects_unsafe_finding_text_and_refs(unsafe_value):
    with pytest.raises(CrossCheckValidationError):
        CrossCheckFinding(
            finding_id="xck-unsafe",
            source="codex-review-a",
            target_ref=unsafe_value,
            summary="Unsafe finding.",
            severity=CrossCheckSeverity.ERROR,
        )

    with pytest.raises(CrossCheckValidationError):
        CrossCheckFinding(
            finding_id="xck-unsafe",
            source="codex-review-a",
            target_ref="xck://candidate/backend-authority",
            summary=unsafe_value,
            severity=CrossCheckSeverity.ERROR,
        )


def test_safe_uri_refs_are_allowed():
    finding = CrossCheckFinding(
        finding_id="xck-safe",
        source="codex-review-a",
        target_ref="xck://candidate/backend-authority",
        summary="Display-safe finding.",
        severity=CrossCheckSeverity.WARNING,
        evidence_refs=(
            "proof://xck/safe",
            "review://codex/a",
            "crosscheck://run/1",
        ),
    )

    assert finding.evidence_refs == (
        "proof://xck/safe",
        "review://codex/a",
        "crosscheck://run/1",
    )


@pytest.mark.parametrize(
    "unsafe_ref",
    (
        "review://docs/backlog.md",
        "xck://../private/evidence.json",
        "crosscheck://./runtime/queue.json",
        r"proof://C:\Users\scott\Meridian",
    ),
)
def test_safe_uri_refs_reject_path_shaped_payloads(unsafe_ref):
    with pytest.raises(CrossCheckValidationError, match="local paths"):
        CrossCheckFinding(
            finding_id="xck-unsafe-ref",
            source="codex-review-a",
            target_ref=unsafe_ref,
            summary="Safe-scheme refs must not smuggle path payloads.",
            severity=CrossCheckSeverity.ERROR,
        )
