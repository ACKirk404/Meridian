"""Tests for the Aegis proof/evidence slice (meridian_core/aegis.py)."""

from __future__ import annotations

import pytest

from meridian_core.aegis import (
    AegisEvidence,
    AggregateGateSummary,
    ApprovalRecord,
    EvidenceSeverity,
    EvidenceStatus,
    EvidenceType,
    GateDecision,
    GateResult,
    GateSummary,
    ProofTrail,
    PromptPayloadMeterDecision,
    PromptPayloadMeterInput,
    PromptPayloadMeterPolicyResult,
    ProviderResultValidationDecision,
    ProviderResultValidationInput,
    ProviderResultValidationPolicyResult,
    PromptPacketProofDecision,
    PromptPacketProofMetadata,
    PromptPacketProofPolicyResult,
    WaiverRecord,
    evidence_from_cross_check,
    evaluate_prompt_payload_meter_advisory,
    evaluate_provider_result_validation_advisory,
    evaluate_prompt_packet_proof_policy,
    format_aggregate_summary_for_display,
    format_gate_summary_for_display,
    gate_account_session_risk,
    gate_aggregator_authority,
    gate_cost_exposure,
    gate_missing_exact_model_id,
    gate_tier3_dual_lane_requirement,
    gate_unvalidated_deepseek,
    gate_unknown_proof_requirement,
    gate_unknown_route_class,
    gate_unsafe_fallback,
    serialize_prompt_payload_meter_policy_result,
    serialize_provider_result_validation_policy_result,
    serialize_prompt_packet_policy_result,
    summarize_aggregate_route_gates,
    summarize_gate_result,
    summarize_gate_results,
)
from meridian_core.review_console import (
    ReviewConsoleAction,
    ReviewConsoleItemType,
    ReviewConsoleResponse,
    ReviewConsoleSeverity,
    ReviewConsoleQueue,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cc(
    id: str = "ev-1",
    source: str = "relay.py",
    target: str = "RelayRoute",
    summary: str = "Missing independence flag",
    severity: EvidenceSeverity = EvidenceSeverity.INFO,
) -> AegisEvidence:
    return evidence_from_cross_check(id, source, target, summary, severity)


def _blocking(id: str = "ev-block") -> AegisEvidence:
    return _cc(id=id, severity=EvidenceSeverity.ERROR)


def _prompt_packet_metadata(**overrides) -> PromptPacketProofMetadata:
    base = {
        "packet_id": "packet-relay-001",
        "packet_hash_status": "present",
        "packet_hash": "sha256:abc123",
        "prompt_tokens": 512,
        "max_context_tokens": 2048,
        "budget_ref": "budget:tier2:default",
        "source_lineage": {"direct_input": 512},
        "allowed_sources": ("direct_input", "atlas_retrieval"),
        "aegis_evidence_ids": (
            "packet:packet-relay-001",
            "budget:budget-tier2-default",
            "source:direct-input",
        ),
        "risk_tier": 2,
        "proof_requirement": "artifact",
        "selected_model_id": "gpt-4o-2026-06-01",
        "model_trust_state": "trusted",
        "snapshot_requirement": "not_required",
        "snapshot_status": "not_required",
        "human_gate_required": False,
        "human_approval_present": False,
        "dual_lane_required": False,
        "dual_lane_proof_present": False,
        "demotion_target_tier": None,
    }
    base.update(overrides)
    return PromptPacketProofMetadata(**base)


def _provider_result_metadata(**overrides) -> ProviderResultValidationInput:
    base = {
        "validation_status": "valid",
        "warning_tags": (),
        "blocker_tags": (),
        "evidence_refs": (
            "result:relay-dispatch-001",
            "proof:direct-provider-route",
            "budget:prompt-drag-ok",
        ),
        "telemetry_available": True,
        "external_review_state": "not_required",
    }
    base.update(overrides)
    return ProviderResultValidationInput(**base)


def _prompt_payload_meter_metadata(**overrides) -> PromptPayloadMeterInput:
    base = {
        "label_bucket": "under-1k",
        "budget_percent": 24.5,
        "growth_delta_tokens": 0,
        "payload_status": "ok",
        "q_mode_prompt_drag_state": "flat",
        "route_continuity_refs": (
            "provider:deepseek",
            "model:deepseek-chat",
            "route:direct",
        ),
        "blocker_tags": (),
        "warning_tags": (),
        "evidence_refs": (
            "payload:snapshot-001",
            "budget:prompt-meter-ok",
            "proof:route-continuity",
        ),
    }
    base.update(overrides)
    return PromptPayloadMeterInput(**base)


# ---------------------------------------------------------------------------
# Cross-check finding becomes Aegis evidence
# ---------------------------------------------------------------------------


class TestCrossCheckBecomesEvidence:
    def test_evidence_type_is_cross_check(self):
        assert _cc().evidence_type is EvidenceType.CROSS_CHECK

    def test_status_starts_open(self):
        assert _cc().status is EvidenceStatus.OPEN

    def test_source_is_preserved(self):
        ev = _cc(source="risk.py")
        assert ev.source == "risk.py"

    def test_target_is_preserved(self):
        ev = _cc(target="RiskAssessment")
        assert ev.target == "RiskAssessment"

    def test_summary_is_preserved(self):
        ev = _cc(summary="Tier 4 not gated")
        assert ev.summary == "Tier 4 not gated"

    def test_severity_is_preserved(self):
        ev = _cc(severity=EvidenceSeverity.WARNING)
        assert ev.severity is EvidenceSeverity.WARNING

    def test_result_is_aegis_evidence_instance(self):
        assert isinstance(_cc(), AegisEvidence)

    def test_id_is_preserved(self):
        ev = _cc(id="xc-42")
        assert ev.id == "xc-42"

    def test_waiver_reason_empty_by_default(self):
        assert _cc().waiver_reason == ""

    def test_console_item_id_none_by_default(self):
        assert _cc().console_item_id is None


# ---------------------------------------------------------------------------
# Proof-blocking: open + high severity
# ---------------------------------------------------------------------------


class TestProofBlocking:
    def test_open_error_is_proof_blocking(self):
        assert _cc(severity=EvidenceSeverity.ERROR).is_proof_blocking() is True

    def test_open_critical_is_proof_blocking(self):
        assert _cc(severity=EvidenceSeverity.CRITICAL).is_proof_blocking() is True

    def test_open_info_is_not_proof_blocking(self):
        assert _cc(severity=EvidenceSeverity.INFO).is_proof_blocking() is False

    def test_open_warning_is_not_proof_blocking(self):
        assert _cc(severity=EvidenceSeverity.WARNING).is_proof_blocking() is False

    def test_escalated_is_proof_blocking_regardless_of_severity(self):
        ev = _cc(severity=EvidenceSeverity.INFO)
        ev.escalate()
        assert ev.is_proof_blocking() is True

    def test_escalated_critical_is_proof_blocking(self):
        ev = _cc(severity=EvidenceSeverity.CRITICAL)
        ev.escalate()
        assert ev.is_proof_blocking() is True


# ---------------------------------------------------------------------------
# Resolved evidence is no longer proof-blocking
# ---------------------------------------------------------------------------


class TestResolvedNotBlocking:
    def test_resolved_error_is_not_proof_blocking(self):
        ev = _blocking()
        ev.resolve()
        assert ev.is_proof_blocking() is False

    def test_resolved_critical_is_not_proof_blocking(self):
        ev = _cc(severity=EvidenceSeverity.CRITICAL)
        ev.resolve()
        assert ev.is_proof_blocking() is False

    def test_resolve_sets_status_to_resolved(self):
        ev = _blocking()
        ev.resolve()
        assert ev.status is EvidenceStatus.RESOLVED

    def test_resolved_info_is_not_proof_blocking(self):
        ev = _cc(severity=EvidenceSeverity.INFO)
        ev.resolve()
        assert ev.is_proof_blocking() is False


# ---------------------------------------------------------------------------
# Waived evidence records waiver reason
# ---------------------------------------------------------------------------


class TestWaived:
    def test_waived_evidence_is_not_proof_blocking(self):
        ev = _blocking()
        ev.waive("acknowledged by Scott on 2026-05-30")
        assert ev.is_proof_blocking() is False

    def test_waive_sets_status_to_waived(self):
        ev = _blocking()
        ev.waive("accepted risk")
        assert ev.status is EvidenceStatus.WAIVED

    def test_waive_records_reason(self):
        ev = _blocking()
        ev.waive("design decision; intentional omission")
        assert ev.waiver_reason == "design decision; intentional omission"

    def test_waive_strips_reason(self):
        ev = _blocking()
        ev.waive("  accepted risk  ")
        assert ev.waiver_reason == "accepted risk"

    def test_waive_preserves_other_fields(self):
        ev = _cc(id="ev-w", source="relay.py", severity=EvidenceSeverity.ERROR)
        ev.waive("accepted")
        assert ev.id == "ev-w"
        assert ev.source == "relay.py"
        assert ev.severity is EvidenceSeverity.ERROR

    def test_waived_info_is_not_proof_blocking(self):
        ev = _cc(severity=EvidenceSeverity.INFO)
        ev.waive("informational only")
        assert ev.is_proof_blocking() is False

    def test_waive_empty_reason_raises(self):
        with pytest.raises(ValueError):
            _blocking().waive("")

    def test_waive_whitespace_reason_raises(self):
        with pytest.raises(ValueError):
            _blocking().waive("   ")


# ---------------------------------------------------------------------------
# Evidence produces / references a Review Console item
# ---------------------------------------------------------------------------


class TestToConsoleItem:
    def test_non_blocking_produces_cross_check_item(self):
        item = _cc(severity=EvidenceSeverity.INFO).to_console_item()
        assert item.item_type is ReviewConsoleItemType.CROSS_CHECK

    def test_blocking_produces_approval_gate(self):
        item = _blocking().to_console_item()
        assert item.item_type is ReviewConsoleItemType.APPROVAL_GATE

    def test_console_item_id_derived_from_evidence_id(self):
        item = _cc(id="ev-99").to_console_item()
        assert item.id == "aegis-ev-99"

    def test_console_item_id_is_recorded_on_evidence(self):
        ev = _cc(id="ev-link")
        item = ev.to_console_item()
        assert ev.console_item_id == item.id

    def test_console_item_severity_matches_evidence_info(self):
        item = _cc(severity=EvidenceSeverity.INFO).to_console_item()
        assert item.severity is ReviewConsoleSeverity.INFO

    def test_console_item_severity_matches_evidence_error(self):
        item = _blocking().to_console_item()
        assert item.severity is ReviewConsoleSeverity.ERROR

    def test_console_item_severity_matches_evidence_critical(self):
        item = _cc(severity=EvidenceSeverity.CRITICAL).to_console_item()
        assert item.severity is ReviewConsoleSeverity.CRITICAL

    def test_console_item_severity_matches_evidence_warning(self):
        item = _cc(severity=EvidenceSeverity.WARNING).to_console_item()
        assert item.severity is ReviewConsoleSeverity.WARNING

    def test_blocking_gate_requires_response(self):
        item = _blocking().to_console_item()
        assert item.requires_response is True

    def test_non_blocking_does_not_require_response(self):
        item = _cc(severity=EvidenceSeverity.INFO).to_console_item()
        assert item.requires_response is False

    def test_resolved_blocking_produces_cross_check_item(self):
        ev = _blocking()
        ev.resolve()
        item = ev.to_console_item()
        assert item.item_type is ReviewConsoleItemType.CROSS_CHECK

    def test_waived_blocking_produces_cross_check_item(self):
        ev = _blocking()
        ev.waive("accepted")
        item = ev.to_console_item()
        assert item.item_type is ReviewConsoleItemType.CROSS_CHECK

    def test_summary_appears_in_console_item_title(self):
        ev = _cc(summary="Route mismatch detected")
        item = ev.to_console_item()
        assert "Route mismatch detected" in item.title

    def test_source_and_target_appear_in_content(self):
        ev = _cc(source="relay.py", target="RelayRoute")
        item = ev.to_console_item()
        assert "relay.py" in item.content
        assert "RelayRoute" in item.content

    def test_resolved_status_appears_in_content(self):
        ev = _blocking()
        ev.resolve()
        item = ev.to_console_item()
        assert "Status: resolved" in item.content

    def test_waived_status_and_reason_appear_in_content(self):
        ev = _blocking()
        ev.waive("accepted risk")
        item = ev.to_console_item()
        assert "Status: waived" in item.content
        assert "Waiver: accepted risk" in item.content

    def test_escalated_status_appears_in_content(self):
        ev = _cc()
        ev.escalate()
        item = ev.to_console_item()
        assert "Status: escalated" in item.content


# ---------------------------------------------------------------------------
# Apply Review Console response
# ---------------------------------------------------------------------------


class TestApplyConsoleResponse:
    def test_approve_resolves_blocking_evidence(self):
        ev = _blocking()
        ev.to_console_item()
        ev.apply_console_response(
            ReviewConsoleResponse("aegis-ev-block", ReviewConsoleAction.APPROVE)
        )
        assert ev.status is EvidenceStatus.RESOLVED

    def test_approve_clears_proof_blocking(self):
        ev = _blocking()
        ev.to_console_item()
        ev.apply_console_response(
            ReviewConsoleResponse("aegis-ev-block", ReviewConsoleAction.APPROVE)
        )
        assert ev.is_proof_blocking() is False

    def test_reject_escalates_evidence(self):
        ev = _blocking()
        ev.to_console_item()
        ev.apply_console_response(
            ReviewConsoleResponse("aegis-ev-block", ReviewConsoleAction.REJECT, "not enough proof")
        )
        assert ev.status is EvidenceStatus.ESCALATED

    def test_modify_escalates_evidence(self):
        ev = _blocking()
        ev.to_console_item()
        ev.apply_console_response(
            ReviewConsoleResponse("aegis-ev-block", ReviewConsoleAction.MODIFY, "fix then rerun")
        )
        assert ev.status is EvidenceStatus.ESCALATED

    def test_acknowledge_does_not_change_nonblocking_status(self):
        ev = _cc(severity=EvidenceSeverity.INFO)
        ev.to_console_item()
        ev.apply_console_response(
            ReviewConsoleResponse("aegis-ev-1", ReviewConsoleAction.ACKNOWLEDGE)
        )
        assert ev.status is EvidenceStatus.OPEN

    def test_acknowledge_does_not_change_blocking_status(self):
        ev = _blocking()
        ev.to_console_item()
        ev.apply_console_response(
            ReviewConsoleResponse("aegis-ev-block", ReviewConsoleAction.ACKNOWLEDGE)
        )
        assert ev.status is EvidenceStatus.OPEN

    def test_acknowledge_leaves_proof_blocking_unchanged(self):
        ev = _blocking()
        ev.to_console_item()
        ev.apply_console_response(
            ReviewConsoleResponse("aegis-ev-block", ReviewConsoleAction.ACKNOWLEDGE)
        )
        assert ev.is_proof_blocking() is True

    def test_mismatched_console_item_id_raises(self):
        ev = _blocking()
        ev.to_console_item()
        with pytest.raises(ValueError, match="does not match"):
            ev.apply_console_response(
                ReviewConsoleResponse("different-item", ReviewConsoleAction.APPROVE)
            )

    def test_response_before_console_item_raises(self):
        ev = _blocking()
        with pytest.raises(ValueError, match="no console item"):
            ev.apply_console_response(
                ReviewConsoleResponse("external-gate", ReviewConsoleAction.APPROVE)
            )

    def test_apply_console_response_does_not_waive_without_reason(self):
        ev = _blocking()
        ev.to_console_item()
        ev.apply_console_response(
            ReviewConsoleResponse("aegis-ev-block", ReviewConsoleAction.APPROVE)
        )
        assert ev.waiver_reason == ""


# ---------------------------------------------------------------------------
# ProofTrail
# ---------------------------------------------------------------------------


class TestProofTrail:
    def test_empty_trail_is_clean(self):
        assert ProofTrail().is_clean() is True

    def test_add_appends_evidence(self):
        trail = ProofTrail()
        ev = _cc()
        trail.add(ev)
        assert ev in trail.evidence

    def test_blocking_returns_only_blocking_evidence(self):
        trail = ProofTrail()
        trail.add(_cc(id="info", severity=EvidenceSeverity.INFO))
        trail.add(_blocking(id="err"))
        blocking = trail.blocking()
        assert len(blocking) == 1
        assert blocking[0].id == "err"

    def test_trail_with_blocking_evidence_is_not_clean(self):
        trail = ProofTrail()
        trail.add(_blocking())
        assert trail.is_clean() is False

    def test_trail_becomes_clean_after_resolve(self):
        trail = ProofTrail()
        ev = _blocking()
        trail.add(ev)
        ev.resolve()
        assert trail.is_clean() is True

    def test_trail_becomes_clean_after_waive(self):
        trail = ProofTrail()
        ev = _blocking()
        trail.add(ev)
        ev.waive("accepted")
        assert trail.is_clean() is True

    def test_open_findings_returns_open_only(self):
        trail = ProofTrail()
        ev_open = _cc(id="open")
        ev_resolved = _cc(id="resolved")
        ev_resolved.resolve()
        trail.add(ev_open)
        trail.add(ev_resolved)
        open_list = trail.open_findings()
        assert ev_open in open_list
        assert ev_resolved not in open_list

    def test_blocking_preserves_insertion_order(self):
        trail = ProofTrail()
        for i in range(4):
            trail.add(_cc(id=f"ev-{i}", severity=EvidenceSeverity.ERROR))
        ids = [e.id for e in trail.blocking()]
        assert ids == ["ev-0", "ev-1", "ev-2", "ev-3"]


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_is_proof_blocking_is_deterministic(self):
        ev = _blocking()
        assert ev.is_proof_blocking() == ev.is_proof_blocking()

    def test_to_console_item_produces_same_type_each_call(self):
        ev = _blocking()
        assert ev.to_console_item().item_type == ev.to_console_item().item_type

    def test_proof_trail_blocking_is_stable(self):
        trail = ProofTrail()
        trail.add(_blocking(id="a"))
        trail.add(_blocking(id="b"))
        assert [e.id for e in trail.blocking()] == [e.id for e in trail.blocking()]

    @pytest.mark.parametrize("sev", [
        EvidenceSeverity.INFO,
        EvidenceSeverity.WARNING,
        EvidenceSeverity.ERROR,
        EvidenceSeverity.CRITICAL,
    ])
    def test_open_evidence_blocking_is_consistent(self, sev):
        ev = _cc(severity=sev)
        assert ev.is_proof_blocking() == ev.is_proof_blocking()


# ---------------------------------------------------------------------------
# ProofTrail Review Console bridge
# ---------------------------------------------------------------------------


class TestProofTrailConsoleItems:
    def test_emits_one_item_per_evidence(self):
        trail = ProofTrail()
        for i in range(3):
            trail.add(_cc(id=f"ev-{i}"))
        assert len(trail.to_console_items()) == 3

    def test_empty_trail_emits_no_items(self):
        assert ProofTrail().to_console_items() == []

    def test_output_preserves_insertion_order(self):
        trail = ProofTrail()
        for i in range(4):
            trail.add(_cc(id=f"ev-{i}"))
        ids = [item.id for item in trail.to_console_items()]
        assert ids == ["aegis-ev-0", "aegis-ev-1", "aegis-ev-2", "aegis-ev-3"]

    def test_blocking_evidence_becomes_approval_gate(self):
        trail = ProofTrail()
        trail.add(_blocking(id="b1"))
        items = trail.to_console_items()
        assert items[0].item_type is ReviewConsoleItemType.APPROVAL_GATE

    def test_blocking_evidence_requires_response(self):
        trail = ProofTrail()
        trail.add(_blocking(id="b1"))
        assert trail.to_console_items()[0].requires_response is True

    def test_nonblocking_evidence_becomes_cross_check(self):
        trail = ProofTrail()
        trail.add(_cc(id="nb1", severity=EvidenceSeverity.INFO))
        items = trail.to_console_items()
        assert items[0].item_type is ReviewConsoleItemType.CROSS_CHECK

    def test_nonblocking_evidence_is_informational(self):
        trail = ProofTrail()
        trail.add(_cc(id="nb1", severity=EvidenceSeverity.INFO))
        assert trail.to_console_items()[0].requires_response is False

    def test_evidence_console_item_id_linked_after_to_console_items(self):
        trail = ProofTrail()
        ev = _cc(id="ev-link")
        trail.add(ev)
        trail.to_console_items()
        assert ev.console_item_id == "aegis-ev-link"

    def test_all_evidence_ids_linked_after_to_console_items(self):
        trail = ProofTrail()
        evidences = [_cc(id=f"ev-{i}") for i in range(3)]
        for ev in evidences:
            trail.add(ev)
        trail.to_console_items()
        for i, ev in enumerate(evidences):
            assert ev.console_item_id == f"aegis-ev-{i}"


class TestProofTrailEnqueueToReviewConsole:
    def test_enqueue_returns_console_item_ids(self):
        trail = ProofTrail()
        for i in range(3):
            trail.add(_cc(id=f"ev-{i}"))
        queue = ReviewConsoleQueue()
        ids = trail.enqueue_to_review_console(queue)
        assert ids == ["aegis-ev-0", "aegis-ev-1", "aegis-ev-2"]

    def test_enqueue_assigns_sequence_numbers(self):
        trail = ProofTrail()
        for i in range(3):
            trail.add(_cc(id=f"ev-{i}"))
        queue = ReviewConsoleQueue()
        trail.enqueue_to_review_console(queue)
        seqs = [item.sequence for item in queue.items]
        assert seqs == sorted(seqs)
        assert len(set(seqs)) == 3

    def test_enqueue_items_appear_in_queue_pending(self):
        trail = ProofTrail()
        trail.add(_cc(id="ev-a"))
        trail.add(_blocking(id="ev-b"))
        queue = ReviewConsoleQueue()
        trail.enqueue_to_review_console(queue)
        assert len(queue.pending()) == 2

    def test_blocking_evidence_in_pending_gates(self):
        trail = ProofTrail()
        trail.add(_blocking(id="gate-1"))
        trail.add(_cc(id="info-1", severity=EvidenceSeverity.INFO))
        queue = ReviewConsoleQueue()
        trail.enqueue_to_review_console(queue)
        gates = queue.pending_gates()
        assert len(gates) == 1
        assert gates[0].id == "aegis-gate-1"

    def test_nonblocking_evidence_in_informational(self):
        trail = ProofTrail()
        trail.add(_cc(id="info-1", severity=EvidenceSeverity.INFO))
        trail.add(_cc(id="info-2", severity=EvidenceSeverity.WARNING))
        queue = ReviewConsoleQueue()
        trail.enqueue_to_review_console(queue)
        info = queue.informational()
        assert len(info) == 2

    def test_evidence_ids_linked_after_enqueue(self):
        trail = ProofTrail()
        ev = _cc(id="ev-enqueue")
        trail.add(ev)
        queue = ReviewConsoleQueue()
        trail.enqueue_to_review_console(queue)
        assert ev.console_item_id == "aegis-ev-enqueue"

    def test_enqueue_into_nonempty_queue_no_sequence_collision(self):
        existing_item = _cc(id="pre-existing").to_console_item()
        existing_item.sequence = 5
        queue = ReviewConsoleQueue(items=[existing_item])
        trail = ProofTrail()
        trail.add(_cc(id="new-ev"))
        trail.enqueue_to_review_console(queue)
        seqs = [item.sequence for item in queue.items]
        assert len(set(seqs)) == len(seqs)

    def test_empty_trail_enqueue_returns_empty_list(self):
        queue = ReviewConsoleQueue()
        result = ProofTrail().enqueue_to_review_console(queue)
        assert result == []
        assert queue.items == []


# ---------------------------------------------------------------------------
# Gate 1: Unknown Route Class Gate
# ---------------------------------------------------------------------------


class TestGateUnknownRouteClass:
    def test_valid_account_session_allows(self):
        result = gate_unknown_route_class("account_session")
        assert result.decision is GateDecision.ALLOW

    def test_valid_local_cli_allows(self):
        result = gate_unknown_route_class("local_cli")
        assert result.decision is GateDecision.ALLOW

    def test_valid_direct_api_allows(self):
        result = gate_unknown_route_class("direct_api")
        assert result.decision is GateDecision.ALLOW

    def test_valid_aggregator_api_allows(self):
        result = gate_unknown_route_class("aggregator_api")
        assert result.decision is GateDecision.ALLOW

    def test_unknown_route_class_blocks(self):
        result = gate_unknown_route_class("unknown_class")
        assert result.decision is GateDecision.BLOCK

    def test_none_route_class_blocks(self):
        result = gate_unknown_route_class(None)
        assert result.decision is GateDecision.BLOCK

    def test_empty_route_class_blocks(self):
        result = gate_unknown_route_class("")
        assert result.decision is GateDecision.BLOCK


# ---------------------------------------------------------------------------
# Gate 2: Missing Exact Model ID Gate
# ---------------------------------------------------------------------------


class TestGateMissingExactModelId:
    def test_tier0_no_model_id_required(self):
        result = gate_missing_exact_model_id(None, 0)
        assert result.decision is GateDecision.ALLOW

    def test_tier1_unversioned_allowed(self):
        result = gate_missing_exact_model_id("gpt-latest", 1)
        assert result.decision is GateDecision.ALLOW

    def test_tier1_missing_allowed(self):
        result = gate_missing_exact_model_id(None, 1)
        assert result.decision is GateDecision.ALLOW

    def test_tier2_missing_blocks(self):
        result = gate_missing_exact_model_id(None, 2)
        assert result.decision is GateDecision.BLOCK

    def test_tier2_unversioned_blocks(self):
        result = gate_missing_exact_model_id("gpt-latest", 2)
        assert result.decision is GateDecision.BLOCK

    def test_tier3_missing_blocks(self):
        result = gate_missing_exact_model_id(None, 3)
        assert result.decision is GateDecision.BLOCK

    def test_tier4_versioned_allows(self):
        result = gate_missing_exact_model_id("gpt-4-turbo-2025-05-13", 4)
        assert result.decision is GateDecision.ALLOW

    def test_versioned_model_with_dash_allowed(self):
        result = gate_missing_exact_model_id("claude-opus-4-7", 2)
        assert result.decision is GateDecision.ALLOW

    def test_versioned_model_with_underscore_allowed(self):
        result = gate_missing_exact_model_id("gpt_4_2025_05", 2)
        assert result.decision is GateDecision.ALLOW


# ---------------------------------------------------------------------------
# Gate 3: Tier 3 Dual-Lane Requirement Gate
# ---------------------------------------------------------------------------


class TestGateTier3DualLaneRequirement:
    def test_tier0_dual_lane_not_required(self):
        result = gate_tier3_dual_lane_requirement(0, False)
        assert result.decision is GateDecision.ALLOW

    def test_tier1_dual_lane_not_required(self):
        result = gate_tier3_dual_lane_requirement(1, False)
        assert result.decision is GateDecision.ALLOW

    def test_tier2_dual_lane_not_required(self):
        result = gate_tier3_dual_lane_requirement(2, False)
        assert result.decision is GateDecision.ALLOW

    def test_tier3_with_dual_lane_allows(self):
        result = gate_tier3_dual_lane_requirement(3, True)
        assert result.decision is GateDecision.ALLOW

    def test_tier3_without_dual_lane_blocks(self):
        result = gate_tier3_dual_lane_requirement(3, False)
        assert result.decision is GateDecision.BLOCK

    def test_tier3_without_dual_lane_with_bare_boolean_blocks(self):
        # Bare boolean waivers are no longer accepted
        result = gate_tier3_dual_lane_requirement(3, False, waiver_record=None)
        assert result.decision is GateDecision.BLOCK

    def test_tier3_without_dual_lane_with_valid_waiver_demotes(self):
        waiver = WaiverRecord(
            waiver_id="waiv-001",
            actor="scott@example.com",
            scope="tier3_dual_lane",
            timestamp="2026-06-13T16:30:00Z",
            reason="Rapid iteration approved by Scott",
        )
        result = gate_tier3_dual_lane_requirement(3, False, waiver_record=waiver)
        assert result.decision is GateDecision.DEMOTE
        assert result.demote_to_tier == 2

    def test_tier3_without_dual_lane_with_invalid_waiver_blocks(self):
        # Waiver missing required fields
        waiver = WaiverRecord(
            waiver_id="waiv-002",
            actor="",  # empty actor
            scope="tier3_dual_lane",
            timestamp="2026-06-13T16:30:00Z",
            reason="Incomplete waiver",
        )
        result = gate_tier3_dual_lane_requirement(3, False, waiver_record=waiver)
        assert result.decision is GateDecision.BLOCK

    def test_tier4_dual_lane_not_required(self):
        result = gate_tier3_dual_lane_requirement(4, False)
        assert result.decision is GateDecision.ALLOW


# ---------------------------------------------------------------------------
# Gate 4: Unknown Proof Requirement Gate
# ---------------------------------------------------------------------------


class TestGateUnknownProofRequirement:
    def test_tier0_none_required_allows(self):
        result = gate_unknown_proof_requirement("none", 0)
        assert result.decision is GateDecision.ALLOW

    def test_tier1_none_allowed(self):
        result = gate_unknown_proof_requirement("none", 1)
        assert result.decision is GateDecision.ALLOW

    def test_tier1_telemetry_allowed(self):
        result = gate_unknown_proof_requirement("telemetry", 1)
        assert result.decision is GateDecision.ALLOW

    def test_tier2_code_review_allowed(self):
        result = gate_unknown_proof_requirement("code_review", 2)
        assert result.decision is GateDecision.ALLOW

    def test_tier3_security_review_allowed(self):
        result = gate_unknown_proof_requirement("security_review", 3)
        assert result.decision is GateDecision.ALLOW

    def test_tier4_human_gate_allowed(self):
        result = gate_unknown_proof_requirement("human_gate", 4)
        assert result.decision is GateDecision.ALLOW

    def test_tier1_missing_proof_blocks(self):
        result = gate_unknown_proof_requirement(None, 1)
        assert result.decision is GateDecision.BLOCK

    def test_tier2_invalid_proof_blocks(self):
        result = gate_unknown_proof_requirement("invalid_type", 2)
        assert result.decision is GateDecision.BLOCK

    def test_tier1_code_review_disallowed(self):
        result = gate_unknown_proof_requirement("code_review", 1)
        assert result.decision is GateDecision.BLOCK


# ---------------------------------------------------------------------------
# Gate 5: Unsafe Fallback Gate
# ---------------------------------------------------------------------------


class TestGateUnsafeFallback:
    def test_no_fallback_allowed(self):
        result = gate_unsafe_fallback(False, None, 2)
        assert result.decision is GateDecision.ALLOW

    def test_silent_fallback_blocker_blocks(self):
        result = gate_unsafe_fallback(True, ["silent_fallback"], 1)
        assert result.decision is GateDecision.BLOCK

    def test_trust_downgrade_blocker_allowed_tier1(self):
        result = gate_unsafe_fallback(True, ["trust_downgrade"], 1)
        assert result.decision is GateDecision.ALLOW

    def test_trust_downgrade_blocker_allowed_tier2(self):
        result = gate_unsafe_fallback(True, ["trust_downgrade"], 2)
        assert result.decision is GateDecision.ALLOW

    def test_model_mismatch_blocker_allowed_tier2(self):
        result = gate_unsafe_fallback(True, ["model_mismatch"], 2)
        assert result.decision is GateDecision.ALLOW

    def test_model_mismatch_blocker_blocks_tier3(self):
        result = gate_unsafe_fallback(True, ["model_mismatch"], 3)
        assert result.decision is GateDecision.BLOCK

    def test_model_mismatch_blocker_blocks_tier4(self):
        result = gate_unsafe_fallback(True, ["model_mismatch"], 4)
        assert result.decision is GateDecision.BLOCK

    def test_cost_increase_blocker_allowed(self):
        result = gate_unsafe_fallback(True, ["cost_increase"], 2)
        assert result.decision is GateDecision.ALLOW

    def test_multiple_blockers_with_silent_fallback_blocks(self):
        result = gate_unsafe_fallback(True, ["cost_increase", "silent_fallback"], 2)
        assert result.decision is GateDecision.BLOCK


# ---------------------------------------------------------------------------
# Gate 6: Unvalidated DeepSeek Gate
# ---------------------------------------------------------------------------


class TestGateUnvalidatedDeepseek:
    def test_non_deepseek_provider_allows(self):
        result = gate_unvalidated_deepseek("openai", "DIRECT", "PASSED", 2)
        assert result.decision is GateDecision.ALLOW

    def test_deepseek_aggregator_blocks(self):
        result = gate_unvalidated_deepseek("deepseek", "AGGREGATOR", "PASSED", 1)
        assert result.decision is GateDecision.BLOCK

    def test_deepseek_direct_passed_tier1_allows(self):
        result = gate_unvalidated_deepseek("deepseek", "DIRECT", "PASSED", 1)
        assert result.decision is GateDecision.ALLOW

    def test_deepseek_direct_passed_tier3_allows(self):
        result = gate_unvalidated_deepseek("deepseek", "DIRECT", "PASSED", 3)
        assert result.decision is GateDecision.ALLOW

    def test_deepseek_pending_tier0_allows(self):
        result = gate_unvalidated_deepseek("deepseek", "DIRECT", "PENDING", 0)
        assert result.decision is GateDecision.ALLOW

    def test_deepseek_pending_tier1_allows(self):
        result = gate_unvalidated_deepseek("deepseek", "DIRECT", "PENDING", 1)
        assert result.decision is GateDecision.ALLOW

    def test_deepseek_pending_tier2_demotes(self):
        result = gate_unvalidated_deepseek("deepseek", "DIRECT", "PENDING", 2)
        assert result.decision is GateDecision.DEMOTE
        assert result.demote_to_tier == 1

    def test_deepseek_failed_blocks(self):
        result = gate_unvalidated_deepseek("deepseek", "DIRECT", "FAILED", 1)
        assert result.decision is GateDecision.BLOCK

    def test_deepseek_expired_blocks(self):
        result = gate_unvalidated_deepseek("deepseek", "DIRECT", "EXPIRED", 2)
        assert result.decision is GateDecision.BLOCK

    def test_deepseek_not_required_blocks(self):
        result = gate_unvalidated_deepseek("deepseek", "DIRECT", "NOT_REQUIRED", 0)
        assert result.decision is GateDecision.BLOCK


# ---------------------------------------------------------------------------
# Gate 7: Aggregator Authority Gate
# ---------------------------------------------------------------------------


class TestGateAggregatorAuthority:
    def test_direct_api_allows_tier3(self):
        result = gate_aggregator_authority("DIRECT", 3)
        assert result.decision is GateDecision.ALLOW

    def test_aggregator_tier0_allows(self):
        result = gate_aggregator_authority("AGGREGATOR", 0)
        assert result.decision is GateDecision.ALLOW

    def test_aggregator_tier1_allows(self):
        result = gate_aggregator_authority("AGGREGATOR", 1)
        assert result.decision is GateDecision.ALLOW

    def test_aggregator_tier2_without_model_evidence_blocks(self):
        # Tier 2 aggregator requires explicit selected_model_evidence
        result = gate_aggregator_authority("AGGREGATOR", 2, selected_model_evidence=None)
        assert result.decision is GateDecision.BLOCK

    def test_aggregator_tier2_with_empty_model_evidence_blocks(self):
        # Empty string model evidence is not allowed
        result = gate_aggregator_authority("AGGREGATOR", 2, selected_model_evidence="")
        assert result.decision is GateDecision.BLOCK

    def test_aggregator_tier2_with_model_evidence_allows(self):
        # Tier 2 aggregator with explicit selected model evidence allows
        result = gate_aggregator_authority("AGGREGATOR", 2, selected_model_evidence="claude-sonnet-4-6")
        assert result.decision is GateDecision.ALLOW

    def test_aggregator_tier3_blocks(self):
        result = gate_aggregator_authority("AGGREGATOR", 3)
        assert result.decision is GateDecision.BLOCK

    def test_aggregator_tier4_blocks(self):
        result = gate_aggregator_authority("AGGREGATOR", 4)
        assert result.decision is GateDecision.BLOCK

    def test_aggregator_no_proof_blocks_tier0(self):
        result = gate_aggregator_authority("AGGREGATOR", 0, proof_strength="NONE")
        assert result.decision is GateDecision.BLOCK

    def test_aggregator_weak_proof_tier1_allows(self):
        result = gate_aggregator_authority("AGGREGATOR", 1, proof_strength="WEAK")
        assert result.decision is GateDecision.ALLOW


# ---------------------------------------------------------------------------
# Gate 8: Account/Session Risk Gate
# ---------------------------------------------------------------------------


class TestGateAccountSessionRisk:
    def test_non_account_session_allows(self):
        result = gate_account_session_risk("direct_api", "HIGH", "CLEAN", 3)
        assert result.decision is GateDecision.ALLOW

    def test_account_session_clean_low_risk_allows(self):
        result = gate_account_session_risk("account_session", "LOW", "CLEAN", 2)
        assert result.decision is GateDecision.ALLOW

    def test_account_session_clean_standard_risk_allows(self):
        result = gate_account_session_risk("account_session", "STANDARD", "CLEAN", 1)
        assert result.decision is GateDecision.ALLOW

    def test_account_session_polluted_health_blocks(self):
        result = gate_account_session_risk("account_session", "LOW", "POLLUTED", 1)
        assert result.decision is GateDecision.BLOCK

    def test_account_session_stale_health_blocks(self):
        result = gate_account_session_risk("account_session", "LOW", "STALE", 1)
        assert result.decision is GateDecision.BLOCK

    def test_account_session_wrong_project_blocks(self):
        result = gate_account_session_risk("account_session", "LOW", "WRONG_PROJECT", 1)
        assert result.decision is GateDecision.BLOCK

    def test_account_session_unknown_risk_demotes(self):
        result = gate_account_session_risk("account_session", None, "CLEAN", 2)
        assert result.decision is GateDecision.DEMOTE
        assert result.demote_to_tier == 1

    def test_account_session_high_risk_tier1_allows(self):
        result = gate_account_session_risk("account_session", "HIGH", "CLEAN", 1)
        assert result.decision is GateDecision.ALLOW

    def test_account_session_high_risk_tier2_blocks(self):
        result = gate_account_session_risk("account_session", "HIGH", "CLEAN", 2)
        assert result.decision is GateDecision.BLOCK

    def test_account_session_high_risk_tier3_blocks(self):
        result = gate_account_session_risk("account_session", "HIGH", "CLEAN", 3)
        assert result.decision is GateDecision.BLOCK


# ---------------------------------------------------------------------------
# Gate 9: Cost Exposure Gate
# ---------------------------------------------------------------------------


class TestGateCostExposure:
    def test_minimal_cost_allows(self):
        result = gate_cost_exposure("MINIMAL", False, 3)
        assert result.decision is GateDecision.ALLOW

    def test_standard_cost_allows(self):
        result = gate_cost_exposure("STANDARD", False, 2)
        assert result.decision is GateDecision.ALLOW

    def test_premium_cost_justified_tier0_allows(self):
        result = gate_cost_exposure("PREMIUM", True, 0)
        assert result.decision is GateDecision.ALLOW

    def test_premium_cost_justified_tier2_blocks(self):
        # Tier 2+ premium cost requires approval record, not just cost_justified
        result = gate_cost_exposure("PREMIUM", True, 2)
        assert result.decision is GateDecision.BLOCK

    def test_premium_cost_tier0_allows(self):
        result = gate_cost_exposure("PREMIUM", False, 0)
        assert result.decision is GateDecision.ALLOW

    def test_premium_cost_tier1_allows(self):
        result = gate_cost_exposure("PREMIUM", False, 1)
        assert result.decision is GateDecision.ALLOW

    def test_premium_cost_tier2_not_justified_blocks(self):
        result = gate_cost_exposure("PREMIUM", False, 2)
        assert result.decision is GateDecision.BLOCK

    def test_premium_cost_tier3_not_justified_blocks(self):
        result = gate_cost_exposure("PREMIUM", False, 3)
        assert result.decision is GateDecision.BLOCK

    def test_tier4_quota_limited_blocks(self):
        result = gate_cost_exposure("MINIMAL", True, 4, cost_pressure="QUOTA_LIMITED")
        assert result.decision is GateDecision.BLOCK

    def test_tier4_quota_exhausted_blocks(self):
        result = gate_cost_exposure("MINIMAL", True, 4, cost_pressure="EXHAUSTED")
        assert result.decision is GateDecision.BLOCK

    def test_tier4_no_cost_pressure_allows(self):
        result = gate_cost_exposure("STANDARD", True, 4, cost_pressure=None)
        assert result.decision is GateDecision.ALLOW

    def test_premium_cost_tier2_without_approval_blocks(self):
        # Premium cost requires valid approval record for Tier 2+
        result = gate_cost_exposure("PREMIUM", False, 2, approval_record=None)
        assert result.decision is GateDecision.BLOCK

    def test_premium_cost_tier2_with_valid_approval_allows(self):
        approval = ApprovalRecord(
            approval_id="app-001",
            actor="user@example.com",
            scope="premium_cost_tier2",
            timestamp="2026-06-13T16:30:00Z",
            reason="User approved premium model for faster inference",
        )
        result = gate_cost_exposure("PREMIUM", False, 2, approval_record=approval)
        assert result.decision is GateDecision.ALLOW

    def test_premium_cost_tier3_with_valid_approval_allows(self):
        approval = ApprovalRecord(
            approval_id="app-002",
            actor="scott@example.com",
            scope="premium_cost_tier3",
            timestamp="2026-06-13T16:35:00Z",
            reason="User approved premium route for critical task",
        )
        result = gate_cost_exposure("PREMIUM", False, 3, approval_record=approval)
        assert result.decision is GateDecision.ALLOW

    def test_premium_cost_tier2_with_invalid_approval_blocks(self):
        # Approval missing required fields
        approval = ApprovalRecord(
            approval_id="app-003",
            actor="",  # empty actor
            scope="premium_cost_tier2",
            timestamp="2026-06-13T16:40:00Z",
            reason="Incomplete approval",
        )
        result = gate_cost_exposure("PREMIUM", False, 2, approval_record=approval)
        assert result.decision is GateDecision.BLOCK


# ---------------------------------------------------------------------------
# Gate Summary Helpers Tests
# ---------------------------------------------------------------------------


class TestGateSummaryHelpers:
    """Tests for Aegis gate summary helpers for Relay/Bifrost display."""

    def test_summarize_allow_gate_result(self):
        """Gate summary for ALLOW decision includes correct fields."""
        result = GateResult(
            gate_name="unknown_route_class",
            decision=GateDecision.ALLOW,
            reason="route_class valid: 'direct_api'",
        )
        summary = summarize_gate_result(result)
        assert summary.gate_id == "unknown_route_class"
        assert summary.gate_label == "Route Class Validation"
        assert summary.decision == "allow"
        assert summary.severity == "info"
        assert summary.reason == "route_class valid: 'direct_api'"
        assert summary.required_evidence == "route metadata"
        assert summary.waiver_approval_status == "none"
        assert summary.downstream_action == "route_allowed"

    def test_summarize_demote_gate_result(self):
        """Gate summary for DEMOTE decision shows demotion tier."""
        result = GateResult(
            gate_name="tier3_dual_lane_requirement",
            decision=GateDecision.DEMOTE,
            reason="Tier 3 without dual-lane; valid waiver permits demotion",
            demote_to_tier=2,
        )
        summary = summarize_gate_result(result)
        assert summary.decision == "demote"
        assert summary.severity == "warning"
        assert summary.waiver_approval_status == "waiver_present"
        assert summary.downstream_action == "route_demoted_to_tier_2"

    def test_summarize_block_gate_result(self):
        """Gate summary for BLOCK decision indicates error severity."""
        result = GateResult(
            gate_name="missing_exact_model_id",
            decision=GateDecision.BLOCK,
            reason="Tier 2: exact model ID required; got None",
        )
        summary = summarize_gate_result(result)
        assert summary.decision == "block"
        assert summary.severity == "error"
        assert summary.downstream_action == "route_blocked"

    def test_summarize_multiple_gate_results(self):
        """summarize_gate_results handles multiple results in order."""
        results = [
            GateResult(
                gate_name="unknown_route_class",
                decision=GateDecision.ALLOW,
                reason="route_class valid",
            ),
            GateResult(
                gate_name="missing_exact_model_id",
                decision=GateDecision.ALLOW,
                reason="model_id exact",
            ),
            GateResult(
                gate_name="cost_exposure",
                decision=GateDecision.BLOCK,
                reason="premium cost requires approval",
            ),
        ]
        summaries = summarize_gate_results(results)
        assert len(summaries) == 3
        assert summaries[0].gate_id == "unknown_route_class"
        assert summaries[1].gate_id == "missing_exact_model_id"
        assert summaries[2].gate_id == "cost_exposure"

    def test_summarize_deepseek_gate_with_valid_approval(self):
        """DeepSeek gate summary shows approval status from reason."""
        result = GateResult(
            gate_name="unvalidated_deepseek",
            decision=GateDecision.ALLOW,
            reason="DeepSeek validation approved by user (approval_id=app-001)",
        )
        summary = summarize_gate_result(result)
        assert summary.gate_label == "DeepSeek Validation"
        assert summary.waiver_approval_status == "approval_present"
        assert summary.required_evidence == "external review status"

    def test_format_gate_summary_for_display(self):
        """Gate summary can be formatted for human-readable display."""
        result = GateResult(
            gate_name="unknown_route_class",
            decision=GateDecision.ALLOW,
            reason="route_class valid: 'direct_api'",
        )
        summary = summarize_gate_result(result)
        display = format_gate_summary_for_display(summary)
        assert "Route Class Validation" in display
        assert "ALLOW" in display
        assert "severity=info" in display
        assert "route metadata" in display
        assert "route_allowed" in display

    def test_gate_metadata_coverage(self):
        """All 9 gate validators have metadata entries."""
        gate_names = [
            "unknown_route_class",
            "missing_exact_model_id",
            "tier3_dual_lane_requirement",
            "unknown_proof_requirement",
            "unsafe_fallback",
            "unvalidated_deepseek",
            "aggregator_authority",
            "account_session_risk",
            "cost_exposure",
        ]
        for gate_name in gate_names:
            result = GateResult(gate_name=gate_name, decision=GateDecision.ALLOW)
            summary = summarize_gate_result(result)
            assert summary.gate_id == gate_name
            assert summary.gate_label  # Should have a label
            assert summary.required_evidence  # Should have proof type

    def test_unknown_gate_has_fallback_metadata(self):
        """Unknown gate names fall back to generated metadata."""
        result = GateResult(
            gate_name="future_gate_not_yet_defined",
            decision=GateDecision.ALLOW,
        )
        summary = summarize_gate_result(result)
        assert summary.gate_label == "Future Gate Not Yet Defined"
        assert summary.required_evidence == "gate-specific evidence"


# ---------------------------------------------------------------------------
# Aggregate Route-Gate Summary Tests
# ---------------------------------------------------------------------------


class TestAggregateGateSummary:
    """Tests for aggregate multi-gate route summary functions."""

    def test_empty_summaries_returns_default_aggregate(self):
        """Empty gate list produces neutral aggregate."""
        aggregate = summarize_aggregate_route_gates([])
        assert aggregate.gate_count == 0
        assert aggregate.highest_severity == "info"
        assert aggregate.aggregate_action == "route_allowed"
        assert aggregate.blocked_gates == []
        assert aggregate.demoted_gates == []
        assert aggregate.allowed_gates == []

    def test_all_allow_gates_produces_allow_aggregate(self):
        """All ALLOW gates produce route_allowed action."""
        summaries = [
            GateSummary(
                gate_id="unknown_route_class",
                gate_label="Route Class",
                decision="allow",
                severity="info",
                reason="Valid",
                required_evidence="metadata",
                waiver_approval_status="none",
                downstream_action="route_allowed",
            ),
            GateSummary(
                gate_id="missing_exact_model_id",
                gate_label="Model ID",
                decision="allow",
                severity="info",
                reason="Valid",
                required_evidence="version",
                waiver_approval_status="none",
                downstream_action="route_allowed",
            ),
        ]
        aggregate = summarize_aggregate_route_gates(summaries)
        assert aggregate.gate_count == 2
        assert aggregate.highest_severity == "info"
        assert aggregate.aggregate_action == "route_allowed"
        assert aggregate.allowed_gates == ["unknown_route_class", "missing_exact_model_id"]
        assert aggregate.blocked_gates == []
        assert aggregate.demoted_gates == []

    def test_single_block_produces_blocked_aggregate(self):
        """Single BLOCK gate overrides ALLOW gates."""
        summaries = [
            GateSummary(
                gate_id="unknown_route_class",
                gate_label="Route Class",
                decision="allow",
                severity="info",
                reason="Valid",
                required_evidence="metadata",
                waiver_approval_status="none",
                downstream_action="route_allowed",
            ),
            GateSummary(
                gate_id="missing_exact_model_id",
                gate_label="Model ID",
                decision="block",
                severity="error",
                reason="Missing",
                required_evidence="version",
                waiver_approval_status="none",
                downstream_action="route_blocked",
            ),
        ]
        aggregate = summarize_aggregate_route_gates(summaries)
        assert aggregate.aggregate_action == "route_blocked"
        assert aggregate.highest_severity == "error"
        assert "missing_exact_model_id" in aggregate.blocked_gates
        assert "unknown_route_class" in aggregate.allowed_gates

    def test_demote_preserves_lowest_tier(self):
        """Multiple demotions keep lowest tier."""
        summaries = [
            GateSummary(
                gate_id="gate1",
                gate_label="Gate 1",
                decision="demote",
                severity="warning",
                reason="Demote",
                required_evidence="proof",
                waiver_approval_status="none",
                downstream_action="route_demoted_to_tier_3",
            ),
            GateSummary(
                gate_id="gate2",
                gate_label="Gate 2",
                decision="demote",
                severity="warning",
                reason="Demote",
                required_evidence="proof",
                waiver_approval_status="none",
                downstream_action="route_demoted_to_tier_2",
            ),
        ]
        aggregate = summarize_aggregate_route_gates(summaries)
        assert aggregate.aggregate_action == "route_demoted_to_tier_2"
        assert aggregate.highest_severity == "warning"

    def test_evidence_aggregation_combines_requirements(self):
        """Evidence requirements are combined across gates."""
        summaries = [
            GateSummary(
                gate_id="gate1",
                gate_label="Gate 1",
                decision="allow",
                severity="info",
                reason="OK",
                required_evidence="proof_type_1",
                waiver_approval_status="none",
                downstream_action="route_allowed",
            ),
            GateSummary(
                gate_id="gate2",
                gate_label="Gate 2",
                decision="allow",
                severity="info",
                reason="OK",
                required_evidence="proof_type_2",
                waiver_approval_status="waiver_present",
                downstream_action="route_allowed",
            ),
        ]
        aggregate = summarize_aggregate_route_gates(summaries)
        assert len(aggregate.evidence_required) == 2
        assert "gate1: proof_type_1" in aggregate.evidence_required
        assert "gate2: proof_type_2" in aggregate.evidence_required
        assert "gate2" in aggregate.waivers_present

    def test_waiver_and_approval_status_tracking(self):
        """Waivers and approvals are tracked across gates."""
        summaries = [
            GateSummary(
                gate_id="tier3_gate",
                gate_label="Tier 3",
                decision="demote",
                severity="warning",
                reason="Waived",
                required_evidence="proof",
                waiver_approval_status="waiver_present",
                downstream_action="route_demoted_to_tier_2",
            ),
            GateSummary(
                gate_id="cost_gate",
                gate_label="Cost",
                decision="allow",
                severity="info",
                reason="Approved",
                required_evidence="approval",
                waiver_approval_status="approval_present",
                downstream_action="route_allowed",
            ),
        ]
        aggregate = summarize_aggregate_route_gates(summaries)
        assert "tier3_gate" in aggregate.waivers_present
        assert "cost_gate" in aggregate.approvals_present

    def test_format_aggregate_summary_for_display(self):
        """Aggregate summary can be formatted for display."""
        summaries = [
            GateSummary(
                gate_id="route_class",
                gate_label="Route Class",
                decision="allow",
                severity="info",
                reason="Valid",
                required_evidence="metadata",
                waiver_approval_status="none",
                downstream_action="route_allowed",
            ),
            GateSummary(
                gate_id="model_id",
                gate_label="Model ID",
                decision="block",
                severity="error",
                reason="Missing",
                required_evidence="version",
                waiver_approval_status="none",
                downstream_action="route_blocked",
            ),
        ]
        aggregate = summarize_aggregate_route_gates(summaries)
        display = format_aggregate_summary_for_display(aggregate)
        assert "Route-Gate Aggregate Summary" in display
        assert "2 gates" in display
        assert "highest severity: error" in display
        assert "aggregate action: route_blocked" in display
        assert "blocked gates" in display
        assert "model_id" in display

    def test_aggregate_deterministic_ordering(self):
        """Aggregate summary maintains deterministic gate ordering."""
        summaries = [
            GateSummary(
                gate_id="gate_a",
                gate_label="A",
                decision="allow",
                severity="info",
                reason="OK",
                required_evidence="proof",
                waiver_approval_status="none",
                downstream_action="route_allowed",
            ),
            GateSummary(
                gate_id="gate_b",
                gate_label="B",
                decision="allow",
                severity="info",
                reason="OK",
                required_evidence="proof",
                waiver_approval_status="none",
                downstream_action="route_allowed",
            ),
        ]
        aggregate = summarize_aggregate_route_gates(summaries)
        assert aggregate.gate_details[0].gate_id == "gate_a"
        assert aggregate.gate_details[1].gate_id == "gate_b"
        assert len(aggregate.gate_details) == 2


# ---------------------------------------------------------------------------
# Prompt Payload Meter Advisory
# ---------------------------------------------------------------------------


class TestPromptPayloadMeterAdvisory:
    def test_valid_prompt_payload_meter_metadata_allows(self):
        result = evaluate_prompt_payload_meter_advisory(_prompt_payload_meter_metadata())
        assert result.decision is PromptPayloadMeterDecision.ALLOW
        assert result.severity == "info"
        assert result.blockers == ()
        assert result.warnings == ()
        assert result.route_continuity_refs == (
            "provider:deepseek",
            "model:deepseek-chat",
            "route:direct",
        )

    def test_budget_watch_warns_without_blocking(self):
        result = evaluate_prompt_payload_meter_advisory(
            _prompt_payload_meter_metadata(budget_percent=94.25)
        )
        assert result.decision is PromptPayloadMeterDecision.WARN
        assert result.warnings == ("prompt_payload_budget_watch",)
        assert result.blockers == ()

    def test_over_budget_label_blocks_fail_closed(self):
        result = evaluate_prompt_payload_meter_advisory(
            _prompt_payload_meter_metadata(
                label_bucket="over_budget",
                budget_percent=121.0,
                payload_status="over_budget",
            )
        )
        assert result.decision is PromptPayloadMeterDecision.BLOCK
        assert "prompt_payload_label_over_budget" in result.blockers
        assert "prompt_payload_budget_over_limit" in result.blockers
        assert "prompt_payload_over_budget" in result.blockers

    def test_unknown_payload_status_blocks_fail_closed(self):
        result = evaluate_prompt_payload_meter_advisory(
            _prompt_payload_meter_metadata(payload_status="mystery")
        )
        assert result.decision is PromptPayloadMeterDecision.BLOCK
        assert "unknown_prompt_payload_status" in result.blockers

    def test_q_mode_degraded_blocks_fail_closed(self):
        result = evaluate_prompt_payload_meter_advisory(
            _prompt_payload_meter_metadata(q_mode_prompt_drag_state="degraded")
        )
        assert result.decision is PromptPayloadMeterDecision.BLOCK
        assert "q_mode_prompt_drag_degraded" in result.blockers

    def test_positive_growth_without_expected_state_blocks(self):
        result = evaluate_prompt_payload_meter_advisory(
            _prompt_payload_meter_metadata(
                growth_delta_tokens=200,
                q_mode_prompt_drag_state="flat",
            )
        )
        assert result.decision is PromptPayloadMeterDecision.BLOCK
        assert "prompt_payload_growth_unexplained" in result.blockers

    def test_expected_positive_growth_allows_when_other_fields_valid(self):
        result = evaluate_prompt_payload_meter_advisory(
            _prompt_payload_meter_metadata(
                growth_delta_tokens=200,
                q_mode_prompt_drag_state="growing_expected",
            )
        )
        assert result.decision is PromptPayloadMeterDecision.ALLOW

    def test_missing_route_continuity_refs_block(self):
        result = evaluate_prompt_payload_meter_advisory(
            _prompt_payload_meter_metadata(route_continuity_refs=())
        )
        assert result.decision is PromptPayloadMeterDecision.BLOCK
        assert "missing_route_continuity_refs" in result.blockers

    def test_missing_evidence_refs_block(self):
        result = evaluate_prompt_payload_meter_advisory(
            _prompt_payload_meter_metadata(evidence_refs=())
        )
        assert result.decision is PromptPayloadMeterDecision.BLOCK
        assert "missing_prompt_payload_meter_evidence_refs" in result.blockers

    def test_blocker_tags_block_and_warning_tags_warn(self):
        result = evaluate_prompt_payload_meter_advisory(
            _prompt_payload_meter_metadata(
                blocker_tags=("route_model_mismatch",),
                warning_tags=("prompt_payload_meter_watch",),
            )
        )
        assert result.decision is PromptPayloadMeterDecision.BLOCK
        assert result.blockers == ("route_model_mismatch",)
        assert result.warnings == ("prompt_payload_meter_watch",)

    def test_prompt_payload_meter_advisory_has_stable_keys(self):
        result = evaluate_prompt_payload_meter_advisory(_prompt_payload_meter_metadata())
        display = serialize_prompt_payload_meter_policy_result(result)
        assert tuple(display.keys()) == (
            "decision",
            "severity",
            "reason",
            "label_bucket",
            "budget_percent",
            "growth_delta_tokens",
            "payload_status",
            "q_mode_prompt_drag_state",
            "route_continuity_refs",
            "evidence_refs",
            "blockers",
            "warnings",
            "reason_tags",
            "relay_advisory",
            "bifrost_advisory",
        )

    def test_prompt_payload_meter_to_advisory_dict_matches_helper(self):
        result = evaluate_prompt_payload_meter_advisory(_prompt_payload_meter_metadata())
        assert result.to_advisory_dict() == serialize_prompt_payload_meter_policy_result(
            result
        )

    def test_prompt_payload_meter_advisory_serializes_allow_state(self):
        result = evaluate_prompt_payload_meter_advisory(_prompt_payload_meter_metadata())
        display = result.to_advisory_dict()
        assert display["decision"] == "allow"
        assert display["severity"] == "info"
        assert display["label_bucket"] == "under-1k"
        assert display["budget_percent"] == 24.5
        assert display["growth_delta_tokens"] == 0
        assert display["payload_status"] == "ok"
        assert display["q_mode_prompt_drag_state"] == "flat"
        assert display["reason_tags"] == ("prompt_payload_meter_allowed",)
        assert display["relay_advisory"] == "allow"
        assert display["bifrost_advisory"] == "display_allowed"

    def test_prompt_payload_meter_advisory_redacts_unsafe_strings(self):
        result = PromptPayloadMeterPolicyResult(
            decision=PromptPayloadMeterDecision.BLOCK,
            severity="error",
            reason="raw_prompt: do not show this",
            label_bucket="under-1k",
            budget_percent=50.0,
            growth_delta_tokens=0,
            payload_status="blocked",
            q_mode_prompt_drag_state="blocked",
            route_continuity_refs=("provider:deepseek", "provider_response:raw"),
            evidence_refs=("payload:safe", "account_id=abc"),
            blockers=("raw_provider_response", "missing_route_continuity_refs"),
            warnings=("process_id=123",),
        )
        display = result.to_advisory_dict()
        assert display["reason"] == "[redacted]"
        assert display["route_continuity_refs"] == ("provider:deepseek", "[redacted]")
        assert display["evidence_refs"] == ("payload:safe", "[redacted]")
        assert display["blockers"] == ("[redacted]", "missing_route_continuity_refs")
        assert display["warnings"] == ("[redacted]",)
        assert display["reason_tags"] == ("[redacted]", "missing_route_continuity_refs")

    def test_prompt_payload_meter_policy_is_deterministic(self):
        metadata = _prompt_payload_meter_metadata(
            label_bucket="over_budget",
            budget_percent=140.0,
            payload_status="over_budget",
            q_mode_prompt_drag_state="degraded",
            blocker_tags=("route_model_mismatch",),
            warning_tags=("prompt_payload_meter_watch",),
        )
        first = evaluate_prompt_payload_meter_advisory(metadata)
        second = evaluate_prompt_payload_meter_advisory(metadata)
        assert first == second
        assert first.to_advisory_dict() == second.to_advisory_dict()

    def test_unsafe_meter_inputs_fail_closed_without_exposing_raw_strings(self):
        result = evaluate_prompt_payload_meter_advisory(
            _prompt_payload_meter_metadata(
                route_continuity_refs=("provider_response:raw",),
                evidence_refs=("raw_prompt:leak",),
                blocker_tags=("account_id=abc",),
                warning_tags=("process_id=123",),
            )
        )
        display = result.to_advisory_dict()
        assert result.decision is PromptPayloadMeterDecision.BLOCK
        assert "unsafe_route_continuity_ref" in result.blockers
        assert "unsafe_prompt_payload_meter_evidence_ref" in result.blockers
        assert "unsafe_prompt_payload_meter_blocker_tag" in result.blockers
        assert "unsafe_prompt_payload_meter_warning_tag" in result.warnings
        assert display["route_continuity_refs"] == ("[redacted]",)
        assert display["evidence_refs"] == ("[redacted]",)


# ---------------------------------------------------------------------------
# Provider Result Validation Advisory
# ---------------------------------------------------------------------------


class TestProviderResultValidationAdvisory:
    def test_valid_provider_result_metadata_allows(self):
        result = evaluate_provider_result_validation_advisory(_provider_result_metadata())
        assert result.decision is ProviderResultValidationDecision.ALLOW
        assert result.severity == "info"
        assert result.blockers == ()
        assert result.warnings == ()
        assert result.evidence_refs == (
            "result:relay-dispatch-001",
            "proof:direct-provider-route",
            "budget:prompt-drag-ok",
        )

    def test_warning_status_warns_with_tags(self):
        result = evaluate_provider_result_validation_advisory(
            _provider_result_metadata(
                validation_status="warning",
                warning_tags=("response_hash_unavailable",),
            )
        )
        assert result.decision is ProviderResultValidationDecision.WARN
        assert result.severity == "warning"
        assert result.warnings == ("response_hash_unavailable",)

    def test_missing_telemetry_warns_without_blocking_valid_result(self):
        result = evaluate_provider_result_validation_advisory(
            _provider_result_metadata(telemetry_available=False)
        )
        assert result.decision is ProviderResultValidationDecision.WARN
        assert result.blockers == ()
        assert result.warnings == ("provider_result_telemetry_unavailable",)

    def test_unknown_validation_status_blocks_fail_closed(self):
        result = evaluate_provider_result_validation_advisory(
            _provider_result_metadata(validation_status="maybe")
        )
        assert result.decision is ProviderResultValidationDecision.BLOCK
        assert "unknown_validation_status" in result.blockers

    def test_blocker_tags_block_fail_closed(self):
        result = evaluate_provider_result_validation_advisory(
            _provider_result_metadata(blocker_tags=("result_model_id_mismatch",))
        )
        assert result.decision is ProviderResultValidationDecision.BLOCK
        assert result.blockers == ("result_model_id_mismatch",)

    def test_missing_evidence_refs_block_fail_closed(self):
        result = evaluate_provider_result_validation_advisory(
            _provider_result_metadata(evidence_refs=())
        )
        assert result.decision is ProviderResultValidationDecision.BLOCK
        assert "missing_provider_result_evidence_refs" in result.blockers

    def test_pending_external_review_blocks_fail_closed(self):
        result = evaluate_provider_result_validation_advisory(
            _provider_result_metadata(external_review_state="pending")
        )
        assert result.decision is ProviderResultValidationDecision.BLOCK
        assert "external_review_pending" in result.blockers

    def test_provider_result_advisory_has_stable_keys(self):
        result = evaluate_provider_result_validation_advisory(_provider_result_metadata())
        display = serialize_provider_result_validation_policy_result(result)
        assert tuple(display.keys()) == (
            "decision",
            "severity",
            "reason",
            "validation_status",
            "external_review_state",
            "telemetry_available",
            "evidence_refs",
            "blockers",
            "warnings",
            "reason_tags",
            "relay_advisory",
            "bifrost_advisory",
        )

    def test_provider_result_to_advisory_dict_matches_helper(self):
        result = evaluate_provider_result_validation_advisory(_provider_result_metadata())
        assert result.to_advisory_dict() == serialize_provider_result_validation_policy_result(
            result
        )

    def test_provider_result_advisory_serializes_allow_state(self):
        result = evaluate_provider_result_validation_advisory(_provider_result_metadata())
        display = result.to_advisory_dict()
        assert display["decision"] == "allow"
        assert display["severity"] == "info"
        assert display["validation_status"] == "valid"
        assert display["external_review_state"] == "not_required"
        assert display["telemetry_available"] is True
        assert display["reason_tags"] == ("provider_result_allowed",)
        assert display["relay_advisory"] == "allow"
        assert display["bifrost_advisory"] == "display_allowed"

    def test_provider_result_advisory_redacts_unsafe_strings(self):
        result = ProviderResultValidationPolicyResult(
            decision=ProviderResultValidationDecision.BLOCK,
            severity="error",
            reason="raw_response: do not show this",
            validation_status="invalid",
            external_review_state="failed",
            telemetry_available=False,
            evidence_refs=("result:safe", "provider_response:raw"),
            blockers=("raw_prompt:leak", "missing_provider_result_evidence_refs"),
            warnings=("account_id=abc",),
        )
        display = result.to_advisory_dict()
        assert display["reason"] == "[redacted]"
        assert display["evidence_refs"] == ("result:safe", "[redacted]")
        assert display["blockers"] == ("[redacted]", "missing_provider_result_evidence_refs")
        assert display["warnings"] == ("[redacted]",)
        assert display["reason_tags"] == ("[redacted]", "missing_provider_result_evidence_refs")

    def test_provider_result_policy_is_deterministic(self):
        metadata = _provider_result_metadata(
            validation_status="warning",
            warning_tags=("response_hash_unavailable",),
            telemetry_available=False,
        )
        first = evaluate_provider_result_validation_advisory(metadata)
        second = evaluate_provider_result_validation_advisory(metadata)
        assert first == second
        assert first.to_advisory_dict() == second.to_advisory_dict()

    def test_unsafe_inputs_fail_closed_without_exposing_raw_strings(self):
        result = evaluate_provider_result_validation_advisory(
            _provider_result_metadata(
                evidence_refs=("provider_response:raw",),
                blocker_tags=("raw_prompt:leak",),
                warning_tags=("account_id=abc",),
            )
        )
        display = result.to_advisory_dict()
        assert result.decision is ProviderResultValidationDecision.BLOCK
        assert "unsafe_provider_result_evidence_ref" in result.blockers
        assert "unsafe_provider_result_blocker_tag" in result.blockers
        assert "unsafe_provider_result_warning_tag" in result.warnings
        assert "[redacted]" in display["evidence_refs"]
        assert "[redacted]" not in display["validation_status"]


# ---------------------------------------------------------------------------
# PromptPacket Proof Policy Evaluator
# ---------------------------------------------------------------------------


class TestPromptPacketProofPolicyEvaluator:
    def test_valid_prompt_packet_metadata_allows(self):
        result = evaluate_prompt_packet_proof_policy(_prompt_packet_metadata())
        assert result.decision is PromptPacketProofDecision.ALLOW
        assert result.severity == "info"
        assert result.blockers == ()
        assert result.evidence_ids == (
            "packet:packet-relay-001",
            "budget:budget-tier2-default",
            "source:direct-input",
        )

    def test_missing_packet_id_blocks(self):
        result = evaluate_prompt_packet_proof_policy(_prompt_packet_metadata(packet_id=""))
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "missing_packet_id" in result.blockers

    def test_missing_required_packet_hash_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(packet_hash_status="missing", packet_hash=None)
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "packet_hash_missing" in result.blockers

    def test_hash_unavailable_warns_for_tier1(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                packet_hash_status="unavailable",
                packet_hash=None,
                risk_tier=1,
                proof_requirement="telemetry",
            )
        )
        assert result.decision is PromptPacketProofDecision.WARN
        assert result.severity == "warning"
        assert "packet_hash_unavailable" in result.warnings

    def test_hash_unavailable_demotes_for_tier2(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                packet_hash_status="unavailable",
                packet_hash=None,
                risk_tier=2,
                demotion_target_tier=1,
            )
        )
        assert result.decision is PromptPacketProofDecision.DEMOTE
        assert result.demote_to_tier == 1
        assert "packet_hash_unavailable_demote" in result.warnings

    def test_hash_unavailable_blocks_for_tier3(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                packet_hash_status="unavailable",
                packet_hash=None,
                risk_tier=3,
            )
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "packet_hash_required_unavailable" in result.blockers

    def test_over_budget_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(prompt_tokens=3000, max_context_tokens=2048)
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "prompt_packet_over_budget" in result.blockers

    def test_missing_budget_ref_blocks(self):
        result = evaluate_prompt_packet_proof_policy(_prompt_packet_metadata(budget_ref=""))
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "missing_budget_ref" in result.blockers

    def test_disallowed_source_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                source_lineage={"direct_input": 256, "unapproved_memory": 10},
                allowed_sources=("direct_input",),
            )
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "disallowed_source:unapproved_memory" in result.blockers

    def test_negative_source_lineage_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(source_lineage={"direct_input": -1})
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "invalid_source_lineage:direct_input" in result.blockers

    def test_source_lineage_total_above_prompt_tokens_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                prompt_tokens=100,
                source_lineage={"direct_input": 80, "atlas_retrieval": 30},
            )
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "source_lineage_exceeds_prompt_tokens" in result.blockers

    def test_empty_source_lineage_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(source_lineage={})
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "missing_source_lineage" in result.blockers

    def test_missing_allowed_sources_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(allowed_sources=())
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "missing_allowed_sources" in result.blockers

    def test_blank_source_lineage_key_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(source_lineage={"": 10})
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "invalid_source_lineage_key" in result.blockers

    def test_missing_evidence_ids_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(aegis_evidence_ids=())
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "missing_aegis_evidence_ids" in result.blockers

    def test_duplicate_evidence_ids_block(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(aegis_evidence_ids=("packet:one", "packet:one"))
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "duplicate_aegis_evidence_ids" in result.blockers

    def test_unsafe_evidence_id_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(aegis_evidence_ids=("packet:one", "raw_prompt:hello"))
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "unsafe_aegis_evidence_id" in result.blockers

    def test_secret_like_evidence_id_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(aegis_evidence_ids=("packet:one", "token=abc123"))
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "unsafe_aegis_evidence_id" in result.blockers

    def test_missing_proof_requirement_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(proof_requirement="")
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "missing_proof_requirement" in result.blockers

    def test_unknown_proof_requirement_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(proof_requirement="mystery_proof")
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "unknown_proof_requirement" in result.blockers

    def test_human_gate_proof_requirement_conflict_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                proof_requirement="human_gate",
                human_gate_required=False,
                human_approval_present=False,
            )
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "human_gate_requirement_conflict" in result.blockers

    def test_human_approval_without_gate_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                proof_requirement="artifact",
                human_gate_required=False,
                human_approval_present=True,
            )
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "human_approval_without_gate" in result.blockers

    def test_dual_review_requirement_without_dual_lane_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                proof_requirement="dual_review",
                dual_lane_required=False,
                dual_lane_proof_present=False,
            )
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "dual_lane_requirement_conflict" in result.blockers

    def test_dual_lane_proof_without_requirement_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                proof_requirement="artifact",
                dual_lane_required=False,
                dual_lane_proof_present=True,
            )
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "dual_lane_proof_without_requirement" in result.blockers

    def test_missing_direct_provider_snapshot_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                snapshot_requirement="direct_provider",
                snapshot_status="missing",
            )
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "snapshot_missing" in result.blockers

    def test_snapshot_unavailable_warns_for_tier1(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                risk_tier=1,
                snapshot_requirement="aggregator",
                snapshot_status="unavailable",
            )
        )
        assert result.decision is PromptPacketProofDecision.WARN
        assert "snapshot_unavailable" in result.warnings

    def test_snapshot_unavailable_blocks_for_tier2(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                risk_tier=2,
                snapshot_requirement="aggregator",
                snapshot_status="unavailable",
            )
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "snapshot_unavailable_for_tier" in result.blockers

    def test_hash_unavailable_tier2_without_demotion_target_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                packet_hash_status="unavailable",
                packet_hash=None,
                risk_tier=2,
                demotion_target_tier=None,
            )
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "missing_demotion_target" in result.blockers
        assert "packet_hash_unavailable_demote" in result.warnings

    def test_hash_unavailable_tier2_invalid_demotion_target_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                packet_hash_status="unavailable",
                packet_hash=None,
                risk_tier=2,
                demotion_target_tier=2,
            )
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "invalid_demotion_target" in result.blockers
        assert "packet_hash_unavailable_demote" in result.warnings

    def test_human_gate_result_when_approval_missing_and_packet_valid(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                risk_tier=4,
                proof_requirement="human_gate",
                human_gate_required=True,
                human_approval_present=False,
            )
        )
        assert result.decision is PromptPacketProofDecision.HUMAN_GATE
        assert result.severity == "warning"
        assert result.blockers == ()

    def test_human_gate_invalid_packet_blocks_before_gate(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                packet_id=None,
                risk_tier=4,
                human_gate_required=True,
                human_approval_present=False,
            )
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "missing_packet_id" in result.blockers

    def test_human_gate_with_approval_allows_when_packet_valid(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                risk_tier=4,
                proof_requirement="human_gate",
                human_gate_required=True,
                human_approval_present=True,
            )
        )
        assert result.decision is PromptPacketProofDecision.ALLOW

    def test_dual_lane_missing_proof_blocks(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                risk_tier=3,
                dual_lane_required=True,
                dual_lane_proof_present=False,
            )
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "dual_lane_proof_missing" in result.blockers

    def test_dual_lane_with_proof_allows_when_packet_valid(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                risk_tier=3,
                dual_lane_required=True,
                dual_lane_proof_present=True,
            )
        )
        assert result.decision is PromptPacketProofDecision.ALLOW

    def test_candidate_model_trust_blocks_high_tier(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(risk_tier=3, model_trust_state="candidate")
        )
        assert result.decision is PromptPacketProofDecision.BLOCK
        assert "candidate_model_trust_for_high_tier" in result.blockers

    def test_policy_result_is_deterministic(self):
        metadata = _prompt_packet_metadata(
            packet_hash_status="unavailable",
            packet_hash=None,
            risk_tier=2,
        )
        first = evaluate_prompt_packet_proof_policy(metadata)
        second = evaluate_prompt_packet_proof_policy(metadata)
        assert first == second

    def test_blocker_tags_are_deterministic_for_relay_edge_inputs(self):
        metadata = _prompt_packet_metadata(
            packet_id="",
            packet_hash_status="missing",
            packet_hash=None,
            source_lineage={},
            allowed_sources=(),
            proof_requirement="mystery_proof",
            aegis_evidence_ids=("raw_prompt:leak", "raw_prompt:leak"),
        )
        first = evaluate_prompt_packet_proof_policy(metadata)
        second = evaluate_prompt_packet_proof_policy(metadata)
        assert first == second
        assert first.blockers == (
            "missing_packet_id",
            "packet_hash_missing",
            "missing_allowed_sources",
            "missing_source_lineage",
            "duplicate_aegis_evidence_ids",
            "unsafe_aegis_evidence_id",
            "unknown_proof_requirement",
        )

    def test_policy_result_display_dict_has_stable_keys(self):
        result = evaluate_prompt_packet_proof_policy(_prompt_packet_metadata())
        display = serialize_prompt_packet_policy_result(result)
        assert tuple(display.keys()) == (
            "decision",
            "severity",
            "reason",
            "evidence_ids",
            "blockers",
            "warnings",
            "missing_fields",
            "reason_tags",
            "demote_to_tier",
        )

    def test_policy_result_to_display_dict_matches_helper(self):
        result = evaluate_prompt_packet_proof_policy(_prompt_packet_metadata())
        assert result.to_display_dict() == serialize_prompt_packet_policy_result(result)

    def test_policy_result_display_dict_serializes_allow_state(self):
        result = evaluate_prompt_packet_proof_policy(_prompt_packet_metadata())
        display = result.to_display_dict()
        assert display["decision"] == "allow"
        assert display["severity"] == "info"
        assert display["reason"] == "PromptPacket proof metadata satisfies Aegis policy"
        assert display["evidence_ids"] == (
            "packet:packet-relay-001",
            "budget:budget-tier2-default",
            "source:direct-input",
        )
        assert display["blockers"] == ()
        assert display["warnings"] == ()
        assert display["missing_fields"] == ()
        assert display["reason_tags"] == ("policy_allowed",)
        assert display["demote_to_tier"] is None

    def test_policy_result_display_dict_preserves_warning_tags(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                packet_hash_status="unavailable",
                packet_hash=None,
                risk_tier=1,
            )
        )
        display = result.to_display_dict()
        assert display["decision"] == "warn"
        assert display["warnings"] == ("packet_hash_unavailable",)
        assert display["reason_tags"] == ("packet_hash_unavailable",)

    def test_policy_result_display_dict_preserves_demotion_target(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                packet_hash_status="unavailable",
                packet_hash=None,
                risk_tier=2,
                demotion_target_tier=1,
            )
        )
        display = result.to_display_dict()
        assert display["decision"] == "demote"
        assert display["warnings"] == ("packet_hash_unavailable_demote",)
        assert display["reason_tags"] == ("packet_hash_unavailable_demote",)
        assert display["demote_to_tier"] == 1

    def test_policy_result_display_dict_derives_missing_fields(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                packet_id="",
                packet_hash_status="missing",
                packet_hash=None,
                source_lineage={},
                allowed_sources=(),
                budget_ref="",
                aegis_evidence_ids=(),
            )
        )
        display = result.to_display_dict()
        assert display["decision"] == "block"
        assert display["missing_fields"] == (
            "packet_id",
            "packet_hash",
            "budget_ref",
            "allowed_sources",
            "source_lineage",
            "aegis_evidence_ids",
        )
        assert "packet_hash_missing" in display["reason_tags"]

    def test_policy_result_display_dict_derives_human_gate_reason_tag(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                risk_tier=4,
                proof_requirement="human_gate",
                human_gate_required=True,
                human_approval_present=False,
            )
        )
        display = result.to_display_dict()
        assert display["decision"] == "human_gate"
        assert display["reason_tags"] == ("human_gate_required",)
        assert display["missing_fields"] == ()

    def test_policy_result_display_dict_redacts_unsafe_strings(self):
        result = PromptPacketProofPolicyResult(
            decision=PromptPacketProofDecision.BLOCK,
            severity="error",
            reason="raw_prompt: do not show this",
            evidence_ids=("safe-evidence", "api_key=secret-value"),
            blockers=("provider_response:raw", "missing_packet_id"),
            warnings=("pid=12345",),
        )
        display = result.to_display_dict()
        assert display["reason"] == "[redacted]"
        assert display["evidence_ids"] == ("safe-evidence", "[redacted]")
        assert display["blockers"] == ("[redacted]", "missing_packet_id")
        assert display["warnings"] == ("[redacted]",)
        assert display["reason_tags"] == ("[redacted]", "missing_packet_id")
        assert display["missing_fields"] == ("packet_id",)

    def test_policy_result_display_dict_is_deterministic(self):
        result = evaluate_prompt_packet_proof_policy(
            _prompt_packet_metadata(
                packet_id="",
                packet_hash_status="missing",
                packet_hash=None,
                source_lineage={},
                allowed_sources=(),
                proof_requirement="mystery_proof",
                aegis_evidence_ids=("raw_prompt:leak", "raw_prompt:leak"),
            )
        )
        assert result.to_display_dict() == result.to_display_dict()
