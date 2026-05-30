import pytest

from meridian_core.decisions import run_decision_loop
from meridian_core.injections import make_injection
from meridian_core.models import AdapterTier, InjectionMode, Priority
from meridian_core.sample_state import (
    make_sample_adapters,
    make_sample_heartbeats,
    make_sample_portfolio,
)


def test_injection_has_all_required_fields():
    inj = make_injection(
        target_session_id="session_abc",
        instruction="Run the test suite and report results.",
        reason="Proof verification required before advancing next move.",
        priority=Priority.HIGH,
        mode=InjectionMode.DIRECTIVE,
    )
    assert inj.id, "id must be set"
    assert inj.target_session_id == "session_abc"
    assert inj.instruction
    assert inj.reason
    assert inj.priority == Priority.HIGH
    assert inj.mode == InjectionMode.DIRECTIVE
    assert inj.created_at is not None


def test_injection_ids_are_unique():
    inj_a = make_injection("session_a", "Do X", "reason A")
    inj_b = make_injection("session_b", "Do Y", "reason B")
    assert inj_a.id != inj_b.id


def test_all_injection_modes_are_constructable():
    for mode in InjectionMode:
        inj = make_injection(
            target_session_id="test_session",
            instruction="Test instruction",
            reason="Test reason",
            mode=mode,
        )
        assert inj.mode == mode


def test_provider_adapter_public_safety():
    adapters = make_sample_adapters()

    public_safe = [a for a in adapters if a.is_public_safe()]
    not_public_safe = [a for a in adapters if not a.is_public_safe()]

    assert public_safe, "Some adapters should be public-safe"
    assert not_public_safe, "Some adapters should not be public-safe"


def test_disabled_for_public_build_adapters_are_not_safe():
    adapters = make_sample_adapters()
    disabled = [a for a in adapters if a.tier == AdapterTier.DISABLED_FOR_PUBLIC_BUILD]
    assert disabled, "Sample adapters must include at least one DISABLED_FOR_PUBLIC_BUILD adapter"
    assert all(not a.is_public_safe() for a in disabled)


def test_official_api_adapters_are_public_safe():
    adapters = make_sample_adapters()
    official = [a for a in adapters if a.tier == AdapterTier.OFFICIAL_API_SUPPORTED]
    assert official, "Sample adapters must include at least one OFFICIAL_API_SUPPORTED adapter"
    assert all(a.is_public_safe() for a in official)


def test_private_only_adapters_are_not_public_safe():
    from meridian_core.models import ProviderAdapter
    private = ProviderAdapter(
        id="adapter_private",
        name="Private Adapter",
        provider="Internal",
        tier=AdapterTier.PRIVATE_ONLY,
        description="Private internal adapter",
    )
    assert not private.is_public_safe()


def test_decision_loop_injections_target_blocked_harnesses():
    portfolio = make_sample_portfolio()
    heartbeats = make_sample_heartbeats()
    result = run_decision_loop(portfolio, heartbeats)

    from meridian_core.models import HeartbeatStatus
    blocked_with_blockers = {
        hb.harness_id
        for hb in heartbeats
        if hb.status in (HeartbeatStatus.BLOCKED, HeartbeatStatus.STALE, HeartbeatStatus.FAILED)
        and hb.blockers
    }

    injection_targets = {inj.target_session_id for inj in result.injections}
    assert injection_targets & blocked_with_blockers, (
        "Expected at least one injection targeting a blocked/stale/failed harness with known blockers"
    )
