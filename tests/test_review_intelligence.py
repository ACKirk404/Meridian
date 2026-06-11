"""Tests for V2.5 display-safe review intelligence."""

from __future__ import annotations

from meridian_core.review_intelligence import (
    RegressionRiskLabel,
    RepairVerificationState,
    ReviewFindingInput,
    ReviewFindingSeverity,
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
