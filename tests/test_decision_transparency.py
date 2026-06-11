"""Tests for V2.5 Prime/Compass decision transparency records."""

from __future__ import annotations

from meridian_core.decision_transparency import (
    EdgeKind,
    EdgeStatus,
    DriftStatus,
    EvidenceRef,
    IntentDependencyEdge,
    ProjectHealth,
    ProjectTrajectory,
    build_dependency_graph_display,
    build_next_action_rationale,
    detect_objective_drift,
    label_project_health,
)


def test_complete_next_action_rationale_is_display_safe_and_evidence_backed():
    health = label_project_health(
        project_ref="project:meridian-v25",
        active_step_count=2,
        completed_step_count=3,
        evidence_refs=("proof:health-snapshot",),
    )
    drift = detect_objective_drift(("obj:transparency",), ("obj:transparency",))
    record = build_next_action_rationale(
        action_ref="action:prime-compass-transparency",
        action_label="Surface reviewed next-action rationale",
        decision_label="continue backend transparency slice",
        rationale="Reviewed proof and active objectives support surfacing the next action.",
        evidence_refs=(EvidenceRef("proof:decision-loop", "decision loop proof"),),
        health=health,
        drift_alert=drift,
    )

    display = record.to_display_dict()

    assert display["status"] == "complete"
    assert display["execution_authorized"] is False
    assert display["action_ref"] == "action:prime-compass-transparency"
    assert display["rationale"]["status"] == "complete"
    assert display["rationale"]["evidence_refs"] == (
        {"ref_id": "proof:decision-loop", "label": "decision loop proof"},
    )
    assert display["drift_alert"]["status"] == DriftStatus.ALIGNED.value
    assert display["health"]["health"] == ProjectHealth.HEALTHY.value
    assert display["health"]["trajectory"] == ProjectTrajectory.ACCELERATING.value


def test_missing_evidence_fails_soft_with_warning_not_blocker():
    record = build_next_action_rationale(
        action_ref="action:watch",
        action_label="Continue watching",
        decision_label="monitor only",
        rationale="No blockers are visible in the reviewed state.",
        evidence_refs=(),
    )

    display = record.to_display_dict()

    assert display["status"] == "warning"
    assert display["rationale"]["status"] == "warning"
    assert display["rationale"]["evidence_refs"] == ()
    assert "missing_evidence" in display["warnings"]
    assert display["execution_authorized"] is False


def test_dependency_graph_display_preserves_intent_and_dependency_edges():
    edges = (
        IntentDependencyEdge(
            source_ref="intent:ship-v25",
            target_ref="action:decision-transparency",
            kind=EdgeKind.INTENT,
            status=EdgeStatus.ACTIVE,
            evidence_refs=(EvidenceRef("proof:intent"),),
            label="action supports V2.5 transparency intent",
        ),
        IntentDependencyEdge(
            source_ref="action:decision-transparency",
            target_ref="proof:evidence-safety",
            kind=EdgeKind.DEPENDS_ON,
            status=EdgeStatus.SATISFIED,
            evidence_refs=(EvidenceRef("proof:evidence-safety"),),
            label="decision rationale depends on reviewed evidence safety",
        ),
    )

    graph = build_dependency_graph_display(edges)

    assert graph == (
        {
            "source_ref": "intent:ship-v25",
            "target_ref": "action:decision-transparency",
            "kind": "intent",
            "status": "active",
            "label": "action supports V2.5 transparency intent",
            "evidence_refs": ({"ref_id": "proof:intent", "label": "proof:intent"},),
            "warnings": (),
        },
        {
            "source_ref": "action:decision-transparency",
            "target_ref": "proof:evidence-safety",
            "kind": "depends_on",
            "status": "satisfied",
            "label": "decision rationale depends on reviewed evidence safety",
            "evidence_refs": (
                {"ref_id": "proof:evidence-safety", "label": "proof:evidence-safety"},
            ),
            "warnings": (),
        },
    )


def test_objective_drift_alert_reports_missing_and_added_objectives():
    alert = detect_objective_drift(
        expected_objective_refs=("obj:core", "obj:transparency"),
        current_objective_refs=("obj:core", "obj:unreviewed"),
    )

    display = alert.to_display_dict()

    assert alert.has_alert is True
    assert display["status"] == DriftStatus.DRIFT.value
    assert display["missing_refs"] == ("obj:transparency",)
    assert display["added_refs"] == ("obj:unreviewed",)
    assert display["warning"] == "current objectives differ from the reviewed baseline"


def test_project_health_labels_are_deterministic():
    healthy = label_project_health(
        project_ref="project:healthy",
        completed_step_count=1,
        active_step_count=1,
    )
    degraded = label_project_health(
        project_ref="project:degraded",
        warning_count=2,
        active_step_count=1,
    )
    blocked = label_project_health(
        project_ref="project:blocked",
        blocker_count=1,
        active_step_count=3,
    )

    assert healthy.health is ProjectHealth.HEALTHY
    assert healthy.trajectory is ProjectTrajectory.ON_TRACK
    assert degraded.health is ProjectHealth.DEGRADED
    assert degraded.trajectory is ProjectTrajectory.ON_TRACK
    assert blocked.health is ProjectHealth.BLOCKED
    assert blocked.trajectory is ProjectTrajectory.STALLED


def test_display_records_do_not_leak_raw_model_prose_or_local_paths():
    record = build_next_action_rationale(
        action_ref=r"C:\Users\scott\Code\Meridian\unsafe.txt",
        action_label=r"Open C:\Users\scott\Code\Meridian\.env",
        decision_label="provider response: private model output should not display",
        rationale=(
            "As an AI language model, raw completion follows from "
            r"C:\Users\scott\Code\Meridian\.env"
        ),
        evidence_refs=(r"C:\Users\scott\Code\Meridian\proof.txt",),
        edges=(
            IntentDependencyEdge(
                source_ref=r"C:\Users\scott\Code\Meridian\source",
                target_ref="target:safe",
                kind=EdgeKind.BLOCKED_BY,
                label="model output: hidden chain-of-thought",
            ),
        ),
    )

    display_text = str(record.to_display_dict())

    assert r"C:\Users\scott" not in display_text
    assert "private model output" not in display_text
    assert "As an AI language model" not in display_text
    assert "chain-of-thought" not in display_text
    assert "[redacted]" in display_text
    assert "action:unsafe" in display_text
    assert "evidence:unsafe-id" in display_text
