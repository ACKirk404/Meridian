"""Tests for ``meridian_core.provider_balance``.

These tests exercise the first V3 Provider Balance / Usage backend domain
slice. They cover the snapshot/summary frozen-dataclass invariants, the
display-safety redaction policy, the fail-safe ``unknown`` defaults, the
deterministic ordering / selected-provider handling, and the mapping
shape compatibility with ``bifrost.cockpit.provider_balance_view_from_summary``.

Bifrost is **not** imported here — the module is the source of truth for
provider-balance policy, and tests verify the mapping shape structurally.
"""

from __future__ import annotations

import dataclasses

import pytest

from meridian_core.provider_balance import (
    ProviderBalanceSnapshot,
    ProviderBalanceSummary,
    ProviderBalanceValidationError,
    ProviderCostPressure,
    ProviderCreditStatus,
    ProviderHealth,
    ProviderPolicyState,
    ProviderQuotaState,
    ProviderRouteKind,
    ProviderRoutingOwner,
    ProviderTrustState,
    build_provider_balance_snapshot,
    build_provider_balance_summary,
    safe_display_label,
    safe_display_notes,
    safe_evidence_ref,
    safe_provider_id,
    unknown_provider_snapshot,
)
from meridian_core.provider_balance import (
    _MAX_EVIDENCE_REFS_PER_RECORD,
    _UNSAFE_DISPLAY_REDACTION,
    _UNSAFE_EVIDENCE_REDACTION,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestProviderEnums:
    def test_provider_health_values(self):
        values = {member.value for member in ProviderHealth}
        assert values == {"unknown", "ok", "degraded", "offline", "unavailable"}

    def test_provider_route_kind_covers_neutral_families(self):
        values = {member.value for member in ProviderRouteKind}
        # direct (Claude/OpenAI/DeepSeek), aggregator (OpenRouter), local
        assert {"unknown", "direct", "aggregator", "local"} <= values

    def test_provider_cost_pressure_has_unknown_and_none_distinct(self):
        # UNKNOWN = no live signal; NONE = live signal says no pressure
        assert ProviderCostPressure.UNKNOWN.value == "unknown"
        assert ProviderCostPressure.NONE.value == "none"
        values = {member.value for member in ProviderCostPressure}
        assert {"low", "moderate", "high", "critical", "degraded"} <= values

    def test_provider_quota_state_values(self):
        values = {member.value for member in ProviderQuotaState}
        assert values == {
            "unknown", "available", "limited", "metered",
            "exhausted", "unavailable",
        }

    def test_provider_credit_status_values(self):
        values = {member.value for member in ProviderCreditStatus}
        assert values == {
            "unknown", "available", "limited", "exhausted", "unavailable",
        }

    def test_provider_trust_state_covers_neutral_families(self):
        values = {member.value for member in ProviderTrustState}
        assert {"unknown", "trusted", "candidate", "aggregator", "local"} <= values

    def test_provider_policy_state_values(self):
        values = {member.value for member in ProviderPolicyState}
        assert values == {"ok", "warning", "blocked", "unknown"}

    def test_provider_routing_owner_values(self):
        assert ProviderRoutingOwner.RELAY.value == "Relay"
        assert ProviderRoutingOwner.BIFROST.value == "Bifrost"
        assert ProviderRoutingOwner.AEGIS.value == "Aegis"
        assert ProviderRoutingOwner.UNKNOWN.value == "unknown"


# ---------------------------------------------------------------------------
# Safety helpers
# ---------------------------------------------------------------------------

class TestSafeProviderId:
    def test_accepts_provider_neutral_slugs(self):
        for pid in ("claude", "openai", "deepseek", "openrouter", "local-llama"):
            assert safe_provider_id(pid) == pid

    def test_empty_returns_empty(self):
        assert safe_provider_id("") == ""
        assert safe_provider_id(None) == ""

    def test_strips_whitespace(self):
        assert safe_provider_id("  claude  ") == "claude"

    def test_redacts_unsafe_marker(self):
        assert safe_provider_id("api_key_provider") == _UNSAFE_DISPLAY_REDACTION
        assert safe_provider_id("secret-thing") == _UNSAFE_DISPLAY_REDACTION
        assert safe_provider_id("raw_prompt") == _UNSAFE_DISPLAY_REDACTION

    def test_redacts_path_separators(self):
        assert safe_provider_id("/etc/claude") == _UNSAFE_DISPLAY_REDACTION
        assert safe_provider_id("a/b") == _UNSAFE_DISPLAY_REDACTION
        assert safe_provider_id("c:\\windows") == _UNSAFE_DISPLAY_REDACTION

    def test_redacts_whitespace_inside(self):
        assert safe_provider_id("hello world") == _UNSAFE_DISPLAY_REDACTION

    def test_redacts_oversized_id(self):
        assert safe_provider_id("a" * 200) == _UNSAFE_DISPLAY_REDACTION


class TestSafeEvidenceRef:
    def test_accepts_kind_id_form(self):
        assert safe_evidence_ref("adapter:claude") == "adapter:claude"
        assert safe_evidence_ref("payload-snapshot:claude-dispatch") == (
            "payload-snapshot:claude-dispatch"
        )
        assert safe_evidence_ref("provider-balance:claude") == (
            "provider-balance:claude"
        )

    def test_accepts_bare_slug(self):
        assert safe_evidence_ref("claude-snapshot") == "claude-snapshot"

    def test_empty_returns_none(self):
        assert safe_evidence_ref("") is None
        assert safe_evidence_ref(None) is None

    def test_redacts_unsafe_marker(self):
        assert safe_evidence_ref("model_payload:abc") == _UNSAFE_EVIDENCE_REDACTION
        assert safe_evidence_ref("api_key:leaked") == _UNSAFE_EVIDENCE_REDACTION

    def test_redacts_path_separators(self):
        assert safe_evidence_ref("/etc/passwd") == _UNSAFE_EVIDENCE_REDACTION
        assert safe_evidence_ref("a/b") == _UNSAFE_EVIDENCE_REDACTION
        assert safe_evidence_ref("a\\b") == _UNSAFE_EVIDENCE_REDACTION

    def test_redacts_whitespace(self):
        assert safe_evidence_ref("kind:id with space") == _UNSAFE_EVIDENCE_REDACTION
        assert safe_evidence_ref("kind:id\nbad") == _UNSAFE_EVIDENCE_REDACTION

    def test_redacts_oversized_ref(self):
        assert safe_evidence_ref("k:" + "a" * 200) == _UNSAFE_EVIDENCE_REDACTION


class TestSafeDisplayLabel:
    def test_accepts_short_labels_with_punctuation(self):
        assert safe_display_label("credit: available") == "credit: available"
        assert safe_display_label("$0.18 estimated") == "$0.18 estimated"

    def test_redacts_unsafe_marker(self):
        assert safe_display_label("api_key: $5") == _UNSAFE_DISPLAY_REDACTION
        assert safe_display_label("raw_prompt LEAKED") == _UNSAFE_DISPLAY_REDACTION
        assert safe_display_label("bearer token") == _UNSAFE_DISPLAY_REDACTION

    def test_redacts_newlines(self):
        assert safe_display_label("a\nb") == _UNSAFE_DISPLAY_REDACTION

    def test_redacts_oversize(self):
        assert safe_display_label("x" * 500) == _UNSAFE_DISPLAY_REDACTION

    def test_empty_returns_empty(self):
        assert safe_display_label("") == ""
        assert safe_display_label(None) == ""


class TestSafeDisplayNotes:
    def test_accepts_short_notes(self):
        assert safe_display_notes("Primary provider ready") == (
            "Primary provider ready"
        )

    def test_redacts_unsafe_marker(self):
        assert safe_display_notes("provider_response sample") == (
            _UNSAFE_DISPLAY_REDACTION
        )
        assert safe_display_notes("git checkout main") == _UNSAFE_DISPLAY_REDACTION
        assert safe_display_notes("worktree drift") == _UNSAFE_DISPLAY_REDACTION

    def test_redacts_overlong_notes(self):
        assert safe_display_notes("x" * 1000) == _UNSAFE_DISPLAY_REDACTION


# ---------------------------------------------------------------------------
# ProviderBalanceSnapshot direct construction
# ---------------------------------------------------------------------------

class TestProviderBalanceSnapshotDirect:
    def test_minimal_construction(self):
        snap = ProviderBalanceSnapshot(provider_id="claude")
        assert snap.provider_id == "claude"
        assert snap.display_name == ""
        assert snap.model_name == ""
        assert snap.evidence_refs == ()

    def test_defaults_are_fail_safe_unknown(self):
        snap = ProviderBalanceSnapshot(provider_id="claude")
        assert snap.trust_state is ProviderTrustState.UNKNOWN
        assert snap.health is ProviderHealth.UNKNOWN
        assert snap.route_kind is ProviderRouteKind.UNKNOWN
        assert snap.cost_pressure is ProviderCostPressure.UNKNOWN
        assert snap.quota_state is ProviderQuotaState.UNKNOWN
        assert snap.credit_status is ProviderCreditStatus.UNKNOWN

    def test_defaults_never_imply_healthy_or_available(self):
        snap = ProviderBalanceSnapshot(provider_id="claude")
        assert snap.health is not ProviderHealth.OK
        assert snap.quota_state is not ProviderQuotaState.AVAILABLE
        assert snap.credit_status is not ProviderCreditStatus.AVAILABLE
        assert snap.cost_pressure is not ProviderCostPressure.NONE
        assert snap.trust_state is not ProviderTrustState.TRUSTED

    def test_default_numeric_zero(self):
        snap = ProviderBalanceSnapshot(provider_id="claude")
        assert snap.context_budget_tokens == 0
        assert snap.prompt_budget_tokens == 0
        assert snap.current_prompt_tokens == 0
        assert snap.prompt_budget_percent == 0.0
        assert snap.prompt_delta_tokens == 0

    def test_frozen_instance(self):
        snap = ProviderBalanceSnapshot(provider_id="claude")
        with pytest.raises(dataclasses.FrozenInstanceError):
            snap.provider_id = "other"  # type: ignore[misc]

    def test_rejects_empty_provider_id(self):
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSnapshot(provider_id="")

    def test_rejects_non_string_provider_id(self):
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSnapshot(provider_id=42)  # type: ignore[arg-type]

    def test_rejects_unsafe_provider_id(self):
        for pid in ("api_key_x", "/etc/claude", "a b", "secret-x"):
            with pytest.raises(ProviderBalanceValidationError):
                ProviderBalanceSnapshot(provider_id=pid)

    def test_rejects_unsafe_display_name(self):
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSnapshot(
                provider_id="claude",
                display_name="raw_prompt sample",
            )

    def test_rejects_unsafe_model_name(self):
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSnapshot(
                provider_id="claude",
                model_name="model_payload:secret",
            )

    def test_rejects_unsafe_notes(self):
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSnapshot(
                provider_id="claude",
                notes="bearer token included",
            )

    def test_rejects_unsafe_estimated_spend_label(self):
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSnapshot(
                provider_id="claude",
                estimated_spend_label="api_key included",
            )

    def test_rejects_unsafe_remaining_credit_label(self):
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSnapshot(
                provider_id="claude",
                remaining_credit_label="credential leak",
            )

    def test_rejects_negative_tokens(self):
        for kw in (
            {"context_budget_tokens": -1},
            {"prompt_budget_tokens": -1},
            {"current_prompt_tokens": -1},
        ):
            with pytest.raises(ProviderBalanceValidationError):
                ProviderBalanceSnapshot(provider_id="claude", **kw)

    def test_rejects_out_of_range_percent(self):
        for pct in (-0.1, 100.1, 150.0):
            with pytest.raises(ProviderBalanceValidationError):
                ProviderBalanceSnapshot(
                    provider_id="claude",
                    prompt_budget_percent=pct,
                )

    def test_rejects_non_enum_health(self):
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSnapshot(
                provider_id="claude",
                health="ok",  # type: ignore[arg-type]
            )

    def test_rejects_non_tuple_evidence_refs(self):
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSnapshot(
                provider_id="claude",
                evidence_refs=["adapter:claude"],  # type: ignore[arg-type]
            )

    def test_rejects_unsafe_evidence_ref(self):
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSnapshot(
                provider_id="claude",
                evidence_refs=("adapter:claude", "model_payload:secret"),
            )

    def test_rejects_overflow_evidence_refs(self):
        too_many = tuple(
            f"adapter:p-{i}" for i in range(_MAX_EVIDENCE_REFS_PER_RECORD + 1)
        )
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSnapshot(
                provider_id="claude",
                evidence_refs=too_many,
            )

    def test_to_mapping_includes_all_required_keys(self):
        snap = ProviderBalanceSnapshot(
            provider_id="claude",
            display_name="Claude",
            model_name="claude-sonnet-4-20250514",
            trust_state=ProviderTrustState.TRUSTED,
            health=ProviderHealth.OK,
            route_kind=ProviderRouteKind.DIRECT,
            context_budget_tokens=200_000,
            prompt_budget_tokens=4_000,
            current_prompt_tokens=920,
            prompt_budget_percent=23.0,
            prompt_delta_tokens=0,
            cost_pressure=ProviderCostPressure.LOW,
            quota_state=ProviderQuotaState.AVAILABLE,
            remaining_credit_label="credit: available",
            credit_status=ProviderCreditStatus.AVAILABLE,
            estimated_spend_label="$0.18 estimated",
            notes="Primary provider ready",
            evidence_refs=("adapter:claude", "payload-snapshot:claude-dispatch"),
        )
        mapping = snap.to_mapping()
        assert set(mapping.keys()) == {
            "provider_id", "display_name", "model_name", "trust_state",
            "health", "route_kind", "context_budget_tokens",
            "prompt_budget_tokens", "current_prompt_tokens",
            "prompt_budget_percent", "prompt_delta_tokens", "cost_pressure",
            "quota_state", "remaining_credit_label", "credit_status",
            "estimated_spend_label", "notes", "evidence_refs",
        }
        assert mapping["provider_id"] == "claude"
        assert mapping["trust_state"] == "trusted"
        assert mapping["health"] == "ok"
        assert mapping["route_kind"] == "direct"
        assert mapping["cost_pressure"] == "low"
        assert mapping["quota_state"] == "available"
        assert mapping["credit_status"] == "available"
        assert mapping["prompt_budget_percent"] == 23.0
        assert mapping["evidence_refs"] == [
            "adapter:claude", "payload-snapshot:claude-dispatch",
        ]


# ---------------------------------------------------------------------------
# unknown_provider_snapshot
# ---------------------------------------------------------------------------

class TestUnknownProviderSnapshot:
    def test_returns_fail_safe_unknown(self):
        snap = unknown_provider_snapshot("claude")
        assert snap.provider_id == "claude"
        assert snap.health is ProviderHealth.UNKNOWN
        assert snap.quota_state is ProviderQuotaState.UNKNOWN
        assert snap.credit_status is ProviderCreditStatus.UNKNOWN
        assert snap.cost_pressure is ProviderCostPressure.UNKNOWN
        assert snap.trust_state is ProviderTrustState.UNKNOWN
        assert snap.route_kind is ProviderRouteKind.UNKNOWN
        assert snap.context_budget_tokens == 0
        assert snap.prompt_budget_tokens == 0
        assert snap.prompt_budget_percent == 0.0
        assert snap.remaining_credit_label == ""
        assert snap.estimated_spend_label == ""
        assert snap.notes == ""
        assert snap.evidence_refs == ()

    def test_mapping_never_reports_ok_or_available(self):
        mapping = unknown_provider_snapshot("openai").to_mapping()
        assert mapping["health"] == "unknown"
        assert mapping["quota_state"] == "unknown"
        assert mapping["credit_status"] == "unknown"
        assert mapping["cost_pressure"] == "unknown"
        assert mapping["trust_state"] == "unknown"
        assert mapping["route_kind"] == "unknown"

    def test_rejects_unsafe_provider_id(self):
        with pytest.raises(ProviderBalanceValidationError):
            unknown_provider_snapshot("api_key_x")

    def test_redacts_unsafe_display_name(self):
        snap = unknown_provider_snapshot("claude", display_name="raw_prompt leak")
        assert snap.display_name == _UNSAFE_DISPLAY_REDACTION


# ---------------------------------------------------------------------------
# build_provider_balance_snapshot
# ---------------------------------------------------------------------------

class TestBuildProviderBalanceSnapshot:
    def test_coerces_string_int(self):
        snap = build_provider_balance_snapshot(
            "claude",
            context_budget_tokens="200000",
            prompt_budget_tokens="4000",
            current_prompt_tokens="920",
            prompt_budget_percent="23.0",
            prompt_delta_tokens="-100",
        )
        assert snap.context_budget_tokens == 200_000
        assert snap.prompt_budget_tokens == 4_000
        assert snap.current_prompt_tokens == 920
        assert snap.prompt_budget_percent == 23.0
        assert snap.prompt_delta_tokens == -100

    def test_invalid_int_falls_back_to_zero(self):
        snap = build_provider_balance_snapshot(
            "claude",
            context_budget_tokens="not-a-number",
            prompt_budget_tokens=None,
            current_prompt_tokens="abc",
        )
        assert snap.context_budget_tokens == 0
        assert snap.prompt_budget_tokens == 0
        assert snap.current_prompt_tokens == 0

    def test_negative_balance_falls_back_to_zero(self):
        snap = build_provider_balance_snapshot(
            "claude",
            context_budget_tokens=-100,
            prompt_budget_tokens=-1,
            current_prompt_tokens=-50,
        )
        assert snap.context_budget_tokens == 0
        assert snap.prompt_budget_tokens == 0
        assert snap.current_prompt_tokens == 0

    def test_percent_clamps_above_100(self):
        snap = build_provider_balance_snapshot(
            "claude", prompt_budget_percent=250.0,
        )
        assert snap.prompt_budget_percent == 100.0

    def test_percent_clamps_below_0(self):
        snap = build_provider_balance_snapshot(
            "claude", prompt_budget_percent=-25.0,
        )
        assert snap.prompt_budget_percent == 0.0

    def test_percent_invalid_falls_back_to_zero(self):
        snap = build_provider_balance_snapshot(
            "claude", prompt_budget_percent="not-numeric",
        )
        assert snap.prompt_budget_percent == 0.0

    def test_bool_input_falls_back_to_default(self):
        # bools are not legitimate numeric data; treat them as missing.
        snap = build_provider_balance_snapshot(
            "claude",
            context_budget_tokens=True,
            prompt_budget_percent=False,
        )
        assert snap.context_budget_tokens == 0
        assert snap.prompt_budget_percent == 0.0

    def test_redacts_unsafe_labels(self):
        snap = build_provider_balance_snapshot(
            "claude",
            display_name="raw_prompt LEAKED",
            model_name="model_payload:secret",
            remaining_credit_label="credential x",
            estimated_spend_label="api_key: $5",
            notes="bearer token data leaked",
        )
        assert snap.display_name == _UNSAFE_DISPLAY_REDACTION
        assert snap.model_name == _UNSAFE_DISPLAY_REDACTION
        assert snap.remaining_credit_label == _UNSAFE_DISPLAY_REDACTION
        assert snap.estimated_spend_label == _UNSAFE_DISPLAY_REDACTION
        assert snap.notes == _UNSAFE_DISPLAY_REDACTION

    def test_does_not_silently_redact_provider_id(self):
        # routing identity must never be silently invented; raises instead.
        with pytest.raises(ProviderBalanceValidationError):
            build_provider_balance_snapshot("api_key_x")

    def test_filters_unsafe_evidence_refs(self):
        snap = build_provider_balance_snapshot(
            "claude",
            evidence_refs=("adapter:claude", "model_payload:secret", "/etc/x"),
        )
        assert "adapter:claude" in snap.evidence_refs
        # Unsafe ones are replaced with the redaction sentinel, not dropped.
        assert _UNSAFE_EVIDENCE_REDACTION in snap.evidence_refs

    def test_drops_empty_evidence_refs(self):
        snap = build_provider_balance_snapshot(
            "claude",
            evidence_refs=("adapter:claude", "", None, "  "),
        )
        assert snap.evidence_refs == ("adapter:claude",)

    def test_caps_evidence_refs_count(self):
        refs = tuple(f"adapter:p-{i}" for i in range(_MAX_EVIDENCE_REFS_PER_RECORD + 32))
        snap = build_provider_balance_snapshot("claude", evidence_refs=refs)
        assert len(snap.evidence_refs) == _MAX_EVIDENCE_REFS_PER_RECORD

    def test_evidence_refs_input_none_yields_empty_tuple(self):
        snap = build_provider_balance_snapshot("claude", evidence_refs=None)
        assert snap.evidence_refs == ()

    def test_preserves_safe_inputs_round_trip(self):
        snap = build_provider_balance_snapshot(
            "deepseek",
            display_name="DeepSeek",
            model_name="deepseek-chat",
            trust_state=ProviderTrustState.CANDIDATE,
            health=ProviderHealth.DEGRADED,
            route_kind=ProviderRouteKind.DIRECT,
            context_budget_tokens=65_536,
            prompt_budget_tokens=2_000,
            current_prompt_tokens=500,
            prompt_budget_percent=25.0,
            cost_pressure=ProviderCostPressure.HIGH,
            quota_state=ProviderQuotaState.LIMITED,
            remaining_credit_label="credit: limited",
            credit_status=ProviderCreditStatus.LIMITED,
            estimated_spend_label="$0.03 estimated",
            notes="DeepSeek metadata candidate-only",
            evidence_refs=("adapter:deepseek", "candidate:metadata-only"),
        )
        assert snap.trust_state is ProviderTrustState.CANDIDATE
        assert snap.health is ProviderHealth.DEGRADED
        assert snap.cost_pressure is ProviderCostPressure.HIGH
        assert snap.quota_state is ProviderQuotaState.LIMITED
        assert snap.evidence_refs == (
            "adapter:deepseek", "candidate:metadata-only",
        )


# ---------------------------------------------------------------------------
# ProviderBalanceSummary
# ---------------------------------------------------------------------------

class TestProviderBalanceSummary:
    def test_construction_with_defaults(self):
        summary = ProviderBalanceSummary()
        assert summary.snapshots == ()
        assert summary.selected_provider == ""
        assert summary.routing_owner is ProviderRoutingOwner.UNKNOWN
        assert summary.policy_state is ProviderPolicyState.OK
        assert summary.evidence_refs == ()

    def test_rejects_duplicate_provider_id(self):
        snap_a = unknown_provider_snapshot("claude")
        snap_b = unknown_provider_snapshot("claude")
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSummary(snapshots=(snap_a, snap_b))

    def test_rejects_selected_provider_not_in_snapshots(self):
        snap = unknown_provider_snapshot("claude")
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSummary(
                snapshots=(snap,), selected_provider="openai",
            )

    def test_accepts_selected_provider_in_snapshots(self):
        snap = unknown_provider_snapshot("claude")
        summary = ProviderBalanceSummary(
            snapshots=(snap,), selected_provider="claude",
        )
        assert summary.selected_provider == "claude"

    def test_rejects_unsafe_selected_provider(self):
        snap = unknown_provider_snapshot("claude")
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSummary(
                snapshots=(snap,), selected_provider="api_key/claude",
            )

    def test_rejects_unsafe_evidence_ref(self):
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSummary(evidence_refs=("model_payload:bad",))

    def test_rejects_non_enum_routing_owner(self):
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSummary(routing_owner="Relay")  # type: ignore[arg-type]

    def test_rejects_non_enum_policy_state(self):
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSummary(policy_state="ok")  # type: ignore[arg-type]

    def test_rejects_non_snapshot_entries(self):
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSummary(snapshots=("not-a-snapshot",))  # type: ignore[arg-type]

    def test_rejects_non_tuple_snapshots(self):
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSummary(snapshots=[unknown_provider_snapshot("claude")])  # type: ignore[arg-type]

    def test_frozen_instance(self):
        summary = ProviderBalanceSummary()
        with pytest.raises(dataclasses.FrozenInstanceError):
            summary.routing_owner = ProviderRoutingOwner.RELAY  # type: ignore[misc]

    def test_ordered_snapshots_puts_selected_first(self):
        snaps = (
            unknown_provider_snapshot("openrouter"),
            unknown_provider_snapshot("claude"),
            unknown_provider_snapshot("deepseek"),
            unknown_provider_snapshot("openai"),
        )
        summary = ProviderBalanceSummary(
            snapshots=snaps, selected_provider="deepseek",
        )
        ordered = summary.ordered_snapshots()
        assert ordered[0].provider_id == "deepseek"
        assert [s.provider_id for s in ordered[1:]] == [
            "claude", "openai", "openrouter",
        ]

    def test_ordered_snapshots_without_selected_sorts_alphabetically(self):
        snaps = (
            unknown_provider_snapshot("openrouter"),
            unknown_provider_snapshot("claude"),
            unknown_provider_snapshot("deepseek"),
        )
        summary = ProviderBalanceSummary(snapshots=snaps)
        ordered = summary.ordered_snapshots()
        assert [s.provider_id for s in ordered] == [
            "claude", "deepseek", "openrouter",
        ]

    def test_ordered_snapshots_empty(self):
        summary = ProviderBalanceSummary()
        assert summary.ordered_snapshots() == ()

    def test_to_mapping_keys(self):
        summary = ProviderBalanceSummary()
        mapping = summary.to_mapping()
        assert set(mapping.keys()) == {
            "providers", "selected_provider", "routing_owner",
            "policy_state", "evidence_refs",
        }

    def test_to_mapping_serializes_owner_and_policy(self):
        summary = ProviderBalanceSummary(
            routing_owner=ProviderRoutingOwner.RELAY,
            policy_state=ProviderPolicyState.WARNING,
        )
        mapping = summary.to_mapping()
        assert mapping["routing_owner"] == "Relay"
        assert mapping["policy_state"] == "warning"

    def test_to_mapping_orders_providers_with_selected_first(self):
        snaps = (
            unknown_provider_snapshot("openrouter"),
            unknown_provider_snapshot("claude"),
        )
        summary = ProviderBalanceSummary(
            snapshots=snaps, selected_provider="openrouter",
        )
        mapping = summary.to_mapping()
        providers = mapping["providers"]
        assert providers[0]["provider_id"] == "openrouter"
        assert providers[1]["provider_id"] == "claude"


# ---------------------------------------------------------------------------
# build_provider_balance_summary
# ---------------------------------------------------------------------------

class TestBuildProviderBalanceSummary:
    def test_normalizes_evidence_refs(self):
        summary = build_provider_balance_summary(
            evidence_refs=(
                "snapshot:provider-balance",
                "model_payload:secret",
                "kind:id with space",
            ),
        )
        assert "snapshot:provider-balance" in summary.evidence_refs
        # Two unsafe refs both become the redaction sentinel.
        assert summary.evidence_refs.count(_UNSAFE_EVIDENCE_REDACTION) == 2

    def test_drops_empty_evidence_refs(self):
        summary = build_provider_balance_summary(
            evidence_refs=("snapshot:a", "", None),
        )
        assert summary.evidence_refs == ("snapshot:a",)

    def test_passes_through_snapshots(self):
        snaps = [
            build_provider_balance_snapshot("claude", display_name="Claude"),
            build_provider_balance_snapshot("openai", display_name="OpenAI"),
        ]
        summary = build_provider_balance_summary(
            snaps,
            selected_provider="claude",
            routing_owner=ProviderRoutingOwner.RELAY,
            policy_state=ProviderPolicyState.OK,
        )
        assert len(summary.snapshots) == 2
        assert summary.selected_provider == "claude"
        assert summary.routing_owner is ProviderRoutingOwner.RELAY


# ---------------------------------------------------------------------------
# Bifrost mapping compatibility (without importing Bifrost)
# ---------------------------------------------------------------------------

class TestBifrostMappingCompatibility:
    """The summary mapping must match the key contract of
    ``bifrost.cockpit.provider_balance_view_from_summary`` exactly."""

    EXPECTED_SUMMARY_KEYS = {
        "providers", "selected_provider", "routing_owner",
        "policy_state", "evidence_refs",
    }
    EXPECTED_PROVIDER_KEYS = {
        "provider_id", "display_name", "model_name", "trust_state", "health",
        "route_kind", "context_budget_tokens", "prompt_budget_tokens",
        "current_prompt_tokens", "prompt_budget_percent", "prompt_delta_tokens",
        "cost_pressure", "quota_state", "remaining_credit_label",
        "credit_status", "estimated_spend_label", "notes", "evidence_refs",
    }

    def test_summary_mapping_keys_match_bifrost_contract(self):
        snap = build_provider_balance_snapshot(
            "claude",
            display_name="Claude",
            model_name="claude-sonnet-4-20250514",
            trust_state=ProviderTrustState.TRUSTED,
            health=ProviderHealth.OK,
            route_kind=ProviderRouteKind.DIRECT,
            context_budget_tokens=200_000,
            prompt_budget_tokens=4_000,
            current_prompt_tokens=920,
            prompt_budget_percent=23.0,
            cost_pressure=ProviderCostPressure.LOW,
            quota_state=ProviderQuotaState.AVAILABLE,
            credit_status=ProviderCreditStatus.AVAILABLE,
            remaining_credit_label="credit: available",
            estimated_spend_label="$0.18 estimated",
            notes="Primary provider ready",
            evidence_refs=("adapter:claude",),
        )
        summary = ProviderBalanceSummary(
            snapshots=(snap,),
            selected_provider="claude",
            routing_owner=ProviderRoutingOwner.RELAY,
            policy_state=ProviderPolicyState.OK,
            evidence_refs=("snapshot:provider-balance",),
        )
        mapping = summary.to_mapping()
        assert set(mapping.keys()) == self.EXPECTED_SUMMARY_KEYS
        assert set(mapping["providers"][0].keys()) == self.EXPECTED_PROVIDER_KEYS

    def test_summary_mapping_provider_id_is_routable_string(self):
        snap = build_provider_balance_snapshot("claude")
        summary = ProviderBalanceSummary(snapshots=(snap,))
        provider_mapping = summary.to_mapping()["providers"][0]
        assert provider_mapping["provider_id"] == "claude"
        assert isinstance(provider_mapping["provider_id"], str)

    def test_summary_mapping_evidence_refs_is_list_of_strings(self):
        snap = build_provider_balance_snapshot(
            "claude", evidence_refs=("adapter:claude",),
        )
        summary = build_provider_balance_summary(
            snapshots=(snap,),
            evidence_refs=("snapshot:provider-balance",),
        )
        mapping = summary.to_mapping()
        assert isinstance(mapping["evidence_refs"], list)
        assert all(isinstance(r, str) for r in mapping["evidence_refs"])
        provider_evidence = mapping["providers"][0]["evidence_refs"]
        assert isinstance(provider_evidence, list)
        assert all(isinstance(r, str) for r in provider_evidence)

    def test_provider_neutral_across_claude_openai_deepseek_openrouter_local(self):
        snaps = (
            build_provider_balance_snapshot(
                "claude", display_name="Claude",
                trust_state=ProviderTrustState.TRUSTED,
                route_kind=ProviderRouteKind.DIRECT,
            ),
            build_provider_balance_snapshot(
                "openai", display_name="OpenAI",
                trust_state=ProviderTrustState.TRUSTED,
                route_kind=ProviderRouteKind.DIRECT,
            ),
            build_provider_balance_snapshot(
                "deepseek", display_name="DeepSeek",
                trust_state=ProviderTrustState.CANDIDATE,
                route_kind=ProviderRouteKind.DIRECT,
            ),
            build_provider_balance_snapshot(
                "openrouter", display_name="OpenRouter",
                trust_state=ProviderTrustState.AGGREGATOR,
                route_kind=ProviderRouteKind.AGGREGATOR,
            ),
            build_provider_balance_snapshot(
                "local-llama", display_name="Local Llama",
                trust_state=ProviderTrustState.LOCAL,
                route_kind=ProviderRouteKind.LOCAL,
            ),
        )
        summary = ProviderBalanceSummary(snapshots=snaps)
        mapping = summary.to_mapping()
        seen_ids = {p["provider_id"] for p in mapping["providers"]}
        seen_route_kinds = {p["route_kind"] for p in mapping["providers"]}
        seen_trust_states = {p["trust_state"] for p in mapping["providers"]}
        assert seen_ids == {
            "claude", "openai", "deepseek", "openrouter", "local-llama",
        }
        assert seen_route_kinds == {"direct", "aggregator", "local"}
        assert seen_trust_states == {
            "trusted", "candidate", "aggregator", "local",
        }


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def _make_summary(self) -> ProviderBalanceSummary:
        snaps = (
            build_provider_balance_snapshot(
                "claude", display_name="Claude",
                health=ProviderHealth.OK,
            ),
            build_provider_balance_snapshot(
                "openai", display_name="OpenAI",
                health=ProviderHealth.OK,
            ),
        )
        return ProviderBalanceSummary(
            snapshots=snaps,
            selected_provider="claude",
            routing_owner=ProviderRoutingOwner.RELAY,
            policy_state=ProviderPolicyState.OK,
            evidence_refs=("snapshot:a",),
        )

    def test_same_inputs_yield_equal_summaries(self):
        assert self._make_summary() == self._make_summary()

    def test_same_inputs_yield_equal_mappings(self):
        assert self._make_summary().to_mapping() == self._make_summary().to_mapping()

    def test_to_mapping_is_stable_across_calls(self):
        summary = self._make_summary()
        first = summary.to_mapping()
        second = summary.to_mapping()
        assert first == second

    def test_ordered_snapshots_is_stable(self):
        summary = self._make_summary()
        a = summary.ordered_snapshots()
        b = summary.ordered_snapshots()
        assert a == b


# ---------------------------------------------------------------------------
# End-to-end display safety
# ---------------------------------------------------------------------------

class TestDisplaySafetyEndToEnd:
    def test_summary_repr_contains_no_credentials_or_raw_prompt_text(self):
        snap = build_provider_balance_snapshot(
            "claude",
            display_name="Claude",
            notes="bearer foo provider_response leaked",
            estimated_spend_label="api_key: $5",
            remaining_credit_label="credential: $5",
            evidence_refs=(
                "adapter:claude",
                "model_payload:secret",
                "/etc/passwd",
                "git checkout main",
            ),
        )
        summary = ProviderBalanceSummary(snapshots=(snap,))
        mapping = summary.to_mapping()
        as_text = repr(mapping)
        for forbidden in (
            "bearer foo",
            "model_payload:secret",
            "api_key:",
            "credential:",
            "provider_response",
            "raw_prompt",
            "/etc/passwd",
            "git checkout",
        ):
            assert forbidden not in as_text

    def test_summary_with_branch_or_worktree_prose_is_redacted(self):
        snap = build_provider_balance_snapshot(
            "claude",
            notes="worktree drift detected during git rebase",
        )
        assert snap.notes == _UNSAFE_DISPLAY_REDACTION

    def test_unknown_provider_summary_mapping_reports_unknown_only(self):
        summary = ProviderBalanceSummary(
            snapshots=(
                unknown_provider_snapshot("claude"),
                unknown_provider_snapshot("openai"),
                unknown_provider_snapshot("deepseek"),
            ),
        )
        mapping = summary.to_mapping()
        for provider in mapping["providers"]:
            assert provider["health"] == "unknown"
            assert provider["quota_state"] == "unknown"
            assert provider["credit_status"] == "unknown"
            assert provider["cost_pressure"] == "unknown"
            assert provider["trust_state"] == "unknown"
            assert provider["route_kind"] == "unknown"
            assert provider["context_budget_tokens"] == 0
            assert provider["prompt_budget_tokens"] == 0
            assert provider["prompt_budget_percent"] == 0.0


# ---------------------------------------------------------------------------
# Review B P2 repair — filesystem-path rejection in labels/notes
# ---------------------------------------------------------------------------

class TestFilesystemPathRejectionInLabels:
    """Review B P2 finding: ``_is_safe_display_value`` only blocked newlines
    and unsafe marker substrings, so ``safe_display_label`` /
    ``safe_display_notes`` and ``build_provider_balance_snapshot`` preserved
    raw filesystem paths in ``display_name``, ``model_name``, ``notes``,
    ``remaining_credit_label``, and ``estimated_spend_label``. This class
    proves the repair: path-shaped inputs are now redacted in builders and
    rejected in direct construction across every string surface.
    """

    # ----- safe_display_label ------------------------------------------------

    def test_safe_display_label_redacts_windows_drive_backslash_path(self):
        assert safe_display_label(r"C:\Users\scott\file.txt") == (
            _UNSAFE_DISPLAY_REDACTION
        )

    def test_safe_display_label_redacts_windows_drive_forward_slash_path(self):
        assert safe_display_label("C:/Users/scott/file.txt") == (
            _UNSAFE_DISPLAY_REDACTION
        )

    def test_safe_display_label_redacts_lowercase_drive_letter_path(self):
        assert safe_display_label(r"d:\projects\meridian") == (
            _UNSAFE_DISPLAY_REDACTION
        )

    def test_safe_display_label_redacts_posix_absolute_path(self):
        assert safe_display_label("/tmp/file.txt") == _UNSAFE_DISPLAY_REDACTION
        assert safe_display_label("/etc/passwd") == _UNSAFE_DISPLAY_REDACTION
        assert safe_display_label("/home/scott/project") == (
            _UNSAFE_DISPLAY_REDACTION
        )

    def test_safe_display_label_redacts_embedded_path_prefix(self):
        assert safe_display_label("cached at /tmp/cache") == (
            _UNSAFE_DISPLAY_REDACTION
        )
        assert safe_display_label("loaded from /Users/scott") == (
            _UNSAFE_DISPLAY_REDACTION
        )
        assert safe_display_label("see /var/log/app.log for details") == (
            _UNSAFE_DISPLAY_REDACTION
        )

    def test_safe_display_label_redacts_unc_path(self):
        # UNC paths contain backslashes which are always rejected.
        assert safe_display_label(r"\\server\share") == _UNSAFE_DISPLAY_REDACTION

    def test_safe_display_label_redacts_any_backslash(self):
        # Backslashes never appear in legitimate display strings.
        assert safe_display_label(r"path\with\backslash") == (
            _UNSAFE_DISPLAY_REDACTION
        )

    def test_safe_display_label_redacts_case_variant_unix_path(self):
        # Case-insensitive prefix match catches lowercase Users on case-
        # insensitive filesystems too.
        assert safe_display_label("loaded from /users/scott/file") == (
            _UNSAFE_DISPLAY_REDACTION
        )

    def test_safe_display_label_preserves_slash_in_non_path_context(self):
        # Bare slash in a non-path display context (e.g. a rate label) is
        # not a filesystem leak — the repair must not regress legitimate
        # labels.
        assert safe_display_label("$5/day") == "$5/day"
        assert safe_display_label("3/4 capacity") == "3/4 capacity"

    def test_safe_display_label_preserves_known_safe_fixtures(self):
        # The Bifrost-compatible fixtures from the original slice must keep
        # passing untouched.
        assert safe_display_label("credit: available") == "credit: available"
        assert safe_display_label("$0.18 estimated") == "$0.18 estimated"
        assert safe_display_label("credit: provider-hidden") == (
            "credit: provider-hidden"
        )

    # ----- safe_display_notes ------------------------------------------------

    def test_safe_display_notes_redacts_windows_drive_backslash_path(self):
        assert safe_display_notes(r"C:\Users\scott\file.txt") == (
            _UNSAFE_DISPLAY_REDACTION
        )

    def test_safe_display_notes_redacts_posix_absolute_path(self):
        assert safe_display_notes("/tmp/file.txt") == _UNSAFE_DISPLAY_REDACTION
        assert safe_display_notes("/etc/credit-config") == (
            _UNSAFE_DISPLAY_REDACTION
        )

    def test_safe_display_notes_redacts_embedded_path_prefix(self):
        assert safe_display_notes(
            "rotation error in /var/log/app.log"
        ) == _UNSAFE_DISPLAY_REDACTION
        assert safe_display_notes("data at /home/scott/snapshot") == (
            _UNSAFE_DISPLAY_REDACTION
        )

    def test_safe_display_notes_redacts_backslash_content(self):
        assert safe_display_notes(r"failure at path\segment") == (
            _UNSAFE_DISPLAY_REDACTION
        )

    def test_safe_display_notes_preserves_legitimate_text(self):
        assert safe_display_notes("Primary provider ready") == (
            "Primary provider ready"
        )
        assert safe_display_notes("DeepSeek metadata candidate-only") == (
            "DeepSeek metadata candidate-only"
        )

    # ----- build_provider_balance_snapshot redaction -------------------------

    def test_build_snapshot_redacts_path_display_name(self):
        snap = build_provider_balance_snapshot(
            "claude", display_name=r"C:\Users\scott\file.txt",
        )
        assert snap.display_name == _UNSAFE_DISPLAY_REDACTION

    def test_build_snapshot_redacts_path_model_name(self):
        snap = build_provider_balance_snapshot(
            "claude", model_name="/home/scott/llama-13b",
        )
        assert snap.model_name == _UNSAFE_DISPLAY_REDACTION

    def test_build_snapshot_redacts_path_notes(self):
        snap = build_provider_balance_snapshot(
            "claude", notes="/tmp/file.txt",
        )
        assert snap.notes == _UNSAFE_DISPLAY_REDACTION

    def test_build_snapshot_redacts_path_estimated_spend_label(self):
        snap = build_provider_balance_snapshot(
            "claude", estimated_spend_label=r"C:\spend.log",
        )
        assert snap.estimated_spend_label == _UNSAFE_DISPLAY_REDACTION

    def test_build_snapshot_redacts_path_remaining_credit_label(self):
        snap = build_provider_balance_snapshot(
            "claude", remaining_credit_label="/etc/credits",
        )
        assert snap.remaining_credit_label == _UNSAFE_DISPLAY_REDACTION

    def test_build_snapshot_redacts_review_b_finding_combo(self):
        # The exact reproducer from the Review B finding:
        # ``build_provider_balance_snapshot("claude",
        # display_name=r"C:\Users\scott\file.txt", notes="/tmp/file.txt")``
        # used to preserve both inputs verbatim. Now both redact.
        snap = build_provider_balance_snapshot(
            "claude",
            display_name=r"C:\Users\scott\file.txt",
            notes="/tmp/file.txt",
        )
        assert snap.display_name == _UNSAFE_DISPLAY_REDACTION
        assert snap.notes == _UNSAFE_DISPLAY_REDACTION

    # ----- ProviderBalanceSnapshot direct construction -----------------------

    def test_direct_construction_with_path_display_name_raises(self):
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSnapshot(
                provider_id="claude",
                display_name=r"C:\Users\scott\file.txt",
            )

    def test_direct_construction_with_path_model_name_raises(self):
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSnapshot(
                provider_id="claude",
                model_name="/home/scott/llama-13b",
            )

    def test_direct_construction_with_path_notes_raises(self):
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSnapshot(
                provider_id="claude",
                notes="/tmp/file.txt",
            )

    def test_direct_construction_with_path_estimated_spend_label_raises(self):
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSnapshot(
                provider_id="claude",
                estimated_spend_label=r"C:\spend.log",
            )

    def test_direct_construction_with_path_remaining_credit_label_raises(self):
        with pytest.raises(ProviderBalanceValidationError):
            ProviderBalanceSnapshot(
                provider_id="claude",
                remaining_credit_label="/etc/credits",
            )

    # ----- end-to-end mapping inspection -------------------------------------

    def test_summary_mapping_repr_contains_no_filesystem_paths(self):
        snap = build_provider_balance_snapshot(
            "claude",
            display_name=r"C:\Users\scott\file.txt",
            model_name="/home/scott/llama-13b",
            notes="/tmp/file.txt",
            remaining_credit_label="/etc/credit",
            estimated_spend_label=r"\\server\spend",
        )
        summary = ProviderBalanceSummary(snapshots=(snap,))
        as_text = repr(summary.to_mapping())
        for forbidden in (
            r"C:\Users",
            "/Users/scott",
            "/tmp/",
            "/etc/",
            "/home/",
            r"\\server",
            r"\spend",
        ):
            assert forbidden not in as_text, (
                f"filesystem path content {forbidden!r} leaked into mapping repr"
            )


# ---------------------------------------------------------------------------
# Review B P2 — verbatim reproduction lock-ins
# ---------------------------------------------------------------------------

class TestReviewBP2VerbatimReproduction:
    """Verbatim reproductions of the Review B P2 finding examples.

    The finding cited three specific call shapes that previously preserved
    raw filesystem paths. These tests lock in that those exact call shapes
    now redact through the label/notes safety path. Treat any failure of
    these tests as a regression of the Review B repair.
    """

    def test_repro_safe_display_label_windows_drive_path(self):
        # Verbatim: safe_display_label(r"C:\Users\scott\file.txt")
        assert safe_display_label(r"C:\Users\scott\file.txt") == (
            _UNSAFE_DISPLAY_REDACTION
        )

    def test_repro_safe_display_notes_posix_absolute_path(self):
        # Verbatim: safe_display_notes("/tmp/file.txt")
        assert safe_display_notes("/tmp/file.txt") == _UNSAFE_DISPLAY_REDACTION

    def test_repro_build_provider_balance_snapshot_path_combo(self):
        # Verbatim: build_provider_balance_snapshot(
        #     "claude",
        #     display_name=r"C:\Users\scott\file.txt",
        #     notes="/tmp/file.txt",
        # )
        snap = build_provider_balance_snapshot(
            "claude",
            display_name=r"C:\Users\scott\file.txt",
            notes="/tmp/file.txt",
        )
        assert snap.display_name == _UNSAFE_DISPLAY_REDACTION
        assert snap.notes == _UNSAFE_DISPLAY_REDACTION

    def test_repro_combo_propagates_through_summary_mapping(self):
        # The redacted snapshot must remain redacted after summary
        # projection — no mapping field carries the raw paths through.
        snap = build_provider_balance_snapshot(
            "claude",
            display_name=r"C:\Users\scott\file.txt",
            notes="/tmp/file.txt",
        )
        summary = ProviderBalanceSummary(snapshots=(snap,))
        mapping = summary.to_mapping()
        provider = mapping["providers"][0]
        assert provider["display_name"] == _UNSAFE_DISPLAY_REDACTION
        assert provider["notes"] == _UNSAFE_DISPLAY_REDACTION
        as_text = repr(mapping)
        assert r"C:\Users\scott" not in as_text
        assert "/tmp/file.txt" not in as_text


# ---------------------------------------------------------------------------
# Review B P2 — Windows + POSIX coverage on every snapshot string field
# ---------------------------------------------------------------------------

class TestSnapshotBuilderRedactsBothPathShapesPerField:
    """For every string field on the snapshot that previously accepted
    raw paths, prove BOTH a Windows drive path and a POSIX absolute path
    redact through the builder. Five fields × two shapes = ten checks.
    """

    WINDOWS_PATH = r"C:\Users\scott\file.txt"
    POSIX_PATH = "/tmp/file.txt"

    def test_display_name_windows_path_redacts(self):
        snap = build_provider_balance_snapshot(
            "claude", display_name=self.WINDOWS_PATH,
        )
        assert snap.display_name == _UNSAFE_DISPLAY_REDACTION

    def test_display_name_posix_path_redacts(self):
        snap = build_provider_balance_snapshot(
            "claude", display_name=self.POSIX_PATH,
        )
        assert snap.display_name == _UNSAFE_DISPLAY_REDACTION

    def test_model_name_windows_path_redacts(self):
        snap = build_provider_balance_snapshot(
            "claude", model_name=self.WINDOWS_PATH,
        )
        assert snap.model_name == _UNSAFE_DISPLAY_REDACTION

    def test_model_name_posix_path_redacts(self):
        snap = build_provider_balance_snapshot(
            "claude", model_name=self.POSIX_PATH,
        )
        assert snap.model_name == _UNSAFE_DISPLAY_REDACTION

    def test_remaining_credit_label_windows_path_redacts(self):
        snap = build_provider_balance_snapshot(
            "claude", remaining_credit_label=self.WINDOWS_PATH,
        )
        assert snap.remaining_credit_label == _UNSAFE_DISPLAY_REDACTION

    def test_remaining_credit_label_posix_path_redacts(self):
        snap = build_provider_balance_snapshot(
            "claude", remaining_credit_label=self.POSIX_PATH,
        )
        assert snap.remaining_credit_label == _UNSAFE_DISPLAY_REDACTION

    def test_estimated_spend_label_windows_path_redacts(self):
        snap = build_provider_balance_snapshot(
            "claude", estimated_spend_label=self.WINDOWS_PATH,
        )
        assert snap.estimated_spend_label == _UNSAFE_DISPLAY_REDACTION

    def test_estimated_spend_label_posix_path_redacts(self):
        snap = build_provider_balance_snapshot(
            "claude", estimated_spend_label=self.POSIX_PATH,
        )
        assert snap.estimated_spend_label == _UNSAFE_DISPLAY_REDACTION

    def test_notes_windows_path_redacts(self):
        snap = build_provider_balance_snapshot(
            "claude", notes=self.WINDOWS_PATH,
        )
        assert snap.notes == _UNSAFE_DISPLAY_REDACTION

    def test_notes_posix_path_redacts(self):
        snap = build_provider_balance_snapshot(
            "claude", notes=self.POSIX_PATH,
        )
        assert snap.notes == _UNSAFE_DISPLAY_REDACTION


# ---------------------------------------------------------------------------
# Review B P2 — Windows + POSIX coverage on safe_display_label / notes
# ---------------------------------------------------------------------------

class TestSafetyHelpersRedactBothPathShapes:
    """Both safety helpers reject both path shapes. Mirrors the
    builder field-coverage class above so the helpers are individually
    locked in regardless of where they are called.
    """

    WINDOWS_PATH = r"C:\Users\scott\file.txt"
    POSIX_PATH = "/tmp/file.txt"

    def test_safe_display_label_windows_path_redacts(self):
        assert safe_display_label(self.WINDOWS_PATH) == _UNSAFE_DISPLAY_REDACTION

    def test_safe_display_label_posix_path_redacts(self):
        assert safe_display_label(self.POSIX_PATH) == _UNSAFE_DISPLAY_REDACTION

    def test_safe_display_notes_windows_path_redacts(self):
        assert safe_display_notes(self.WINDOWS_PATH) == _UNSAFE_DISPLAY_REDACTION

    def test_safe_display_notes_posix_path_redacts(self):
        assert safe_display_notes(self.POSIX_PATH) == _UNSAFE_DISPLAY_REDACTION
