"""Tests for V2.5 session/promotion provenance records."""

from __future__ import annotations

from datetime import datetime, timezone

from meridian_core.promotion_provenance import (
    BranchLeaseStatus,
    CommitIntentVerificationStatus,
    RollbackBundlePlan,
    SessionFreshnessStatus,
    build_promotion_provenance,
    build_session_provenance,
)


NOW = datetime(2026, 6, 11, 8, 30, tzinfo=timezone.utc)


def _rollback_plan() -> RollbackBundlePlan:
    return RollbackBundlePlan(
        artifact_id="rollback:rank3",
        strategy="restore_review_ref",
        target_ref="main@rank3",
        restore_ref="review@rank3",
        evidence_refs=("proof:rollback-plan",),
    )


def _fresh_session():
    return build_session_provenance(
        session_id="session:rank3",
        session_label="Rank 3 Backend",
        branch_name="codex/rank3-provenance",
        branch_lease_status=BranchLeaseStatus.ACTIVE,
        session_freshness=SessionFreshnessStatus.FRESH,
        lease_holder="session:rank3",
        observed_at=NOW,
        evidence_refs=("lease:rank3",),
    )


def test_clean_promotion_chain_is_verified_and_display_safe():
    provenance = build_promotion_provenance(
        provenance_id="promotion:rank3",
        session=_fresh_session(),
        candidate_ref="candidate@abc123",
        review_ref="review@abc123",
        intent_ref="intent@abc123",
        main_ref="main@abc123",
        intended_diff_fingerprint="diff:abc123",
        observed_diff_fingerprint="diff:abc123",
        rollback_plan=_rollback_plan(),
        observed_at=NOW,
        evidence_refs=("proof:promotion-chain",),
    )

    display = provenance.to_display_dict()

    assert provenance.is_clean is True
    assert provenance.commit_intent_verification is CommitIntentVerificationStatus.VERIFIED
    assert display["branch_lease_status"] == "active"
    assert display["commit_intent_verification"] == "verified"
    assert display["promotion_chain_summary"] == (
        "candidate:candidate@abc123->review:review@abc123"
        "->intent:intent@abc123->main:main@abc123"
    )
    assert display["promotion_chain"] == {
        "candidate": "candidate@abc123",
        "review": "review@abc123",
        "intent": "intent@abc123",
        "main": "main@abc123",
    }
    assert display["warnings"] == ()
    assert display["blockers"] == ()


def test_stale_session_advises_refresh_without_blocking_by_itself():
    session = build_session_provenance(
        session_id="session:rank3",
        session_label="Rank 3 Backend",
        branch_name="codex/rank3-provenance",
        branch_lease_status="active",
        session_freshness="stale",
        observed_at=NOW,
        evidence_refs=("session:freshness",),
    )
    provenance = build_promotion_provenance(
        provenance_id="promotion:rank3",
        session=session,
        candidate_ref="candidate@abc123",
        review_ref="review@abc123",
        intent_ref="intent@abc123",
        main_ref="main@abc123",
        intended_diff_fingerprint="diff:abc123",
        observed_diff_fingerprint="diff:abc123",
        rollback_plan=_rollback_plan(),
    )

    display = provenance.to_display_dict()

    assert session.stale_session_recommendation == "refresh_session_before_promotion"
    assert "session.stale.advisory" in session.warnings
    assert "promotion.session_stale" in provenance.warnings
    assert display["stale_session_recommendation"] == "refresh_session_before_promotion"
    assert display["session"]["session_freshness"] == "stale"
    assert display["blockers"] == ()


def test_intent_diff_mismatch_warns_and_keeps_fingerprints_bounded():
    provenance = build_promotion_provenance(
        provenance_id="promotion:rank3",
        session=_fresh_session(),
        candidate_ref="candidate@abc123",
        review_ref="review@abc123",
        intent_ref="intent@abc123",
        main_ref="main@abc123",
        intended_diff_fingerprint="diff:intended",
        observed_diff_fingerprint="diff:observed",
        rollback_plan=_rollback_plan(),
    )

    display = provenance.to_display_dict()

    assert provenance.commit_intent_verification is CommitIntentVerificationStatus.MISMATCH
    assert "commit_intent.diff_mismatch" in provenance.warnings
    assert display["commit_intent_verification"] == "mismatch"
    assert display["intended_diff_fingerprint"] == "diff:intended"
    assert display["observed_diff_fingerprint"] == "diff:observed"


def test_rollback_plan_display_is_planning_only_and_non_executable():
    plan = RollbackBundlePlan(
        artifact_id="rollback:rank3",
        strategy="restore_review_ref",
        target_ref="main@rank3",
        restore_ref="review@rank3",
        evidence_refs=("proof:rollback-plan",),
        human_gate_required=True,
        executable_now=True,
    )

    display = plan.to_display_dict()

    assert display == {
        "artifact_id": "rollback:rank3",
        "strategy": "restore_review_ref",
        "target_ref": "main@rank3",
        "restore_ref": "review@rank3",
        "evidence_refs": ("proof:rollback-plan",),
        "human_gate_required": True,
        "executable_now": False,
        "planning_only": True,
    }


def test_display_dicts_do_not_leak_local_paths_or_raw_logs():
    unsafe_session = build_session_provenance(
        session_id=r"C:\Users\scott\Code\Meridian\secret-session",
        session_label="raw log: private worker trace",
        branch_name=r"C:\Users\scott\Code\Meridian\.git",
        branch_lease_status="active",
        session_freshness="fresh",
        lease_holder=r"C:\Users\scott\owner",
        evidence_refs=(r"C:\Users\scott\Code\Meridian\raw.log", "raw_log:secret"),
    )
    unsafe_plan = RollbackBundlePlan(
        artifact_id=r"C:\Users\scott\rollback.json",
        strategy="raw log restore",
        target_ref=r"C:\Users\scott\main",
        restore_ref="raw log: restore details",
        evidence_refs=(r"C:\Users\scott\rollback.log",),
    )
    provenance = build_promotion_provenance(
        provenance_id=r"C:\Users\scott\promotion.json",
        session=unsafe_session,
        candidate_ref=r"C:\Users\scott\candidate",
        review_ref="raw log: review details",
        intent_ref="intent@abc123",
        main_ref="main@abc123",
        intended_diff_fingerprint="raw log: intended secret",
        observed_diff_fingerprint="diff:observed",
        rollback_plan=unsafe_plan,
        evidence_refs=(r"C:\Users\scott\promotion.log", "raw log: promotion trace"),
    )

    display_text = repr(provenance.to_display_dict()).lower()

    assert r"c:\users\scott".lower() not in display_text
    assert "private worker trace" not in display_text
    assert "promotion trace" not in display_text
    assert "raw log" not in display_text
    assert "[redacted]" in display_text
