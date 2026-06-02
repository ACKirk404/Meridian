"""Tests for Prime runtime decision contract."""

from meridian_core.compass_logic_snapshot import compass_logic_snapshot
from meridian_core.prime_runtime import (
    PrimeAegisRiskInput,
    PrimeDecisionStatus,
    PrimeInteractionRequest,
    PrimeIntentKind,
    aegis_risk_from_aggregate,
    assemble_prime_runtime_context,
    audit_prime_decision,
    evaluate_prime_executability,
    make_prime_decision,
    resolve_prime_decision,
    resolve_prime_interaction,
    resolve_prime_owner,
    prime_runtime_snapshot,
)
from meridian_core.aegis import (
    GateDecision,
    GateResult,
    summarize_aggregate_route_gates,
    summarize_gate_results,
)
from meridian_core.relay_logic_snapshot import relay_logic_snapshot
from meridian_core.vulcan_logic_snapshot import vulcan_logic_snapshot


def test_prime_runtime_context_assembles_backend_sources():
    context = assemble_prime_runtime_context(
        compass_snapshot=compass_logic_snapshot(),
        vulcan_snapshot=vulcan_logic_snapshot(),
        relay_snapshot=relay_logic_snapshot(),
    )

    assert context.project_id == "Meridian"
    assert "Prime oriented" in context.project_summary
    assert "session targets" in context.session_state
    assert "model-routing" in context.relay_route_summary
    assert [source.harness for source in context.source_refs] == [
        "Compass",
        "Vulcan",
        "Relay",
        "Aegis",
    ]
    assert context.aegis_risk is None


def test_prime_decision_shape_is_visible_and_executable():
    context = assemble_prime_runtime_context(
        compass_snapshot=compass_logic_snapshot(),
        vulcan_snapshot=vulcan_logic_snapshot(),
        relay_snapshot=relay_logic_snapshot(),
    )
    decision = make_prime_decision(context=context)
    payload = decision.to_dict()

    assert payload["decisionId"] == "prime-runtime-decision-v1"
    assert payload["status"] == "executable"
    assert payload["ownerHarness"] == "Prime"
    assert payload["executable"] is True
    assert payload["blockers"] == []
    assert len(payload["proof"]) == 5
    assert {item["source"] for item in payload["proof"]} == {
        "Aegis",
        "Compass",
        "Vulcan",
        "Relay",
        "Prime",
    }
    assert "visibleToScott" in payload
    assert payload["driftAudit"]["status"] == "clean"
    assert payload["driftAudit"]["clean"] is True


def test_prime_decision_blockers_force_blocked_status():
    context = assemble_prime_runtime_context(
        compass_snapshot=compass_logic_snapshot(),
        vulcan_snapshot=vulcan_logic_snapshot(),
        relay_snapshot=relay_logic_snapshot(),
    )
    decision = make_prime_decision(
        context=context,
        status=PrimeDecisionStatus.EXECUTABLE,
        blockers=("Relay route unavailable",),
    )

    assert decision.status == PrimeDecisionStatus.BLOCKED
    assert decision.is_executable() is False
    assert decision.to_dict()["blockers"] == ["Relay route unavailable"]


def test_prime_decision_preserves_needs_approval_status_with_blockers():
    context = assemble_prime_runtime_context(
        compass_snapshot=compass_logic_snapshot(),
        vulcan_snapshot=vulcan_logic_snapshot(),
        relay_snapshot=relay_logic_snapshot(),
    )
    decision = make_prime_decision(
        context=context,
        status=PrimeDecisionStatus.NEEDS_APPROVAL,
        blockers=("approval required",),
    )

    assert decision.status == PrimeDecisionStatus.NEEDS_APPROVAL
    assert decision.is_executable() is False


def test_prime_context_falls_back_without_inventing_sources():
    context = assemble_prime_runtime_context(
        compass_snapshot={},
        vulcan_snapshot={},
        relay_snapshot={},
        project_id="Unknown",
    )
    payload = context.to_dict()

    assert payload["projectId"] == "Unknown"
    assert payload["projectSummary"] == "Compass project context unavailable."
    assert payload["sessionState"] == "Vulcan session lifecycle unavailable."
    assert payload["relayRouteSummary"] == "Relay model route unavailable."
    assert payload["aegisRisk"] is None
    assert all(source["source"] in {"unknown", "pending"} for source in payload["sourceRefs"])


def test_prime_context_consumes_aegis_aggregate_gate_summary():
    aggregate = summarize_aggregate_route_gates(summarize_gate_results([]))
    aegis_risk = aegis_risk_from_aggregate(aggregate)
    context = assemble_prime_runtime_context(
        compass_snapshot=compass_logic_snapshot(),
        vulcan_snapshot=vulcan_logic_snapshot(),
        relay_snapshot=relay_logic_snapshot(),
        aegis_risk=aegis_risk,
    )
    payload = context.to_dict()

    assert context.aegis_risk is not None
    assert payload["aegisRisk"]["aggregateAction"] == "route_allowed"
    assert payload["aegisRisk"]["highestSeverity"] == "info"
    assert payload["aegisRisk"]["blocking"] is False
    assert payload["sourceRefs"][-1]["source"] == "meridian_core.aegis.summarize_aggregate_route_gates"


def test_prime_executability_needs_approval_when_aegis_blocks():
    aggregate = summarize_aggregate_route_gates(
        summarize_gate_results([
            GateResult(
                gate_name="unknown_route_class",
                decision=GateDecision.BLOCK,
                reason="route class missing",
            )
        ])
    )
    context = assemble_prime_runtime_context(
        compass_snapshot=compass_logic_snapshot(),
        vulcan_snapshot=vulcan_logic_snapshot(),
        relay_snapshot=relay_logic_snapshot(),
        aegis_risk=aegis_risk_from_aggregate(aggregate),
    )
    gate = evaluate_prime_executability(context=context, owner_harness="Prime")

    assert gate.status == PrimeDecisionStatus.NEEDS_APPROVAL
    assert "Aegis gate blocked: unknown_route_class" in gate.blockers
    assert "approval required" in gate.blockers


def test_prime_aegis_risk_input_serializes_without_aegis_imports():
    risk = PrimeAegisRiskInput(
        source="manual-test",
        highest_severity="warning",
        aggregate_action="route_demoted_to_tier_1",
        evidence_required=("gate: proof",),
        demoted_gates=("deepseek_validation",),
    )

    assert risk.is_blocking() is False
    assert risk.requires_approval() is False
    assert risk.to_dict()["demotedGates"] == ["deepseek_validation"]


def test_prime_owner_resolver_maps_intents_to_harnesses():
    assert resolve_prime_owner(PrimeIntentKind.PROJECT_CONTEXT) == "Compass"
    assert resolve_prime_owner("session lifecycle") == "Vulcan"
    assert resolve_prime_owner("model-route") == "Relay"
    assert resolve_prime_owner("proof_risk") == "Aegis"
    assert resolve_prime_owner(None) == "Prime"


def test_prime_interaction_request_serializes_visible_fields():
    request = PrimeInteractionRequest(
        request_id="req-1",
        intent=PrimeIntentKind.MODEL_ROUTE,
        action="select_model_route",
        why="Need a route before dispatch.",
        project_id="Meridian",
        visible_prompt_ref="prime-input-1",
    )

    assert request.to_dict() == {
        "requestId": "req-1",
        "intent": "model_route",
        "action": "select_model_route",
        "why": "Need a route before dispatch.",
        "projectId": "Meridian",
        "risk": "safe_read_only",
        "requiresApproval": False,
        "requiresClarification": False,
        "visiblePromptRef": "prime-input-1",
    }


def test_resolve_prime_interaction_uses_request_owner_and_payload():
    context = assemble_prime_runtime_context(
        compass_snapshot=compass_logic_snapshot(),
        vulcan_snapshot=vulcan_logic_snapshot(),
        relay_snapshot=relay_logic_snapshot(),
    )
    request = PrimeInteractionRequest(
        request_id="req-model-route",
        intent=PrimeIntentKind.MODEL_ROUTE,
        action="select_model_route",
        why="Prime needs Relay before asking a model.",
    )
    decision = resolve_prime_interaction(context=context, request=request)
    payload = decision.to_dict()

    assert decision.owner_harness == "Relay"
    assert payload["request"]["requestId"] == "req-model-route"
    assert payload["request"]["intent"] == "model_route"
    assert payload["ownerHarness"] == "Relay"
    assert payload["driftAudit"]["clean"] is True


def test_prime_drift_audit_detects_project_mismatch():
    context = assemble_prime_runtime_context(
        compass_snapshot=compass_logic_snapshot(),
        vulcan_snapshot=vulcan_logic_snapshot(),
        relay_snapshot=relay_logic_snapshot(),
        project_id="Meridian",
    )
    request = PrimeInteractionRequest(
        request_id="req-wrong-project",
        intent=PrimeIntentKind.ORCHESTRATION,
        action="inspect_backend_context",
        why="Test mismatch.",
        project_id="Polaris",
    )
    decision = resolve_prime_interaction(context=context, request=request)
    audit = audit_prime_decision(decision)

    assert audit.status == "drift"
    assert "request project does not match context project" in audit.failures


def test_prime_drift_audit_detects_missing_owner_source():
    context = assemble_prime_runtime_context(
        compass_snapshot=compass_logic_snapshot(),
        vulcan_snapshot=vulcan_logic_snapshot(),
        relay_snapshot={},
    )
    request = PrimeInteractionRequest(
        request_id="req-missing-relay",
        intent=PrimeIntentKind.MODEL_ROUTE,
        action="select_model_route",
        why="Relay source is missing.",
    )
    decision = resolve_prime_interaction(context=context, request=request)
    audit = audit_prime_decision(decision)

    assert audit.status == "drift"
    assert "owner source unavailable: Relay" in audit.failures


def test_prime_executability_blocks_missing_owner_source():
    context = assemble_prime_runtime_context(
        compass_snapshot={},
        vulcan_snapshot={},
        relay_snapshot={},
    )
    gate = evaluate_prime_executability(context=context, owner_harness="Relay")

    assert gate.status == PrimeDecisionStatus.BLOCKED
    assert gate.to_dict()["executable"] is False
    assert "Relay source unavailable" in gate.blockers
    assert "model route proof unavailable" in gate.blockers


def test_prime_executability_approval_and_clarification_are_explicit():
    context = assemble_prime_runtime_context(
        compass_snapshot=compass_logic_snapshot(),
        vulcan_snapshot=vulcan_logic_snapshot(),
        relay_snapshot=relay_logic_snapshot(),
    )

    approval_gate = evaluate_prime_executability(
        context=context,
        owner_harness="Aegis",
        requires_approval=True,
    )
    clarification_gate = evaluate_prime_executability(
        context=context,
        owner_harness="Prime",
        requires_clarification=True,
    )

    assert approval_gate.status == PrimeDecisionStatus.NEEDS_APPROVAL
    assert "approval required" in approval_gate.blockers
    assert clarification_gate.status == PrimeDecisionStatus.NEEDS_CLARIFICATION
    assert "clarification required" in clarification_gate.blockers


def test_resolve_prime_decision_applies_hierarchy_and_gate():
    context = assemble_prime_runtime_context(
        compass_snapshot=compass_logic_snapshot(),
        vulcan_snapshot=vulcan_logic_snapshot(),
        relay_snapshot=relay_logic_snapshot(),
    )
    decision = resolve_prime_decision(
        context=context,
        intent="model_route",
        action="select_model_route",
        why="Prime needs a model access path before dispatch.",
    )
    payload = decision.to_dict()

    assert payload["ownerHarness"] == "Relay"
    assert payload["status"] == "executable"
    assert payload["executable"] is True
    assert payload["proof"][-1]["answer"] == (
        "Relay owns this decision after Prime hierarchy resolution."
    )


def test_resolve_prime_decision_blocks_when_backend_source_missing():
    context = assemble_prime_runtime_context(
        compass_snapshot=compass_logic_snapshot(),
        vulcan_snapshot=vulcan_logic_snapshot(),
        relay_snapshot={},
    )
    decision = resolve_prime_decision(
        context=context,
        intent=PrimeIntentKind.MODEL_ROUTE,
        action="select_model_route",
        why="Prime needs Relay before model dispatch.",
    )

    assert decision.status == PrimeDecisionStatus.BLOCKED
    assert decision.is_executable() is False
    assert "Relay source unavailable" in decision.blockers


def test_prime_runtime_snapshot_is_backend_visible_contract():
    snapshot = prime_runtime_snapshot()
    titles = [section["title"] for section in snapshot["capabilitySections"]]

    assert snapshot["ok"] is True
    assert snapshot["service"] == "meridian-prime-runtime"
    assert snapshot["source"] == "meridian_core.prime_runtime.resolve_prime_decision"
    assert snapshot["decision"]["ownerHarness"] == "Prime"
    assert snapshot["decision"]["request"]["requestId"] == "prime-runtime-request-v1"
    assert snapshot["decision"]["driftAudit"]["status"] == "clean"
    assert snapshot["decision"]["context"]["sourceRefs"][0]["harness"] == "Compass"
    assert snapshot["decision"]["context"]["aegisRisk"]["aggregateAction"] == "route_allowed"
    assert "Interaction Request" in titles
    assert "Prime Job" in titles
    assert "Logic Hierarchy" in titles
    assert "Aegis Binding" in titles
    assert "Executability Logic" in titles
    assert "No Drift Audit" in titles
    assert "Proof Packet" in titles
