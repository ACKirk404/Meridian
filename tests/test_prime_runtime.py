"""Tests for Prime runtime decision contract."""

from meridian_core.compass_logic_snapshot import compass_logic_snapshot
from meridian_core.prime_runtime import (
    PrimeDecisionStatus,
    PrimeIntentKind,
    assemble_prime_runtime_context,
    evaluate_prime_executability,
    make_prime_decision,
    resolve_prime_decision,
    resolve_prime_owner,
    prime_runtime_snapshot,
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
    assert len(payload["proof"]) == 4
    assert {item["source"] for item in payload["proof"]} == {
        "Compass",
        "Vulcan",
        "Relay",
        "Prime",
    }
    assert "visibleToScott" in payload


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
    assert all(source["source"] in {"unknown", "pending"} for source in payload["sourceRefs"])


def test_prime_owner_resolver_maps_intents_to_harnesses():
    assert resolve_prime_owner(PrimeIntentKind.PROJECT_CONTEXT) == "Compass"
    assert resolve_prime_owner("session lifecycle") == "Vulcan"
    assert resolve_prime_owner("model-route") == "Relay"
    assert resolve_prime_owner("proof_risk") == "Aegis"
    assert resolve_prime_owner(None) == "Prime"


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
    assert snapshot["decision"]["context"]["sourceRefs"][0]["harness"] == "Compass"
    assert "Prime Job" in titles
    assert "Logic Hierarchy" in titles
    assert "Executability Logic" in titles
    assert "Proof Packet" in titles
