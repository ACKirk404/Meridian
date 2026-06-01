"""Tests for the Relay executor (meridian_core/relay_executor.py)."""

from __future__ import annotations

import pytest

from meridian_core.aegis import (
    AegisEvidence,
    EvidenceSeverity,
    EvidenceStatus,
    EvidenceType,
    ProofTrail,
)
from meridian_core.model_adapter import AdapterRegistry, FakeModelAdapter, MissingAdapterError
from meridian_core.prompt_payload_meter import PayloadStatus, PromptPayloadSnapshot
from meridian_core.relay import ModelRole, route_from_tier
from meridian_core.relay_dispatch import RelayDispatchLane, RelayDispatchPlan
from meridian_core.cognition_policy import evaluate_cognition_policy
from meridian_core.relay_executor import (
    RelayExecutionError,
    RelayExecutionResult,
    RelayExecutionSummary,
    RelayProofGateError,
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


class TestAdapterMetadata:
    def test_execution_result_without_metadata(self) -> None:
        result = RelayExecutionResult(
            role=ModelRole.BUILDER,
            preferred_model="gpt-4",
            output="output text",
        )
        assert result.adapter_metadata is None

    def test_execution_result_with_metadata(self) -> None:
        from meridian_core.model_adapter import ModelHarnessMetadata

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

    def test_fake_adapter_with_custom_metadata(self) -> None:
        from meridian_core.model_adapter import ModelHarnessMetadata

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

    def test_adapter_metadata_immutable(self) -> None:
        from meridian_core.model_adapter import ModelHarnessMetadata

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
