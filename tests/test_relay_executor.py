"""Tests for the Relay executor (meridian_core/relay_executor.py)."""

from __future__ import annotations

import pytest

from meridian_core.relay import ModelRole, route_from_tier
from meridian_core.relay_dispatch import RelayDispatchLane, RelayDispatchPlan
from meridian_core.relay_executor import (
    RelayExecutionError,
    RelayExecutionResult,
    RelayExecutionSummary,
    execute_relay_dispatch_plan,
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
