"""Tests for V2.5 display-safe review intelligence."""

from __future__ import annotations

from meridian_core.review_intelligence import (
    DuplicateFindingGroup,
    RegressionRiskLabel,
    RepairVerification,
    RepairVerificationState,
    ReviewFindingFingerprint,
    ReviewFindingInput,
    ReviewFindingSeverity,
    SeverityCalibration,
    WaiverVisibility,
    build_review_intelligence,
    fingerprint_finding,
)


def _finding(
    *,
    source_id: str = "review-a",
    artifact_id: str = "artifact:relay-repair",
    rule_id: str = "rule:proof-gap",
    severity: ReviewFindingSeverity = ReviewFindingSeverity.WARNING,
    body: str = "repair proof does not verify fixed behavior",
    log: str = "",
    repair_state: RepairVerificationState = RepairVerificationState.NOT_FIXED,
    waiver_id: str = "",
    waiver_reason: str = "",
    evidence_refs: tuple[str, ...] = (),
    components: tuple[str, ...] = (),
    blockers: tuple[str, ...] = (),
) -> ReviewFindingInput:
    return ReviewFindingInput(
        source_id=source_id,
        artifact_id=artifact_id,
        rule_id=rule_id,
        severity=severity,
        finding_body=body,
        log_excerpt=log,
        location="repair-loop",
        repair_state=repair_state,
        waiver_id=waiver_id,
        waiver_reason=waiver_reason,
        repair_evidence_refs=evidence_refs,
        changed_components=components,
        blocker_tags=blockers,
    )


def test_fingerprint_is_stable_for_same_finding_identity_and_body():
    left = fingerprint_finding(_finding())
    right = fingerprint_finding(_finding(source_id="review-a"))

    assert left.fingerprint == right.fingerprint
    assert left.to_display_dict() == right.to_display_dict()


def test_duplicate_collapse_preserves_highest_severity():
    report = build_review_intelligence(
        (
            _finding(source_id="review-a", severity=ReviewFindingSeverity.WARNING),
            _finding(source_id="review-b", severity=ReviewFindingSeverity.ERROR),
        )
    )

    assert len(report.groups) == 1
    group = report.groups[0]
    assert group.duplicate_count == 2
    assert group.severity.severity is ReviewFindingSeverity.ERROR
    assert group.to_display_dict()["severity"]["severity"] == "error"
    assert "highest observed severity is error" in group.severity.rationale
    assert "collapsed 2 duplicate observations" in group.severity.rationale


def test_repair_state_fixed_closes_group_with_evidence_refs():
    report = build_review_intelligence(
        (
            _finding(
                repair_state=RepairVerificationState.FIXED,
                evidence_refs=("proof:test-review-intelligence",),
            ),
        )
    )

    group = report.groups[0]
    assert group.repair.state is RepairVerificationState.FIXED
    assert group.repair.is_closed is True
    assert group.repair.evidence_refs == ("proof:test-review-intelligence",)
    assert report.open_count == 0


def test_repair_state_not_fixed_keeps_group_open():
    report = build_review_intelligence((_finding(repair_state=RepairVerificationState.NOT_FIXED),))

    group = report.groups[0]
    assert group.repair.state is RepairVerificationState.NOT_FIXED
    assert group.repair.is_closed is False
    assert report.open_count == 1


def test_repair_state_waived_is_visible_without_exposing_reason_body():
    report = build_review_intelligence(
        (
            _finding(
                repair_state=RepairVerificationState.WAIVED,
                waiver_id="waiver:rank5-accepted-risk",
                waiver_reason="accepted because raw log contains secret token=shhh123456",
            ),
        )
    )

    group = report.groups[0]
    display = group.to_display_dict()
    assert group.repair.state is RepairVerificationState.WAIVED
    assert group.repair.is_closed is True
    assert group.waiver.present is True
    assert display["waiver"] == {
        "present": True,
        "waiver_ref": "waiver:rank5-accepted-risk",
        "reason_visible": True,
    }
    assert "shhh123456" not in str(display)
    assert "accepted because" not in str(display)


def test_regression_risk_classifies_high_for_error_in_core_repair_loop():
    report = build_review_intelligence(
        (
            _finding(
                severity=ReviewFindingSeverity.ERROR,
                components=("core", "repair"),
            ),
        )
    )

    assert report.groups[0].regression_risk is RegressionRiskLabel.HIGH
    assert report.groups[0].to_display_dict()["regression_risk"] == "high"


def test_regression_risk_classifies_medium_for_single_error_without_risky_component():
    report = build_review_intelligence(
        (
            _finding(
                severity=ReviewFindingSeverity.ERROR,
                components=("isolated-test",),
            ),
        )
    )

    assert report.groups[0].regression_risk is RegressionRiskLabel.MEDIUM


def test_display_dicts_do_not_expose_raw_finding_bodies_logs_or_unsafe_refs():
    secret_body = "raw finding body includes token=super-secret-token-123456"
    local_path_log = r"traceback at C:\Users\scott\Code\Meridian\.env"
    report = build_review_intelligence(
        (
            _finding(
                source_id=r"C:\Users\scott\Code\Meridian\private-review.log",
                artifact_id=r"C:\Users\scott\Code\Meridian\raw-output.txt",
                rule_id="rule:raw-log",
                severity=ReviewFindingSeverity.CRITICAL,
                body=secret_body,
                log=local_path_log,
                evidence_refs=(r"C:\Users\scott\Code\Meridian\repair-proof.log",),
            ),
        )
    )

    display = report.to_display_dict()
    display_text = str(display)
    assert "super-secret-token" not in display_text
    assert r"C:\Users\scott" not in display_text
    assert "raw finding body" not in display_text
    assert "traceback" not in display_text.lower()
    group = display["groups"][0]
    assert group["fingerprint"]["source_ref"].startswith("source:unsafe:")
    assert group["fingerprint"]["artifact_ref"].startswith("artifact:unsafe:")
    assert group["repair"]["evidence_refs"][0].startswith("evidence:unsafe:")


def test_direct_review_finding_fingerprint_display_sanitizes_unsafe_refs():
    fingerprint = ReviewFindingFingerprint(
        fingerprint="rfp:deadbeef",
        source_ref=r"C:\Users\scott\source",
        artifact_ref="/home/scott/artifact",
        rule_ref=r"C:\Users\scott\rule",
    )

    display = fingerprint.to_display_dict()
    rendered = str(display)

    assert display["fingerprint"] == "rfp:deadbeef"
    assert display["source_ref"].startswith("source:unsafe:")
    assert display["artifact_ref"].startswith("artifact:unsafe:")
    assert display["rule_ref"].startswith("rule:unsafe:")
    assert r"C:\Users\scott" not in rendered
    assert "/home/scott" not in rendered


def test_direct_severity_calibration_display_sanitizes_rationale():
    calibration = SeverityCalibration(
        severity=ReviewFindingSeverity.ERROR,
        rationale=r"traceback at C:\Users\scott\Code\Meridian\review.log",
    )

    display = calibration.to_display_dict()
    rendered = str(display)

    assert display["rationale"] == "[redacted]"
    assert r"C:\Users\scott" not in rendered


def test_direct_repair_verification_display_sanitizes_evidence_refs():
    repair = RepairVerification(
        state=RepairVerificationState.FIXED,
        evidence_refs=(r"C:\Users\scott\evidence", "/home/scott/log"),
    )

    display = repair.to_display_dict()
    rendered = str(display)

    assert all(ref.startswith("evidence:unsafe:") for ref in display["evidence_refs"])
    assert r"C:\Users\scott" not in rendered
    assert "/home/scott" not in rendered


def test_direct_waiver_visibility_display_sanitizes_waiver_ref():
    waiver = WaiverVisibility(
        present=True,
        waiver_ref=r"C:\Users\scott\waiver",
        reason_visible=False,
    )

    display = waiver.to_display_dict()
    rendered = str(display)

    assert display["waiver_ref"].startswith("waiver:unsafe:")
    assert r"C:\Users\scott" not in rendered


def test_direct_review_finding_fingerprint_redacts_raw_prompt_refs():
    fingerprint = ReviewFindingFingerprint(
        fingerprint="rfp:deadbeef",
        source_ref="raw prompt: hidden source body",
        artifact_ref="provider output: hidden artifact body",
        rule_ref="model output: hidden rule body",
    )

    display = fingerprint.to_display_dict()
    rendered = str(display)

    assert display["source_ref"].startswith("source:unsafe:")
    assert display["artifact_ref"].startswith("artifact:unsafe:")
    assert display["rule_ref"].startswith("rule:unsafe:")
    assert "hidden source body" not in rendered
    assert "hidden artifact body" not in rendered
    assert "hidden rule body" not in rendered


def test_direct_severity_calibration_redacts_provider_response_rationale():
    calibration = SeverityCalibration(
        severity=ReviewFindingSeverity.ERROR,
        rationale="provider response: hidden rationale body",
    )

    display = calibration.to_display_dict()
    rendered = str(display)

    assert display["rationale"] == "[redacted]"
    assert "hidden rationale body" not in rendered


def test_direct_severity_calibration_redacts_full_prompt_rationale():
    calibration = SeverityCalibration(
        severity=ReviewFindingSeverity.ERROR,
        rationale="full prompt: another hidden rationale",
    )

    display = calibration.to_display_dict()
    rendered = str(display)

    assert display["rationale"] == "[redacted]"
    assert "another hidden rationale" not in rendered


def test_direct_duplicate_finding_group_display_sanitizes_sources():
    group = DuplicateFindingGroup(
        fingerprint=ReviewFindingFingerprint(
            fingerprint="rfp:cafebabe",
            source_ref="source:ok",
            artifact_ref="artifact:ok",
            rule_ref="rule:ok",
        ),
        duplicate_count=1,
        sources=(r"C:\Users\scott\source-a", "/home/scott/source-b"),
        severity=SeverityCalibration(
            severity=ReviewFindingSeverity.INFO,
            rationale="highest observed severity is info",
        ),
        repair=RepairVerification(state=RepairVerificationState.FIXED),
        waiver=WaiverVisibility(present=False),
        regression_risk=RegressionRiskLabel.LOW,
    )

    display = group.to_display_dict()
    rendered = str(display)

    assert all(source.startswith("source:unsafe:") for source in display["sources"])
    assert r"C:\Users\scott" not in rendered
    assert "/home/scott" not in rendered


def test_direct_duplicate_finding_group_redacts_github_token_shaped_sources():
    group = DuplicateFindingGroup(
        fingerprint=ReviewFindingFingerprint(
            fingerprint="rfp:cafebabe",
            source_ref="ghp_abcdefghijklmnopqrstuvwxyz0123456789",
            artifact_ref="ghs_abcdefghijklmnopqrstuvwxyz0123456789",
            rule_ref="gho_abcdefghijklmnopqrstuvwxyz0123456789",
        ),
        duplicate_count=1,
        sources=("ghu_abcdefghijklmnopqrstuvwxyz0123456789",),
        severity=SeverityCalibration(
            severity=ReviewFindingSeverity.INFO,
            rationale="highest observed severity is info",
        ),
        repair=RepairVerification(state=RepairVerificationState.FIXED),
        waiver=WaiverVisibility(present=False),
        regression_risk=RegressionRiskLabel.LOW,
    )

    rendered = str(group.to_display_dict())

    for prefix in ("ghp_", "gho_", "ghs_", "ghu_"):
        assert prefix not in rendered
    assert "abcdefghijklmnopqrstuvwxyz0123456789" not in rendered


def test_direct_duplicate_finding_group_redacts_fine_grained_github_pat_sources():
    pat = "github_pat_abcdefghijklmnopqrstuvwxyz0123456789_ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    group = DuplicateFindingGroup(
        fingerprint=ReviewFindingFingerprint(
            fingerprint="rfp:cafebabe",
            source_ref=pat,
            artifact_ref=pat,
            rule_ref=pat,
        ),
        duplicate_count=1,
        sources=(pat,),
        severity=SeverityCalibration(
            severity=ReviewFindingSeverity.INFO,
            rationale="highest observed severity is info",
        ),
        repair=RepairVerification(state=RepairVerificationState.FIXED),
        waiver=WaiverVisibility(present=False),
        regression_risk=RegressionRiskLabel.LOW,
    )

    rendered = str(group.to_display_dict())

    assert "github_pat_" not in rendered
    assert "abcdefghijklmnopqrstuvwxyz0123456789" not in rendered
    assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in rendered
