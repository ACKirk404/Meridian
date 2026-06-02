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
)
from meridian_core.prompt_payload_meter import PayloadStatus, PromptPayloadSnapshot
from meridian_core.relay import ModelRole, route_from_tier
from meridian_core.relay_dispatch import RelayDispatchLane, RelayDispatchPlan
from meridian_core.cognition_policy import evaluate_cognition_policy
from meridian_core.relay_executor import (
    AegisGateEvidenceSummary,
    RelayDecisionRecord,
    RelayDispatchEnvelope,
    RelayExecutionError,
    RelayExecutionResult,
    RelayExecutionSummary,
    RelayPromptPayloadEvidence,
    RelayProofGateError,
    _build_decision_record,
    execute_relay_dispatch_plan,
    execute_relay_dispatch_plan_with_policy,
    execute_relay_plan_with_registry,
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


def _constant_model_call(text: str):
    """Return a model_call that always returns *text*."""
    def _call(payload: str) -> str:
        return text
    return _call


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

    def test_tier3_clean_proof_allows_dispatch(self):
        plan = _make_plan(3)
        summary = execute_relay_dispatch_plan_with_policy(
            plan,
            _constant_model_call("ok"),
            proof_trail=ProofTrail(),
        )
        assert len(summary.results) == len(plan.lanes)

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
                proof_trail=ProofTrail(),
                human_gate_approved=False,
            )

        assert calls == []

    def test_tier4_clean_proof_with_human_approval_allows_dispatch(self):
        plan = _make_plan(4)
        summary = execute_relay_dispatch_plan_with_policy(
            plan,
            _constant_model_call("ok"),
            proof_trail=ProofTrail(),
            human_gate_approved=True,
        )
        assert len(summary.results) == len(plan.lanes)

    def test_tier2_still_dispatches_without_proof(self):
        plan = _make_plan(2)
        summary = execute_relay_dispatch_plan_with_policy(
            plan,
            _constant_model_call("ok"),
            proof_trail=None,
        )
        assert len(summary.results) == len(plan.lanes)


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
            proof_trail=ProofTrail(),
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
        # Verify order preservation (Python 3.7+ guarantees dict insertion order)
        assert list(dict1.keys()) == list(dict2.keys())
