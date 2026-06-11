"""Tests for display-safe V2.5 harness diagnostics."""

from __future__ import annotations

import json

from meridian_core.harness_diagnostics import (
    BackendSnapshotProof,
    HarnessDiagnosticInput,
    build_harness_diagnostic_snapshot,
    classify_heartbeat_anomaly,
    detect_backend_snapshot_drift,
)


def _proof(
    backend: str | None = "harness-diagnostics-v1",
    displayed: str | None = "harness-diagnostics-v1",
    proof_count: int = 1,
) -> BackendSnapshotProof:
    return BackendSnapshotProof(
        backend_snapshot_id=backend,
        displayed_snapshot_id=displayed,
        backend_proof_count=proof_count,
        required_proof_count=1,
    )


def test_healthy_snapshot_is_display_only_and_scores_high() -> None:
    snapshot = build_harness_diagnostic_snapshot(
        [
            HarnessDiagnosticInput(
                harness_id="build-1",
                heartbeat_status="alive",
                heartbeat_age_seconds=10,
                expected_heartbeat_seconds=60,
                proof_count=2,
                required_proof_count=1,
                current_work_present=True,
            )
        ],
        _proof(),
    )
    display = snapshot.to_display_dict()

    assert display["display_only"] is True
    assert display["mutation_authorized"] is False
    assert display["process_inspection_authorized"] is False
    assert display["model_calls_authorized"] is False
    assert display["automatic_intervention_authorized"] is False
    assert display["records"][0]["heartbeat_anomaly"] == "healthy"
    assert display["records"][0]["stale_worker_classification"] == "active"
    assert display["backend_drift"]["classification"] == "aligned"
    assert display["reliability"]["score"] == 100
    assert "healthy" in display["escalation_recommendation"]


def test_stale_worker_is_classified_from_age_without_process_inspection() -> None:
    snapshot = build_harness_diagnostic_snapshot(
        [
            HarnessDiagnosticInput(
                harness_id="build-2",
                heartbeat_status="alive",
                heartbeat_age_seconds=121,
                expected_heartbeat_seconds=120,
                proof_count=1,
            )
        ],
        _proof(),
    )

    record = snapshot.to_display_dict()["records"][0]
    assert record["heartbeat_anomaly"] == "stale"
    assert record["stale_worker_classification"] == "stale"
    assert snapshot.reliability.stale_count == 1
    assert 0 <= snapshot.reliability.score < 100


def test_blocked_status_takes_precedence_over_missing_heartbeat_age() -> None:
    anomaly = classify_heartbeat_anomaly(
        "blocked",
        heartbeat_age_seconds=None,
        expected_heartbeat_seconds=60,
        blocker_count=1,
    )

    assert anomaly.value == "blocked"


def test_divergent_backend_snapshot_is_detected_and_escalated() -> None:
    drift = detect_backend_snapshot_drift(
        BackendSnapshotProof(
            backend_snapshot_id="backend-v2",
            displayed_snapshot_id="display-v1",
            backend_proof_count=3,
            required_proof_count=1,
        )
    )

    snapshot = build_harness_diagnostic_snapshot([], BackendSnapshotProof("backend-v2", "display-v1", 3))

    assert drift.to_display_dict()["classification"] == "divergent"
    assert snapshot.to_display_dict()["backend_drift"]["classification"] == "divergent"
    assert "snapshot drift review" in snapshot.escalation_recommendation
    assert snapshot.reliability.divergent_snapshot_count == 1


def test_missing_snapshot_proof_is_classified_without_exposing_ids() -> None:
    snapshot = build_harness_diagnostic_snapshot(
        [
            HarnessDiagnosticInput(
                harness_id="review-console",
                heartbeat_status="alive",
                heartbeat_age_seconds=1,
                expected_heartbeat_seconds=60,
                proof_count=1,
            )
        ],
        BackendSnapshotProof(
            backend_snapshot_id=None,
            displayed_snapshot_id="displayed-v1",
            backend_proof_count=0,
            required_proof_count=1,
        ),
    )

    drift = snapshot.to_display_dict()["backend_drift"]
    assert drift["classification"] == "missing_backend"
    assert drift["backend_snapshot_present"] is False
    assert drift["snapshot_ids_visible"] is False
    assert drift["under_proven"] is True
    assert "missing snapshot proof" in snapshot.escalation_recommendation


def test_under_proven_worker_stays_healthy_but_requires_more_proof() -> None:
    snapshot = build_harness_diagnostic_snapshot(
        [
            HarnessDiagnosticInput(
                harness_id="relay",
                heartbeat_status="alive",
                heartbeat_age_seconds=5,
                expected_heartbeat_seconds=60,
                proof_count=0,
                required_proof_count=2,
            )
        ],
        _proof(),
    )

    record = snapshot.to_display_dict()["records"][0]
    assert record["heartbeat_anomaly"] == "healthy"
    assert record["stale_worker_classification"] == "under_proven"
    assert record["under_proven"] is True
    assert snapshot.reliability.under_proven_count == 1
    assert "additional proof" in snapshot.escalation_recommendation


def test_reliability_score_is_clamped_between_zero_and_one_hundred() -> None:
    bad_workers = [
        HarnessDiagnosticInput(
            harness_id=f"worker-{index}",
            heartbeat_status="failed",
            heartbeat_age_seconds=999,
            expected_heartbeat_seconds=1,
            proof_count=0,
            required_proof_count=5,
        )
        for index in range(10)
    ]
    bad = build_harness_diagnostic_snapshot(
        bad_workers,
        BackendSnapshotProof(
            backend_snapshot_id="backend-v2",
            displayed_snapshot_id="display-v1",
            backend_proof_count=0,
            required_proof_count=2,
        ),
    )
    good = build_harness_diagnostic_snapshot([], _proof(proof_count=3))

    assert bad.reliability.score == 0
    assert good.reliability.score == 100


def test_display_dicts_do_not_leak_local_paths_or_raw_logs() -> None:
    snapshot = build_harness_diagnostic_snapshot(
        [
            HarnessDiagnosticInput(
                harness_id=r"C:\Users\scott\secret\worker.log",
                heartbeat_status="blocked",
                heartbeat_age_seconds=5,
                expected_heartbeat_seconds=60,
                proof_count=1,
                blocker_count=1,
                current_work_present=True,
                raw_event_text="RAW LOG: token=SECRET at C:\\Users\\scott\\secret\\worker.log",
            )
        ],
        BackendSnapshotProof(
            backend_snapshot_id=r"C:\Users\scott\secret\backend.json",
            displayed_snapshot_id=r"C:\Users\scott\secret\backend.json",
            backend_proof_count=1,
        ),
    )

    rendered = json.dumps(snapshot.to_display_dict(), sort_keys=True)
    assert "C:\\Users\\scott" not in rendered
    assert "RAW LOG" not in rendered
    assert "SECRET" not in rendered
    assert "worker.log" not in rendered
    assert "harness:unsafe-id" in rendered
    assert '"raw_logs_visible": false' in rendered
    assert '"raw_event_visible": false' in rendered


def test_heartbeat_anomaly_classification_covers_warning_and_missing() -> None:
    assert classify_heartbeat_anomaly("alive", 49, 60).value == "warning"
    assert classify_heartbeat_anomaly("unknown", None, 60).value == "missing"