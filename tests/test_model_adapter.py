"""Tests for provider-neutral Model Harness adapters."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from meridian_core.model_adapter import (
    AdapterRegistry,
    DEEPSEEK_DIRECT_ENDPOINT,
    DEEPSEEK_DIRECT_MODEL,
    EnvConfiguredModelAdapter,
    FakeModelAdapter,
    HttpJsonModelAdapter,
    HttpModelAdapterConfig,
    MissingAdapterError,
    ModelCandidateRoutePreset,
    ModelAdapterConfig,
    ModelAdapterConfigError,
    ModelHarnessMetadata,
    ModelRouteMetadataBinding,
    bind_model_route_metadata,
    deepseek_candidate_metadata_preset,
    deepseek_candidate_route_presets,
)
from meridian_core.prompt_payload_meter import PromptPayloadSnapshot
from meridian_core.relay import CostPosture, LatencyPosture
from meridian_core.relay import ModelRole


class TestFakeModelAdapter:
    def test_returns_deterministic_response(self) -> None:
        adapter = FakeModelAdapter("ok")
        assert adapter("payload") == "ok"

    def test_records_only_payload_text(self) -> None:
        adapter = FakeModelAdapter("ok")
        adapter("approved prompt")
        assert adapter.received_payloads == ["approved prompt"]


class TestModelAdapterConfig:
    def test_require_api_key_reads_configured_env_name(self) -> None:
        config = ModelAdapterConfig(
            provider="example",
            model="example-model",
            api_key_env_var="EXAMPLE_API_KEY",
        )
        assert config.require_api_key({"EXAMPLE_API_KEY": "secret"}) == "secret"

    def test_require_api_key_strips_whitespace(self) -> None:
        config = ModelAdapterConfig(
            provider="example",
            model="example-model",
            api_key_env_var="EXAMPLE_API_KEY",
        )
        assert config.require_api_key({"EXAMPLE_API_KEY": "  secret  "}) == "secret"

    def test_missing_api_key_raises_clear_error(self) -> None:
        config = ModelAdapterConfig(
            provider="example",
            model="example-model",
            api_key_env_var="EXAMPLE_API_KEY",
        )
        with pytest.raises(ModelAdapterConfigError, match="EXAMPLE_API_KEY"):
            config.require_api_key({})


class TestEnvConfiguredModelAdapter:
    def test_missing_config_fails_before_transport_call(self) -> None:
        calls: list[str] = []

        def transport(payload: str, config: ModelAdapterConfig, api_key: str) -> str:
            calls.append(payload)
            return "should not run"

        adapter = EnvConfiguredModelAdapter(
            ModelAdapterConfig("example", "example-model", "EXAMPLE_API_KEY"),
            transport,
            env={},
        )

        with pytest.raises(ModelAdapterConfigError):
            adapter("approved prompt")

        assert calls == []

    def test_transport_receives_payload_when_configured(self) -> None:
        calls: list[str] = []

        def transport(payload: str, config: ModelAdapterConfig, api_key: str) -> str:
            calls.append(payload)
            assert config.provider == "example"
            assert api_key == "secret"
            return "live response"

        adapter = EnvConfiguredModelAdapter(
            ModelAdapterConfig("example", "example-model", "EXAMPLE_API_KEY"),
            transport,
            env={"EXAMPLE_API_KEY": "secret"},
        )

        assert adapter("approved prompt") == "live response"
        assert calls == ["approved prompt"]


class TestAdapterRegistry:
    def test_empty_registry_raises_on_resolve(self) -> None:
        registry = AdapterRegistry()
        with pytest.raises(MissingAdapterError, match="fast-default"):
            registry.resolve(ModelRole.BUILDER, "fast-default")

    def test_exact_model_adapter_selected(self) -> None:
        exact = FakeModelAdapter("exact-response")
        registry = AdapterRegistry().register_model("fast-default", exact)
        resolved = registry.resolve(ModelRole.BUILDER, "fast-default")
        assert resolved is exact

    def test_role_default_used_when_no_exact_model(self) -> None:
        role_adapter = FakeModelAdapter("role-response")
        registry = AdapterRegistry().register_role_default(ModelRole.BUILDER, role_adapter)
        resolved = registry.resolve(ModelRole.BUILDER, "any-model-not-registered")
        assert resolved is role_adapter

    def test_exact_model_takes_priority_over_role_default(self) -> None:
        exact = FakeModelAdapter("exact")
        role_default = FakeModelAdapter("role-default")
        registry = (
            AdapterRegistry()
            .register_model("fast-default", exact)
            .register_role_default(ModelRole.BUILDER, role_default)
        )
        assert registry.resolve(ModelRole.BUILDER, "fast-default") is exact

    def test_missing_adapter_error_names_model_and_role(self) -> None:
        registry = AdapterRegistry()
        with pytest.raises(MissingAdapterError) as exc_info:
            registry.resolve(ModelRole.REVIEWER, "independent-reviewer")
        assert "independent-reviewer" in str(exc_info.value)
        assert "reviewer" in str(exc_info.value)

    def test_registration_returns_new_registry_instance(self) -> None:
        original = AdapterRegistry()
        updated = original.register_model("fast-default", FakeModelAdapter())
        with pytest.raises(MissingAdapterError):
            original.resolve(ModelRole.BUILDER, "fast-default")
        assert updated.resolve(ModelRole.BUILDER, "fast-default") is not None

    def test_role_registration_returns_new_registry_instance(self) -> None:
        original = AdapterRegistry()
        updated = original.register_role_default(ModelRole.BUILDER, FakeModelAdapter())
        with pytest.raises(MissingAdapterError):
            original.resolve(ModelRole.BUILDER, "any-model")
        assert updated.resolve(ModelRole.BUILDER, "any-model") is not None

    def test_multiple_roles_registered_independently(self) -> None:
        builder_adapter = FakeModelAdapter("builder")
        reviewer_adapter = FakeModelAdapter("reviewer")
        registry = (
            AdapterRegistry()
            .register_role_default(ModelRole.BUILDER, builder_adapter)
            .register_role_default(ModelRole.REVIEWER, reviewer_adapter)
        )
        assert registry.resolve(ModelRole.BUILDER, "x") is builder_adapter
        assert registry.resolve(ModelRole.REVIEWER, "x") is reviewer_adapter

    def test_multiple_model_keys_registered_independently(self) -> None:
        fast = FakeModelAdapter("fast")
        primary = FakeModelAdapter("primary")
        registry = (
            AdapterRegistry()
            .register_model("fast-default", fast)
            .register_model("primary-default", primary)
        )
        assert registry.resolve(ModelRole.BUILDER, "fast-default") is fast
        assert registry.resolve(ModelRole.BUILDER, "primary-default") is primary

    def test_resolve_wrong_model_no_role_default_raises(self) -> None:
        registry = AdapterRegistry().register_model("fast-default", FakeModelAdapter())
        with pytest.raises(MissingAdapterError, match="primary-default"):
            registry.resolve(ModelRole.BUILDER, "primary-default")


class TestDeepSeekCandidatePresets:
    def test_presets_include_default_quality_and_fast_lanes(self) -> None:
        presets = deepseek_candidate_route_presets()
        assert tuple(p.lane for p in presets) == ("default_quality", "fast")
        assert tuple(p.variant_label for p in presets) == (
            "deepseek-v4-pro",
            "deepseek-v4-flash",
        )

    def test_presets_use_deepseek_chat_as_only_dispatch_identity(self) -> None:
        for preset in deepseek_candidate_route_presets():
            assert preset.provider_name == "deepseek"
            assert preset.dispatch_model == DEEPSEEK_DIRECT_MODEL
            assert preset.dispatch_model == "deepseek-chat"
            assert preset.variant_label != preset.dispatch_model

    def test_default_quality_metadata_keeps_variant_out_of_dispatch_model(self) -> None:
        metadata = deepseek_candidate_metadata_preset()
        assert metadata.provider_name == "deepseek"
        assert metadata.model_name == "deepseek-chat"
        assert metadata.deepseek_candidate_state is not None
        assert metadata.deepseek_candidate_state["variant_label"] == "deepseek-v4-pro"
        assert metadata.deepseek_candidate_state["lane"] == "default_quality"

    def test_fast_metadata_keeps_variant_out_of_dispatch_model(self) -> None:
        metadata = deepseek_candidate_metadata_preset("fast")
        assert metadata.provider_name == "deepseek"
        assert metadata.model_name == "deepseek-chat"
        assert metadata.deepseek_candidate_state is not None
        assert metadata.deepseek_candidate_state["variant_label"] == "deepseek-v4-flash"
        assert metadata.deepseek_candidate_state["lane"] == "fast"

    def test_presets_remain_candidate_direct_provider_routes(self) -> None:
        for preset in deepseek_candidate_route_presets():
            assert preset.api_mode == "direct"
            assert preset.trust_state == "candidate"
            assert preset.requires_external_review is True
            assert preset.external_review_status == "pending"
            assert preset.direct_api_endpoint == DEEPSEEK_DIRECT_ENDPOINT
            assert preset.known_authorities == (
                "deepseek-official-endpoint",
                "direct-api-only",
            )

    def test_presets_preserve_validation_gate_blocks(self) -> None:
        for preset in deepseek_candidate_route_presets():
            assert preset.allowed_task_types == ("verify", "explain")
            assert "build" in preset.blocked_task_types
            assert "review" in preset.blocked_task_types
            assert "branch_movement" in preset.blocked_task_types
            assert "review_clearance" in preset.blocked_task_types
            assert "autonomous_coding" in preset.blocked_task_types
            assert preset.max_risk_tier == 1
            assert preset.can_clear_reviews is False
            assert preset.can_move_branches is False
            assert preset.bypasses_relay_aegis is False
            assert preset.autonomous_coding_allowed is False

    def test_metadata_candidate_state_is_read_only(self) -> None:
        metadata = deepseek_candidate_metadata_preset()
        assert metadata.deepseek_candidate_state is not None
        with pytest.raises(TypeError):
            metadata.deepseek_candidate_state["trust_state"] = "trusted"  # type: ignore[index]

    def test_preset_is_frozen(self) -> None:
        preset = deepseek_candidate_route_presets()[0]
        with pytest.raises(FrozenInstanceError):
            preset.variant_label = "deepseek-chat"  # type: ignore[misc]

    def test_rejects_deepseek_marketing_label_as_dispatch_model(self) -> None:
        template = deepseek_candidate_route_presets()[0]
        with pytest.raises(ModelAdapterConfigError, match="deepseek-chat"):
            ModelCandidateRoutePreset(
                provider_name=template.provider_name,
                dispatch_model="deepseek-v4-pro",
                variant_label=template.variant_label,
                lane=template.lane,
                api_mode=template.api_mode,
                trust_state=template.trust_state,
                requires_external_review=template.requires_external_review,
                external_review_status=template.external_review_status,
                direct_api_endpoint=template.direct_api_endpoint,
                capability_tier=template.capability_tier,
                context_budget=template.context_budget,
                prompt_payload_budget=template.prompt_payload_budget,
                allowed_task_types=template.allowed_task_types,
                blocked_task_types=template.blocked_task_types,
                max_risk_tier=template.max_risk_tier,
                q_mode_flat=template.q_mode_flat,
                can_clear_reviews=template.can_clear_reviews,
                can_move_branches=template.can_move_branches,
                bypasses_relay_aegis=template.bypasses_relay_aegis,
                autonomous_coding_allowed=template.autonomous_coding_allowed,
                known_authorities=template.known_authorities,
            )

    def test_unknown_preset_lane_raises(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="Unknown DeepSeek candidate lane"):
            deepseek_candidate_metadata_preset("review_clearance")


class TestModelRouteMetadataBinding:
    def test_bind_model_route_metadata_carries_capability_tier_and_route_tier(self) -> None:
        metadata = ModelHarnessMetadata(
            provider_name="provider",
            model_name="exact-model",
            capability_tier="standard",
            context_budget=8192,
            prompt_payload_budget=4096,
            trust_state="trusted",
            requires_external_review=False,
        )
        binding = bind_model_route_metadata(
            metadata,
            route_risk_tier=2,
            route_cost_posture=CostPosture.STANDARD,
            route_latency_posture=LatencyPosture.FAST,
        )
        assert binding.provider_name == "provider"
        assert binding.model_name == "exact-model"
        assert binding.capability_tier == "standard"
        assert binding.route_risk_tier == 2
        assert binding.route_cost_posture == "standard"
        assert binding.route_latency_posture == "fast"

    def test_bind_model_route_metadata_carries_budget_and_prompt_drag(self) -> None:
        metadata = ModelHarnessMetadata(
            provider_name="provider",
            model_name="exact-model",
            capability_tier="standard",
            context_budget=8192,
            prompt_payload_budget=4096,
            trust_state="trusted",
            requires_external_review=False,
        )
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=1600,
            budget_tokens=2000,
            prior_estimated_tokens=1500,
            queue_mode=True,
        )
        binding = bind_model_route_metadata(
            metadata,
            route_risk_tier=2,
            route_cost_posture=CostPosture.STANDARD,
            route_latency_posture=LatencyPosture.FAST,
            payload_snapshot=snapshot,
        )
        assert binding.context_budget == 8192
        assert binding.prompt_payload_budget == 4096
        assert binding.prompt_payload_status == "watch"
        assert binding.prompt_payload_estimated_tokens == 1600
        assert binding.prompt_payload_budget_percent == 80.0
        assert binding.prompt_payload_growth_tokens == 100

    def test_route_metadata_binding_to_dict_is_stable(self) -> None:
        binding = ModelRouteMetadataBinding(
            provider_name="provider",
            model_name="exact-model",
            capability_tier="standard",
            route_risk_tier=1,
            route_cost_posture="minimal",
            route_latency_posture="fast",
            context_budget=4096,
            prompt_payload_budget=2048,
            trust_state="trusted",
            requires_external_review=False,
        )
        assert binding.to_dict() == binding.to_dict()
        assert tuple(binding.to_dict().keys()) == (
            "provider_name",
            "model_name",
            "capability_tier",
            "route_risk_tier",
            "route_cost_posture",
            "route_latency_posture",
            "context_budget",
            "prompt_payload_budget",
            "trust_state",
            "requires_external_review",
            "prompt_payload_status",
            "prompt_payload_estimated_tokens",
            "prompt_payload_budget_percent",
            "prompt_payload_growth_tokens",
            "prompt_payload_growth_percent",
        )

    def test_route_metadata_binding_rejects_negative_route_tier(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="route_risk_tier"):
            ModelRouteMetadataBinding(
                provider_name="provider",
                model_name="exact-model",
                capability_tier="standard",
                route_risk_tier=-1,
                route_cost_posture="minimal",
                route_latency_posture="fast",
                context_budget=4096,
                prompt_payload_budget=2048,
                trust_state="trusted",
                requires_external_review=False,
            )

    def test_deepseek_candidate_metadata_binds_without_special_case(self) -> None:
        binding = bind_model_route_metadata(
            deepseek_candidate_metadata_preset("fast"),
            route_risk_tier=1,
            route_cost_posture=CostPosture.MINIMAL,
            route_latency_posture=LatencyPosture.FAST,
        )
        assert binding.provider_name == "deepseek"
        assert binding.model_name == "deepseek-chat"
        assert binding.capability_tier == "candidate-fast"
        assert binding.trust_state == "candidate"
        assert binding.requires_external_review is True


class TestHttpJsonModelAdapter:
    _config = HttpModelAdapterConfig(
        provider="example",
        model="example-model",
        api_key_env_var="EXAMPLE_API_KEY",
        endpoint_url="https://api.example.com/v1/chat",
    )

    def test_missing_api_key_fails_before_transport_call(self) -> None:
        calls: list[str] = []

        def fake_post(
            payload: str,
            endpoint: str,
            provider: str,
            model: str,
            api_key: str,
        ) -> str:
            calls.append(payload)
            return "should not run"

        adapter = HttpJsonModelAdapter(self._config, env={}, http_post=fake_post)
        with pytest.raises(ModelAdapterConfigError, match="EXAMPLE_API_KEY"):
            adapter("approved prompt")
        assert calls == []

    def test_missing_endpoint_fails_before_transport_call(self) -> None:
        calls: list[str] = []

        def fake_post(
            payload: str,
            endpoint: str,
            provider: str,
            model: str,
            api_key: str,
        ) -> str:
            calls.append(payload)
            return "should not run"

        config = HttpModelAdapterConfig(
            provider="example",
            model="example-model",
            api_key_env_var="EXAMPLE_API_KEY",
            endpoint_url="   ",
        )
        adapter = HttpJsonModelAdapter(config, env={"EXAMPLE_API_KEY": "secret"}, http_post=fake_post)
        with pytest.raises(ModelAdapterConfigError, match="endpoint_url"):
            adapter("approved prompt")
        assert calls == []

    def test_transport_receives_only_payload_endpoint_provider_model_and_key(self) -> None:
        received: dict[str, str] = {}

        def fake_post(
            payload: str,
            endpoint: str,
            provider: str,
            model: str,
            api_key: str,
        ) -> str:
            received["payload"] = payload
            received["endpoint"] = endpoint
            received["provider"] = provider
            received["model"] = model
            received["api_key"] = api_key
            return "ok"

        adapter = HttpJsonModelAdapter(
            self._config,
            env={"EXAMPLE_API_KEY": "secret"},
            http_post=fake_post,
        )
        adapter("approved payload text")
        assert received["payload"] == "approved payload text"
        assert received["endpoint"] == "https://api.example.com/v1/chat"
        assert received["provider"] == "example"
        assert received["model"] == "example-model"
        assert received["api_key"] == "secret"
        assert set(received) == {"payload", "endpoint", "provider", "model", "api_key"}

    def test_api_key_not_echoed_in_response_or_error(self) -> None:
        def fake_post(
            payload: str,
            endpoint: str,
            provider: str,
            model: str,
            api_key: str,
        ) -> str:
            return "response text without credentials"

        adapter = HttpJsonModelAdapter(
            self._config,
            env={"EXAMPLE_API_KEY": "super-secret-key"},
            http_post=fake_post,
        )
        result = adapter("approved prompt")
        assert "super-secret-key" not in result

    def test_returns_transport_response(self) -> None:
        def fake_post(
            payload: str,
            endpoint: str,
            provider: str,
            model: str,
            api_key: str,
        ) -> str:
            return "model response text"

        adapter = HttpJsonModelAdapter(
            self._config,
            env={"EXAMPLE_API_KEY": "secret"},
            http_post=fake_post,
        )
        assert adapter("approved prompt") == "model response text"
