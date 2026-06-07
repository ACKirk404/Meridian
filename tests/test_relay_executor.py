"""Tests for the Relay executor (meridian_core/relay_executor.py)."""

from __future__ import annotations

import dataclasses
import pytest

from meridian_core.aegis import (
    AegisEvidence,
    EvidenceSeverity,
    EvidenceStatus,
    EvidenceType,
    ProofTrail,
)
from meridian_core.model_adapter import (
    AdapterRegistry,
    FakeModelAdapter,
    MissingAdapterError,
    ModelHarnessMetadata,
    ModelRouteMetadataBinding,
    deepseek_candidate_metadata_preset,
)
from meridian_core.prompt_payload_meter import PayloadStatus, PromptPayloadSnapshot
from meridian_core.relay import ModelRole, route_from_tier
from meridian_core.relay_dispatch import RelayDispatchLane, RelayDispatchPlan
from meridian_core.cognition_policy import evaluate_cognition_policy
from meridian_core.relay_executor import (
    AegisGateEvidenceSummary,
    RelayAegisProviderResultValidationAdvisory,
    RelayAegisPromptPacketHandoffSummary,
    RelayDecisionRecord,
    RelayDispatchEnvelope,
    RelayDispatchMetadataEnvelope,
    RelayExecutionError,
    RelayExecutionResult,
    RelayExecutionSummary,
    RelayModelCapabilityMetadataSummary,
    RelayPromptPayloadMeterEvidence,
    RelayProviderResultValidationEvidence,
    RelayPromptPacketPolicyDisposition,
    RelayPromptPacketPolicyEvidence,
    RelayPromptPayloadEvidence,
    RelayProofGateError,
    _build_decision_record,
    _build_dispatch_envelope,
    _build_dispatch_metadata_envelope,
    _build_provider_result_validation_evidence,
    _build_prompt_payload_meter_evidence,
    _evaluate_relay_prompt_packet_policy,
    _relay_prompt_packet_policy_disposition,
    execute_relay_dispatch_plan,
    execute_relay_dispatch_plan_with_policy,
    execute_relay_plan_with_registry,
    relay_display_safe_handoff_tags,
    relay_execution_summary_to_proof_trail,
)
from meridian_core.relay_packet import assemble_relay_packet


_PROMPT = "Summarize the situation and recommend next action."
_PACKET_ID = "EXECUTOR-TEST-PKT"


def _make_plan(tier: int) -> RelayDispatchPlan:
    route = route_from_tier(tier)
    packet = assemble_relay_packet(
        packet_id=_PACKET_ID,
        serialized_prompt=_PROMPT,
        route=route,
    )
    from meridian_core.relay_dispatch import build_relay_dispatch_plan
    return build_relay_dispatch_plan(route, packet)


def _deepseek_authorized_metadata(lane: str = "fast") -> ModelHarnessMetadata:
    """Return DeepSeek metadata equivalent to the candidate preset but with the
    minimal candidate-state fields needed for AUTHORIZED_TRANSPORT_ONLY (a
    ``deepseek-validation:level-1:`` ref plus both gate flags exactly ``"true"``),
    so end-to-end dispatch tests that aren't auditing the transport-authority
    block can still exercise a full result path after the Codex Review A repair
    made the DeepSeek transport authority an execution gate."""
    base = deepseek_candidate_metadata_preset(lane)
    assert base.deepseek_candidate_state is not None
    authorized_state = dict(base.deepseek_candidate_state)
    authorized_state["validation_evidence_ref"] = (
        "deepseek-validation:level-1:validation-cleared"
    )
    authorized_state["external_review_evidence_ref"] = (
        "external-review:deepseek:deepseek-chat:passed"
    )
    authorized_state["external_review_status"] = "passed"
    authorized_state["human_gate_satisfied"] = "true"
    authorized_state["prime_authority_satisfied"] = "true"
    return dataclasses.replace(base, deepseek_candidate_state=authorized_state)


def _deepseek_authorized_candidate_state() -> dict[str, str]:
    """Return the minimal DeepSeek candidate_state mapping that authorizes
    transport. Use this when a test builds its own ``ModelHarnessMetadata``
    in-line rather than starting from the candidate preset."""
    return {
        "validation_evidence_ref": (
            "deepseek-validation:level-1:validation-cleared"
        ),
        "external_review_evidence_ref": (
            "external-review:deepseek:deepseek-chat:passed"
        ),
        "external_review_status": "passed",
        "direct_endpoint_evidence_ref": (
            "deepseek-direct-endpoint:https://api.deepseek.com/v1/chat/completions"
        ),
        "trust_mode": "direct",
        "human_gate_satisfied": "true",
        "prime_authority_satisfied": "true",
    }


def _constant_model_call(text: str):
    """Return a model_call that always returns *text*."""
    def _call(payload: str) -> str:
        return text
    return _call


def _clean_proof_trail(evidence_id: str = "packet-proof-1") -> ProofTrail:
    return ProofTrail([
        AegisEvidence(
            id=evidence_id,
            evidence_type=EvidenceType.BUILD_OUTPUT,
            severity=EvidenceSeverity.INFO,
            status=EvidenceStatus.OPEN,
            source="test",
            target="relay",
            summary="non-blocking proof",
        )
    ])


class TestExecuteEmptyPlan:
    def test_empty_plan_returns_summary(self):
        plan = _make_plan(0)
        summary = execute_relay_dispatch_plan(plan, _constant_model_call("out"))
        assert isinstance(summary, RelayExecutionSummary)

    def test_empty_plan_results_empty(self):
        plan = _make_plan(0)
        summary = execute_relay_dispatch_plan(plan, _constant_model_call("out"))
        assert summary.results == ()

    def test_empty_plan_errors_empty(self):
        plan = _make_plan(0)
        summary = execute_relay_dispatch_plan(plan, _constant_model_call("out"))
        assert summary.errors == ()

    def test_empty_plan_model_call_never_invoked(self):
        calls: list[str] = []

        def recording_call(payload: str) -> str:
            calls.append(payload)
            return "out"

        plan = _make_plan(0)
        execute_relay_dispatch_plan(plan, recording_call)
        assert calls == []


class TestOneModelCallPerLane:
    def test_tier1_produces_one_call(self):
        calls: list[str] = []

        def recording_call(payload: str) -> str:
            calls.append(payload)
            return "response"

        plan = _make_plan(1)
        execute_relay_dispatch_plan(plan, recording_call)
        assert len(calls) == 1

    def test_tier2_produces_two_calls(self):
        calls: list[str] = []

        def recording_call(payload: str) -> str:
            calls.append(payload)
            return "response"

        plan = _make_plan(2)
        execute_relay_dispatch_plan(plan, recording_call)
        assert len(calls) == 2

    def test_tier3_produces_three_calls(self):
        calls: list[str] = []

        def recording_call(payload: str) -> str:
            calls.append(payload)
            return "response"

        plan = _make_plan(3)
        execute_relay_dispatch_plan(plan, recording_call)
        assert len(calls) == 3

    def test_call_count_matches_lane_count(self):
        for tier in (1, 2, 3):
            calls: list[str] = []

            def recording_call(payload: str) -> str:
                calls.append(payload)
                return "out"

            plan = _make_plan(tier)
            execute_relay_dispatch_plan(plan, recording_call)
            assert len(calls) == len(plan.lanes)


class TestOutputCapturedPerLane:
    def test_result_output_matches_model_call_return(self):
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(plan, _constant_model_call("hello world"))
        assert summary.results[0].output == "hello world"

    def test_each_lane_output_stored_independently(self):
        counter = {"n": 0}

        def incremental_call(payload: str) -> str:
            counter["n"] += 1
            return f"response-{counter['n']}"

        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan(plan, incremental_call)
        assert summary.results[0].output == "response-1"
        assert summary.results[1].output == "response-2"

    def test_result_role_matches_lane(self):
        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan(plan, _constant_model_call("ok"))
        assert summary.results[0].role == ModelRole.BUILDER
        assert summary.results[1].role == ModelRole.REVIEWER

    def test_result_preferred_model_matches_lane(self):
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(plan, _constant_model_call("ok"))
        assert summary.results[0].preferred_model == plan.lanes[0].preferred_model

    def test_result_order_matches_lane_order(self):
        plan = _make_plan(3)
        roles_seen: list[ModelRole] = []

        def recording_call(payload: str) -> str:
            return "out"

        summary = execute_relay_dispatch_plan(plan, recording_call)
        result_roles = [r.role for r in summary.results]
        lane_roles = [lane.role for lane in plan.lanes]
        assert result_roles == lane_roles


class TestExceptionConvertedToError:
    def test_exception_produces_error_not_result(self):
        def raising_call(payload: str) -> str:
            raise RuntimeError("model failure")

        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(plan, raising_call)
        assert len(summary.results) == 0
        assert len(summary.errors) == 1

    def test_error_is_relay_execution_error(self):
        def raising_call(payload: str) -> str:
            raise ValueError("bad input")

        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(plan, raising_call)
        assert isinstance(summary.errors[0], RelayExecutionError)

    def test_error_message_captured(self):
        def raising_call(payload: str) -> str:
            raise RuntimeError("timeout after 30s")

        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(plan, raising_call)
        assert "timeout after 30s" in summary.errors[0].error

    def test_error_role_matches_lane(self):
        def raising_call(payload: str) -> str:
            raise RuntimeError("fail")

        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(plan, raising_call)
        assert summary.errors[0].role == plan.lanes[0].role

    def test_error_preferred_model_matches_lane(self):
        def raising_call(payload: str) -> str:
            raise RuntimeError("fail")

        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(plan, raising_call)
        assert summary.errors[0].preferred_model == plan.lanes[0].preferred_model

    def test_partial_failure_splits_results_and_errors(self):
        call_count = {"n": 0}

        def mixed_call(payload: str) -> str:
            call_count["n"] += 1
            if call_count["n"] == 1:
                return "ok"
            raise RuntimeError("second lane failed")

        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan(plan, mixed_call)
        assert len(summary.results) == 1
        assert len(summary.errors) == 1

    def test_all_lanes_fail_produces_empty_results(self):
        def always_raise(payload: str) -> str:
            raise RuntimeError("fail")

        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan(plan, always_raise)
        assert summary.results == ()
        assert len(summary.errors) == 2


class TestMetadataNotPassedToModelCall:
    def test_only_payload_string_passed_to_model_call(self):
        """model_call must receive only the lane payload string, not role or metadata."""
        received: list[object] = []

        def capturing_call(payload: str) -> str:
            received.append(payload)
            return "out"

        plan = _make_plan(1)
        execute_relay_dispatch_plan(plan, capturing_call)

        assert len(received) == 1
        assert isinstance(received[0], str)
        assert received[0] == plan.lanes[0].payload

    def test_payload_is_model_payload_only(self):
        """Payload received by model_call equals the lane's prompt text, not packet metadata."""
        plan = _make_plan(1)
        received: list[str] = []

        def capturing_call(payload: str) -> str:
            received.append(payload)
            return "done"

        execute_relay_dispatch_plan(plan, capturing_call)

        assert received[0] == _PROMPT
        assert _PACKET_ID not in received[0]

    def test_role_enum_not_in_payload(self):
        plan = _make_plan(1)
        received: list[str] = []

        def capturing_call(payload: str) -> str:
            received.append(payload)
            return "ok"

        execute_relay_dispatch_plan(plan, capturing_call)
        assert "builder" not in received[0].lower() or received[0] == _PROMPT

    def test_fake_model_adapter_receives_only_lane_payload(self):
        plan = _make_plan(1)
        adapter = FakeModelAdapter("ok")
        execute_relay_dispatch_plan(plan, adapter)
        assert adapter.received_payloads == [plan.lanes[0].payload]


class TestImmutability:
    def test_summary_is_frozen(self):
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(plan, _constant_model_call("ok"))
        with pytest.raises((AttributeError, TypeError)):
            summary.results = ()  # type: ignore[misc]

    def test_result_is_frozen(self):
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(plan, _constant_model_call("ok"))
        with pytest.raises((AttributeError, TypeError)):
            summary.results[0].output = "mutated"  # type: ignore[misc]

    def test_results_tuple_is_immutable(self):
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(plan, _constant_model_call("ok"))
        with pytest.raises(TypeError):
            summary.results[0] = None  # type: ignore[index]


class TestAegisProofGate:
    def _blocking_trail(self) -> ProofTrail:
        return ProofTrail([
            AegisEvidence(
                id="proof-001",
                evidence_type=EvidenceType.BUILD_OUTPUT,
                severity=EvidenceSeverity.ERROR,
                status=EvidenceStatus.OPEN,
                source="test",
                target="relay",
                summary="blocking evidence",
            )
        ])

    def test_tier3_blocking_proof_trail_blocks_dispatch(self):
        plan = _make_plan(3)

        with pytest.raises(RelayProofGateError):
            execute_relay_dispatch_plan(plan, _constant_model_call("ok"), self._blocking_trail())

    def test_blocked_dispatch_does_not_call_model(self):
        plan = _make_plan(3)
        calls: list[str] = []

        def recording_call(payload: str) -> str:
            calls.append(payload)
            return "ok"

        with pytest.raises(RelayProofGateError):
            execute_relay_dispatch_plan(plan, recording_call, self._blocking_trail())

        assert calls == []

    def test_tier3_clean_proof_trail_allows_dispatch(self):
        plan = _make_plan(3)
        summary = execute_relay_dispatch_plan(plan, _constant_model_call("ok"), ProofTrail())
        assert len(summary.results) == len(plan.lanes)

    def test_tier2_blocking_proof_trail_does_not_block_dispatch(self):
        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            self._blocking_trail(),
        )
        assert len(summary.results) == len(plan.lanes)

    def test_gate_error_names_blocking_evidence(self):
        plan = _make_plan(3)
        with pytest.raises(RelayProofGateError, match="proof-001"):
            execute_relay_dispatch_plan(plan, _constant_model_call("ok"), self._blocking_trail())

    def test_blocking_proof_trail_prevents_adapter_call(self):
        plan = _make_plan(3)
        adapter = FakeModelAdapter("ok")

        with pytest.raises(RelayProofGateError):
            execute_relay_dispatch_plan(plan, adapter, self._blocking_trail())

        assert adapter.received_payloads == []


class TestRelayExecutionSummaryToProofTrail:
    def test_clean_execution_summary_produces_clean_proof_trail(self):
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(plan, _constant_model_call("clean output"))
        trail = relay_execution_summary_to_proof_trail(summary)
        assert trail.is_clean()

    def test_successful_lane_output_becomes_build_output_evidence(self):
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(plan, _constant_model_call("clean output"))
        trail = relay_execution_summary_to_proof_trail(summary)
        assert trail.evidence[0].evidence_type.value == "build_output"
        assert trail.evidence[0].severity.value == "info"

    def test_execution_errors_produce_blocking_evidence(self):
        def raising_call(payload: str) -> str:
            raise RuntimeError("vendor timeout")

        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(plan, raising_call)
        trail = relay_execution_summary_to_proof_trail(summary)
        assert not trail.is_clean()
        assert trail.blocking()[0].severity.value == "error"

    def test_evidence_records_include_lane_role_and_model_target(self):
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(plan, _constant_model_call("clean output"))
        trail = relay_execution_summary_to_proof_trail(summary)
        evidence = trail.evidence[0]
        assert plan.lanes[0].role.value in evidence.target
        assert plan.lanes[0].preferred_model in evidence.target

    def test_evidence_records_do_not_leak_prompt_payloads(self):
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(plan, _constant_model_call("clean output"))
        trail = relay_execution_summary_to_proof_trail(summary)
        evidence_text = " ".join(
            f"{ev.id} {ev.source} {ev.target} {ev.summary}" for ev in trail.evidence
        )
        assert _PROMPT not in evidence_text
        assert _PACKET_ID not in evidence_text

    def test_error_proof_evidence_does_not_leak_free_text_failure(self):
        danger = (
            "RAW_PROMPT_SENTINEL worker_chat=private "
            "credential=sk-test-secret BRANCH_MOVE_REQUEST "
            "free-text blocker summary: move main"
        )

        def raising_call(payload: str) -> str:
            raise RuntimeError(danger)

        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(plan, raising_call)
        trail = relay_execution_summary_to_proof_trail(summary)
        evidence_text = " ".join(
            f"{ev.id} {ev.source} {ev.target} {ev.summary}" for ev in trail.evidence
        )

        assert len(summary.errors) == 1
        assert danger in summary.errors[0].error
        assert "error length" in evidence_text
        for sentinel in (
            "RAW_PROMPT_SENTINEL",
            "worker_chat=private",
            "credential=sk-test-secret",
            "BRANCH_MOVE_REQUEST",
            "free-text blocker summary",
            "move main",
        ):
            assert sentinel not in evidence_text

    def test_relay_evidence_views_do_not_leak_prompt_output_or_branch_requests(self):
        dangerous_payload = (
            "RAW_PROMPT_SENTINEL worker_chat=private "
            "credential=sk-test-secret BRANCH_MOVE_REQUEST "
            "free-text blocker summary: move main"
        )
        route = route_from_tier(1)
        packet = assemble_relay_packet(
            packet_id="NEGATIVE-PAYLOAD-PKT",
            serialized_prompt=dangerous_payload,
            route=route,
        )
        from meridian_core.relay_dispatch import build_relay_dispatch_plan

        plan = build_relay_dispatch_plan(route, packet)
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=len(dangerous_payload),
            estimated_tokens=256,
            budget_tokens=2048,
        )

        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call(dangerous_payload),
            payload_snapshots=(snapshot,),
            include_decision_record=True,
        )
        proof_trail = relay_execution_summary_to_proof_trail(summary)
        rendered = " ".join(
            str(value)
            for value in (
                [evidence.summary for evidence in proof_trail.evidence],
                summary.results[0].payload_evidence.to_dict(),
                summary.results[0].payload_meter_evidence.to_dict(),
                summary.results[0].dispatch_envelope.to_dict(),
                summary.results[0].dispatch_metadata_envelope.to_dict(),
                summary.results[0].provider_result_validation_evidence.to_dict(),
                summary.prompt_payload_meter_consumer_view(),
                summary.dispatch_metadata_consumer_view(),
                summary.provider_result_validation_consumer_view(),
                summary.decision_record.packet_hash,
                summary.decision_record.prompt_budget_ref,
                summary.decision_record.packet_proof_metadata_ref,
                summary.decision_record.fallback_blockers,
            )
        )

        for sentinel in (
            "RAW_PROMPT_SENTINEL",
            "worker_chat=private",
            "credential=sk-test-secret",
            "BRANCH_MOVE_REQUEST",
            "free-text blocker summary",
            "move main",
        ):
            assert sentinel not in rendered
        assert summary.results[0].output == dangerous_payload

    def test_empty_execution_summary_produces_clean_empty_proof_trail(self):
        summary = RelayExecutionSummary(results=(), errors=())
        trail = relay_execution_summary_to_proof_trail(summary)
        assert trail.evidence == []
        assert trail.is_clean()


def _make_registry_for_tier(tier: int) -> AdapterRegistry:
    """Build an AdapterRegistry pre-populated for the given tier's preferred_model names."""
    plan = _make_plan(tier)
    registry = AdapterRegistry()
    for lane in plan.lanes:
        registry = registry.register_model(lane.preferred_model, FakeModelAdapter(f"response-for-{lane.preferred_model}"))
    return registry


class TestRegistryDispatch:
    def test_exact_model_adapter_selected_for_lane(self):
        plan = _make_plan(1)
        exact = FakeModelAdapter("exact-output")
        registry = AdapterRegistry().register_model(plan.lanes[0].preferred_model, exact)
        summary = execute_relay_plan_with_registry(plan, registry)
        assert exact.received_payloads == [plan.lanes[0].payload]

    def test_role_default_used_when_no_exact_model(self):
        plan = _make_plan(1)
        role_adapter = FakeModelAdapter("role-output")
        registry = AdapterRegistry().register_role_default(plan.lanes[0].role, role_adapter)
        summary = execute_relay_plan_with_registry(plan, registry)
        assert role_adapter.received_payloads == [plan.lanes[0].payload]

    def test_missing_adapter_raises_before_any_call(self):
        plan = _make_plan(1)
        empty_registry = AdapterRegistry()
        calls: list[str] = []

        with pytest.raises(MissingAdapterError):
            execute_relay_plan_with_registry(plan, empty_registry)

        assert calls == []

    def test_missing_adapter_error_contains_model_name(self):
        plan = _make_plan(1)
        with pytest.raises(MissingAdapterError) as exc_info:
            execute_relay_plan_with_registry(plan, AdapterRegistry())
        assert plan.lanes[0].preferred_model in str(exc_info.value)

    def test_selected_adapter_receives_only_lane_payload(self):
        plan = _make_plan(1)
        adapter = FakeModelAdapter("ok")
        registry = AdapterRegistry().register_model(plan.lanes[0].preferred_model, adapter)
        execute_relay_plan_with_registry(plan, registry)
        assert adapter.received_payloads == [_PROMPT]

    def test_per_lane_adapters_selected_independently(self):
        plan = _make_plan(2)
        builder_adapter = FakeModelAdapter("builder-response")
        reviewer_adapter = FakeModelAdapter("reviewer-response")
        registry = (
            AdapterRegistry()
            .register_model(plan.lanes[0].preferred_model, builder_adapter)
            .register_model(plan.lanes[1].preferred_model, reviewer_adapter)
        )
        summary = execute_relay_plan_with_registry(plan, registry)
        assert len(summary.results) == 2
        assert builder_adapter.received_payloads == [plan.lanes[0].payload]
        assert reviewer_adapter.received_payloads == [plan.lanes[1].payload]

    def test_summary_has_correct_results(self):
        plan = _make_plan(1)
        registry = _make_registry_for_tier(1)
        summary = execute_relay_plan_with_registry(plan, registry)
        assert len(summary.results) == 1
        assert isinstance(summary.results[0], RelayExecutionResult)

    def test_tier3_blocking_proof_trail_blocks_before_adapter_resolution(self):
        plan = _make_plan(3)
        registry = _make_registry_for_tier(3)
        blocking_trail = ProofTrail([
            AegisEvidence(
                id="block-001",
                evidence_type=EvidenceType.BUILD_OUTPUT,
                severity=EvidenceSeverity.ERROR,
                status=EvidenceStatus.OPEN,
                source="test",
                target="relay",
                summary="blocking evidence",
            )
        ])
        adapters = [FakeModelAdapter("ok") for _ in plan.lanes]
        model_registry = AdapterRegistry()
        for lane, adapter in zip(plan.lanes, adapters):
            model_registry = model_registry.register_model(lane.preferred_model, adapter)

        with pytest.raises(RelayProofGateError):
            execute_relay_plan_with_registry(plan, model_registry, blocking_trail)

        for adapter in adapters:
            assert adapter.received_payloads == []

    def test_tier4_blocking_proof_trail_blocks_dispatch(self):
        plan = _make_plan(4)
        blocking_trail = ProofTrail([
            AegisEvidence(
                id="block-002",
                evidence_type=EvidenceType.BUILD_OUTPUT,
                severity=EvidenceSeverity.ERROR,
                status=EvidenceStatus.OPEN,
                source="test",
                target="relay",
                summary="blocking evidence tier4",
            )
        ])
        registry = _make_registry_for_tier(4)
        with pytest.raises(RelayProofGateError):
            execute_relay_plan_with_registry(plan, registry, blocking_trail)

    def test_tier2_blocking_proof_trail_does_not_block(self):
        plan = _make_plan(2)
        registry = _make_registry_for_tier(2)
        blocking_trail = ProofTrail([
            AegisEvidence(
                id="block-003",
                evidence_type=EvidenceType.BUILD_OUTPUT,
                severity=EvidenceSeverity.ERROR,
                status=EvidenceStatus.OPEN,
                source="test",
                target="relay",
                summary="blocking evidence tier2",
            )
        ])
        summary = execute_relay_plan_with_registry(plan, registry, blocking_trail)
        assert len(summary.results) == len(plan.lanes)

    def test_backward_compatible_execute_relay_dispatch_plan_unchanged(self):
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(plan, _constant_model_call("still works"))
        assert summary.results[0].output == "still works"


class TestExecuteRelayDispatchPlanWithPolicy:
    def test_tier3_missing_proof_blocks_before_model_call(self):
        plan = _make_plan(3)
        calls: list[str] = []

        def recording_call(payload: str) -> str:
            calls.append(payload)
            return "response"

        with pytest.raises(RelayProofGateError):
            execute_relay_dispatch_plan_with_policy(plan, recording_call, proof_trail=None)

        assert calls == []

    def test_tier3_candidate_trust_blocks_after_clean_proof(self):
        plan = _make_plan(3)
        calls: list[str] = []

        def recording_call(payload: str) -> str:
            calls.append(payload)
            return "response"

        with pytest.raises(RelayProofGateError, match="candidate_model_trust_for_high_tier"):
            execute_relay_dispatch_plan_with_policy(
                plan,
                recording_call,
                proof_trail=_clean_proof_trail(),
            )

        assert calls == []

    def test_tier4_clean_proof_without_human_approval_blocks_before_model_call(self):
        plan = _make_plan(4)
        calls: list[str] = []

        def recording_call(payload: str) -> str:
            calls.append(payload)
            return "response"

        with pytest.raises(RelayProofGateError, match="human gate approval required"):
            execute_relay_dispatch_plan_with_policy(
                plan,
                recording_call,
                proof_trail=_clean_proof_trail("packet-proof-human-missing"),
                human_gate_approved=False,
            )

        assert calls == []

    def test_tier4_clean_proof_with_human_approval_allows_dispatch(self):
        plan = _make_plan(4)
        summary = execute_relay_dispatch_plan_with_policy(
            plan,
            _constant_model_call("ok"),
            proof_trail=_clean_proof_trail("packet-proof-human-approved"),
            human_gate_approved=True,
        )
        assert len(summary.results) == len(plan.lanes)
        assert summary.prompt_packet_policy_evidence.decision == "allow"

    def test_tier2_prompt_packet_policy_blocks_without_evidence(self):
        plan = _make_plan(2)
        calls: list[str] = []

        def recording_call(payload: str) -> str:
            calls.append(payload)
            return "response"

        with pytest.raises(RelayProofGateError, match="missing_aegis_evidence_ids"):
            execute_relay_dispatch_plan_with_policy(
                plan,
                recording_call,
                proof_trail=None,
            )

        assert calls == []

    def test_tier2_clean_dual_lane_proof_allows_dispatch(self):
        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan_with_policy(
            plan,
            _constant_model_call("ok"),
            proof_trail=_clean_proof_trail("packet-proof-tier2"),
            include_decision_record=True,
        )

        assert len(summary.results) == len(plan.lanes)
        assert summary.prompt_packet_policy_evidence.decision == "allow"
        assert summary.decision_record.prompt_packet_policy_evidence.evidence_ids == (
            "packet-proof-tier2",
        )
        assert summary.prompt_packet_policy_disposition.transport_allowed is True
        assert (
            summary.decision_record.prompt_packet_policy_disposition.transport_action
            == "dispatch"
        )

    def test_prompt_packet_policy_unknown_proof_requirement_blocks(self):
        plan = _make_plan(1)
        packet = dataclasses.replace(plan.packet, proof_required=("mystery_proof",))
        plan = dataclasses.replace(plan, packet=packet)

        evidence = _evaluate_relay_prompt_packet_policy(
            plan,
            proof_trail=_clean_proof_trail("packet-proof-unknown"),
        )

        assert evidence.decision == "block"
        assert "unknown_proof_requirement" in evidence.blockers

    def test_prompt_packet_policy_unavailable_hash_blocks_dual_lane_tier2(self):
        plan = _make_plan(2)
        degraded_proof = dataclasses.replace(
            plan.packet.proof_metadata,
            packet_hash=None,
            prompt_payload_snapshot_hash=None,
            snapshot_hash_available=False,
        )
        degraded_packet = dataclasses.replace(plan.packet, proof_metadata=degraded_proof)
        degraded_plan = dataclasses.replace(plan, packet=degraded_packet)

        evidence = _evaluate_relay_prompt_packet_policy(
            degraded_plan,
            proof_trail=_clean_proof_trail("packet-proof-hash-unavailable"),
        )

        assert evidence.decision == "block"
        assert "packet_hash_required_unavailable" in evidence.blockers

    def test_prompt_packet_policy_warn_degraded_tier1_is_display_safe(self):
        plan = _make_plan(1)
        degraded_proof = dataclasses.replace(
            plan.packet.proof_metadata,
            packet_hash=None,
            prompt_payload_snapshot_hash=None,
            snapshot_hash_available=False,
        )
        degraded_packet = dataclasses.replace(plan.packet, proof_metadata=degraded_proof)
        degraded_plan = dataclasses.replace(plan, packet=degraded_packet)

        evidence = _evaluate_relay_prompt_packet_policy(
            degraded_plan,
            proof_trail=_clean_proof_trail("packet-proof-warn"),
        )

        assert evidence.decision == "warn"
        assert "packet_hash_unavailable" in evidence.warnings
        assert _PROMPT not in " ".join(str(value) for value in evidence.to_dict().values())

    def test_prompt_packet_policy_missing_proof_metadata_fails_closed(self):
        plan = _make_plan(1)
        packet = dataclasses.replace(plan.packet, proof_metadata=False)  # type: ignore[arg-type]
        plan = dataclasses.replace(plan, packet=packet)

        evidence = _evaluate_relay_prompt_packet_policy(
            plan,
            proof_trail=_clean_proof_trail("packet-proof-missing"),
        )

        assert evidence.decision == "block"
        assert "packet_hash_missing" in evidence.blockers

    def test_prompt_packet_policy_block_prevents_model_call(self):
        plan = _make_plan(1)
        calls: list[str] = []

        def recording_call(payload: str) -> str:
            calls.append(payload)
            return "response"

        with pytest.raises(RelayProofGateError, match="unsafe_aegis_evidence_id"):
            execute_relay_dispatch_plan_with_policy(
                plan,
                recording_call,
                proof_trail=_clean_proof_trail("raw_prompt:secret"),
            )

        assert calls == []

    def test_prompt_packet_policy_disposition_allows_warn_without_retry(self):
        plan = _make_plan(1)
        evidence = RelayPromptPacketPolicyEvidence(
            decision="warn",
            severity="warning",
            reason="packet hash unavailable",
            evidence_ids=("packet-proof-warn",),
            warnings=("packet_hash_unavailable",),
            packet_id=_PACKET_ID,
        )

        disposition = _relay_prompt_packet_policy_disposition(plan, evidence)

        assert disposition == RelayPromptPacketPolicyDisposition(
            transport_allowed=True,
            transport_action="dispatch",
            fallback_allowed=True,
            audit_tags=("aegis_prompt_packet_policy_warn",),
            explanation="packet hash unavailable",
        )
        assert disposition.to_dict()["retry_requires_fresh_evaluation"] is False

    def test_prompt_packet_policy_disposition_demote_requires_fresh_evaluation(self):
        plan = _make_plan(2)
        evidence = RelayPromptPacketPolicyEvidence(
            decision="demote",
            severity="warning",
            reason="packet hash unavailable; demote to lower tier",
            evidence_ids=("packet-proof-demote",),
            warnings=("packet_hash_unavailable_demote",),
            demote_to_tier=1,
            packet_id=_PACKET_ID,
        )

        disposition = _relay_prompt_packet_policy_disposition(plan, evidence)

        assert disposition.transport_allowed is False
        assert disposition.transport_action == "demote_requires_fresh_evaluation"
        assert disposition.retry_requires_fresh_evaluation is True
        assert disposition.demotion_target_tier == 1
        assert disposition.demotion_authorized is True
        assert disposition.fallback_allowed is False
        assert "aegis_demotion_requires_fresh_policy_evaluation" in disposition.blockers
        assert "rerun_aegis_before_transport" in disposition.audit_tags

    def test_prompt_packet_policy_disposition_invalid_demote_target_blocks(self):
        plan = _make_plan(2)
        evidence = RelayPromptPacketPolicyEvidence(
            decision="demote",
            severity="warning",
            reason="invalid demotion target",
            evidence_ids=("packet-proof-demote",),
            warnings=("packet_hash_unavailable_demote",),
            demote_to_tier=2,
            packet_id=_PACKET_ID,
        )

        disposition = _relay_prompt_packet_policy_disposition(plan, evidence)

        assert disposition.transport_allowed is False
        assert disposition.demotion_authorized is False
        assert "aegis_demotion_target_unauthorized" in disposition.blockers

    def test_prompt_packet_policy_demote_prevents_model_call_until_rerun(
        self,
        monkeypatch,
    ):
        plan = _make_plan(2)
        calls: list[str] = []
        demote_evidence = RelayPromptPacketPolicyEvidence(
            decision="demote",
            severity="warning",
            reason="packet hash unavailable; demote to lower tier",
            evidence_ids=("packet-proof-demote",),
            warnings=("packet_hash_unavailable_demote",),
            demote_to_tier=1,
            packet_id=_PACKET_ID,
        )

        def recording_call(payload: str) -> str:
            calls.append(payload)
            return "response"

        monkeypatch.setattr(
            "meridian_core.relay_executor._evaluate_relay_prompt_packet_policy",
            lambda *args, **kwargs: demote_evidence,
        )

        with pytest.raises(
            RelayProofGateError,
            match="demote_requires_fresh_evaluation",
        ):
            execute_relay_dispatch_plan_with_policy(
                plan,
                recording_call,
                proof_trail=_clean_proof_trail("packet-proof-demote"),
            )

        assert calls == []

    def test_prompt_packet_policy_human_gate_disposition_adds_blocker(self):
        plan = _make_plan(4)
        evidence = _evaluate_relay_prompt_packet_policy(
            plan,
            proof_trail=_clean_proof_trail("packet-proof-human-gate"),
            human_gate_approved=False,
        )

        disposition = _relay_prompt_packet_policy_disposition(plan, evidence)

        assert disposition.transport_allowed is False
        assert disposition.transport_action == "human_gate_required"
        assert disposition.fail_closed is True
        assert disposition.retry_requires_fresh_evaluation is True
        assert "aegis_human_gate_required" in disposition.blockers
        assert "wait_for_review_console_approval" in disposition.audit_tags

    def test_prompt_packet_policy_missing_metadata_disposition_fails_closed(self):
        plan = _make_plan(1)
        packet = dataclasses.replace(plan.packet, proof_metadata=False)  # type: ignore[arg-type]
        plan = dataclasses.replace(plan, packet=packet)
        evidence = _evaluate_relay_prompt_packet_policy(
            plan,
            proof_trail=_clean_proof_trail("packet-proof-missing"),
        )

        disposition = _relay_prompt_packet_policy_disposition(plan, evidence)

        assert disposition.transport_allowed is False
        assert disposition.transport_action == "block"
        assert disposition.fail_closed is True
        assert disposition.retry_requires_fresh_evaluation is True
        assert "missing_metadata_fail_closed" in disposition.blockers
        assert "correct_metadata_before_retry" in disposition.audit_tags


class TestPayloadSnapshot:
    def test_execution_result_without_snapshot(self) -> None:
        result = RelayExecutionResult(
            role=ModelRole.BUILDER,
            preferred_model="gpt-4",
            output="output text",
        )
        assert result.payload_snapshot is None

    def test_execution_result_with_snapshot(self) -> None:
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=1500,
            estimated_tokens=450,
            budget_tokens=2000,
        )
        result = RelayExecutionResult(
            role=ModelRole.BUILDER,
            preferred_model="gpt-4",
            output="output text",
            payload_snapshot=snapshot,
        )
        assert result.payload_snapshot is snapshot
        assert result.payload_snapshot.status == PayloadStatus.HEALTHY

    def test_execute_plan_accepts_optional_snapshots(self) -> None:
        plan = _make_plan(1)
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=1000,
            estimated_tokens=300,
            budget_tokens=4000,
        )
        snapshots = (snapshot,)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            payload_snapshots=snapshots,
        )
        assert len(summary.results) == 1
        assert summary.results[0].payload_snapshot is snapshot

    def test_execute_plan_without_snapshots_still_works(self) -> None:
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
        )
        assert len(summary.results) == 1
        assert summary.results[0].payload_snapshot is None

    def test_payload_snapshot_evidence_in_proof_trail(self) -> None:
        snapshot_healthy = PromptPayloadSnapshot(
            raw_prompt_chars=800,
            estimated_tokens=250,
            budget_tokens=4000,
        )
        result = RelayExecutionResult(
            role=ModelRole.BUILDER,
            preferred_model="gpt-4",
            output="output",
            payload_snapshot=snapshot_healthy,
        )
        summary = RelayExecutionSummary(results=(result,), errors=())
        trail = relay_execution_summary_to_proof_trail(summary)

        evidence_ids = [e.id for e in trail.evidence]
        assert "relay-payload-0-builder" in evidence_ids

        payload_evidence = next(
            e for e in trail.evidence if e.id == "relay-payload-0-builder"
        )
        assert payload_evidence.evidence_type == EvidenceType.BUILD_OUTPUT
        assert payload_evidence.severity == EvidenceSeverity.INFO
        assert "healthy" in payload_evidence.summary.lower()
        assert "(under 1k)" in payload_evidence.summary

    def test_payload_snapshot_watch_status_in_evidence(self) -> None:
        snapshot_watch = PromptPayloadSnapshot(
            raw_prompt_chars=3200,
            estimated_tokens=1600,
            budget_tokens=2000,
        )
        result = RelayExecutionResult(
            role=ModelRole.REVIEWER,
            preferred_model="gpt-4",
            output="review",
            payload_snapshot=snapshot_watch,
        )
        summary = RelayExecutionSummary(results=(result,), errors=())
        trail = relay_execution_summary_to_proof_trail(summary)

        payload_evidence = next(
            e for e in trail.evidence if "payload" in e.id
        )
        assert payload_evidence.severity == EvidenceSeverity.INFO
        assert "watch" in payload_evidence.summary.lower()

    def test_payload_snapshot_degraded_status_in_evidence(self) -> None:
        snapshot_degraded = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=2500,
            budget_tokens=2000,
        )
        result = RelayExecutionResult(
            role=ModelRole.REVIEWER,
            preferred_model="independent-reviewer",
            output="review",
            payload_snapshot=snapshot_degraded,
        )
        summary = RelayExecutionSummary(results=(result,), errors=())
        trail = relay_execution_summary_to_proof_trail(summary)

        payload_evidence = next(
            e for e in trail.evidence if "payload" in e.id
        )
        assert payload_evidence.severity == EvidenceSeverity.WARNING
        assert "degraded" in payload_evidence.summary.lower()

    def test_execute_with_registry_accepts_snapshots(self) -> None:
        plan = _make_plan(1)
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            FakeModelAdapter("response"),
        )
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=1200,
            estimated_tokens=360,
            budget_tokens=4096,
        )
        snapshots = (snapshot,)
        summary = execute_relay_plan_with_registry(
            plan,
            registry,
            payload_snapshots=snapshots,
        )
        assert len(summary.results) == 1
        assert summary.results[0].payload_snapshot is snapshot

    def test_execute_with_policy_passes_snapshots(self) -> None:
        plan = _make_plan(1)
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=900,
            estimated_tokens=270,
            budget_tokens=4096,
        )
        snapshots = (snapshot,)
        summary = execute_relay_dispatch_plan_with_policy(
            plan,
            _constant_model_call("ok"),
            payload_snapshots=snapshots,
            proof_trail=_clean_proof_trail("packet-proof-snapshot"),
        )
        assert len(summary.results) == 1
        assert summary.results[0].payload_snapshot is snapshot


class TestPayloadSnapshotEdgeCases:
    """Edge case tests for payload snapshot metadata in Relay evidence."""

    def test_payload_snapshot_with_none_budget_evidence(self) -> None:
        """Evidence formatting when snapshot has None budget_tokens."""
        snapshot_no_budget = PromptPayloadSnapshot(
            raw_prompt_chars=2000,
            estimated_tokens=500,
            budget_tokens=None,
        )
        result = RelayExecutionResult(
            role=ModelRole.BUILDER,
            preferred_model="gpt-4",
            output="output",
            payload_snapshot=snapshot_no_budget,
        )
        summary = RelayExecutionSummary(results=(result,), errors=())
        trail = relay_execution_summary_to_proof_trail(summary)

        payload_evidence = next(
            e for e in trail.evidence if "payload" in e.id
        )
        assert payload_evidence.severity == EvidenceSeverity.INFO
        assert "0.0%" in payload_evidence.summary
        assert snapshot_no_budget.status == PayloadStatus.HEALTHY

    def test_payload_snapshot_with_zero_budget_evidence(self) -> None:
        """Evidence formatting when snapshot has zero budget_tokens."""
        snapshot_zero_budget = PromptPayloadSnapshot(
            raw_prompt_chars=0,
            estimated_tokens=0,
            budget_tokens=0,
        )
        result = RelayExecutionResult(
            role=ModelRole.BUILDER,
            preferred_model="test-model",
            output="output",
            payload_snapshot=snapshot_zero_budget,
        )
        summary = RelayExecutionSummary(results=(result,), errors=())
        trail = relay_execution_summary_to_proof_trail(summary)

        payload_evidence = next(
            e for e in trail.evidence if "payload" in e.id
        )
        assert payload_evidence.severity == EvidenceSeverity.INFO
        assert "0.0%" in payload_evidence.summary
        assert snapshot_zero_budget.status == PayloadStatus.HEALTHY

    def test_payload_snapshot_queue_mode_growth_evidence(self) -> None:
        """Evidence includes queue-mode growth status in snapshot metadata."""
        snapshot_queue_growth = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=1050,
            prior_estimated_tokens=1000,
            queue_mode=True,
        )
        result = RelayExecutionResult(
            role=ModelRole.REVIEWER,
            preferred_model="reviewer-model",
            output="review",
            payload_snapshot=snapshot_queue_growth,
        )
        summary = RelayExecutionSummary(results=(result,), errors=())
        trail = relay_execution_summary_to_proof_trail(summary)

        payload_evidence = next(
            e for e in trail.evidence if "payload" in e.id
        )
        assert payload_evidence.severity == EvidenceSeverity.INFO
        assert "watch" in payload_evidence.summary.lower()
        assert snapshot_queue_growth.status == PayloadStatus.WATCH

    def test_payload_snapshot_multiple_lanes_mixed_statuses(self) -> None:
        """Evidence for multiple lanes with different snapshot statuses."""
        snapshot_healthy = PromptPayloadSnapshot(
            raw_prompt_chars=500,
            estimated_tokens=100,
            budget_tokens=2000,
        )
        snapshot_degraded = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=2500,
            budget_tokens=2000,
        )
        result1 = RelayExecutionResult(
            role=ModelRole.BUILDER,
            preferred_model="gpt-4",
            output="output1",
            payload_snapshot=snapshot_healthy,
        )
        result2 = RelayExecutionResult(
            role=ModelRole.REVIEWER,
            preferred_model="claude-3-opus",
            output="output2",
            payload_snapshot=snapshot_degraded,
        )
        summary = RelayExecutionSummary(results=(result1, result2), errors=())
        trail = relay_execution_summary_to_proof_trail(summary)

        payload_evidence_ids = [e.id for e in trail.evidence if "payload" in e.id]
        assert len(payload_evidence_ids) == 2
        assert "relay-payload-0-builder" in payload_evidence_ids
        assert "relay-payload-1-reviewer" in payload_evidence_ids

        builder_evidence = next(
            e for e in trail.evidence if e.id == "relay-payload-0-builder"
        )
        assert builder_evidence.severity == EvidenceSeverity.INFO

        reviewer_evidence = next(
            e for e in trail.evidence if e.id == "relay-payload-1-reviewer"
        )
        assert reviewer_evidence.severity == EvidenceSeverity.WARNING

    def test_payload_snapshot_partial_snapshots_tuple(self) -> None:
        """Execute with partial snapshots tuple (fewer than lanes)."""
        plan = _make_plan(2)
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=1000,
            estimated_tokens=300,
            budget_tokens=4000,
        )
        snapshots = (snapshot, None)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            payload_snapshots=snapshots,
        )
        assert len(summary.results) == 2
        assert summary.results[0].payload_snapshot is snapshot
        assert summary.results[1].payload_snapshot is None

    def test_payload_snapshot_evidence_not_leaked_to_errors(self) -> None:
        """Lane errors do not include payload snapshot evidence."""
        def failing_call(payload: str) -> str:
            raise RuntimeError("model failed")

        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=1000,
            estimated_tokens=300,
            budget_tokens=4000,
        )
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(
            plan,
            failing_call,
            payload_snapshots=(snapshot,),
        )
        assert len(summary.errors) == 1
        assert len(summary.results) == 0

        trail = relay_execution_summary_to_proof_trail(summary)
        error_evidence = next(
            e for e in trail.evidence if "error" in e.id
        )
        assert error_evidence.severity == EvidenceSeverity.ERROR
        payload_evidence = [e for e in trail.evidence if "payload" in e.id]
        assert len(payload_evidence) == 0

    def test_snapshot_severity_mapping_completeness(self) -> None:
        """_snapshot_severity maps all PayloadStatus values correctly."""
        from meridian_core.relay_executor import _snapshot_severity

        snapshot_healthy = PromptPayloadSnapshot(
            raw_prompt_chars=500,
            estimated_tokens=100,
            budget_tokens=2000,
        )
        assert _snapshot_severity(snapshot_healthy) == EvidenceSeverity.INFO

        snapshot_watch = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=1600,
            budget_tokens=2000,
        )
        assert _snapshot_severity(snapshot_watch) == EvidenceSeverity.INFO

        snapshot_degraded = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=2500,
            budget_tokens=2000,
        )
        assert _snapshot_severity(snapshot_degraded) == EvidenceSeverity.WARNING


class TestRelayPromptPayloadMeterEvidence:
    """Tests for Relay-visible prompt payload meter evidence."""

    def test_meter_evidence_uses_snapshot_label_budget_and_growth(self) -> None:
        plan = _make_plan(1)
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=12400,
            estimated_tokens=2500,
            budget_tokens=2000,
            prior_estimated_tokens=2000,
            queue_mode=True,
        )
        adapter = FakeModelAdapter(
            "response",
            metadata=_deepseek_authorized_metadata("fast"),
        )
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            adapter,
        )

        summary = execute_relay_plan_with_registry(
            plan,
            registry,
            payload_snapshots=(snapshot,),
            include_decision_record=True,
        )

        evidence = summary.results[0].payload_meter_evidence
        assert isinstance(evidence, RelayPromptPayloadMeterEvidence)
        assert summary.decision_record.payload_meter_evidence is evidence
        assert evidence.display_label == "(12.4k)"
        assert evidence.estimated_prompt_tokens == 2500
        assert evidence.prompt_budget_tokens == 2000
        assert evidence.budget_percent == 125.0
        assert evidence.payload_status == PayloadStatus.DEGRADED.value
        assert evidence.growth_delta_tokens == 500
        assert evidence.growth_delta_percent == 25.0
        assert evidence.q_mode is True
        assert evidence.selected_provider == "deepseek"
        assert evidence.exact_model_id == "deepseek-chat"
        assert evidence.provider_route_kind == "direct"
        assert "prompt_drag_over_budget" in evidence.prompt_drag_tags
        assert "prompt_drag_degraded" in evidence.prompt_drag_tags
        assert "prompt_payload_degraded" in evidence.blocker_tags
        assert evidence.payload_evidence_ref == (
            f"relay-payload-evidence:{_PACKET_ID}:"
            f"{plan.lanes[0].role.value}:{plan.lanes[0].preferred_model}"
        )
        assert adapter.received_payloads == [_PROMPT]

    def test_meter_consumer_view_is_stable_and_display_safe(self) -> None:
        plan = _make_plan(1)
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=800,
            estimated_tokens=200,
            budget_tokens=2000,
        )

        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("provider response should stay out"),
            payload_snapshots=(snapshot,),
            include_decision_record=True,
        )
        first = summary.prompt_payload_meter_consumer_view()
        second = summary.prompt_payload_meter_consumer_view()
        rendered = " ".join(str(value) for value in first.values())

        assert first == second
        assert first["heartbeat_id"] == plan.packet.packet_id
        assert first["consumer_view_kind"] == "relay_prompt_payload_meter"
        assert len(first["meter_evidence"]) == 1
        assert first["meter_evidence"][0]["display_label"] == "(under 1k)"
        assert first["meter_evidence"][0]["budget_percent"] == 10.0
        assert first["meter_evidence"][0]["payload_status"] == "healthy"
        assert first["decision_record_meter_evidence"] == first["meter_evidence"][0]
        assert first["prompt_drag_blocked"] is False
        assert _PROMPT not in rendered
        assert "provider response" not in rendered
        assert "credential" not in rendered.lower()

    def test_meter_fallback_snapshot_exists_for_dispatch_without_snapshot(self) -> None:
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(plan, _constant_model_call("ok"))

        evidence = summary.results[0].payload_meter_evidence
        assert evidence is not None
        assert evidence.display_label == "(under 1k)"
        assert evidence.estimated_prompt_tokens == plan.packet.prompt_tokens
        assert evidence.payload_status == "healthy"
        assert evidence.serialization_only is True
        assert _PROMPT not in " ".join(str(value) for value in evidence.to_dict().values())

    def test_meter_labels_rounding_and_missing_metadata_edges(self) -> None:
        plan = _make_plan(1)
        rounded = _build_prompt_payload_meter_evidence(
            plan,
            PromptPayloadSnapshot(
                raw_prompt_chars=999,
                estimated_tokens=1,
                budget_tokens=3,
                prior_estimated_tokens=4,
                queue_mode=True,
            ),
        )
        fallback = _build_prompt_payload_meter_evidence(
            plan,
            payload_snapshot=None,
            payload_evidence=RelayPromptPayloadEvidence(
                heartbeat_id=_PACKET_ID,
                lane_id="builder:edge-model",
                estimated_prompt_tokens=None,
                prompt_budget_tokens=None,
            ),
        )

        assert rounded.display_label == "(under 1k)"
        assert rounded.budget_percent == 33.3
        assert rounded.growth_delta_tokens == -3
        assert rounded.growth_delta_percent == -75.0
        assert fallback.estimated_prompt_tokens == plan.packet.prompt_tokens
        assert fallback.warning_tags == (
            "prompt_payload_snapshot_missing",
            "prompt_tokens_fallback_from_packet",
            "prompt_budget_unknown",
        )
        assert fallback.blocker_tags == ()

    def test_meter_q_mode_continuity_and_decision_record_error_fallback(self) -> None:
        plan = _make_plan(1)
        degraded = _build_prompt_payload_meter_evidence(
            plan,
            PromptPayloadSnapshot(
                raw_prompt_chars=12400,
                estimated_tokens=111,
                budget_tokens=1000,
                prior_estimated_tokens=100,
                queue_mode=True,
            ),
            RelayPromptPayloadEvidence(
                heartbeat_id=_PACKET_ID,
                route_id="tier-1:fast",
                lane_id="builder:deepseek-chat",
                selected_provider="deepseek",
                selected_model="deepseek-chat",
                capability_tier="candidate",
                provider_route_kind="direct",
                trust_state="candidate_reviewed",
                model_metadata_ref="model-harness:deepseek-chat",
                external_review_evidence_ref="review:deepseek-candidate",
                estimated_prompt_tokens=111,
                prompt_budget_tokens=1000,
                prompt_drag_tags=("prompt_drag_degraded", "prompt_drag_growth"),
            ),
        )

        def failing_model_call(payload: str) -> str:
            raise RuntimeError("provider unavailable")

        summary = execute_relay_dispatch_plan(
            plan,
            failing_model_call,
            include_decision_record=True,
        )
        consumer_view = summary.prompt_payload_meter_consumer_view()

        assert degraded.display_label == "(12.4k)"
        assert degraded.payload_status == "degraded"
        assert degraded.warning_tags == ("prompt_drag_growth",)
        assert degraded.blocker_tags == (
            "prompt_payload_degraded",
            "prompt_drag_degraded",
        )
        assert degraded.selected_provider == "deepseek"
        assert degraded.exact_model_id == "deepseek-chat"
        assert degraded.provider_route_kind == "direct"
        assert degraded.payload_evidence_ref == (
            f"relay-payload-evidence:{_PACKET_ID}:builder:deepseek-chat"
        )
        assert summary.results == ()
        assert summary.decision_record.payload_meter_evidence is not None
        assert consumer_view["meter_evidence"] == (
            summary.decision_record.payload_meter_evidence.to_dict(),
        )
        assert _PROMPT not in str(consumer_view)
        assert "provider unavailable" not in str(consumer_view)


class TestAdapterMetadata:
    def test_execution_result_without_metadata(self) -> None:
        result = RelayExecutionResult(
            role=ModelRole.BUILDER,
            preferred_model="gpt-4",
            output="output text",
        )
        assert result.adapter_metadata is None
        assert result.route_metadata is None
        assert result.payload_evidence is None

    def test_execution_result_with_metadata(self) -> None:
        metadata = ModelHarnessMetadata(
            provider_name="openai",
            model_name="gpt-4",
            capability_tier="premium",
            context_budget=8192,
            prompt_payload_budget=4096,
            trust_state="verified",
            requires_external_review=False,
        )
        result = RelayExecutionResult(
            role=ModelRole.BUILDER,
            preferred_model="gpt-4",
            output="output text",
            adapter_metadata=metadata,
        )
        assert result.adapter_metadata is metadata
        assert result.adapter_metadata.provider_name == "openai"
        assert result.adapter_metadata.model_name == "gpt-4"

    def test_fake_adapter_provides_default_metadata(self) -> None:
        adapter = FakeModelAdapter("ok")
        assert adapter.metadata is not None
        assert adapter.metadata.provider_name == "fake"
        assert adapter.metadata.model_name == "fake-model"
        assert adapter.metadata.capability_tier == "test"
        assert adapter.metadata.supports_payload_snapshot is False
        assert adapter.metadata.supports_response_hash is False

    def test_fake_adapter_with_custom_metadata(self) -> None:
        custom_metadata = ModelHarnessMetadata(
            provider_name="custom",
            model_name="custom-model",
            capability_tier="experimental",
            context_budget=2048,
            prompt_payload_budget=1024,
            trust_state="untested",
            requires_external_review=True,
        )
        adapter = FakeModelAdapter("ok", metadata=custom_metadata)
        assert adapter.metadata.provider_name == "custom"
        assert adapter.metadata.requires_external_review is True

    def test_execute_with_registry_includes_metadata_in_results(self) -> None:
        plan = _make_plan(1)
        adapter = FakeModelAdapter("response")
        registry = AdapterRegistry().register_model(plan.lanes[0].preferred_model, adapter)
        summary = execute_relay_plan_with_registry(plan, registry)
        assert len(summary.results) == 1
        assert summary.results[0].adapter_metadata is not None
        assert summary.results[0].adapter_metadata.provider_name == "fake"
        assert summary.results[0].route_metadata is not None
        assert summary.results[0].route_metadata.provider_name == "fake"
        assert summary.results[0].route_metadata.route_risk_tier == 1

    def test_execute_with_registry_multiple_lanes_includes_metadata_per_lane(self) -> None:
        plan = _make_plan(2)
        builder_adapter = FakeModelAdapter("builder-response")
        reviewer_adapter = FakeModelAdapter("reviewer-response")
        registry = (
            AdapterRegistry()
            .register_model(plan.lanes[0].preferred_model, builder_adapter)
            .register_model(plan.lanes[1].preferred_model, reviewer_adapter)
        )
        summary = execute_relay_plan_with_registry(plan, registry)
        assert len(summary.results) == 2
        assert summary.results[0].adapter_metadata is not None
        assert summary.results[1].adapter_metadata is not None
        assert summary.results[0].route_metadata is not None
        assert summary.results[1].route_metadata is not None

    def test_metadata_fields_present_in_result(self) -> None:
        plan = _make_plan(1)
        adapter = FakeModelAdapter("ok")
        registry = AdapterRegistry().register_model(plan.lanes[0].preferred_model, adapter)
        summary = execute_relay_plan_with_registry(plan, registry)
        metadata = summary.results[0].adapter_metadata

        assert metadata.provider_name is not None
        assert metadata.model_name is not None
        assert metadata.capability_tier is not None
        assert metadata.context_budget is not None
        assert metadata.prompt_payload_budget is not None
        assert metadata.trust_state is not None
        assert isinstance(metadata.requires_external_review, bool)

    def test_execute_dispatch_plan_without_registry_has_no_metadata(self) -> None:
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(plan, _constant_model_call("ok"))
        assert len(summary.results) == 1
        assert summary.results[0].adapter_metadata is None
        assert summary.results[0].route_metadata is None

    def test_adapter_metadata_immutable(self) -> None:
        metadata = ModelHarnessMetadata(
            provider_name="openai",
            model_name="gpt-4",
            capability_tier="premium",
            context_budget=8192,
            prompt_payload_budget=4096,
            trust_state="verified",
            requires_external_review=False,
        )
        with pytest.raises((AttributeError, TypeError)):
            metadata.provider_name = "anthropic"  # type: ignore[misc]

    def test_route_metadata_binding_uses_payload_snapshot(self) -> None:
        plan = _make_plan(1)
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=1600,
            budget_tokens=2000,
            prior_estimated_tokens=1500,
            queue_mode=True,
        )
        adapter = FakeModelAdapter("response")
        registry = AdapterRegistry().register_model(plan.lanes[0].preferred_model, adapter)
        summary = execute_relay_plan_with_registry(
            plan,
            registry,
            payload_snapshots=(snapshot,),
        )
        route_metadata = summary.results[0].route_metadata
        assert route_metadata is not None
        assert route_metadata.prompt_payload_status == "watch"
        assert route_metadata.prompt_payload_estimated_tokens == 1600
        assert route_metadata.prompt_payload_budget_percent == 80.0
        assert route_metadata.prompt_payload_growth_tokens == 100

    def test_route_metadata_binding_does_not_enter_model_payload(self) -> None:
        plan = _make_plan(1)
        adapter = FakeModelAdapter("response")
        registry = AdapterRegistry().register_model(plan.lanes[0].preferred_model, adapter)
        execute_relay_plan_with_registry(plan, registry)
        assert adapter.received_payloads == [plan.lanes[0].payload]
        assert "capability_tier" not in adapter.received_payloads[0]

    def test_payload_evidence_attached_to_registry_result_before_model_call_boundary(self) -> None:
        plan = _make_plan(1)
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=1600,
            budget_tokens=2000,
            prior_estimated_tokens=1500,
            queue_mode=True,
        )
        metadata = ModelHarnessMetadata(
            provider_name="deepseek",
            model_name="deepseek-chat",
            capability_tier="candidate-fast",
            context_budget=65536,
            prompt_payload_budget=57344,
            trust_state="candidate",
            requires_external_review=True,
            max_output_tokens=8192,
            tokenizer_family="deepseek",
            supports_completion_tokens=True,
            supports_latency_ms=True,
            supports_payload_snapshot=True,
            supports_response_hash=True,
            deepseek_candidate_state=_deepseek_authorized_candidate_state(),
        )
        registry = AdapterRegistry()
        for lane in plan.lanes:
            registry = registry.register_model(
                lane.preferred_model,
                FakeModelAdapter("response", metadata=metadata),
            )
        summary = execute_relay_plan_with_registry(
            plan,
            registry,
            payload_snapshots=(snapshot,),
        )
        evidence = summary.results[0].payload_evidence
        assert evidence is not None
        assert evidence.prompt_source == "relay"
        assert evidence.selected_provider == "deepseek"
        assert evidence.selected_model == "deepseek-chat"
        assert evidence.estimated_prompt_tokens == 1600
        assert evidence.prompt_budget_tokens == 2000
        assert evidence.model_context_window_tokens == 65536
        assert evidence.max_output_tokens == 8192
        assert evidence.budget_percent == 80.0
        assert evidence.budget_status == "watch"
        assert evidence.growth_state == "growing_expected"
        assert evidence.adapter_supports_snapshot is True
        assert evidence.supports_response_hash is True
        assert evidence.telemetry_error_tags == ()

    def test_payload_evidence_does_not_contain_raw_prompt_text(self) -> None:
        plan = _make_plan(1)
        metadata = ModelHarnessMetadata(
            provider_name="provider",
            model_name="model",
            capability_tier="standard",
            context_budget=8192,
            prompt_payload_budget=4096,
            trust_state="trusted",
            requires_external_review=False,
            supports_payload_snapshot=True,
        )
        registry = AdapterRegistry()
        for lane in plan.lanes:
            registry = registry.register_model(
                lane.preferred_model,
                FakeModelAdapter("response", metadata=metadata),
            )
        summary = execute_relay_plan_with_registry(plan, registry)
        evidence_dict = summary.results[0].payload_evidence.to_dict()
        evidence_text = " ".join(str(value) for value in evidence_dict.values())
        assert _PROMPT not in evidence_text
        assert summary.results[0].payload_evidence.prompt_payload_snapshot_hash is not None

    def test_payload_evidence_missing_telemetry_tags_without_adapter_metadata(self) -> None:
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("response"),
            include_decision_record=True,
        )
        evidence = summary.decision_record.payload_evidence
        assert evidence is not None
        assert "telemetry_unavailable" in evidence.telemetry_error_tags
        assert "provider_metadata_missing" in evidence.telemetry_error_tags
        assert "context_window_unknown" in evidence.telemetry_error_tags
        assert evidence.prompt_payload_snapshot_hash is None

    def test_payload_evidence_to_dict_stable_keys(self) -> None:
        evidence = RelayPromptPayloadEvidence(
            prompt_source="relay",
            heartbeat_id="pkt-1",
            selected_provider="provider",
            selected_model="model",
        )
        assert evidence.to_dict() == evidence.to_dict()
        assert tuple(evidence.to_dict().keys())[-1] == "telemetry_error_tags"


class TestRelayDispatchEnvelope:
    """Tests for safe provider-neutral dispatch envelope metadata."""

    def test_registry_result_dispatch_envelope_uses_exact_adapter_model_id(self) -> None:
        plan = _make_plan(1)
        metadata = ModelHarnessMetadata(
            provider_name="deepseek",
            model_name="deepseek-chat",
            capability_tier="candidate-fast",
            context_budget=65536,
            prompt_payload_budget=57344,
            trust_state="candidate",
            requires_external_review=True,
            supports_completion_tokens=True,
            supports_latency_ms=True,
            supports_payload_snapshot=True,
            supports_response_hash=True,
            deepseek_candidate_state=_deepseek_authorized_candidate_state(),
        )
        registry = AdapterRegistry()
        for lane in plan.lanes:
            registry = registry.register_model(
                lane.preferred_model,
                FakeModelAdapter("response", metadata=metadata),
            )

        summary = execute_relay_plan_with_registry(plan, registry)

        envelope = summary.results[0].dispatch_envelope
        assert isinstance(envelope, RelayDispatchEnvelope)
        assert envelope.requested_model_id == plan.lanes[0].preferred_model
        assert envelope.exact_model_id == "deepseek-chat"
        assert envelope.selected_provider == "deepseek"
        assert envelope.capability_tier == "candidate-fast"
        assert envelope.trust_state == "candidate"
        assert envelope.safe_to_dispatch is True

    def test_dispatch_envelope_references_payload_evidence_without_prompt_text(self) -> None:
        plan = _make_plan(1)
        metadata = ModelHarnessMetadata(
            provider_name="provider",
            model_name="exact-model",
            capability_tier="standard",
            context_budget=8192,
            prompt_payload_budget=4096,
            trust_state="trusted",
            requires_external_review=False,
            supports_payload_snapshot=True,
        )
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            FakeModelAdapter("raw response should stay out", metadata=metadata),
        )

        summary = execute_relay_plan_with_registry(plan, registry)

        envelope_dict = summary.results[0].dispatch_envelope.to_dict()
        envelope_text = " ".join(str(value) for value in envelope_dict.values())
        assert envelope_dict["payload_evidence_ref"] == (
            f"relay-payload-evidence:{_PACKET_ID}:"
            f"{plan.lanes[0].role.value}:{plan.lanes[0].preferred_model}"
        )
        assert _PROMPT not in envelope_text
        assert "secret" not in envelope_text.lower()
        assert "raw response" not in envelope_text

    def test_dispatch_envelope_without_adapter_metadata_blocks_unknowns(self) -> None:
        plan = _make_plan(2)

        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("response"),
            include_decision_record=True,
        )

        envelope = summary.decision_record.dispatch_envelope
        assert envelope is not None
        assert envelope.selected_provider is None
        assert envelope.exact_model_id == plan.lanes[0].preferred_model
        assert "provider_metadata_missing" in envelope.blocked_error_tags
        assert "context_window_unknown" in envelope.blocked_error_tags
        assert "vendor_unknown" in envelope.blocked_error_tags
        assert envelope.safe_to_dispatch is False

    def test_decision_record_dispatch_envelope_carries_aegis_blocker_tags(self) -> None:
        plan = _make_plan(2)

        record = _build_decision_record(
            plan,
            aegis_gate_decision="block",
            aegis_explanation="policy violation",
        )

        envelope = record.dispatch_envelope
        assert envelope is not None
        assert envelope.aegis_gate_decision == "block"
        assert "aegis_gate_blocked" in envelope.blocked_error_tags
        assert envelope.proof_required == tuple(plan.route.audit.proof_required)
        assert envelope.safe_to_dispatch is False

    def test_dispatch_envelope_binds_prompt_packet_proof_metadata(self) -> None:
        plan = _make_plan(3)
        metadata = ModelHarnessMetadata(
            provider_name="provider",
            model_name="exact-model",
            capability_tier="standard",
            context_budget=8192,
            prompt_payload_budget=4096,
            trust_state="trusted",
            requires_external_review=False,
            supports_completion_tokens=True,
            supports_latency_ms=True,
            supports_payload_snapshot=True,
            supports_response_hash=True,
        )
        registry = AdapterRegistry()
        for lane in plan.lanes:
            registry = registry.register_model(
                lane.preferred_model,
                FakeModelAdapter("response", metadata=metadata),
            )

        summary = execute_relay_plan_with_registry(
            plan,
            registry,
            proof_trail=ProofTrail(),
        )

        envelope = summary.results[0].dispatch_envelope
        packet_proof = plan.packet.proof_metadata
        assert envelope.packet_hash == packet_proof.packet_hash
        assert envelope.prompt_budget_ref == packet_proof.prompt_budget_ref
        assert envelope.source_lineage_compliant is True
        assert envelope.packet_proof_metadata_ref == f"prompt-packet-proof:{_PACKET_ID}"
        assert envelope.proof_required == packet_proof.proof_required

    def test_dispatch_envelope_carries_aegis_evidence_ids_from_proof_trail(self) -> None:
        plan = _make_plan(3)
        proof_trail = ProofTrail([
            AegisEvidence(
                id="aegis-proof-1",
                evidence_type=EvidenceType.BUILD_OUTPUT,
                severity=EvidenceSeverity.INFO,
                status=EvidenceStatus.OPEN,
                source="test",
                target="relay",
                summary="non-blocking proof",
            )
        ])
        metadata = ModelHarnessMetadata(
            provider_name="provider",
            model_name="exact-model",
            capability_tier="standard",
            context_budget=8192,
            prompt_payload_budget=4096,
            trust_state="trusted",
            requires_external_review=False,
            supports_completion_tokens=True,
            supports_latency_ms=True,
            supports_payload_snapshot=True,
            supports_response_hash=True,
        )
        registry = AdapterRegistry()
        for lane in plan.lanes:
            registry = registry.register_model(
                lane.preferred_model,
                FakeModelAdapter("response", metadata=metadata),
            )

        summary = execute_relay_plan_with_registry(
            plan,
            registry,
            proof_trail=proof_trail,
            include_decision_record=True,
        )

        assert summary.results[0].dispatch_envelope.aegis_evidence_ids == (
            "aegis-proof-1",
        )
        assert summary.decision_record.dispatch_envelope.aegis_evidence_ids == (
            "aegis-proof-1",
        )

    def test_dispatch_envelope_to_dict_has_stable_audit_keys(self) -> None:
        envelope = RelayDispatchEnvelope(
            envelope_id="relay-dispatch:pkt:builder:model",
            heartbeat_id="pkt",
            role="builder",
            requested_model_id="alias",
            exact_model_id="model",
            selected_provider="provider",
        )
        assert envelope.to_dict() == envelope.to_dict()
        assert tuple(envelope.to_dict().keys()) == (
            "envelope_id",
            "heartbeat_id",
            "role",
            "requested_model_id",
            "exact_model_id",
            "selected_provider",
            "route_id",
            "route_class",
            "route_kind",
            "risk_tier",
            "trust_state",
            "capability_tier",
            "payload_evidence_ref",
            "payload_snapshot_hash",
            "packet_hash",
            "prompt_budget_ref",
            "source_lineage_compliant",
            "packet_proof_metadata_ref",
            "aegis_gate_decision",
            "aegis_evidence_ids",
            "proof_required",
            "human_gate_required",
            "blocked_error_tags",
            "safe_to_dispatch",
            "transport_payload_kind",
            "audit_fields",
        )


class TestRelayDispatchMetadataEnvelope:
    """Tests for provider-neutral metadata-only dispatch envelopes."""

    def test_registry_result_metadata_envelope_uses_reviewed_model_metadata(self) -> None:
        plan = _make_plan(1)
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=7200,
            estimated_tokens=2100,
            budget_tokens=2000,
            prior_estimated_tokens=1500,
            queue_mode=True,
        )
        adapter = FakeModelAdapter(
            "response",
            metadata=deepseek_candidate_metadata_preset("fast"),
        )
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            adapter,
        )

        summary = execute_relay_plan_with_registry(
            plan,
            registry,
            payload_snapshots=(snapshot,),
        )

        # Candidate-state metadata is now refused at the pre-dispatch gate —
        # the envelope rides on the error and the adapter is never called.
        envelope = summary.errors[0].dispatch_metadata_envelope
        assert isinstance(envelope, RelayDispatchMetadataEnvelope)
        assert envelope.exact_model_id == "deepseek-chat"
        assert envelope.selected_provider == "deepseek"
        assert envelope.provider_route_kind == "direct"
        assert envelope.trust_mode == "direct"
        assert envelope.trust_state == "candidate"
        assert envelope.proof_strength == "weak"
        assert envelope.direct_endpoint_evidence_ref == (
            "deepseek-direct-endpoint:"
            "https://api.deepseek.com/v1/chat/completions"
        )
        assert envelope.validation_evidence_ref == (
            "deepseek-validation:level-0:metadata-only"
        )
        assert envelope.allowed_task_types == ("verify", "explain")
        assert "review_clearance" in envelope.blocked_task_types
        assert "aggregator_authority" in envelope.blocked_authority_tags
        assert envelope.max_risk_tier == 1
        assert envelope.context_window_tokens == 65536
        assert envelope.prompt_payload_budget_tokens == 57344
        assert envelope.prompt_payload_status == "degraded"
        assert envelope.growth_state == "over_budget"
        assert envelope.requires_external_review is True
        assert envelope.external_review_status == "pending"
        assert envelope.model_metadata_ref == "model-harness-metadata:deepseek:deepseek-chat"
        assert envelope.external_review_evidence_ref == (
            "external-review:deepseek:deepseek-chat:pending"
        )
        assert envelope.fail_closed_advisory is True
        assert "external_review_pending" in envelope.fail_closed_tags
        assert envelope.transport_payload_kind == "metadata_only"
        assert envelope.serialization_only is True
        assert envelope.metadata_transport_allowed is False
        assert envelope.retry_requires_fresh_metadata is True
        assert envelope.supports_payload_snapshot is True
        assert envelope.supports_response_hash is True
        assert adapter.received_payloads == []

    def test_metadata_envelope_without_route_metadata_has_fail_closed_advisories(self) -> None:
        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("response"),
        )

        envelope = summary.results[0].dispatch_metadata_envelope
        assert envelope is not None
        assert envelope.selected_provider is None
        assert envelope.exact_model_id == plan.lanes[0].preferred_model
        assert envelope.fail_closed_advisory is True
        assert "model_metadata_missing" in envelope.validation_tags
        assert "selected_provider_missing" in envelope.fail_closed_tags
        assert "provider_route_kind_unknown" in envelope.fail_closed_tags
        assert "context_window_unknown" in envelope.fail_closed_tags
        assert "vendor_unknown" in envelope.fail_closed_tags

    def test_metadata_envelope_helper_is_display_safe_and_stable(self) -> None:
        plan = _make_plan(1)
        payload_evidence = summary_evidence = RelayPromptPayloadEvidence(
            prompt_source="relay",
            heartbeat_id=plan.packet.packet_id,
            lane_id=f"{plan.lanes[0].role.value}:{plan.lanes[0].preferred_model}",
            selected_provider="provider",
            selected_model="exact-model",
            capability_tier="standard",
            provider_route_kind="direct",
            trust_state="trusted",
            model_context_window_tokens=8192,
            prompt_budget_tokens=4096,
            budget_status="healthy",
            external_review_status="passed",
            model_metadata_ref="model-harness-metadata:provider:exact-model",
        )
        dispatch_envelope = _build_dispatch_envelope(
            plan,
            lane_role=plan.lanes[0].role,
            requested_model_id=plan.lanes[0].preferred_model,
            payload_evidence=summary_evidence,
        )

        envelope = _build_dispatch_metadata_envelope(
            plan,
            lane_role=plan.lanes[0].role,
            requested_model_id=plan.lanes[0].preferred_model,
            payload_evidence=payload_evidence,
            dispatch_envelope=dispatch_envelope,
        )
        rendered = " ".join(str(value) for value in envelope.to_dict().values())

        assert envelope.to_dict() == envelope.to_dict()
        assert tuple(envelope.to_dict().keys()) == (
            "envelope_id",
            "heartbeat_id",
            "lane_id",
            "role",
            "requested_model_id",
            "exact_model_id",
            "selected_provider",
            "provider_route_kind",
            "trust_mode",
            "trust_state",
            "proof_strength",
            "capability_tier",
            "direct_endpoint_evidence_ref",
            "aggregator_evidence_ref",
            "validation_evidence_ref",
            "allowed_task_types",
            "blocked_task_types",
            "blocked_authority_tags",
            "max_risk_tier",
            "context_window_tokens",
            "prompt_payload_budget_tokens",
            "prompt_payload_status",
            "estimated_prompt_tokens",
            "prompt_budget_percent",
            "prompt_growth_tokens",
            "prompt_growth_percent",
            "growth_state",
            "prompt_drag_tags",
            "requires_external_review",
            "external_review_status",
            "model_metadata_ref",
            "external_review_evidence_ref",
            "payload_evidence_ref",
            "payload_snapshot_hash",
            "dispatch_envelope_ref",
            "packet_proof_metadata_ref",
            "supports_completion_tokens",
            "supports_latency_ms",
            "supports_payload_snapshot",
            "supports_response_hash",
            "validation_tags",
            "fail_closed_advisory",
            "fail_closed_tags",
            "metadata_transport_allowed",
            "retry_requires_fresh_metadata",
            "transport_payload_kind",
            "serialization_only",
            "deepseek_validation_disposition",
            "deepseek_transport_authority",
        )
        assert _PROMPT not in rendered
        assert "raw response" not in rendered
        assert "credential" not in rendered.lower()

    def test_summary_returns_metadata_envelopes(self) -> None:
        plan = _make_plan(1)
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            FakeModelAdapter("response", metadata=_deepseek_authorized_metadata("fast")),
        )

        summary = execute_relay_plan_with_registry(plan, registry)

        envelopes = summary.dispatch_metadata_envelopes()
        assert len(envelopes) == 1
        assert envelopes[0] is summary.results[0].dispatch_metadata_envelope
        assert envelopes[0].payload_evidence_ref == (
            f"relay-payload-evidence:{_PACKET_ID}:"
            f"{plan.lanes[0].role.value}:{plan.lanes[0].preferred_model}"
        )

    def test_metadata_envelope_preserves_payload_only_transport_boundary(self) -> None:
        plan = _make_plan(1)
        adapter = FakeModelAdapter(
            "response",
            metadata=_deepseek_authorized_metadata("default_quality"),
        )
        registry = AdapterRegistry().register_model(plan.lanes[0].preferred_model, adapter)

        summary = execute_relay_plan_with_registry(plan, registry)

        rendered_metadata = " ".join(
            str(value)
            for value in summary.dispatch_metadata_envelopes()[0].to_dict().values()
        )
        assert adapter.received_payloads == [plan.lanes[0].payload]
        assert "direct_endpoint_evidence_ref" not in adapter.received_payloads[0]
        assert "external_review" not in adapter.received_payloads[0]
        assert "credential" not in rendered_metadata.lower()
        assert "provider response" not in rendered_metadata.lower()
        assert "Polaris" not in rendered_metadata

    def test_decision_record_carries_metadata_envelope_consumer_view(self) -> None:
        plan = _make_plan(1)
        adapter = FakeModelAdapter(
            "response",
            metadata=_deepseek_authorized_metadata("fast"),
        )
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            adapter,
        )

        summary = execute_relay_plan_with_registry(
            plan,
            registry,
            include_decision_record=True,
        )

        result_envelope = summary.results[0].dispatch_metadata_envelope
        decision_envelope = summary.decision_record.dispatch_metadata_envelope
        assert decision_envelope is result_envelope
        assert decision_envelope.exact_model_id == "deepseek-chat"
        assert decision_envelope.provider_route_kind == "direct"
        assert decision_envelope.external_review_status == "passed"
        assert adapter.received_payloads == [_PROMPT]

    def test_summary_metadata_consumer_view_is_deterministic_and_display_safe(self) -> None:
        plan = _make_plan(1)
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            FakeModelAdapter(
                "raw provider response should stay private",
                metadata=deepseek_candidate_metadata_preset("fast"),
            ),
        )

        summary = execute_relay_plan_with_registry(
            plan,
            registry,
            include_decision_record=True,
        )
        first = summary.dispatch_metadata_consumer_view()
        second = summary.dispatch_metadata_consumer_view()
        rendered = " ".join(str(value) for value in first.values())

        assert first == second
        assert first["heartbeat_id"] == plan.packet.packet_id
        assert first["consumer_view_kind"] == "relay_dispatch_metadata"
        assert first["serialization_only"] is True
        assert len(first["envelopes"]) == 1
        assert first["decision_record_envelope"] == first["envelopes"][0]
        assert first["fail_closed_advisory"] is True
        assert "external_review_pending" in first["fail_closed_tags"]
        assert _PROMPT not in rendered
        assert "raw provider response" not in rendered
        assert "credential" not in rendered.lower()

    def test_summary_metadata_consumer_view_falls_back_to_decision_record(self) -> None:
        plan = _make_plan(2)
        record = _build_decision_record(plan)
        summary = RelayExecutionSummary(results=(), errors=(), decision_record=record)

        view = summary.dispatch_metadata_consumer_view()

        assert view["heartbeat_id"] == plan.packet.packet_id
        assert len(view["envelopes"]) == 1
        assert view["decision_record_envelope"] == view["envelopes"][0]
        assert "model_metadata_missing" in view["envelopes"][0]["validation_tags"]
        assert "vendor_unknown" in view["fail_closed_tags"]


class TestRelayProviderResultValidationEvidence:
    """Tests for display-safe post-adapter result validation evidence."""

    def test_registry_result_validation_evidence_carries_safe_metadata_only(self) -> None:
        plan = _make_plan(1)
        adapter = FakeModelAdapter(
            "raw provider response body secret should not appear",
            metadata=_deepseek_authorized_metadata("fast"),
        )
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            adapter,
        )

        summary = execute_relay_plan_with_registry(
            plan,
            registry,
            include_decision_record=True,
        )

        evidence = summary.results[0].provider_result_validation_evidence
        assert isinstance(evidence, RelayProviderResultValidationEvidence)
        assert summary.decision_record.provider_result_validation_evidence is evidence
        assert evidence.selected_provider == "deepseek"
        assert evidence.exact_model_id == "deepseek-chat"
        assert evidence.provider_route_kind == "direct"
        assert evidence.trust_state == "candidate"
        assert evidence.direct_endpoint_evidence_ref == (
            "deepseek-direct-endpoint:https://api.deepseek.com/v1/chat/completions"
        )
        assert evidence.external_review_status == "passed"
        assert evidence.output_length == len(
            "raw provider response body secret should not appear"
        )
        assert evidence.normalized_output_hash is not None
        assert evidence.response_hash_status == "computed"
        assert adapter.received_payloads == [_PROMPT]

        rendered = " ".join(str(value) for value in evidence.to_dict().values())
        assert _PROMPT not in rendered
        assert "raw provider response body" not in rendered
        assert "credential" not in rendered.lower()
        assert "Polaris" not in rendered

    def test_result_validation_evidence_empty_result_fails_closed(self) -> None:
        plan = _make_plan(1)
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            FakeModelAdapter("", metadata=_deepseek_authorized_metadata("fast")),
        )

        summary = execute_relay_plan_with_registry(plan, registry)

        evidence = summary.results[0].provider_result_validation_evidence
        assert evidence is not None
        assert evidence.response_hash_status == "empty"
        assert evidence.result_validation_status == "blocked"
        assert "adapter_result_empty" in evidence.blocker_tags
        assert evidence.usable_for_lane is False
        assert evidence.retry_requires_fresh_validation is True
        assert evidence.human_gate_required is True

    def test_result_validation_without_provider_metadata_fails_closed(self) -> None:
        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("safe output"),
            include_decision_record=True,
        )

        evidence = summary.results[0].provider_result_validation_evidence
        assert evidence is not None
        assert evidence.selected_provider is None
        assert evidence.exact_model_id == plan.lanes[0].preferred_model
        assert evidence.result_validation_status == "blocked"
        assert "model_metadata_missing" in evidence.blocker_tags
        assert "provider_route_kind_unknown" in evidence.blocker_tags
        assert "response_hash_telemetry_unavailable" in evidence.warning_tags
        assert summary.decision_record.provider_result_validation_evidence is evidence

    def test_result_validation_consumer_view_is_stable_and_display_safe(self) -> None:
        plan = _make_plan(1)
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            FakeModelAdapter(
                "provider output text must remain private",
                metadata=_deepseek_authorized_metadata("fast"),
            ),
        )

        summary = execute_relay_plan_with_registry(
            plan,
            registry,
            include_decision_record=True,
        )
        first = summary.provider_result_validation_consumer_view()
        second = summary.provider_result_validation_consumer_view()
        rendered = " ".join(str(value) for value in first.values())

        assert first == second
        assert first["heartbeat_id"] == plan.packet.packet_id
        assert first["consumer_view_kind"] == "relay_provider_result_validation"
        assert first["serialization_only"] is True
        assert len(first["result_evidence"]) == 1
        assert first["decision_record_result_evidence"] == first["result_evidence"][0]
        assert _PROMPT not in rendered
        assert "provider output text" not in rendered
        assert "credential" not in rendered.lower()


class TestRelayAegisProviderResultValidationAdvisory:
    """Tests for post-result provider validation Aegis advisory binding."""

    def test_advisory_empty_without_result_validation_evidence(self) -> None:
        summary = RelayExecutionSummary(results=(), errors=(), decision_record=None)

        advisory = summary.aegis_provider_result_validation_advisory()

        assert advisory == RelayAegisProviderResultValidationAdvisory()
        assert advisory.to_dict()["execution_mode"] == "display_advisory_only"
        assert advisory.to_dict()["aegis_execution_timing_unchanged"] is True

    def test_advisory_projects_result_blockers_for_future_aegis_input(self) -> None:
        plan = _make_plan(1)
        adapter = FakeModelAdapter(
            "private provider output must not appear",
            metadata=_deepseek_authorized_metadata("fast"),
        )
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            adapter,
        )

        summary = execute_relay_plan_with_registry(
            plan,
            registry,
            include_decision_record=True,
        )

        advisory = summary.aegis_provider_result_validation_advisory()
        result_evidence = summary.results[0].provider_result_validation_evidence
        assert advisory.advisory_id == f"relay-aegis-provider-result:{_PACKET_ID}"
        assert advisory.result_evidence_ids == (result_evidence.result_evidence_id,)
        assert advisory.exact_model_ids == ("deepseek-chat",)
        assert advisory.provider_route_kinds == ("direct",)
        assert advisory.trust_states == ("candidate",)
        assert advisory.external_review_statuses == ("passed",)
        assert advisory.response_hash_statuses == ("computed",)
        assert result_evidence.model_metadata_ref in advisory.proof_refs
        assert result_evidence.dispatch_metadata_envelope_ref in advisory.proof_refs
        assert advisory.adapter_boundary_unchanged is True
        assert advisory.aegis_execution_timing_unchanged is True
        assert adapter.received_payloads == [_PROMPT]

    def test_advisory_consumer_view_is_stable_and_display_safe(self) -> None:
        plan = _make_plan(1)
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            FakeModelAdapter(
                "raw provider output should stay private",
                metadata=deepseek_candidate_metadata_preset("fast"),
            ),
        )

        summary = execute_relay_plan_with_registry(
            plan,
            registry,
            include_decision_record=True,
        )
        first = summary.aegis_provider_result_validation_advisory().to_dict()
        second = summary.aegis_provider_result_validation_advisory().to_dict()
        rendered = " ".join(str(value) for value in first.values())

        assert first == second
        assert first["timing"] == "post_adapter_return"
        assert first["execution_mode"] == "display_advisory_only"
        assert first["serialization_only"] is True
        assert first["adapter_boundary_unchanged"] is True
        assert first["aegis_execution_timing_unchanged"] is True
        assert _PROMPT not in rendered
        assert "raw provider output" not in rendered
        assert "credential" not in rendered.lower()
        assert "Polaris" not in rendered

    def test_advisory_does_not_run_before_blocking_aegis_proof_gate(self) -> None:
        plan = _make_plan(3)
        adapter = FakeModelAdapter("should not run")

        with pytest.raises(RelayProofGateError):
            execute_relay_dispatch_plan(
                plan,
                adapter,
                proof_trail=self._blocking_proof_trail(),
                include_decision_record=True,
            )

        assert adapter.received_payloads == []

    def _blocking_proof_trail(self) -> ProofTrail:
        return ProofTrail([
            AegisEvidence(
                id="aegis-blocking-provider-result-precheck",
                evidence_type=EvidenceType.BUILD_OUTPUT,
                severity=EvidenceSeverity.ERROR,
                status=EvidenceStatus.OPEN,
                source="test",
                target="relay",
                summary="blocking proof gate remains pre-dispatch",
            )
        ])


class TestRelayDecisionRecord:
    """Tests for provider-neutral decision records exposing route rationale for Prime."""

    def test_decision_record_none_by_default(self) -> None:
        """Decision record is None when include_decision_record not set."""
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(plan, _constant_model_call("ok"))
        assert summary.decision_record is None

    def test_decision_record_generated_when_requested(self) -> None:
        """Decision record is generated when include_decision_record=True."""
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            include_decision_record=True,
        )
        assert summary.decision_record is not None
        assert isinstance(summary.decision_record, RelayDecisionRecord)

    def test_decision_record_captures_heartbeat_id(self) -> None:
        """Decision record heartbeat_id matches packet_id."""
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            include_decision_record=True,
        )
        assert summary.decision_record.heartbeat_id == plan.packet.packet_id

    def test_decision_record_captures_risk_tier(self) -> None:
        """Decision record risk_tier matches route."""
        for tier in (0, 1, 2, 3, 4):
            plan = _make_plan(tier)
            summary = execute_relay_dispatch_plan(
                plan,
                _constant_model_call("ok"),
                include_decision_record=True,
            )
            assert summary.decision_record.risk_tier == tier

    def test_decision_record_captures_session_action(self) -> None:
        """Decision record session_action maps from route.audit.session_action."""
        for tier in (1, 2, 3, 4):
            plan = _make_plan(tier)
            summary = execute_relay_dispatch_plan(
                plan,
                _constant_model_call("ok"),
                include_decision_record=True,
            )
            assert summary.decision_record.session_action == plan.route.audit.session_action.value

    def test_decision_record_captures_route_class(self) -> None:
        """Decision record route_class maps from route.audit.route_class."""
        for tier in (0, 1, 2, 3, 4):
            plan = _make_plan(tier)
            summary = execute_relay_dispatch_plan(
                plan,
                _constant_model_call("ok"),
                include_decision_record=True,
            )
            expected = plan.route.audit.route_class.value if plan.route.audit.route_class else None
            assert summary.decision_record.route_class == expected

    def test_decision_record_context_health_from_route(self) -> None:
        """Decision record context_health maps from route."""
        for tier in (0, 1, 2, 3, 4):
            plan = _make_plan(tier)
            summary = execute_relay_dispatch_plan(
                plan,
                _constant_model_call("ok"),
                include_decision_record=True,
            )
            assert summary.decision_record.context_health == plan.route.context_health.value

    def test_decision_record_latency_posture_from_route(self) -> None:
        """Decision record latency_posture maps from route."""
        for tier in (0, 1, 2, 3, 4):
            plan = _make_plan(tier)
            summary = execute_relay_dispatch_plan(
                plan,
                _constant_model_call("ok"),
                include_decision_record=True,
            )
            assert summary.decision_record.latency_posture == plan.route.latency_posture.value

    def test_decision_record_privacy_notes_from_route(self) -> None:
        """Decision record privacy_notes maps from route.privacy_level."""
        for tier in (0, 1, 2, 3, 4):
            plan = _make_plan(tier)
            summary = execute_relay_dispatch_plan(
                plan,
                _constant_model_call("ok"),
                include_decision_record=True,
            )
            assert summary.decision_record.privacy_notes == plan.route.privacy_level.value

    def test_decision_record_cost_posture_from_route(self) -> None:
        """Decision record cost_posture maps from route."""
        for tier in (0, 1, 2, 3, 4):
            plan = _make_plan(tier)
            summary = execute_relay_dispatch_plan(
                plan,
                _constant_model_call("ok"),
                include_decision_record=True,
            )
            assert summary.decision_record.cost_posture == plan.route.cost_posture.value

    def test_decision_record_trust_state_from_audit(self) -> None:
        """Decision record trust_state maps from audit."""
        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            include_decision_record=True,
        )
        assert summary.decision_record.trust_state == plan.route.audit.trust_state.value

    def test_decision_record_proof_required_from_audit(self) -> None:
        """Decision record proof_required captures audit tuple."""
        for tier in (1, 2, 3, 4):
            plan = _make_plan(tier)
            summary = execute_relay_dispatch_plan(
                plan,
                _constant_model_call("ok"),
                include_decision_record=True,
            )
            assert summary.decision_record.proof_required == plan.route.audit.proof_required

    def test_decision_record_binds_prompt_packet_proof_metadata(self) -> None:
        """Decision record exposes packet proof metadata without nested envelope access."""
        plan = _make_plan(3)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            proof_trail=ProofTrail(),
            include_decision_record=True,
        )

        record = summary.decision_record
        packet_proof = plan.packet.proof_metadata
        assert record.packet_hash == packet_proof.packet_hash
        assert record.prompt_budget_ref == packet_proof.prompt_budget_ref
        assert record.source_lineage_compliant is True
        assert record.packet_proof_metadata_ref == f"prompt-packet-proof:{_PACKET_ID}"
        assert record.packet_proof_blocked_tags == ()

    def test_decision_record_uses_packet_proof_required(self) -> None:
        plan = _make_plan(3)
        record = _build_decision_record(plan)

        assert record.proof_required == plan.packet.proof_metadata.proof_required
        assert record.proof_required == tuple(plan.route.audit.proof_required)

    def test_decision_record_carries_aegis_ids_from_dispatch_envelope(self) -> None:
        plan = _make_plan(3)
        proof_trail = ProofTrail([
            AegisEvidence(
                id="packet-proof-aegis-1",
                evidence_type=EvidenceType.BUILD_OUTPUT,
                severity=EvidenceSeverity.INFO,
                status=EvidenceStatus.OPEN,
                source="test",
                target="relay",
                summary="non-blocking proof",
            )
        ])
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            proof_trail=proof_trail,
            include_decision_record=True,
        )

        assert summary.decision_record.aegis_evidence_ids == (
            "packet-proof-aegis-1",
        )

    def test_decision_record_packet_proof_fields_do_not_contain_raw_prompt(self) -> None:
        plan = _make_plan(2)
        record = _build_decision_record(plan)
        proof_text = " ".join(
            str(value)
            for value in (
                record.packet_hash,
                record.prompt_budget_ref,
                record.packet_proof_metadata_ref,
                record.packet_proof_blocked_tags,
                record.aegis_evidence_ids,
            )
        )
        assert _PROMPT not in proof_text

    def test_decision_record_fallback_blockers_from_audit(self) -> None:
        """Decision record fallback_blockers captures audit tuple plus vendor/model_id unknowns for Tier 2+."""
        from meridian_core.relay import ModelRole
        for tier in (1, 2, 3, 4):
            plan = _make_plan(tier)
            summary = execute_relay_dispatch_plan(
                plan,
                _constant_model_call("ok"),
                include_decision_record=True,
            )
            expected_blockers = list(plan.route.audit.fallback_blockers)
            # Tier 2+ without adapter metadata adds vendor_unknown as explicit blocker
            if tier >= 2:
                expected_blockers.append("vendor_unknown")
            # Check if plan has a builder lane for model_id extraction
            has_builder_lane = any(lane.role == ModelRole.BUILDER for lane in plan.lanes)
            if tier >= 2 and not has_builder_lane:
                expected_blockers.append("model_id_unknown")
            assert summary.decision_record.fallback_blockers == tuple(expected_blockers)

    def test_decision_record_human_gate_required_from_route(self) -> None:
        """Decision record human_gate_required matches route requirement."""
        plan = _make_plan(4)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            include_decision_record=True,
        )
        assert summary.decision_record.human_gate_required == plan.route.requires_human_gate

    def test_decision_record_dual_lane_required_from_route(self) -> None:
        """Decision record dual_lane_required matches route.requires_independence."""
        plan2 = _make_plan(2)
        summary2 = execute_relay_dispatch_plan(
            plan2,
            _constant_model_call("ok"),
            include_decision_record=True,
        )
        assert summary2.decision_record.dual_lane_required == plan2.route.requires_independence

        plan3 = _make_plan(3)
        summary3 = execute_relay_dispatch_plan(
            plan3,
            _constant_model_call("ok"),
            include_decision_record=True,
        )
        assert summary3.decision_record.dual_lane_required == plan3.route.requires_independence

    def test_decision_record_lane_independence_reason_for_tier3(self) -> None:
        """Decision record lane_independence_reason populated for Tier 3 with blockers."""
        plan = _make_plan(3)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            include_decision_record=True,
        )
        if plan.route.requires_independence and "dual_lane_independence_required" in plan.route.audit.fallback_blockers:
            assert "Tier 3" in summary.decision_record.lane_independence_reason
            assert "dual-lane independence" in summary.decision_record.lane_independence_reason

    def test_decision_record_vendor_none_for_tier0_1(self) -> None:
        """Decision record vendor is None for Tier 0-1 (low-risk, no block)."""
        for tier in (0, 1):
            plan = _make_plan(tier)
            summary = execute_relay_dispatch_plan(
                plan,
                _constant_model_call("ok"),
                include_decision_record=True,
            )
            assert summary.decision_record.vendor is None

    def test_decision_record_vendor_unknown_for_tier2plus_without_metadata(self) -> None:
        """Decision record vendor is 'unknown' for Tier 2+ without adapter metadata."""
        for tier in (2, 3, 4):
            plan = _make_plan(tier)
            summary = execute_relay_dispatch_plan(
                plan,
                _constant_model_call("ok"),
                include_decision_record=True,
            )
            assert summary.decision_record.vendor == "unknown"

    def test_decision_record_model_id_populated_from_preferred_model(self) -> None:
        """Decision record model_id is populated from lane preferred_model when available."""
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            include_decision_record=True,
        )
        assert summary.decision_record.model_id == plan.lanes[0].preferred_model

    def test_decision_record_model_id_unknown_for_empty_plan(self) -> None:
        """Decision record model_id is 'unknown' for Tier 2+ with no lanes."""
        plan = _make_plan(2)
        # Manually create a plan with no lanes
        from meridian_core.relay_dispatch import RelayDispatchPlan
        empty_plan = RelayDispatchPlan(route=plan.route, packet=plan.packet, lanes=())
        record = _build_decision_record(empty_plan)
        assert record.model_id == "unknown"

    def test_decision_record_project_is_none_context_dependent(self) -> None:
        """Decision record project is None (context-dependent metadata)."""
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            include_decision_record=True,
        )
        assert summary.decision_record.project is None

    def test_decision_record_surface_mode_is_none_context_dependent(self) -> None:
        """Decision record surface_mode is None (context-dependent metadata)."""
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            include_decision_record=True,
        )
        assert summary.decision_record.surface_mode is None

    def test_decision_record_intent_is_none_context_dependent(self) -> None:
        """Decision record intent is None (context-dependent metadata)."""
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            include_decision_record=True,
        )
        assert summary.decision_record.intent is None

    def test_decision_record_account_or_api_source_from_precedence(self) -> None:
        """Decision record account_or_api_source maps from route_precedence."""
        for tier in (1, 2, 3, 4):
            plan = _make_plan(tier)
            summary = execute_relay_dispatch_plan(
                plan,
                _constant_model_call("ok"),
                include_decision_record=True,
            )
            if plan.route.audit.route_precedence:
                expected = plan.route.audit.route_precedence[0].value
            else:
                expected = "unknown"
            assert summary.decision_record.account_or_api_source == expected

    def test_decision_record_fallback_allowed_matches_blockers(self) -> None:
        """Decision record fallback_allowed=False when fallback_blockers present."""
        for tier in (0, 1, 2, 3, 4):
            plan = _make_plan(tier)
            summary = execute_relay_dispatch_plan(
                plan,
                _constant_model_call("ok"),
                include_decision_record=True,
            )
            has_blockers = len(plan.route.audit.fallback_blockers) > 0
            assert summary.decision_record.fallback_allowed == (not has_blockers)

    def test_decision_record_observability_fields_from_telemetry(self) -> None:
        """Decision record observability_fields maps from audit.telemetry_required."""
        for tier in (0, 1, 2, 3, 4):
            plan = _make_plan(tier)
            summary = execute_relay_dispatch_plan(
                plan,
                _constant_model_call("ok"),
                include_decision_record=True,
            )
            assert summary.decision_record.observability_fields == plan.route.audit.telemetry_required

    def test_decision_record_telemetry_required_from_audit(self) -> None:
        """Decision record telemetry_required captures audit tuple."""
        for tier in (0, 1, 2, 3, 4):
            plan = _make_plan(tier)
            summary = execute_relay_dispatch_plan(
                plan,
                _constant_model_call("ok"),
                include_decision_record=True,
            )
            assert summary.decision_record.telemetry_required == plan.route.audit.telemetry_required

    def test_decision_record_explanation_includes_risk_tier(self) -> None:
        """Decision record explanation_for_prime includes risk tier."""
        for tier in (0, 1, 2, 3, 4):
            plan = _make_plan(tier)
            summary = execute_relay_dispatch_plan(
                plan,
                _constant_model_call("ok"),
                include_decision_record=True,
            )
            assert f"Risk tier {tier}" in summary.decision_record.explanation_for_prime

    def test_decision_record_explanation_includes_route_reason(self) -> None:
        """Decision record explanation_for_prime includes route reason."""
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            include_decision_record=True,
        )
        assert plan.route.reason in summary.decision_record.explanation_for_prime

    def test_decision_record_explanation_includes_context_health(self) -> None:
        """Decision record explanation_for_prime includes context health."""
        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            include_decision_record=True,
        )
        assert plan.route.context_health.value in summary.decision_record.explanation_for_prime

    def test_decision_record_prompt_payload_status_when_snapshot_present(self) -> None:
        """Decision record prompt_payload_status maps from snapshot when available."""
        plan = _make_plan(1)
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=1000,
            estimated_tokens=300,
            budget_tokens=4000,
        )
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            payload_snapshots=(snapshot,),
            include_decision_record=True,
        )
        assert summary.decision_record.prompt_payload_status == snapshot.status.value

    def test_decision_record_immutable(self) -> None:
        """Decision record is frozen and immutable."""
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            include_decision_record=True,
        )
        with pytest.raises((AttributeError, TypeError)):
            summary.decision_record.risk_tier = 999  # type: ignore[misc]

    def test_decision_record_with_registry(self) -> None:
        """Decision record generated correctly with registry-based execution."""
        plan = _make_plan(2)
        registry = _make_registry_for_tier(2)
        summary = execute_relay_plan_with_registry(
            plan,
            registry,
            include_decision_record=True,
        )
        assert summary.decision_record is not None
        assert summary.decision_record.risk_tier == 2

    def test_decision_record_with_policy(self) -> None:
        """Decision record generated correctly with policy-based execution."""
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan_with_policy(
            plan,
            _constant_model_call("ok"),
            proof_trail=_clean_proof_trail("packet-proof-decision-record"),
            include_decision_record=True,
        )
        assert summary.decision_record is not None
        assert summary.decision_record.risk_tier == 1

    def test_backward_compatible_execution_without_decision_record(self) -> None:
        """Existing code without include_decision_record still works."""
        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan(plan, _constant_model_call("ok"))
        assert len(summary.results) == len(plan.lanes)
        assert summary.decision_record is None

    def test_decision_record_all_fields_assigned(self) -> None:
        """Decision record has all required fields with non-None or sensible defaults."""
        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            include_decision_record=True,
        )
        record = summary.decision_record
        assert record.heartbeat_id is not None
        assert record.risk_tier is not None
        assert record.session_action is not None
        assert record.context_health is not None
        assert record.cost_posture is not None
        assert record.latency_posture is not None
        assert record.privacy_notes is not None
        assert isinstance(record.dual_lane_required, bool)
        assert isinstance(record.human_gate_required, bool)
        assert isinstance(record.fallback_allowed, bool)
        assert isinstance(record.proof_required, tuple)
        assert isinstance(record.fallback_blockers, tuple)
        assert isinstance(record.observability_fields, tuple)
        assert isinstance(record.telemetry_required, tuple)
        assert record.packet_hash is not None
        assert record.prompt_budget_ref is not None
        assert isinstance(record.source_lineage_compliant, bool)
        assert record.packet_proof_metadata_ref is not None
        assert isinstance(record.packet_proof_blocked_tags, tuple)

    def test_decision_record_vendor_from_adapter_metadata(self) -> None:
        """Decision record vendor populated from adapter metadata when available."""
        plan = _make_plan(2)
        registry = _make_registry_for_tier(2)
        summary = execute_relay_plan_with_registry(
            plan,
            registry,
            include_decision_record=True,
        )
        assert summary.decision_record.vendor == "fake"  # FakeModelAdapter.metadata.provider_name
        assert summary.decision_record.route_metadata is not None
        assert summary.decision_record.route_metadata.provider_name == "fake"
        assert summary.decision_record.route_metadata.route_risk_tier == 2

    def test_decision_record_route_metadata_carries_capability_and_budget(self) -> None:
        plan = _make_plan(1)
        metadata = ModelHarnessMetadata(
            provider_name="openai",
            model_name=plan.lanes[0].preferred_model,
            capability_tier="premium",
            context_budget=8192,
            prompt_payload_budget=4096,
            trust_state="trusted",
            requires_external_review=False,
        )
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=1600,
            budget_tokens=2000,
        )
        adapter = FakeModelAdapter("response", metadata=metadata)
        registry = AdapterRegistry().register_model(plan.lanes[0].preferred_model, adapter)
        summary = execute_relay_plan_with_registry(
            plan,
            registry,
            payload_snapshots=(snapshot,),
            include_decision_record=True,
        )
        route_metadata = summary.decision_record.route_metadata
        assert route_metadata is not None
        assert route_metadata.capability_tier == "premium"
        assert route_metadata.context_budget == 8192
        assert route_metadata.prompt_payload_budget == 4096
        assert route_metadata.prompt_payload_status == "watch"
        assert summary.decision_record.prompt_payload_status == "watch"

    def test_decision_record_carries_payload_evidence_from_first_lane(self) -> None:
        plan = _make_plan(1)
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=1600,
            budget_tokens=2000,
            prior_estimated_tokens=1500,
            queue_mode=True,
        )
        metadata = ModelHarnessMetadata(
            provider_name="provider",
            model_name=plan.lanes[0].preferred_model,
            capability_tier="standard",
            context_budget=8192,
            prompt_payload_budget=4096,
            trust_state="trusted",
            requires_external_review=False,
            supports_completion_tokens=True,
            supports_latency_ms=True,
            supports_payload_snapshot=True,
            supports_response_hash=True,
        )
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            FakeModelAdapter("response", metadata=metadata),
        )
        summary = execute_relay_plan_with_registry(
            plan,
            registry,
            payload_snapshots=(snapshot,),
            include_decision_record=True,
        )
        evidence = summary.decision_record.payload_evidence
        assert evidence is not None
        assert evidence.heartbeat_id == plan.packet.packet_id
        assert evidence.lane_id == f"{plan.lanes[0].role.value}:{plan.lanes[0].preferred_model}"
        assert evidence.selected_provider == "provider"
        assert evidence.budget_status == "watch"
        assert evidence.telemetry_error_tags == ()
        assert _PROMPT not in " ".join(str(value) for value in evidence.to_dict().values())

    def test_payload_evidence_carries_model_capability_metadata(self) -> None:
        plan = _make_plan(1)
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=7200,
            estimated_tokens=2100,
            budget_tokens=2000,
            prior_estimated_tokens=1200,
            queue_mode=True,
        )
        metadata = deepseek_candidate_metadata_preset("fast")
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            FakeModelAdapter("response", metadata=metadata),
        )

        summary = execute_relay_plan_with_registry(
            plan,
            registry,
            payload_snapshots=(snapshot,),
            include_decision_record=True,
        )

        evidence = summary.decision_record.payload_evidence
        assert evidence.capability_tier == "candidate-fast"
        assert evidence.provider_route_kind == "direct"
        assert evidence.trust_state == "candidate"
        assert evidence.requires_external_review is True
        assert evidence.external_review_status == "pending"
        assert evidence.model_metadata_ref == "model-harness-metadata:deepseek:deepseek-chat"
        assert evidence.external_review_evidence_ref == (
            "external-review:deepseek:deepseek-chat:pending"
        )
        assert evidence.prompt_drag_tags == (
            "prompt_drag_over_budget",
            "prompt_drag_degraded",
            "prompt_drag_growth",
        )
        assert "budget_exceeded" in evidence.telemetry_error_tags
        rendered = " ".join(str(value) for value in evidence.to_dict().values())
        assert _PROMPT not in rendered
        assert "credential" not in rendered

    def test_execution_summary_model_capability_metadata_summary(self) -> None:
        plan = _make_plan(1)
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=1600,
            budget_tokens=2000,
            prior_estimated_tokens=1600,
            queue_mode=True,
        )
        metadata = ModelHarnessMetadata(
            provider_name="provider",
            model_name=plan.lanes[0].preferred_model,
            capability_tier="standard",
            context_budget=8192,
            prompt_payload_budget=4096,
            trust_state="trusted",
            requires_external_review=False,
            supports_completion_tokens=True,
            supports_latency_ms=True,
            supports_payload_snapshot=True,
            supports_response_hash=True,
        )
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            FakeModelAdapter("response", metadata=metadata),
        )

        summary = execute_relay_plan_with_registry(
            plan,
            registry,
            payload_snapshots=(snapshot,),
            include_decision_record=True,
        )
        capability_summary = summary.model_capability_metadata_summary()
        first = capability_summary.to_dict()
        second = summary.model_capability_metadata_summary().to_dict()

        assert isinstance(capability_summary, RelayModelCapabilityMetadataSummary)
        assert first == second
        assert first["missing_metadata_tags"] == ()
        assert len(first["lanes"]) == 1
        lane = first["lanes"][0]
        assert lane["selected_provider"] == "provider"
        assert lane["exact_model_id"] == plan.lanes[0].preferred_model
        assert lane["capability_tier"] == "standard"
        assert lane["trust_state"] == "trusted"
        assert lane["context_window_tokens"] == 8192
        assert lane["prompt_payload_budget_tokens"] == 4096
        assert lane["prompt_payload_status"] == "watch"
        assert lane["prompt_drag_tags"] == ("prompt_drag_flat",)
        assert lane["requires_external_review"] is False
        assert lane["external_review_status"] == "not_required"
        assert lane["model_metadata_ref"] == (
            f"model-harness-metadata:provider:{plan.lanes[0].preferred_model}"
        )
        assert lane["payload_evidence_ref"] == (
            f"relay-payload-evidence:{plan.packet.packet_id}:"
            f"{plan.lanes[0].role.value}:{plan.lanes[0].preferred_model}"
        )
        rendered = " ".join(str(value) for value in first.values())
        assert _PROMPT not in rendered

    def test_decision_record_route_metadata_uses_first_lane_even_if_first_lane_errors(self) -> None:
        plan = _make_plan(2)
        first_metadata = ModelHarnessMetadata(
            provider_name="first-provider",
            model_name=plan.lanes[0].preferred_model,
            capability_tier="first-tier",
            context_budget=8192,
            prompt_payload_budget=4096,
            trust_state="trusted",
            requires_external_review=False,
        )
        second_metadata = ModelHarnessMetadata(
            provider_name="second-provider",
            model_name=plan.lanes[1].preferred_model,
            capability_tier="second-tier",
            context_budget=8192,
            prompt_payload_budget=4096,
            trust_state="trusted",
            requires_external_review=False,
        )
        class RaisingAdapter:
            @property
            def metadata(self) -> ModelHarnessMetadata:
                return first_metadata

            def __call__(self, payload: str) -> str:
                raise RuntimeError("first lane failed")

        registry = (
            AdapterRegistry()
            .register_model(plan.lanes[0].preferred_model, RaisingAdapter())
            .register_model(plan.lanes[1].preferred_model, FakeModelAdapter("second", metadata=second_metadata))
        )
        summary = execute_relay_plan_with_registry(
            plan,
            registry,
            include_decision_record=True,
        )
        assert len(summary.errors) == 1
        assert summary.decision_record.route_metadata is not None
        assert summary.decision_record.route_metadata.provider_name == "first-provider"
        assert summary.decision_record.route_metadata.capability_tier == "first-tier"

    def test_decision_record_model_id_from_lane_preferred_model(self) -> None:
        """Decision record model_id extracted from builder lane preferred_model."""
        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            include_decision_record=True,
        )
        builder_lane = next(l for l in plan.lanes if l.role.value == "builder")
        assert summary.decision_record.model_id == builder_lane.preferred_model

    def test_decision_record_stop_condition_tier3_dual_lane_independence_missing(self) -> None:
        """Decision record flags stop condition when Tier 3 dual-lane independence missing."""
        from meridian_core.relay_dispatch import RelayDispatchLane, RelayDispatchPlan

        plan = _make_plan(3)
        # Create a plan variant with non-independent lanes
        non_independent_lanes = tuple(
            RelayDispatchLane(
                role=lane.role,
                preferred_model=lane.preferred_model,
                independent=False,  # Override independence
                payload=lane.payload,
            )
            for lane in plan.lanes
        )
        bad_plan = RelayDispatchPlan(route=plan.route, packet=plan.packet, lanes=non_independent_lanes)

        record = _build_decision_record(bad_plan)
        assert "tier3_dual_lane_independence_missing" in record.fallback_blockers
        assert not record.fallback_allowed

    def test_decision_record_explanation_includes_vendor_binding_status(self) -> None:
        """Decision record explanation mentions vendor binding status."""
        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            include_decision_record=True,
        )
        assert "Vendor:" in summary.decision_record.explanation_for_prime

    def test_decision_record_fallback_blockers_tuple_format(self) -> None:
        """Decision record fallback_blockers is always tuple, even with additions."""
        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("ok"),
            include_decision_record=True,
        )
        assert isinstance(summary.decision_record.fallback_blockers, tuple)

    def test_decision_record_vendor_unknown_becomes_blocker_for_tier2plus(self) -> None:
        """Decision record treats vendor='unknown' as explicit fallback blocker for Tier 2+."""
        from meridian_core.relay_dispatch import RelayDispatchLane, RelayDispatchPlan

        plan = _make_plan(2)
        # Create plan with no lanes (clean audit, no builder lane to extract model_id from)
        empty_lanes = ()
        empty_plan = RelayDispatchPlan(route=plan.route, packet=plan.packet, lanes=empty_lanes)

        # Build with no adapter metadata (so vendor="unknown" gets set)
        record = _build_decision_record(empty_plan)

        # vendor should be "unknown" due to Tier 2+ with no metadata
        assert record.vendor == "unknown"
        # This unknown should be a fallback blocker
        assert "vendor_unknown" in record.fallback_blockers
        assert not record.fallback_allowed

    def test_decision_record_model_id_unknown_becomes_blocker_for_tier2plus(self) -> None:
        """Decision record treats model_id='unknown' as explicit fallback blocker for Tier 2+."""
        from meridian_core.relay_dispatch import RelayDispatchLane, RelayDispatchPlan

        plan = _make_plan(2)
        # Create plan with non-builder lanes only (no builder lane to extract model_id from)
        non_builder_lanes = tuple(
            RelayDispatchLane(
                role=ModelRole.REVIEWER,  # Not builder
                preferred_model=lane.preferred_model,
                independent=lane.independent,
                payload=lane.payload,
            )
            for lane in plan.lanes
            if lane.role.value != "builder"
        )
        if not non_builder_lanes:
            # If test setup doesn't have non-builder lanes, create one
            builder_lane = next(l for l in plan.lanes if l.role.value == "builder")
            non_builder_lanes = (
                RelayDispatchLane(
                    role=ModelRole.REVIEWER,
                    preferred_model=builder_lane.preferred_model,
                    independent=builder_lane.independent,
                    payload=builder_lane.payload,
                ),
            )

        no_builder_plan = RelayDispatchPlan(route=plan.route, packet=plan.packet, lanes=non_builder_lanes)

        record = _build_decision_record(no_builder_plan)

        # model_id should be "unknown" due to Tier 2+ with no builder lane
        assert record.model_id == "unknown"
        # This unknown should be a fallback blocker
        assert "model_id_unknown" in record.fallback_blockers
        assert not record.fallback_allowed

    def test_decision_record_aegis_gate_decision_optional(self) -> None:
        """Decision record has optional aegis_gate_decision field for gate outcomes."""
        plan = _make_plan(2)
        record = _build_decision_record(plan)
        # Should have aegis_gate_decision field
        assert hasattr(record, "aegis_gate_decision")
        # Defaults to None when not provided
        assert record.aegis_gate_decision is None

    def test_decision_record_aegis_gate_decision_immutable(self) -> None:
        """Decision record aegis_gate_decision is immutable (frozen dataclass)."""
        plan = _make_plan(2)
        record = _build_decision_record(plan)
        # Should not be able to modify
        with pytest.raises(AttributeError):
            record.aegis_gate_decision = "allow"  # type: ignore

    def test_decision_record_aegis_evidence_ids_optional(self) -> None:
        """Decision record has optional aegis_evidence_ids field for evidence references."""
        plan = _make_plan(2)
        record = _build_decision_record(plan)
        # Should have aegis_evidence_ids field
        assert hasattr(record, "aegis_evidence_ids")
        # Defaults to empty tuple when not provided
        assert record.aegis_evidence_ids == ()

    def test_decision_record_aegis_waiver_present_optional(self) -> None:
        """Decision record has optional aegis_waiver_present field for waiver tracking."""
        plan = _make_plan(2)
        record = _build_decision_record(plan)
        # Should have aegis_waiver_present field
        assert hasattr(record, "aegis_waiver_present")
        # Defaults to False when not provided
        assert record.aegis_waiver_present is False

    def test_decision_record_aegis_gate_severity_optional(self) -> None:
        """Decision record has optional aegis_gate_severity field for severity level."""
        plan = _make_plan(2)
        record = _build_decision_record(plan)
        # Should have aegis_gate_severity field
        assert hasattr(record, "aegis_gate_severity")
        # Defaults to None when not provided
        assert record.aegis_gate_severity is None

    def test_decision_record_aegis_explanation_optional(self) -> None:
        """Decision record has optional aegis_explanation field for gate explanation."""
        plan = _make_plan(2)
        record = _build_decision_record(plan)
        # Should have aegis_explanation field
        assert hasattr(record, "aegis_explanation")
        # Defaults to empty string when not provided
        assert record.aegis_explanation == ""

    def test_decision_record_aegis_block_gate_adds_fallback_blocker(self) -> None:
        """Decision record treats Aegis 'block' gate decision as explicit fallback blocker."""
        plan = _make_plan(2)
        record = _build_decision_record(
            plan,
            aegis_gate_decision="block",
            aegis_explanation="security policy violation",
        )
        # block decision should add fallback blocker
        assert "aegis_gate_blocked" in record.fallback_blockers
        assert not record.fallback_allowed
        # Aegis explanation should be stored
        assert record.aegis_gate_decision == "block"
        assert record.aegis_explanation == "security policy violation"
        # Explanation should include Aegis context
        assert "Aegis" in record.explanation_for_prime
        assert "block" in record.explanation_for_prime

    def test_decision_record_aegis_human_gate_adds_fallback_blocker(self) -> None:
        """Decision record treats Aegis 'human_gate' decision as explicit fallback blocker."""
        plan = _make_plan(2)
        record = _build_decision_record(
            plan,
            aegis_gate_decision="human_gate",
            aegis_explanation="escalation required",
        )
        # human_gate decision should add fallback blocker
        assert "aegis_human_gate_required" in record.fallback_blockers
        assert not record.fallback_allowed
        # Aegis explanation should be stored
        assert record.aegis_gate_decision == "human_gate"
        assert record.aegis_explanation == "escalation required"
        # Explanation should include Aegis context
        assert "Aegis" in record.explanation_for_prime
        assert "human_gate" in record.explanation_for_prime
        # Note: human_gate_required field represents route base requirement only;
        # Aegis gate decisions are captured separately in fallback_blockers and explanation.
        # The explicit "aegis_human_gate_required" blocker serves as the downstream signal.

    def test_decision_record_aegis_demote_adds_explanation_only(self) -> None:
        """Decision record treats Aegis 'demote' decision as non-silent demotion."""
        plan = _make_plan(2)
        record = _build_decision_record(
            plan,
            aegis_gate_decision="demote",
            aegis_explanation="cost constraint triggered",
        )
        # demote decision should NOT add fallback blocker
        assert "aegis_gate_blocked" not in record.fallback_blockers
        assert "aegis_human_gate_required" not in record.fallback_blockers
        # Aegis decision should be stored
        assert record.aegis_gate_decision == "demote"
        assert record.aegis_explanation == "cost constraint triggered"
        # Explanation should note the demotion
        assert "Aegis" in record.explanation_for_prime
        assert "demoted" in record.explanation_for_prime or "demote" in record.explanation_for_prime

    def test_decision_record_aegis_allow_decision_silent(self) -> None:
        """Decision record handles Aegis 'allow' decision without adding blockers."""
        plan = _make_plan(2)
        record = _build_decision_record(
            plan,
            aegis_gate_decision="allow",
            aegis_explanation="policy satisfied",
        )
        # allow decision should not add fallback blockers (handles normally)
        assert "aegis_gate_blocked" not in record.fallback_blockers
        assert "aegis_human_gate_required" not in record.fallback_blockers
        # Aegis decision should still be stored for audit
        assert record.aegis_gate_decision == "allow"
        assert record.aegis_explanation == "policy satisfied"


class TestAegisGateEvidenceSummary:
    """Test serialization of Aegis gate evidence for downstream Bifrost/Prime surfaces."""

    def test_evidence_summary_empty_when_no_decision_record(self) -> None:
        """Summary returns empty AegisGateEvidenceSummary when decision_record is None."""
        summary = RelayExecutionSummary(results=(), errors=(), decision_record=None)
        evidence = summary.aegis_gate_evidence_summary()
        assert evidence.gate_decision is None
        assert evidence.severity is None
        assert evidence.evidence_ids == ()
        assert evidence.waiver_present is False
        assert evidence.explanation == ""
        assert evidence.fallback_blockers_from_aegis == ()


class TestRelayAegisPromptPacketHandoffSummary:
    """Test display-safe PromptPacket policy handoff for Bifrost."""

    def test_display_safe_handoff_tag_contract_redacts_unsafe_downstream_values(
        self,
    ) -> None:
        result = relay_display_safe_handoff_tags(
            (
                "credential:sk-test-secret",
                "raw_prompt_secret",
                "branch_move_request",
                "packet-proof-credential:sk-test-secret",
                "packet_hash_missing",
                "packet-proof-safe",
                "aegis-proof-safe",
                "PromptPacket proof metadata satisfies Aegis policy",
            ),
            fallback="redacted_downstream_tag",
        )

        assert result == (
            "redacted_downstream_tag",
            "packet_hash_missing",
            "packet-proof-safe",
            "aegis-proof-safe",
            "PromptPacket proof metadata satisfies Aegis policy",
        )

    def test_display_safe_handoff_tag_contract_dedupes_redactions(self) -> None:
        result = relay_display_safe_handoff_tags(
            (
                "credential:sk-test-secret",
                "raw_prompt_secret",
                "packet_hash_unavailable",
                "packet_hash_unavailable",
            ),
            fallback="redacted_downstream_tag",
        )

        assert result == ("redacted_downstream_tag", "packet_hash_unavailable")

    def test_display_safe_handoff_tag_contract_redacts_source_git_commands(
        self,
    ) -> None:
        result = relay_display_safe_handoff_tags(
            (
                "git reset --hard origin/main",
                "merge origin/main into worktree",
                "rebase current branch",
                "cherry-pick review commit",
                "stash-pop across worktrees",
                "unapproved_main_write_request",
                "packet-proof-git-reset-hard",
                "aegis-proof-main-write-request",
                "packet_hash_missing",
                "packet-proof-safe",
                "aegis-proof-safe",
                "human approval required before dispatch",
            ),
            fallback="redacted_source_git_handoff",
        )

        assert result == (
            "redacted_source_git_handoff",
            "packet_hash_missing",
            "packet-proof-safe",
            "aegis-proof-safe",
            "human approval required before dispatch",
        )

    def test_display_safe_handoff_tag_contract_preserves_goal_checkpoint_tags(
        self,
    ) -> None:
        result = relay_display_safe_handoff_tags(
            (
                "goal_objective_summary_present",
                "lane_session_label_present",
                "blocker_continuation_policy_required",
                "goal_checkpoint_required",
                "regular_git_checkpoint_expected",
                "regular_obsidian_checkpoint_expected",
                "goal-proof-checkpoint-1",
                "aegis-proof-safe",
                "packet_hash_missing",
            ),
            fallback="redacted_goal_runtime_handoff",
        )

        assert result == (
            "goal_objective_summary_present",
            "lane_session_label_present",
            "blocker_continuation_policy_required",
            "goal_checkpoint_required",
            "regular_git_checkpoint_expected",
            "regular_obsidian_checkpoint_expected",
            "goal-proof-checkpoint-1",
            "aegis-proof-safe",
            "packet_hash_missing",
        )

    def test_display_safe_handoff_tag_contract_redacts_goal_runtime_leakage(
        self,
    ) -> None:
        result = relay_display_safe_handoff_tags(
            (
                "objective: replay raw prompt and worker chat",
                "lane=C:\\Users\\Scott\\Secrets\\goal.md",
                "provider_account_token:sk-test-secret",
                "continue blocker by running git reset --hard",
                "move worktree branch for checkpoint",
                "write uncoordinated main checkpoint",
                "goal-proof-provider-account-token",
                "goal-proof-users-scott-obsidian-path",
                "goal-proof-git-checkpoint",
                "regular_git_checkpoint_expected",
                "regular_obsidian_checkpoint_expected",
            ),
            fallback="redacted_goal_runtime_handoff",
        )

        assert result == (
            "redacted_goal_runtime_handoff",
            "regular_git_checkpoint_expected",
            "regular_obsidian_checkpoint_expected",
        )

    def test_handoff_empty_when_policy_not_evaluated(self) -> None:
        summary = RelayExecutionSummary(results=(), errors=(), decision_record=None)

        handoff = summary.aegis_prompt_packet_policy_handoff()

        assert handoff == RelayAegisPromptPacketHandoffSummary()
        assert handoff.to_dict() == {
            "decision": None,
            "severity": None,
            "packet_id": None,
            "packet_hash_status": "missing",
            "packet_hash": None,
            "proof_requirement": None,
            "aegis_evidence_ids": (),
            "blockers": (),
            "warnings": (),
            "missing_metadata_fields": (),
            "reason_tags": (),
            "demotion_target_tier": None,
            "human_gate_state": "not_required",
            "fail_closed": False,
            "missing_metadata": False,
            "prompt_budget_ref": None,
            "packet_proof_metadata_ref": None,
        }

    def test_handoff_projects_allow_policy_and_envelope_proof_metadata(self) -> None:
        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan_with_policy(
            plan,
            _constant_model_call("ok"),
            proof_trail=_clean_proof_trail("packet-proof-tier2"),
            include_decision_record=True,
        )

        handoff = summary.aegis_prompt_packet_policy_handoff()
        result = handoff.to_dict()

        assert result["decision"] == "allow"
        assert result["severity"] == "info"
        assert result["packet_id"] == _PACKET_ID
        assert result["packet_hash_status"] == "present"
        assert result["packet_hash"] == plan.packet.proof_metadata.packet_hash
        assert result["proof_requirement"] == "independent_review_when_meaningful"
        assert result["aegis_evidence_ids"] == ("packet-proof-tier2",)
        assert result["blockers"] == ()
        assert result["warnings"] == ()
        assert result["missing_metadata_fields"] == ()
        assert result["reason_tags"] == (
            "PromptPacket proof metadata satisfies Aegis policy",
        )
        assert result["demotion_target_tier"] is None
        assert result["human_gate_state"] == "not_required"
        assert result["fail_closed"] is False
        assert result["missing_metadata"] is False
        assert result["prompt_budget_ref"] == plan.packet.proof_metadata.prompt_budget_ref
        assert result["packet_proof_metadata_ref"] == (
            f"prompt-packet-proof:{_PACKET_ID}"
        )

    def test_handoff_falls_back_to_decision_record_policy_evidence(self) -> None:
        plan = _make_plan(1)
        evidence = RelayPromptPacketPolicyEvidence(
            decision="warn",
            severity="warning",
            reason="policy_warn",
            evidence_ids=("packet-proof-warn",),
            warnings=("packet_hash_unavailable",),
            packet_id=_PACKET_ID,
            packet_hash=None,
            prompt_budget_ref="budget:test",
            packet_proof_metadata_ref="relay-packet-proof:test",
        )
        envelope = _build_dispatch_envelope(
            plan,
            lane_role=plan.lanes[0].role,
            requested_model_id=plan.lanes[0].preferred_model,
            aegis_evidence_ids=("packet-proof-warn",),
        )
        envelope = dataclasses.replace(envelope, packet_hash=None)
        record = _build_decision_record(plan, dispatch_envelope=envelope)
        record = dataclasses.replace(
            record,
            dispatch_envelope=envelope,
            prompt_packet_policy_evidence=evidence,
        )
        summary = RelayExecutionSummary(
            results=(),
            errors=(),
            decision_record=record,
            prompt_packet_policy_evidence=None,
        )

        handoff = summary.aegis_prompt_packet_policy_handoff()

        assert handoff.decision == "warn"
        assert handoff.packet_hash_status == "missing"
        assert handoff.warnings == ("packet_hash_unavailable",)
        assert handoff.reason_tags == ("packet_hash_unavailable",)
        assert handoff.missing_metadata_fields == ("packet_hash",)
        assert handoff.missing_metadata is True

    def test_handoff_redacts_arbitrary_policy_free_text(self) -> None:
        danger = (
            "RAW_PROMPT_SENTINEL worker_chat=private "
            "credential=sk-test-secret BRANCH_MOVE_REQUEST "
            "free-text blocker summary: move main"
        )
        evidence = RelayPromptPacketPolicyEvidence(
            decision="block",
            severity="error",
            reason=danger,
            evidence_ids=(danger,),
            blockers=(danger,),
            warnings=(danger,),
            packet_id=_PACKET_ID,
            packet_hash="packet-hash-safe",
            prompt_budget_ref="budget:safe",
            packet_proof_metadata_ref="prompt-packet-proof:safe",
        )
        summary = RelayExecutionSummary(
            results=(),
            errors=(),
            prompt_packet_policy_evidence=evidence,
        )

        handoff = summary.aegis_prompt_packet_policy_handoff().to_dict()
        rendered = " ".join(str(value) for value in handoff.values())

        assert handoff["aegis_evidence_ids"] == ("redacted_evidence_id",)
        assert handoff["blockers"] == ("redacted_policy_blocker",)
        assert handoff["warnings"] == ("redacted_policy_warning",)
        assert handoff["reason_tags"] == ("redacted_policy_reason",)
        for sentinel in (
            "RAW_PROMPT_SENTINEL",
            "worker_chat=private",
            "credential=sk-test-secret",
            "BRANCH_MOVE_REQUEST",
            "free-text blocker summary",
            "move main",
        ):
            assert sentinel not in rendered

    def test_handoff_redacts_lowercase_structured_looking_sensitive_tags(self) -> None:
        evidence = RelayPromptPacketPolicyEvidence(
            decision="block",
            severity="error",
            reason="raw_prompt_secret",
            evidence_ids=(
                "credential:sk-test-secret",
                "packet-proof-credential:sk-test-secret",
            ),
            blockers=("branch_move_request",),
            warnings=("raw_prompt_secret",),
            packet_id=_PACKET_ID,
            packet_hash="packet-hash-safe",
            prompt_budget_ref="budget:safe",
            packet_proof_metadata_ref="prompt-packet-proof:safe",
        )
        summary = RelayExecutionSummary(
            results=(),
            errors=(),
            prompt_packet_policy_evidence=evidence,
        )

        handoff = summary.aegis_prompt_packet_policy_handoff().to_dict()
        rendered = " ".join(str(value) for value in handoff.values())

        assert handoff["aegis_evidence_ids"] == ("redacted_evidence_id",)
        assert handoff["blockers"] == ("redacted_policy_blocker",)
        assert handoff["warnings"] == ("redacted_policy_warning",)
        assert handoff["reason_tags"] == ("redacted_policy_reason",)
        for sentinel in (
            "credential:sk-test-secret",
            "packet-proof-credential:sk-test-secret",
            "raw_prompt_secret",
            "branch_move_request",
        ):
            assert sentinel not in rendered

    def test_handoff_redacts_source_git_main_write_policy_surfaces(self) -> None:
        unsafe_values = (
            "git reset --hard origin/main",
            "merge origin/main",
            "rebase current branch",
            "cherry-pick review commit",
            "stash-pop across worktrees",
            "unapproved_main_write_request",
            "packet-proof-git-reset-hard",
            "aegis-proof-main-write-request",
        )
        evidence = RelayPromptPacketPolicyEvidence(
            decision="block",
            severity="error",
            reason="git reset --hard origin/main",
            evidence_ids=unsafe_values,
            blockers=unsafe_values,
            warnings=unsafe_values,
            packet_id=_PACKET_ID,
            packet_hash="packet-hash-safe",
            prompt_budget_ref="budget:safe",
            packet_proof_metadata_ref="prompt-packet-proof:safe",
        )
        summary = RelayExecutionSummary(
            results=(),
            errors=(),
            prompt_packet_policy_evidence=evidence,
        )

        handoff = summary.aegis_prompt_packet_policy_handoff().to_dict()
        rendered = " ".join(str(value) for value in handoff.values())

        assert handoff["aegis_evidence_ids"] == ("redacted_evidence_id",)
        assert handoff["blockers"] == ("redacted_policy_blocker",)
        assert handoff["warnings"] == ("redacted_policy_warning",)
        assert handoff["reason_tags"] == ("redacted_policy_reason",)
        for sentinel in unsafe_values:
            assert sentinel not in rendered
        for token in ("reset --hard", "merge origin", "rebase", "cherry-pick", "stash-pop"):
            assert token not in rendered

    def test_handoff_redacts_goal_runtime_checkpoint_policy_surfaces(self) -> None:
        unsafe_values = (
            "objective summary includes RAW_PROMPT_SENTINEL and worker chat",
            "lane label C:\\Users\\Scott\\Obsidian\\Goal.md",
            "session label provider_account_token:sk-test-secret",
            "free-text blocker says git reset --hard origin/main",
            "branch/worktree movement requested before checkpoint",
            "uncoordinated main-write request",
            "goal-proof-provider-account-token",
            "goal-proof-users-scott-obsidian-path",
            "goal-proof-git-checkpoint",
        )
        evidence = RelayPromptPacketPolicyEvidence(
            decision="warn",
            severity="warning",
            reason="objective summary includes RAW_PROMPT_SENTINEL and worker chat",
            evidence_ids=unsafe_values
            + (
                "goal-proof-checkpoint-1",
                "regular_git_checkpoint_expected",
            ),
            blockers=unsafe_values + ("goal_checkpoint_required",),
            warnings=unsafe_values + ("regular_obsidian_checkpoint_expected",),
            packet_id=_PACKET_ID,
            packet_hash="packet-hash-safe",
            prompt_budget_ref="budget:safe",
            packet_proof_metadata_ref="prompt-packet-proof:safe",
        )
        summary = RelayExecutionSummary(
            results=(),
            errors=(),
            prompt_packet_policy_evidence=evidence,
        )

        handoff = summary.aegis_prompt_packet_policy_handoff().to_dict()
        rendered = " ".join(str(value) for value in handoff.values())

        assert handoff["aegis_evidence_ids"] == (
            "redacted_evidence_id",
            "goal-proof-checkpoint-1",
            "regular_git_checkpoint_expected",
        )
        assert handoff["blockers"] == (
            "redacted_policy_blocker",
            "goal_checkpoint_required",
        )
        assert handoff["warnings"] == (
            "redacted_policy_warning",
            "regular_obsidian_checkpoint_expected",
        )
        assert handoff["reason_tags"] == (
            "redacted_policy_reason",
            "goal_checkpoint_required",
        )
        for sentinel in unsafe_values:
            assert sentinel not in rendered
        for token in (
            "RAW_PROMPT_SENTINEL",
            "worker chat",
            "provider_account_token",
            "Users\\Scott",
            "git reset --hard",
            "main-write",
        ):
            assert token not in rendered

    def test_handoff_preserves_known_structured_tags_and_fixed_phrases(self) -> None:
        evidence = RelayPromptPacketPolicyEvidence(
            decision="allow",
            severity="info",
            reason="PromptPacket proof metadata satisfies Aegis policy",
            evidence_ids=("packet-proof-safe", "aegis-proof-safe"),
            warnings=("packet_hash_unavailable",),
            packet_id=_PACKET_ID,
            packet_hash="packet-hash-safe",
            prompt_budget_ref="budget:safe",
            packet_proof_metadata_ref="prompt-packet-proof:safe",
        )
        summary = RelayExecutionSummary(
            results=(),
            errors=(),
            prompt_packet_policy_evidence=evidence,
        )

        handoff = summary.aegis_prompt_packet_policy_handoff()

        assert handoff.aegis_evidence_ids == (
            "packet-proof-safe",
            "aegis-proof-safe",
        )
        assert handoff.warnings == ("packet_hash_unavailable",)
        assert handoff.reason_tags == ("packet_hash_unavailable",)

    def test_handoff_carries_human_gate_and_fail_closed_state(self) -> None:
        plan = _make_plan(4)
        evidence = _evaluate_relay_prompt_packet_policy(
            plan,
            proof_trail=_clean_proof_trail("packet-proof-human-gate"),
            human_gate_approved=False,
        )
        envelope = _build_dispatch_envelope(
            plan,
            lane_role=plan.lanes[0].role,
            requested_model_id=plan.lanes[0].preferred_model,
            aegis_evidence_ids=("packet-proof-human-gate",),
        )
        record = _build_decision_record(
            plan,
            dispatch_envelope=envelope,
            prompt_packet_policy_evidence=evidence,
        )
        summary = RelayExecutionSummary(
            results=(),
            errors=(),
            decision_record=record,
            prompt_packet_policy_evidence=evidence,
        )

        handoff = summary.aegis_prompt_packet_policy_handoff()

        assert handoff.decision == "human_gate"
        assert handoff.human_gate_state == "required"
        assert handoff.fail_closed is True
        assert handoff.reason_tags == ("human approval required before dispatch",)

    def test_handoff_missing_metadata_fields_are_deterministic(self) -> None:
        evidence = RelayPromptPacketPolicyEvidence(
            decision="block",
            severity="error",
            reason="policy_block",
            blockers=("packet_hash_missing",),
        )
        summary = RelayExecutionSummary(
            results=(),
            errors=(),
            prompt_packet_policy_evidence=evidence,
        )

        handoff = summary.aegis_prompt_packet_policy_handoff()

        assert handoff.fail_closed is True
        assert handoff.missing_metadata is True
        assert handoff.missing_metadata_fields == (
            "packet_id",
            "packet_hash",
            "prompt_budget_ref",
            "packet_proof_metadata_ref",
            "proof_requirement",
            "aegis_evidence_ids",
        )
        assert handoff.reason_tags == ("packet_hash_missing",)

    def test_handoff_is_display_safe_and_deterministic(self) -> None:
        plan = _make_plan(1)
        summary = execute_relay_dispatch_plan_with_policy(
            plan,
            _constant_model_call("raw provider secret should stay out"),
            proof_trail=_clean_proof_trail("packet-proof-display-safe"),
            include_decision_record=True,
        )

        first = summary.aegis_prompt_packet_policy_handoff().to_dict()
        second = summary.aegis_prompt_packet_policy_handoff().to_dict()
        rendered = " ".join(str(value) for value in first.values())

        assert first == second
        assert _PROMPT not in rendered
        assert "raw provider secret" not in rendered
        assert "packet-proof-display-safe" in rendered
        assert isinstance(first["aegis_evidence_ids"], tuple)
        assert isinstance(first["blockers"], tuple)
        assert isinstance(first["warnings"], tuple)
        assert isinstance(first["missing_metadata_fields"], tuple)
        assert isinstance(first["reason_tags"], tuple)

    def test_evidence_summary_extracts_allow_decision(self) -> None:
        """Summary serializes allow gate decision without blockers."""
        plan = _make_plan(2)
        record = _build_decision_record(
            plan,
            aegis_gate_decision="allow",
            aegis_explanation="policy satisfied",
        )
        summary = RelayExecutionSummary(results=(), errors=(), decision_record=record)
        evidence = summary.aegis_gate_evidence_summary()
        assert evidence.gate_decision == "allow"
        assert evidence.explanation == "policy satisfied"
        assert evidence.fallback_blockers_from_aegis == ()

    def test_evidence_summary_extracts_block_decision_and_blocker(self) -> None:
        """Summary serializes block gate decision with aegis_gate_blocked blocker."""
        plan = _make_plan(2)
        record = _build_decision_record(
            plan,
            aegis_gate_decision="block",
            aegis_explanation="security policy violation",
        )
        summary = RelayExecutionSummary(results=(), errors=(), decision_record=record)
        evidence = summary.aegis_gate_evidence_summary()
        assert evidence.gate_decision == "block"
        assert evidence.explanation == "security policy violation"
        assert "aegis_gate_blocked" in evidence.fallback_blockers_from_aegis

    def test_evidence_summary_extracts_human_gate_blocker(self) -> None:
        """Summary serializes human_gate decision with aegis_human_gate_required blocker."""
        plan = _make_plan(2)
        record = _build_decision_record(
            plan,
            aegis_gate_decision="human_gate",
            aegis_explanation="escalation required",
        )
        summary = RelayExecutionSummary(results=(), errors=(), decision_record=record)
        evidence = summary.aegis_gate_evidence_summary()
        assert evidence.gate_decision == "human_gate"
        assert evidence.explanation == "escalation required"
        assert "aegis_human_gate_required" in evidence.fallback_blockers_from_aegis

    def test_evidence_summary_filters_only_aegis_blockers(self) -> None:
        """Summary extracts only aegis_* prefixed blockers from fallback_blockers."""
        plan = _make_plan(2)
        record = _build_decision_record(plan, aegis_gate_decision="block")
        # Manually construct a record with mixed blockers for testing
        record = dataclasses.replace(
            record,
            fallback_blockers=(
                "vendor_unknown",
                "aegis_gate_blocked",
                "model_id_unknown",
                "aegis_other_evidence",
            ),
        )
        summary = RelayExecutionSummary(results=(), errors=(), decision_record=record)
        evidence = summary.aegis_gate_evidence_summary()
        # Should only extract aegis_* prefixed blockers
        assert "vendor_unknown" not in evidence.fallback_blockers_from_aegis
        assert "model_id_unknown" not in evidence.fallback_blockers_from_aegis
        assert "aegis_gate_blocked" in evidence.fallback_blockers_from_aegis
        assert "aegis_other_evidence" in evidence.fallback_blockers_from_aegis

    def test_evidence_summary_extracts_severity_and_evidence_ids(self) -> None:
        """Summary serializes severity, evidence_ids, and waiver_present."""
        plan = _make_plan(2)
        record = _build_decision_record(
            plan,
            aegis_gate_decision="demote",
            aegis_explanation="cost constraint",
        )
        # Manually set severity, evidence_ids, and waiver_present
        record = dataclasses.replace(
            record,
            aegis_gate_severity="WARNING",
            aegis_evidence_ids=("evidence-1", "evidence-2"),
            aegis_waiver_present=True,
        )
        summary = RelayExecutionSummary(results=(), errors=(), decision_record=record)
        evidence = summary.aegis_gate_evidence_summary()
        assert evidence.severity == "WARNING"
        assert evidence.evidence_ids == ("evidence-1", "evidence-2")
        assert evidence.waiver_present is True

    def test_evidence_summary_immutable(self) -> None:
        """AegisGateEvidenceSummary is frozen and cannot be modified."""
        evidence = AegisGateEvidenceSummary(
            gate_decision="allow",
            explanation="test",
        )
        with pytest.raises(Exception):  # FrozenInstanceError from dataclass
            evidence.gate_decision = "block"  # type: ignore

    def test_evidence_summary_to_dict_empty(self) -> None:
        """to_dict() returns stable keys for empty summary."""
        evidence = AegisGateEvidenceSummary()
        result = evidence.to_dict()
        assert result == {
            "gate_decision": None,
            "severity": None,
            "evidence_ids": (),
            "waiver_present": False,
            "explanation": "",
            "fallback_blockers_from_aegis": (),
        }

    def test_evidence_summary_to_dict_with_data(self) -> None:
        """to_dict() preserves all fields in stable format."""
        evidence = AegisGateEvidenceSummary(
            gate_decision="block",
            severity="ERROR",
            evidence_ids=("evidence-1", "evidence-2"),
            waiver_present=True,
            explanation="policy violation detected",
            fallback_blockers_from_aegis=("aegis_gate_blocked",),
        )
        result = evidence.to_dict()
        assert result == {
            "gate_decision": "block",
            "severity": "ERROR",
            "evidence_ids": ("evidence-1", "evidence-2"),
            "waiver_present": True,
            "explanation": "policy violation detected",
            "fallback_blockers_from_aegis": ("aegis_gate_blocked",),
        }

    def test_evidence_summary_to_dict_stable_keys(self) -> None:
        """to_dict() returns consistent keys regardless of data values."""
        evidence1 = AegisGateEvidenceSummary(gate_decision="allow")
        evidence2 = AegisGateEvidenceSummary(gate_decision="block")
        # Both should have the same keys
        assert set(evidence1.to_dict().keys()) == set(evidence2.to_dict().keys())
        assert set(evidence1.to_dict().keys()) == {
            "gate_decision",
            "severity",
            "evidence_ids",
            "waiver_present",
            "explanation",
            "fallback_blockers_from_aegis",
        }

    def test_evidence_summary_to_dict_immutable_values(self) -> None:
        """to_dict() returns immutable values (no mutable nested structures)."""
        evidence = AegisGateEvidenceSummary(
            evidence_ids=("id-1", "id-2"),
            fallback_blockers_from_aegis=("blocker-1",),
        )
        result = evidence.to_dict()
        # All values should be immutable
        assert isinstance(result["gate_decision"], type(None))
        assert isinstance(result["severity"], type(None))
        assert isinstance(result["evidence_ids"], tuple)
        assert isinstance(result["waiver_present"], bool)
        assert isinstance(result["explanation"], str)
        assert isinstance(result["fallback_blockers_from_aegis"], tuple)

    def test_evidence_summary_demote_decision_no_blockers(self) -> None:
        """Demote decision with explanation but no blockers generated."""
        plan = _make_plan(2)
        record = _build_decision_record(
            plan,
            aegis_gate_decision="demote",
            aegis_explanation="cost constraint applied",
        )
        summary = RelayExecutionSummary(results=(), errors=(), decision_record=record)
        evidence = summary.aegis_gate_evidence_summary()
        assert evidence.gate_decision == "demote"
        assert evidence.explanation == "cost constraint applied"
        assert evidence.fallback_blockers_from_aegis == ()

    def test_evidence_summary_missing_evidence_ids_empty_tuple(self) -> None:
        """Evidence ids default to empty tuple when not provided."""
        evidence = AegisGateEvidenceSummary(
            gate_decision="block",
            explanation="no evidence collected",
        )
        assert evidence.evidence_ids == ()
        result = evidence.to_dict()
        assert result["evidence_ids"] == ()

    def test_evidence_summary_absent_waiver_defaults_false(self) -> None:
        """Waiver presence defaults to False when not explicitly set."""
        evidence = AegisGateEvidenceSummary(
            gate_decision="block",
        )
        assert evidence.waiver_present is False
        result = evidence.to_dict()
        assert result["waiver_present"] is False

    def test_evidence_summary_to_dict_multiple_calls_identical(self) -> None:
        """Multiple calls to to_dict() produce identical deterministic output."""
        evidence = AegisGateEvidenceSummary(
            gate_decision="block",
            severity="ERROR",
            evidence_ids=("ev-1", "ev-2", "ev-3"),
            waiver_present=True,
            explanation="security violation",
            fallback_blockers_from_aegis=("aegis_gate_blocked", "aegis_other"),
        )
        result1 = evidence.to_dict()
        result2 = evidence.to_dict()
        result3 = evidence.to_dict()
        assert result1 == result2 == result3
        # Verify exact content
        assert result1["gate_decision"] == "block"
        assert result1["severity"] == "ERROR"
        assert len(result1["evidence_ids"]) == 3

    def test_evidence_summary_empty_explanation_with_decision(self) -> None:
        """Gate decision can exist with empty explanation text."""
        evidence = AegisGateEvidenceSummary(
            gate_decision="allow",
            explanation="",  # explicitly empty
        )
        result = evidence.to_dict()
        assert result["gate_decision"] == "allow"
        assert result["explanation"] == ""

    def test_evidence_summary_no_gate_decision_present(self) -> None:
        """No gate decision (None) with various other fields."""
        evidence = AegisGateEvidenceSummary(
            gate_decision=None,  # explicitly no decision
            severity="INFO",
            evidence_ids=("ev-1",),
            explanation="gate not evaluated",
        )
        result = evidence.to_dict()
        assert result["gate_decision"] is None
        assert result["severity"] == "INFO"
        assert result["evidence_ids"] == ("ev-1",)
        assert result["explanation"] == "gate not evaluated"

    def test_evidence_summary_mixed_empty_and_full_fields(self) -> None:
        """Partial evidence: some fields empty, others populated."""
        evidence = AegisGateEvidenceSummary(
            gate_decision="demote",  # present
            severity=None,  # absent
            evidence_ids=(),  # empty
            waiver_present=False,  # default
            explanation="partial evidence",  # present
            fallback_blockers_from_aegis=("aegis_demote",),  # present
        )
        result = evidence.to_dict()
        assert result["gate_decision"] == "demote"
        assert result["severity"] is None
        assert result["evidence_ids"] == ()
        assert result["waiver_present"] is False
        assert result["explanation"] == "partial evidence"
        assert result["fallback_blockers_from_aegis"] == ("aegis_demote",)

    def test_evidence_summary_to_dict_multiple_calls_identical_with_partial_evidence(self) -> None:
        """to_dict() returns identical output on multiple calls with partial evidence (deterministic)."""
        evidence = AegisGateEvidenceSummary(
            gate_decision="demote",
            severity="WARNING",
            evidence_ids=("e1", "e2", "e3"),
            explanation="cost constraint",
            fallback_blockers_from_aegis=("aegis_evidence",),
        )
        dict1 = evidence.to_dict()
        dict2 = evidence.to_dict()
        assert dict1 == dict2
        assert list(dict1.keys()) == list(dict2.keys())


class TestRelayDispatchMetadataEnvelopeDeepSeekDisposition:
    """Relay dispatch metadata envelope binds bounded DeepSeek validation-state disposition."""

    def test_envelope_binds_deepseek_validation_disposition_for_deepseek_adapter(self) -> None:
        plan = _make_plan(1)
        adapter = FakeModelAdapter(
            "response",
            metadata=deepseek_candidate_metadata_preset("fast"),
        )
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            adapter,
        )

        summary = execute_relay_plan_with_registry(plan, registry)

        # Candidate DeepSeek metadata is now refused at the pre-dispatch gate;
        # the envelope (which still carries the disposition) rides on the error.
        envelope = summary.errors[0].dispatch_metadata_envelope
        assert envelope is not None
        disposition = envelope.deepseek_validation_disposition
        assert disposition is not None
        assert disposition.validation_level == "level-0:metadata-only"
        assert disposition.direct_dispatch_id == "deepseek-chat"
        assert disposition.variant_labels == ("deepseek-v4-flash",)
        assert disposition.transport_cleared is False
        assert disposition.validation_evidence_ref == (
            "deepseek-validation:level-0:metadata-only"
        )
        assert disposition.direct_endpoint_evidence_ref == (
            "deepseek-direct-endpoint:"
            "https://api.deepseek.com/v1/chat/completions"
        )
        assert disposition.external_review_evidence_ref == (
            "external-review:deepseek:deepseek-chat:pending"
        )

    def test_envelope_disposition_never_grants_autonomous_authority(self) -> None:
        plan = _make_plan(1)
        adapter = FakeModelAdapter(
            "response",
            metadata=deepseek_candidate_metadata_preset("default_quality"),
        )
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            adapter,
        )

        summary = execute_relay_plan_with_registry(plan, registry)

        envelope = summary.errors[0].dispatch_metadata_envelope
        assert envelope is not None
        disposition = envelope.deepseek_validation_disposition
        assert disposition is not None
        assert disposition.autonomous_implementation_authorized is False
        assert disposition.review_clearing_authorized is False
        assert disposition.branch_movement_authorized is False
        assert disposition.live_coding_authority_authorized is False
        assert disposition.relay_bypass_authorized is False
        assert disposition.serialization_only is True

    def test_envelope_disposition_carries_blocked_authority_tags(self) -> None:
        plan = _make_plan(1)
        adapter = FakeModelAdapter(
            "response",
            metadata=deepseek_candidate_metadata_preset("fast"),
        )
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            adapter,
        )

        summary = execute_relay_plan_with_registry(plan, registry)

        envelope = summary.errors[0].dispatch_metadata_envelope
        assert envelope is not None
        disposition = envelope.deepseek_validation_disposition
        assert disposition is not None
        assert "review_clearance" in disposition.blocked_authority_tags
        assert "branch_movement" in disposition.blocked_authority_tags
        assert "relay_aegis_bypass" in disposition.blocked_authority_tags
        assert "autonomous_coding" in disposition.blocked_authority_tags
        assert "aggregator_authority" in disposition.blocked_authority_tags

    def test_envelope_disposition_absent_when_no_adapter_metadata(self) -> None:
        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("response"),
        )

        envelope = summary.results[0].dispatch_metadata_envelope
        assert envelope is not None
        assert envelope.deepseek_validation_disposition is None

    def test_envelope_disposition_absent_for_non_deepseek_adapter(self) -> None:
        plan = _make_plan(1)
        non_deepseek_metadata = ModelHarnessMetadata(
            provider_name="anthropic",
            model_name="claude-opus",
            capability_tier="primary",
            context_budget=200000,
            prompt_payload_budget=150000,
            trust_state="trusted",
            requires_external_review=False,
            supports_completion_tokens=True,
            supports_latency_ms=True,
            supports_payload_snapshot=True,
            supports_response_hash=True,
            tokenizer_family="anthropic",
            max_output_tokens=8192,
        )
        adapter = FakeModelAdapter("response", metadata=non_deepseek_metadata)
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            adapter,
        )

        summary = execute_relay_plan_with_registry(plan, registry)

        envelope = summary.results[0].dispatch_metadata_envelope
        assert envelope is not None
        assert envelope.deepseek_validation_disposition is None

    def test_envelope_disposition_serializes_to_dict(self) -> None:
        plan = _make_plan(1)
        adapter = FakeModelAdapter(
            "response",
            metadata=deepseek_candidate_metadata_preset("fast"),
        )
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            adapter,
        )

        summary = execute_relay_plan_with_registry(plan, registry)

        envelope = summary.errors[0].dispatch_metadata_envelope
        assert envelope is not None
        rendered = envelope.to_dict()
        disposition_dict = rendered["deepseek_validation_disposition"]
        assert isinstance(disposition_dict, dict)
        assert disposition_dict["direct_dispatch_id"] == "deepseek-chat"
        assert disposition_dict["variant_labels"] == ("deepseek-v4-flash",)
        assert disposition_dict["transport_cleared"] is False
        assert disposition_dict["autonomous_implementation_authorized"] is False
        assert disposition_dict["serialization_only"] is True

    def test_envelope_disposition_dict_is_none_when_disposition_absent(self) -> None:
        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("response"),
        )

        envelope = summary.results[0].dispatch_metadata_envelope
        assert envelope is not None
        assert envelope.to_dict()["deepseek_validation_disposition"] is None


class TestRelayDispatchMetadataEnvelopeDeepSeekTransportAuthority:
    """Relay dispatch metadata envelope binds fail-closed transport-authority."""

    def test_envelope_binds_transport_authority_for_deepseek_adapter(self) -> None:
        plan = _make_plan(1)
        adapter = FakeModelAdapter(
            "response",
            metadata=deepseek_candidate_metadata_preset("fast"),
        )
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            adapter,
        )

        summary = execute_relay_plan_with_registry(plan, registry)

        # Blocked DeepSeek transport authority refuses dispatch — the envelope
        # is carried on the error, not on a result.
        assert summary.results == ()
        envelope = summary.errors[0].dispatch_metadata_envelope
        assert envelope is not None
        authority = envelope.deepseek_transport_authority
        assert authority is not None
        assert authority.direct_dispatch_id == "deepseek-chat"
        assert authority.status.value == "blocked:candidate-only"
        assert authority.transport_authorized is False
        assert "deepseek_proof_candidate_only" in authority.blocker_tags

    def test_envelope_transport_authority_preserves_blocked_autonomy(self) -> None:
        plan = _make_plan(1)
        adapter = FakeModelAdapter(
            "response",
            metadata=deepseek_candidate_metadata_preset("default_quality"),
        )
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            adapter,
        )

        summary = execute_relay_plan_with_registry(plan, registry)

        envelope = summary.errors[0].dispatch_metadata_envelope
        assert envelope is not None
        authority = envelope.deepseek_transport_authority
        assert authority is not None
        assert authority.autonomous_implementation_authorized is False
        assert authority.review_clearing_authorized is False
        assert authority.branch_movement_authorized is False
        assert authority.live_coding_authority_authorized is False
        assert authority.relay_bypass_authorized is False
        for marker in (
            "autonomous_implementation",
            "review_clearance",
            "branch_movement",
            "live_coding",
            "relay_bypass",
        ):
            assert marker in authority.blocked_authority_tags

    def test_envelope_transport_authority_proof_carries_evidence_refs(self) -> None:
        plan = _make_plan(1)
        adapter = FakeModelAdapter(
            "response",
            metadata=deepseek_candidate_metadata_preset("fast"),
        )
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            adapter,
        )

        summary = execute_relay_plan_with_registry(plan, registry)

        envelope = summary.errors[0].dispatch_metadata_envelope
        assert envelope is not None
        authority = envelope.deepseek_transport_authority
        assert authority is not None
        assert authority.proof.proof_state.value == "candidate-metadata-only"
        assert authority.proof.proof_evidence_refs == (
            "deepseek-validation:level-0:metadata-only",
        )
        assert authority.proof.review_evidence_ref == (
            "external-review:deepseek:deepseek-chat:pending"
        )
        assert authority.proof.human_gate_satisfied is False
        assert authority.proof.prime_authority_satisfied is False

    def test_envelope_transport_authority_absent_when_no_adapter_metadata(self) -> None:
        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("response"),
        )

        envelope = summary.results[0].dispatch_metadata_envelope
        assert envelope is not None
        assert envelope.deepseek_transport_authority is None

    def test_envelope_transport_authority_absent_for_non_deepseek_adapter(self) -> None:
        plan = _make_plan(1)
        non_deepseek_metadata = ModelHarnessMetadata(
            provider_name="anthropic",
            model_name="claude-opus",
            capability_tier="primary",
            context_budget=200000,
            prompt_payload_budget=150000,
            trust_state="trusted",
            requires_external_review=False,
            supports_completion_tokens=True,
            supports_latency_ms=True,
            supports_payload_snapshot=True,
            supports_response_hash=True,
            tokenizer_family="anthropic",
            max_output_tokens=8192,
        )
        adapter = FakeModelAdapter("response", metadata=non_deepseek_metadata)
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            adapter,
        )

        summary = execute_relay_plan_with_registry(plan, registry)

        envelope = summary.results[0].dispatch_metadata_envelope
        assert envelope is not None
        assert envelope.deepseek_transport_authority is None

    def test_envelope_transport_authority_to_dict_is_display_safe(self) -> None:
        plan = _make_plan(1)
        adapter = FakeModelAdapter(
            "response",
            metadata=deepseek_candidate_metadata_preset("fast"),
        )
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            adapter,
        )

        summary = execute_relay_plan_with_registry(plan, registry)

        envelope = summary.errors[0].dispatch_metadata_envelope
        assert envelope is not None
        rendered = envelope.to_dict()["deepseek_transport_authority"]
        assert isinstance(rendered, dict)
        assert rendered["direct_dispatch_id"] == "deepseek-chat"
        assert rendered["status"] == "blocked:candidate-only"
        assert rendered["transport_authorized"] is False
        assert rendered["autonomous_implementation_authorized"] is False
        assert "deepseek_proof_candidate_only" in rendered["blocker_tags"]
        flat = " ".join(str(v) for v in rendered.values()).lower()
        assert "credential" not in flat
        assert "api_key" not in flat

    def test_envelope_transport_authority_dict_is_none_when_absent(self) -> None:
        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan(
            plan,
            _constant_model_call("response"),
        )

        envelope = summary.results[0].dispatch_metadata_envelope
        assert envelope is not None
        assert envelope.to_dict()["deepseek_transport_authority"] is None

    def test_blocked_deepseek_authority_refuses_adapter_dispatch(self) -> None:
        """Codex Review A HIGH fix: a blocked DeepSeek transport-authority must
        prevent the adapter from being called at all — proven by checking that
        the adapter never received the lane payload and that the lane lands in
        ``summary.errors`` rather than ``summary.results``."""
        plan = _make_plan(1)
        adapter = FakeModelAdapter(
            "response",
            metadata=deepseek_candidate_metadata_preset("fast"),
        )
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            adapter,
        )

        summary = execute_relay_plan_with_registry(plan, registry)

        assert adapter.received_payloads == []
        assert summary.results == ()
        assert len(summary.errors) == 1
        error = summary.errors[0]
        assert error.role is plan.lanes[0].role
        assert error.preferred_model == plan.lanes[0].preferred_model
        assert error.error.startswith("deepseek_transport_blocked:")
        assert "blocked:candidate-only" in error.error
        assert "deepseek_proof_candidate_only" in error.error
        envelope = error.dispatch_metadata_envelope
        assert envelope is not None
        assert envelope.metadata_transport_allowed is False
        authority = envelope.deepseek_transport_authority
        assert authority is not None
        assert authority.transport_authorized is False
        assert error.dispatch_envelope is not None

    def test_blocked_no_proof_deepseek_authority_refuses_adapter_dispatch(self) -> None:
        """The ``blocked:no-proof`` path (DeepSeek metadata with no candidate
        state) must also refuse dispatch — covers the new BLOCKED_NO_PROOF
        emission in the binder."""
        plan = _make_plan(1)
        metadata = ModelHarnessMetadata(
            provider_name="deepseek",
            model_name="deepseek-chat",
            capability_tier="standard",
            context_budget=65536,
            prompt_payload_budget=57344,
            trust_state="candidate",
            requires_external_review=True,
        )
        adapter = FakeModelAdapter("response", metadata=metadata)
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            adapter,
        )

        summary = execute_relay_plan_with_registry(plan, registry)

        assert adapter.received_payloads == []
        assert summary.results == ()
        assert len(summary.errors) == 1
        error = summary.errors[0]
        assert "blocked:no-proof" in error.error
        assert "deepseek_proof_missing" in error.error

    def test_authorized_deepseek_lane_dispatches_and_returns_result(self) -> None:
        """Authorized DeepSeek transport (level-1 ref + both gates ``"true"``)
        is the only path that lets the adapter be called and produce a
        result."""
        plan = _make_plan(1)
        metadata = ModelHarnessMetadata(
            provider_name="deepseek",
            model_name="deepseek-chat",
            capability_tier="standard",
            context_budget=65536,
            prompt_payload_budget=57344,
            trust_state="candidate",
            requires_external_review=False,
            deepseek_candidate_state={
                "validation_evidence_ref": (
                    "deepseek-validation:level-1:validation-cleared"
                ),
                "external_review_evidence_ref": (
                    "external-review:deepseek:deepseek-chat:passed"
                ),
                "direct_endpoint_evidence_ref": (
                    "deepseek-direct-endpoint:https://api.deepseek.com/v1/chat/completions"
                ),
                "trust_mode": "direct",
                "human_gate_satisfied": "true",
                "prime_authority_satisfied": "true",
            },
        )
        adapter = FakeModelAdapter("response", metadata=metadata)
        registry = AdapterRegistry().register_model(
            plan.lanes[0].preferred_model,
            adapter,
        )

        summary = execute_relay_plan_with_registry(plan, registry)

        assert adapter.received_payloads == [plan.lanes[0].payload]
        assert summary.errors == ()
        assert len(summary.results) == 1
        result = summary.results[0]
        assert result.output == "response"
        envelope = result.dispatch_metadata_envelope
        assert envelope is not None
        authority = envelope.deepseek_transport_authority
        assert authority is not None
        assert authority.transport_authorized is True
        assert authority.status.value == "authorized:transport-only"

    def test_provider_result_validation_blocks_when_deepseek_authority_blocked(
        self,
    ) -> None:
        """Defence-in-depth: even if a caller bypasses the pre-dispatch gate
        and feeds an output through ``_build_provider_result_validation_evidence``
        with a blocked envelope, the result-validation evidence must surface the
        DeepSeek blocker tags and mark the lane ``blocked``."""
        plan = _make_plan(1)
        payload_evidence = self._clean_payload_evidence(plan)
        dispatch_envelope = _build_dispatch_envelope(
            plan,
            lane_role=plan.lanes[0].role,
            requested_model_id=plan.lanes[0].preferred_model,
            payload_evidence=payload_evidence,
        )
        candidate_state = self._clean_deepseek_candidate_state()
        candidate_state.update(
            {
                "validation_evidence_ref": "deepseek-validation:level-0:metadata-only",
                "external_review_evidence_ref": (
                    "external-review:deepseek:deepseek-chat:passed"
                ),
                "human_gate_satisfied": "false",
                "prime_authority_satisfied": "false",
            }
        )
        adapter_metadata = ModelHarnessMetadata(
            provider_name="deepseek",
            model_name="deepseek-chat",
            capability_tier="standard",
            context_budget=65536,
            prompt_payload_budget=57344,
            trust_state="candidate",
            requires_external_review=False,
            deepseek_candidate_state=candidate_state,
        )
        dispatch_metadata_envelope = _build_dispatch_metadata_envelope(
            plan,
            lane_role=plan.lanes[0].role,
            requested_model_id=plan.lanes[0].preferred_model,
            adapter_metadata=adapter_metadata,
            route_metadata=self._clean_route_metadata(),
            payload_evidence=payload_evidence,
            dispatch_envelope=dispatch_envelope,
        )

        validation_evidence = _build_provider_result_validation_evidence(
            plan,
            "would-be response",
            lane_role=plan.lanes[0].role,
            requested_model_id=plan.lanes[0].preferred_model,
            dispatch_metadata_envelope=dispatch_metadata_envelope,
            payload_evidence=payload_evidence,
            dispatch_envelope=dispatch_envelope,
        )

        assert validation_evidence.result_validation_status == "blocked"
        assert "deepseek_proof_candidate_only" in validation_evidence.blocker_tags

    def _clean_payload_evidence(self, plan: RelayDispatchPlan) -> RelayPromptPayloadEvidence:
        """Payload evidence with all gate-passing fields so fail_closed_advisory
        does NOT trip — isolates the DeepSeek transport-authority contribution
        to metadata_transport_allowed."""
        lane = plan.lanes[0]
        return RelayPromptPayloadEvidence(
            prompt_source="relay",
            heartbeat_id=plan.packet.packet_id,
            lane_id=f"{lane.role.value}:{lane.preferred_model}",
            selected_provider="deepseek",
            selected_model="deepseek-chat",
            capability_tier="standard",
            provider_route_kind="direct",
            trust_state="trusted",
            requires_external_review=False,
            external_review_status="not_required",
            model_metadata_ref="model-harness-metadata:deepseek:deepseek-chat",
            model_context_window_tokens=65536,
            prompt_budget_tokens=57344,
            budget_status="healthy",
        )

    def _clean_route_metadata(self) -> ModelRouteMetadataBinding:
        """Route metadata binding with all gate-passing fields so the metadata
        envelope's validation_tags stay empty for non-DeepSeek-authority gates."""
        return ModelRouteMetadataBinding(
            provider_name="deepseek",
            model_name="deepseek-chat",
            capability_tier="standard",
            route_risk_tier=1,
            route_cost_posture="minimal",
            route_latency_posture="standard",
            context_budget=65536,
            prompt_payload_budget=57344,
            trust_state="trusted",
            requires_external_review=False,
            provider_route_kind="direct",
            external_review_status="not_required",
            model_metadata_ref="model-harness-metadata:deepseek:deepseek-chat",
            prompt_payload_status="healthy",
        )

    def _clean_deepseek_candidate_state(self) -> dict[str, str]:
        """Candidate-state fields that satisfy every non-DeepSeek-authority
        validation tag in _build_dispatch_metadata_envelope."""
        return {
            "trust_mode": "direct",
            "proof_strength": "weak",
            "direct_endpoint_evidence_ref": (
                "deepseek-direct-endpoint:https://api.deepseek.com/v1/chat/completions"
            ),
        }

    def test_envelope_metadata_transport_blocked_by_deepseek_authority_only(self) -> None:
        """Repair contract: metadata_transport_allowed must be False when the
        DeepSeek transport-authority is the only blocker — even if no other
        fail-closed advisory tag fires."""
        plan = _make_plan(1)
        payload_evidence = self._clean_payload_evidence(plan)
        dispatch_envelope = _build_dispatch_envelope(
            plan,
            lane_role=plan.lanes[0].role,
            requested_model_id=plan.lanes[0].preferred_model,
            payload_evidence=payload_evidence,
        )
        candidate_state = self._clean_deepseek_candidate_state()
        candidate_state.update(
            {
                "validation_evidence_ref": "deepseek-validation:level-0:metadata-only",
                "external_review_evidence_ref": (
                    "external-review:deepseek:deepseek-chat:passed"
                ),
                "human_gate_satisfied": "false",
                "prime_authority_satisfied": "false",
            }
        )
        adapter_metadata = ModelHarnessMetadata(
            provider_name="deepseek",
            model_name="deepseek-chat",
            capability_tier="standard",
            context_budget=65536,
            prompt_payload_budget=57344,
            trust_state="candidate",
            requires_external_review=False,
            deepseek_candidate_state=candidate_state,
        )

        envelope = _build_dispatch_metadata_envelope(
            plan,
            lane_role=plan.lanes[0].role,
            requested_model_id=plan.lanes[0].preferred_model,
            adapter_metadata=adapter_metadata,
            route_metadata=self._clean_route_metadata(),
            payload_evidence=payload_evidence,
            dispatch_envelope=dispatch_envelope,
        )

        assert envelope.fail_closed_advisory is False
        assert envelope.fail_closed_tags == ()
        authority = envelope.deepseek_transport_authority
        assert authority is not None
        assert authority.transport_authorized is False
        assert envelope.metadata_transport_allowed is False

    def test_envelope_metadata_transport_allowed_when_deepseek_authorized_and_gates_clean(
        self,
    ) -> None:
        """Repair contract: metadata_transport_allowed is True only when the
        DeepSeek authority is AUTHORIZED_TRANSPORT_ONLY *and* no other
        fail-closed gate trips. Level-1 validation ref plus both gate flags
        explicitly ``"true"`` is the sole path that lifts both conditions."""
        plan = _make_plan(1)
        payload_evidence = self._clean_payload_evidence(plan)
        dispatch_envelope = _build_dispatch_envelope(
            plan,
            lane_role=plan.lanes[0].role,
            requested_model_id=plan.lanes[0].preferred_model,
            payload_evidence=payload_evidence,
        )
        candidate_state = self._clean_deepseek_candidate_state()
        candidate_state.update(
            {
                "validation_evidence_ref": (
                    "deepseek-validation:level-1:validation-cleared"
                ),
                "external_review_evidence_ref": (
                    "external-review:deepseek:deepseek-chat:passed"
                ),
                "human_gate_satisfied": "true",
                "prime_authority_satisfied": "true",
            }
        )
        adapter_metadata = ModelHarnessMetadata(
            provider_name="deepseek",
            model_name="deepseek-chat",
            capability_tier="standard",
            context_budget=65536,
            prompt_payload_budget=57344,
            trust_state="candidate",
            requires_external_review=False,
            deepseek_candidate_state=candidate_state,
        )

        envelope = _build_dispatch_metadata_envelope(
            plan,
            lane_role=plan.lanes[0].role,
            requested_model_id=plan.lanes[0].preferred_model,
            adapter_metadata=adapter_metadata,
            route_metadata=self._clean_route_metadata(),
            payload_evidence=payload_evidence,
            dispatch_envelope=dispatch_envelope,
        )

        assert envelope.fail_closed_advisory is False
        assert envelope.fail_closed_tags == ()
        authority = envelope.deepseek_transport_authority
        assert authority is not None
        assert authority.transport_authorized is True
        assert envelope.metadata_transport_allowed is True


class TestDirectAndPolicyPathDeepSeekTransportGate:
    """Codex Review B follow-up: the DeepSeek execution gate must close the
    direct ``execute_relay_dispatch_plan`` path and its policy wrapper, not
    just the registry-backed executor. When the ``model_call`` passed in
    exposes DeepSeek candidate metadata via its ``.metadata`` attribute, the
    direct path must bind that metadata, evaluate the transport authority,
    and refuse adapter dispatch on a block — identical to
    ``execute_relay_plan_with_registry``."""

    def test_direct_dispatch_refuses_blocked_deepseek_candidate_metadata(self) -> None:
        plan = _make_plan(1)
        adapter = FakeModelAdapter(
            "response",
            metadata=deepseek_candidate_metadata_preset("fast"),
        )

        summary = execute_relay_dispatch_plan(plan, adapter)

        assert adapter.received_payloads == []
        assert summary.results == ()
        assert len(summary.errors) == 1
        error = summary.errors[0]
        assert error.error.startswith("deepseek_transport_blocked:")
        assert "blocked:candidate-only" in error.error
        assert "deepseek_proof_candidate_only" in error.error
        envelope = error.dispatch_metadata_envelope
        assert envelope is not None
        assert envelope.metadata_transport_allowed is False
        authority = envelope.deepseek_transport_authority
        assert authority is not None
        assert authority.transport_authorized is False

    def test_direct_dispatch_refuses_blocked_no_proof_deepseek_metadata(self) -> None:
        plan = _make_plan(1)
        metadata = ModelHarnessMetadata(
            provider_name="deepseek",
            model_name="deepseek-chat",
            capability_tier="standard",
            context_budget=65536,
            prompt_payload_budget=57344,
            trust_state="candidate",
            requires_external_review=True,
        )
        adapter = FakeModelAdapter("response", metadata=metadata)

        summary = execute_relay_dispatch_plan(plan, adapter)

        assert adapter.received_payloads == []
        assert summary.results == ()
        assert len(summary.errors) == 1
        assert "blocked:no-proof" in summary.errors[0].error
        assert "deepseek_proof_missing" in summary.errors[0].error

    def test_direct_dispatch_allows_authorized_deepseek_metadata(self) -> None:
        plan = _make_plan(1)
        adapter = FakeModelAdapter(
            "response",
            metadata=_deepseek_authorized_metadata("fast"),
        )

        summary = execute_relay_dispatch_plan(plan, adapter)

        assert adapter.received_payloads == [plan.lanes[0].payload]
        assert summary.errors == ()
        assert len(summary.results) == 1
        result = summary.results[0]
        assert result.output == "response"
        envelope = result.dispatch_metadata_envelope
        assert envelope is not None
        authority = envelope.deepseek_transport_authority
        assert authority is not None
        assert authority.transport_authorized is True
        assert authority.status.value == "authorized:transport-only"

    def test_direct_dispatch_with_plain_function_unchanged(self) -> None:
        """A plain ``Callable[[str], str]`` has no ``.metadata`` and must
        continue to dispatch as before — the new gate must not regress the
        legacy direct-call signature."""
        plan = _make_plan(1)

        summary = execute_relay_dispatch_plan(plan, _constant_model_call("plain"))

        assert summary.errors == ()
        assert len(summary.results) == 1
        envelope = summary.results[0].dispatch_metadata_envelope
        assert envelope is not None
        assert envelope.deepseek_transport_authority is None

    def test_direct_dispatch_with_non_deepseek_adapter_dispatches(self) -> None:
        """A non-DeepSeek adapter's metadata is bound (so the envelope reflects
        the real provider), but no DeepSeek transport authority is emitted, so
        the gate is not engaged and the lane dispatches."""
        plan = _make_plan(1)
        metadata = ModelHarnessMetadata(
            provider_name="anthropic",
            model_name="claude-opus",
            capability_tier="primary",
            context_budget=200000,
            prompt_payload_budget=150000,
            trust_state="trusted",
            requires_external_review=False,
            supports_completion_tokens=True,
            supports_latency_ms=True,
            supports_payload_snapshot=True,
            supports_response_hash=True,
            tokenizer_family="anthropic",
            max_output_tokens=8192,
        )
        adapter = FakeModelAdapter("response", metadata=metadata)

        summary = execute_relay_dispatch_plan(plan, adapter)

        assert adapter.received_payloads == [plan.lanes[0].payload]
        assert summary.errors == ()
        assert len(summary.results) == 1
        envelope = summary.results[0].dispatch_metadata_envelope
        assert envelope is not None
        assert envelope.deepseek_transport_authority is None

    def test_policy_wrapper_refuses_blocked_deepseek_candidate_metadata(self) -> None:
        """``execute_relay_dispatch_plan_with_policy`` must not remain a
        bypass: when policy permits dispatch but the DeepSeek transport
        authority blocks, the lane must still be refused before adapter call."""
        plan = _make_plan(1)
        adapter = FakeModelAdapter(
            "response",
            metadata=deepseek_candidate_metadata_preset("fast"),
        )

        summary = execute_relay_dispatch_plan_with_policy(
            plan,
            adapter,
            proof_trail=_clean_proof_trail("packet-proof-policy-block"),
        )

        assert adapter.received_payloads == []
        assert summary.results == ()
        assert len(summary.errors) == 1
        error = summary.errors[0]
        assert error.error.startswith("deepseek_transport_blocked:")
        assert "blocked:candidate-only" in error.error
        envelope = error.dispatch_metadata_envelope
        assert envelope is not None
        assert envelope.deepseek_transport_authority is not None
        assert envelope.deepseek_transport_authority.transport_authorized is False

    def test_policy_wrapper_allows_authorized_deepseek_metadata(self) -> None:
        plan = _make_plan(1)
        adapter = FakeModelAdapter(
            "response",
            metadata=_deepseek_authorized_metadata("fast"),
        )

        summary = execute_relay_dispatch_plan_with_policy(
            plan,
            adapter,
            proof_trail=_clean_proof_trail("packet-proof-policy-allow"),
        )

        assert adapter.received_payloads == [plan.lanes[0].payload]
        assert summary.errors == ()
        assert len(summary.results) == 1
        envelope = summary.results[0].dispatch_metadata_envelope
        assert envelope is not None
        assert envelope.deepseek_transport_authority is not None
        assert envelope.deepseek_transport_authority.transport_authorized is True

    def test_direct_dispatch_blocked_by_uppercase_true_gate_strings(self) -> None:
        """Codex Review A MEDIUM contract preserved on the direct path: case
        variants like ``"True"`` keep the gate flag False and the lane
        refused, even though the validation ref is level-1."""
        plan = _make_plan(1)
        base = deepseek_candidate_metadata_preset("fast")
        assert base.deepseek_candidate_state is not None
        case_variant_state = dict(base.deepseek_candidate_state)
        case_variant_state.update(
            {
                "validation_evidence_ref": (
                    "deepseek-validation:level-1:validation-cleared"
                ),
                "external_review_evidence_ref": (
                    "external-review:deepseek:deepseek-chat:passed"
                ),
                "external_review_status": "passed",
                "human_gate_satisfied": "True",
                "prime_authority_satisfied": "true",
            }
        )
        metadata = dataclasses.replace(
            base, deepseek_candidate_state=case_variant_state
        )
        adapter = FakeModelAdapter("response", metadata=metadata)

        summary = execute_relay_dispatch_plan(plan, adapter)

        assert adapter.received_payloads == []
        assert summary.results == ()
        assert len(summary.errors) == 1
        assert "blocked:human-gate-required" in summary.errors[0].error
