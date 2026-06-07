"""Tests for provider-neutral Model Harness adapters."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from meridian_core.model_adapter import (
    AdapterRegistry,
    DEEPSEEK_DIRECT_ENDPOINT,
    DEEPSEEK_DIRECT_MODEL,
    DeepSeekTransportAuthority,
    DeepSeekTransportAuthorityStatus,
    DeepSeekValidationDisposition,
    DeepSeekValidationGateProof,
    DeepSeekValidationLevel,
    DeepSeekValidationProofState,
    DeepSeekValidationState,
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
    bind_deepseek_transport_authority,
    bind_deepseek_validation_disposition,
    bind_model_route_metadata,
    deepseek_candidate_metadata_preset,
    deepseek_candidate_route_presets,
    deepseek_validation_state_from_preset,
    evaluate_deepseek_transport_authority,
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
            assert preset.trust_mode == "direct"
            assert preset.trust_state == "candidate"
            assert preset.proof_strength == "weak"
            assert preset.requires_external_review is True
            assert preset.external_review_status == "pending"
            assert preset.direct_api_endpoint == DEEPSEEK_DIRECT_ENDPOINT
            assert preset.direct_endpoint_evidence_ref == (
                "deepseek-direct-endpoint:"
                "https://api.deepseek.com/v1/chat/completions"
            )
            assert preset.external_review_evidence_ref == (
                "external-review:deepseek:deepseek-chat:pending"
            )
            assert preset.validation_evidence_ref == (
                "deepseek-validation:level-0:metadata-only"
            )
            assert preset.known_authorities == (
                "deepseek-official-endpoint",
                "direct-api-only",
            )
            assert preset.direct_provider_authority is True
            assert preset.aggregator_authority is False

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
            assert preset.blocked_authorities == (
                "review_clearance",
                "branch_movement",
                "relay_aegis_bypass",
                "autonomous_coding",
                "aggregator_authority",
            )

    def test_presets_carry_prompt_drag_defaults(self) -> None:
        for preset in deepseek_candidate_route_presets():
            assert preset.context_budget == 65536
            assert preset.prompt_payload_budget == 57344
            assert preset.prompt_drag_default_status == "unknown_until_relay_snapshot"
            assert preset.prompt_drag_warning_tags == (
                "prompt_drag_requires_relay_snapshot",
                "q_mode_growth_requires_task_change",
            )
            assert preset.q_mode_flat is True

    def test_preset_to_dict_is_display_safe_and_stable(self) -> None:
        preset = deepseek_candidate_route_presets()[0]
        first = preset.to_dict()
        second = preset.to_dict()

        assert first == second
        assert tuple(first.keys()) == (
            "provider_name",
            "dispatch_model",
            "variant_label",
            "lane",
            "api_mode",
            "trust_mode",
            "trust_state",
            "proof_strength",
            "requires_external_review",
            "external_review_status",
            "direct_endpoint_evidence_ref",
            "external_review_evidence_ref",
            "validation_evidence_ref",
            "capability_tier",
            "context_budget",
            "prompt_payload_budget",
            "allowed_task_types",
            "blocked_task_types",
            "blocked_authorities",
            "max_risk_tier",
            "q_mode_flat",
            "prompt_drag_default_status",
            "prompt_drag_warning_tags",
            "can_clear_reviews",
            "can_move_branches",
            "bypasses_relay_aegis",
            "autonomous_coding_allowed",
            "direct_provider_authority",
            "aggregator_authority",
            "known_authorities",
        )
        rendered = " ".join(str(value) for value in first.values())
        assert "deepseek-chat" in rendered
        assert "deepseek-v4-pro" in rendered
        assert "credential" not in rendered
        assert "provider response" not in rendered
        assert "Polaris" not in rendered

    def test_metadata_candidate_state_carries_display_safe_proof_fields(self) -> None:
        metadata = deepseek_candidate_metadata_preset("fast")
        state = metadata.deepseek_candidate_state
        assert state is not None
        assert state["trust_mode"] == "direct"
        assert state["proof_strength"] == "weak"
        assert state["direct_endpoint_evidence_ref"] == (
            "deepseek-direct-endpoint:"
            "https://api.deepseek.com/v1/chat/completions"
        )
        assert state["external_review_evidence_ref"] == (
            "external-review:deepseek:deepseek-chat:pending"
        )
        assert state["validation_evidence_ref"] == (
            "deepseek-validation:level-0:metadata-only"
        )
        assert state["blocked_authorities"] == (
            "review_clearance,branch_movement,relay_aegis_bypass,"
            "autonomous_coding,aggregator_authority"
        )
        assert state["prompt_drag_default_status"] == "unknown_until_relay_snapshot"
        assert state["direct_provider_authority"] == "true"
        assert state["aggregator_authority"] == "false"

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

    def test_rejects_deepseek_direct_endpoint_mismatch(self) -> None:
        template = deepseek_candidate_route_presets()[0]
        with pytest.raises(ModelAdapterConfigError, match="reviewed endpoint"):
            ModelCandidateRoutePreset(
                provider_name=template.provider_name,
                dispatch_model=template.dispatch_model,
                variant_label=template.variant_label,
                lane=template.lane,
                api_mode=template.api_mode,
                trust_state=template.trust_state,
                requires_external_review=template.requires_external_review,
                external_review_status=template.external_review_status,
                direct_api_endpoint="https://openrouter.example.invalid/v1/chat",
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

    def test_candidate_presets_do_not_construct_live_transport(self) -> None:
        metadata = deepseek_candidate_metadata_preset()
        assert isinstance(metadata, ModelHarnessMetadata)
        assert not callable(metadata)
        assert metadata.model_name == "deepseek-chat"

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
            "provider_route_kind",
            "external_review_status",
            "model_metadata_ref",
            "external_review_evidence_ref",
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
        assert binding.provider_route_kind == "direct"
        assert binding.external_review_status == "pending"
        assert binding.model_metadata_ref == "model-harness-metadata:deepseek:deepseek-chat"
        assert binding.external_review_evidence_ref == (
            "external-review:deepseek:deepseek-chat:pending"
        )

    def test_deepseek_candidate_metadata_declares_direct_telemetry_support(self) -> None:
        metadata = deepseek_candidate_metadata_preset()
        assert metadata.max_output_tokens == 8192
        assert metadata.tokenizer_family == "deepseek"
        assert metadata.supports_completion_tokens is True
        assert metadata.supports_latency_ms is True
        assert metadata.supports_payload_snapshot is True
        assert metadata.supports_response_hash is True


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


class TestDeepSeekValidationState:
    def test_validation_level_enum_defines_all_gates(self) -> None:
        assert DeepSeekValidationLevel.METADATA_ONLY.value == "level-0:metadata-only"
        assert DeepSeekValidationLevel.VALIDATION_CLEARED.value == "level-1:validation-cleared"
        assert DeepSeekValidationLevel.REVIEW_CLEARANCE.value == "level-2:review-clearance"
        assert DeepSeekValidationLevel.BRANCH_MOVEMENT.value == "level-3:branch-movement"
        assert DeepSeekValidationLevel.AUTONOMOUS_CODING.value == "level-4:autonomous-coding"

    def test_metadata_only_state_blocks_all_operations(self) -> None:
        state = DeepSeekValidationState(
            current_level=DeepSeekValidationLevel.METADATA_ONLY,
            can_receive_prompt_payloads=False,
            can_clear_reviews=False,
            can_move_branches=False,
            can_enable_autonomous_coding=False,
            blocked_operations=(
                "prompt_payload_dispatch",
                "review_clearance",
                "branch_movement",
                "autonomous_coding",
            ),
            validation_ref="deepseek-validation:level-0:metadata-only",
        )
        assert state.current_level == DeepSeekValidationLevel.METADATA_ONLY
        assert not state.can_receive_prompt_payloads
        assert not state.can_clear_reviews
        assert not state.can_move_branches
        assert not state.can_enable_autonomous_coding
        assert len(state.blocked_operations) == 4

    def test_validation_cleared_state_allows_payload_dispatch(self) -> None:
        state = DeepSeekValidationState(
            current_level=DeepSeekValidationLevel.VALIDATION_CLEARED,
            can_receive_prompt_payloads=True,
            can_clear_reviews=False,
            can_move_branches=False,
            can_enable_autonomous_coding=False,
            blocked_operations=(
                "review_clearance",
                "branch_movement",
                "autonomous_coding",
            ),
            validation_ref="deepseek-validation:level-1:validation-cleared",
        )
        assert state.current_level == DeepSeekValidationLevel.VALIDATION_CLEARED
        assert state.can_receive_prompt_payloads
        assert not state.can_clear_reviews
        assert not state.can_move_branches
        assert not state.can_enable_autonomous_coding

    def test_metadata_only_rejects_any_operational_authority(self) -> None:
        with pytest.raises(
            ModelAdapterConfigError, match="metadata-only validation level"
        ):
            DeepSeekValidationState(
                current_level=DeepSeekValidationLevel.METADATA_ONLY,
                can_receive_prompt_payloads=True,
                can_clear_reviews=False,
                can_move_branches=False,
                can_enable_autonomous_coding=False,
                blocked_operations=(),
                validation_ref="deepseek-validation:level-0:metadata-only",
            )

    def test_validation_cleared_requires_prompt_payload_authority(self) -> None:
        with pytest.raises(
            ModelAdapterConfigError, match="validation-cleared level must grant"
        ):
            DeepSeekValidationState(
                current_level=DeepSeekValidationLevel.VALIDATION_CLEARED,
                can_receive_prompt_payloads=False,
                can_clear_reviews=False,
                can_move_branches=False,
                can_enable_autonomous_coding=False,
                blocked_operations=(),
                validation_ref="deepseek-validation:level-1:validation-cleared",
            )

    def test_validation_cleared_blocks_review_branch_autonomous(self) -> None:
        with pytest.raises(
            ModelAdapterConfigError, match="validation-cleared level cannot grant"
        ):
            DeepSeekValidationState(
                current_level=DeepSeekValidationLevel.VALIDATION_CLEARED,
                can_receive_prompt_payloads=True,
                can_clear_reviews=True,
                can_move_branches=False,
                can_enable_autonomous_coding=False,
                blocked_operations=(),
                validation_ref="deepseek-validation:level-1:validation-cleared",
            )

    def test_review_clearance_level_is_reserved_and_unconstructible_when_all_false(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="level-2:review-clearance.*reserved"):
            DeepSeekValidationState(
                current_level=DeepSeekValidationLevel.REVIEW_CLEARANCE,
                can_receive_prompt_payloads=False,
                can_clear_reviews=False,
                can_move_branches=False,
                can_enable_autonomous_coding=False,
                blocked_operations=(),
                validation_ref="deepseek-validation:level-2:review-clearance",
            )

    def test_review_clearance_level_is_reserved_even_with_consistent_authority_bits(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="level-2:review-clearance.*reserved"):
            DeepSeekValidationState(
                current_level=DeepSeekValidationLevel.REVIEW_CLEARANCE,
                can_receive_prompt_payloads=True,
                can_clear_reviews=True,
                can_move_branches=False,
                can_enable_autonomous_coding=False,
                blocked_operations=("branch_movement", "autonomous_coding"),
                validation_ref="deepseek-validation:level-2:review-clearance",
            )

    def test_review_clearance_level_is_reserved_even_with_full_authority_request(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="no autonomy by accident"):
            DeepSeekValidationState(
                current_level=DeepSeekValidationLevel.REVIEW_CLEARANCE,
                can_receive_prompt_payloads=True,
                can_clear_reviews=True,
                can_move_branches=True,
                can_enable_autonomous_coding=True,
                blocked_operations=(),
                validation_ref="deepseek-validation:level-2:review-clearance",
            )

    def test_branch_movement_level_is_reserved_and_unconstructible_when_all_false(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="level-3:branch-movement.*reserved"):
            DeepSeekValidationState(
                current_level=DeepSeekValidationLevel.BRANCH_MOVEMENT,
                can_receive_prompt_payloads=False,
                can_clear_reviews=False,
                can_move_branches=False,
                can_enable_autonomous_coding=False,
                blocked_operations=(),
                validation_ref="deepseek-validation:level-3:branch-movement",
            )

    def test_branch_movement_level_is_reserved_even_with_consistent_authority_bits(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="level-3:branch-movement.*reserved"):
            DeepSeekValidationState(
                current_level=DeepSeekValidationLevel.BRANCH_MOVEMENT,
                can_receive_prompt_payloads=True,
                can_clear_reviews=True,
                can_move_branches=True,
                can_enable_autonomous_coding=False,
                blocked_operations=("autonomous_coding",),
                validation_ref="deepseek-validation:level-3:branch-movement",
            )

    def test_branch_movement_level_is_reserved_even_with_full_authority_request(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="no autonomy by accident"):
            DeepSeekValidationState(
                current_level=DeepSeekValidationLevel.BRANCH_MOVEMENT,
                can_receive_prompt_payloads=True,
                can_clear_reviews=True,
                can_move_branches=True,
                can_enable_autonomous_coding=True,
                blocked_operations=(),
                validation_ref="deepseek-validation:level-3:branch-movement",
            )

    def test_autonomous_coding_level_is_reserved_and_unconstructible_when_all_false(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="level-4:autonomous-coding.*reserved"):
            DeepSeekValidationState(
                current_level=DeepSeekValidationLevel.AUTONOMOUS_CODING,
                can_receive_prompt_payloads=False,
                can_clear_reviews=False,
                can_move_branches=False,
                can_enable_autonomous_coding=False,
                blocked_operations=(),
                validation_ref="deepseek-validation:level-4:autonomous-coding",
            )

    def test_autonomous_coding_level_is_reserved_even_with_consistent_authority_bits(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="level-4:autonomous-coding.*reserved"):
            DeepSeekValidationState(
                current_level=DeepSeekValidationLevel.AUTONOMOUS_CODING,
                can_receive_prompt_payloads=True,
                can_clear_reviews=True,
                can_move_branches=True,
                can_enable_autonomous_coding=True,
                blocked_operations=(),
                validation_ref="deepseek-validation:level-4:autonomous-coding",
            )

    def test_autonomous_coding_level_is_reserved_even_with_mixed_authority_bits(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="no autonomy by accident"):
            DeepSeekValidationState(
                current_level=DeepSeekValidationLevel.AUTONOMOUS_CODING,
                can_receive_prompt_payloads=True,
                can_clear_reviews=False,
                can_move_branches=True,
                can_enable_autonomous_coding=False,
                blocked_operations=("review_clearance",),
                validation_ref="deepseek-validation:level-4:autonomous-coding",
            )

    def test_reserved_levels_cannot_be_reached_via_preset_derivation(self) -> None:
        for level_value in (
            "deepseek-validation:level-2:review-clearance",
            "deepseek-validation:level-3:branch-movement",
            "deepseek-validation:level-4:autonomous-coding",
        ):
            direct_preset = deepseek_candidate_route_presets()[0]
            with pytest.raises(ModelAdapterConfigError, match="Unknown DeepSeek"):
                deepseek_validation_state_from_preset(
                    ModelCandidateRoutePreset(
                        provider_name="deepseek",
                        dispatch_model=direct_preset.dispatch_model,
                        variant_label=direct_preset.variant_label,
                        lane=direct_preset.lane,
                        api_mode=direct_preset.api_mode,
                        trust_state=direct_preset.trust_state,
                        requires_external_review=direct_preset.requires_external_review,
                        external_review_status=direct_preset.external_review_status,
                        direct_api_endpoint=direct_preset.direct_api_endpoint,
                        capability_tier=direct_preset.capability_tier,
                        context_budget=direct_preset.context_budget,
                        prompt_payload_budget=direct_preset.prompt_payload_budget,
                        allowed_task_types=direct_preset.allowed_task_types,
                        blocked_task_types=direct_preset.blocked_task_types,
                        max_risk_tier=direct_preset.max_risk_tier,
                        q_mode_flat=direct_preset.q_mode_flat,
                        can_clear_reviews=direct_preset.can_clear_reviews,
                        can_move_branches=direct_preset.can_move_branches,
                        bypasses_relay_aegis=direct_preset.bypasses_relay_aegis,
                        autonomous_coding_allowed=direct_preset.autonomous_coding_allowed,
                        known_authorities=direct_preset.known_authorities,
                        validation_evidence_ref=level_value,
                    )
                )

    def test_state_is_frozen(self) -> None:
        state = DeepSeekValidationState(
            current_level=DeepSeekValidationLevel.METADATA_ONLY,
            can_receive_prompt_payloads=False,
            can_clear_reviews=False,
            can_move_branches=False,
            can_enable_autonomous_coding=False,
            blocked_operations=(),
            validation_ref="deepseek-validation:level-0:metadata-only",
        )
        with pytest.raises(FrozenInstanceError):
            state.can_receive_prompt_payloads = True  # type: ignore[misc]

    def test_derive_state_from_metadata_only_preset(self) -> None:
        preset = deepseek_candidate_route_presets()[0]
        state = deepseek_validation_state_from_preset(preset)
        assert state.current_level == DeepSeekValidationLevel.METADATA_ONLY
        assert not state.can_receive_prompt_payloads
        assert not state.can_clear_reviews
        assert not state.can_move_branches
        assert not state.can_enable_autonomous_coding
        assert state.validation_ref == "deepseek-validation:level-0:metadata-only"

    def test_derive_state_preserves_dispatch_identity_rule(self) -> None:
        preset = deepseek_candidate_route_presets()[0]
        state = deepseek_validation_state_from_preset(preset)
        assert state.current_level == DeepSeekValidationLevel.METADATA_ONLY
        assert preset.dispatch_model == DEEPSEEK_DIRECT_MODEL
        assert preset.dispatch_model == "deepseek-chat"

    def test_rejects_non_deepseek_presets(self) -> None:
        non_deepseek = ModelCandidateRoutePreset(
            provider_name="anthropic",
            dispatch_model="claude-opus",
            variant_label="claude-opus-4",
            lane="default_quality",
            api_mode="direct",
            trust_state="trusted",
            requires_external_review=False,
            external_review_status="not_required",
            direct_api_endpoint="https://api.anthropic.com/v1",
            capability_tier="primary",
            context_budget=200000,
            prompt_payload_budget=150000,
            allowed_task_types=("all",),
            blocked_task_types=(),
            max_risk_tier=10,
            q_mode_flat=False,
            can_clear_reviews=True,
            can_move_branches=True,
            bypasses_relay_aegis=False,
            autonomous_coding_allowed=True,
            known_authorities=("anthropic",),
        )
        with pytest.raises(
            ModelAdapterConfigError, match="only for direct DeepSeek"
        ):
            deepseek_validation_state_from_preset(non_deepseek)

    def test_rejects_indirect_deepseek_dispatch_at_preset_construction(self) -> None:
        direct_preset = deepseek_candidate_route_presets()[0]
        with pytest.raises(ModelAdapterConfigError, match="deepseek-chat"):
            ModelCandidateRoutePreset(
                provider_name="deepseek",
                dispatch_model="openrouter-deepseek",
                variant_label=direct_preset.variant_label,
                lane=direct_preset.lane,
                api_mode=direct_preset.api_mode,
                trust_state=direct_preset.trust_state,
                requires_external_review=direct_preset.requires_external_review,
                external_review_status=direct_preset.external_review_status,
                direct_api_endpoint=direct_preset.direct_api_endpoint,
                capability_tier=direct_preset.capability_tier,
                context_budget=direct_preset.context_budget,
                prompt_payload_budget=direct_preset.prompt_payload_budget,
                allowed_task_types=direct_preset.allowed_task_types,
                blocked_task_types=direct_preset.blocked_task_types,
                max_risk_tier=direct_preset.max_risk_tier,
                q_mode_flat=direct_preset.q_mode_flat,
                can_clear_reviews=direct_preset.can_clear_reviews,
                can_move_branches=direct_preset.can_move_branches,
                bypasses_relay_aegis=direct_preset.bypasses_relay_aegis,
                autonomous_coding_allowed=direct_preset.autonomous_coding_allowed,
                known_authorities=direct_preset.known_authorities,
            )

    def test_rejects_unknown_validation_reference(self) -> None:
        direct_preset = deepseek_candidate_route_presets()[0]
        with pytest.raises(ModelAdapterConfigError, match="Unknown DeepSeek"):
            deepseek_validation_state_from_preset(
                ModelCandidateRoutePreset(
                    provider_name="deepseek",
                    dispatch_model=direct_preset.dispatch_model,
                    variant_label=direct_preset.variant_label,
                    lane=direct_preset.lane,
                    api_mode=direct_preset.api_mode,
                    trust_state=direct_preset.trust_state,
                    requires_external_review=direct_preset.requires_external_review,
                    external_review_status=direct_preset.external_review_status,
                    direct_api_endpoint=direct_preset.direct_api_endpoint,
                    capability_tier=direct_preset.capability_tier,
                    context_budget=direct_preset.context_budget,
                    prompt_payload_budget=direct_preset.prompt_payload_budget,
                    allowed_task_types=direct_preset.allowed_task_types,
                    blocked_task_types=direct_preset.blocked_task_types,
                    max_risk_tier=direct_preset.max_risk_tier,
                    q_mode_flat=direct_preset.q_mode_flat,
                    can_clear_reviews=direct_preset.can_clear_reviews,
                    can_move_branches=direct_preset.can_move_branches,
                    bypasses_relay_aegis=direct_preset.bypasses_relay_aegis,
                    autonomous_coding_allowed=direct_preset.autonomous_coding_allowed,
                    known_authorities=direct_preset.known_authorities,
                    validation_evidence_ref="unknown-validation:xyz",
                )
            )

    def test_validation_state_blocks_dangerous_operations_at_metadata_level(self) -> None:
        state = deepseek_validation_state_from_preset(
            deepseek_candidate_route_presets()[0]
        )
        assert "prompt_payload_dispatch" in state.blocked_operations
        assert "review_clearance" in state.blocked_operations
        assert "branch_movement" in state.blocked_operations
        assert "autonomous_coding" in state.blocked_operations

    def test_fast_lane_preset_derives_same_validation_level_as_default(self) -> None:
        default_state = deepseek_validation_state_from_preset(
            deepseek_candidate_route_presets()[0]
        )
        fast_state = deepseek_validation_state_from_preset(
            deepseek_candidate_route_presets()[1]
        )
        assert default_state.current_level == fast_state.current_level
        assert (
            default_state.can_receive_prompt_payloads
            == fast_state.can_receive_prompt_payloads
        )


class TestDeepSeekValidationDisposition:
    def test_disposition_from_metadata_only_preset_blocks_transport(self) -> None:
        metadata = deepseek_candidate_metadata_preset("default_quality")
        disposition = bind_deepseek_validation_disposition(metadata)
        assert disposition is not None
        assert disposition.validation_level == "level-0:metadata-only"
        assert disposition.direct_dispatch_id == "deepseek-chat"
        assert disposition.variant_labels == ("deepseek-v4-pro",)
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

    def test_disposition_fast_lane_carries_correct_variant_label(self) -> None:
        metadata = deepseek_candidate_metadata_preset("fast")
        disposition = bind_deepseek_validation_disposition(metadata)
        assert disposition is not None
        assert disposition.variant_labels == ("deepseek-v4-flash",)
        assert disposition.direct_dispatch_id == "deepseek-chat"

    def test_disposition_carries_blocked_authority_tags(self) -> None:
        metadata = deepseek_candidate_metadata_preset("fast")
        disposition = bind_deepseek_validation_disposition(metadata)
        assert disposition is not None
        assert "review_clearance" in disposition.blocked_authority_tags
        assert "branch_movement" in disposition.blocked_authority_tags
        assert "relay_aegis_bypass" in disposition.blocked_authority_tags
        assert "autonomous_coding" in disposition.blocked_authority_tags
        assert "aggregator_authority" in disposition.blocked_authority_tags

    def test_disposition_never_grants_autonomous_authority(self) -> None:
        metadata = deepseek_candidate_metadata_preset("default_quality")
        disposition = bind_deepseek_validation_disposition(metadata)
        assert disposition is not None
        assert disposition.autonomous_implementation_authorized is False
        assert disposition.review_clearing_authorized is False
        assert disposition.branch_movement_authorized is False
        assert disposition.live_coding_authority_authorized is False
        assert disposition.relay_bypass_authorized is False
        assert disposition.serialization_only is True

    def test_disposition_rejects_autonomous_authority_at_construction(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="autonomous authority"):
            DeepSeekValidationDisposition(
                validation_level="level-0:metadata-only",
                direct_dispatch_id="deepseek-chat",
                variant_labels=("deepseek-v4-pro",),
                transport_cleared=False,
                blocked_authority_tags=(),
                validation_evidence_ref="deepseek-validation:level-0:metadata-only",
                autonomous_implementation_authorized=True,
            )

    def test_disposition_rejects_review_clearing_authority(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="autonomous authority"):
            DeepSeekValidationDisposition(
                validation_level="level-0:metadata-only",
                direct_dispatch_id="deepseek-chat",
                variant_labels=("deepseek-v4-pro",),
                transport_cleared=False,
                blocked_authority_tags=(),
                validation_evidence_ref="deepseek-validation:level-0:metadata-only",
                review_clearing_authorized=True,
            )

    def test_disposition_rejects_branch_movement_authority(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="autonomous authority"):
            DeepSeekValidationDisposition(
                validation_level="level-0:metadata-only",
                direct_dispatch_id="deepseek-chat",
                variant_labels=("deepseek-v4-pro",),
                transport_cleared=False,
                blocked_authority_tags=(),
                validation_evidence_ref="deepseek-validation:level-0:metadata-only",
                branch_movement_authorized=True,
            )

    def test_disposition_rejects_live_coding_authority(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="autonomous authority"):
            DeepSeekValidationDisposition(
                validation_level="level-0:metadata-only",
                direct_dispatch_id="deepseek-chat",
                variant_labels=("deepseek-v4-pro",),
                transport_cleared=False,
                blocked_authority_tags=(),
                validation_evidence_ref="deepseek-validation:level-0:metadata-only",
                live_coding_authority_authorized=True,
            )

    def test_disposition_rejects_relay_bypass_authority(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="autonomous authority"):
            DeepSeekValidationDisposition(
                validation_level="level-0:metadata-only",
                direct_dispatch_id="deepseek-chat",
                variant_labels=("deepseek-v4-pro",),
                transport_cleared=False,
                blocked_authority_tags=(),
                validation_evidence_ref="deepseek-validation:level-0:metadata-only",
                relay_bypass_authorized=True,
            )

    def test_disposition_rejects_non_deepseek_dispatch_id(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="deepseek-chat"):
            DeepSeekValidationDisposition(
                validation_level="level-0:metadata-only",
                direct_dispatch_id="claude-opus",
                variant_labels=("claude-opus-4",),
                transport_cleared=False,
                blocked_authority_tags=(),
                validation_evidence_ref="deepseek-validation:level-0:metadata-only",
            )

    def test_disposition_rejects_variant_label_masquerading_as_dispatch_model(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="masquerade"):
            DeepSeekValidationDisposition(
                validation_level="level-0:metadata-only",
                direct_dispatch_id="deepseek-chat",
                variant_labels=("deepseek-chat",),
                transport_cleared=False,
                blocked_authority_tags=(),
                validation_evidence_ref="deepseek-validation:level-0:metadata-only",
            )

    def test_disposition_rejects_non_serialization_only(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="serialization-only"):
            DeepSeekValidationDisposition(
                validation_level="level-0:metadata-only",
                direct_dispatch_id="deepseek-chat",
                variant_labels=("deepseek-v4-pro",),
                transport_cleared=False,
                blocked_authority_tags=(),
                validation_evidence_ref="deepseek-validation:level-0:metadata-only",
                serialization_only=False,
            )

    def test_bind_returns_none_when_metadata_missing(self) -> None:
        assert bind_deepseek_validation_disposition(None) is None

    def test_bind_returns_none_for_non_deepseek_provider(self) -> None:
        metadata = ModelHarnessMetadata(
            provider_name="anthropic",
            model_name="claude-opus",
            capability_tier="primary",
            context_budget=200000,
            prompt_payload_budget=150000,
            trust_state="trusted",
            requires_external_review=False,
        )
        assert bind_deepseek_validation_disposition(metadata) is None

    def test_bind_returns_none_for_deepseek_without_candidate_state(self) -> None:
        metadata = ModelHarnessMetadata(
            provider_name="deepseek",
            model_name="deepseek-chat",
            capability_tier="standard",
            context_budget=65536,
            prompt_payload_budget=57344,
            trust_state="candidate",
            requires_external_review=True,
        )
        assert bind_deepseek_validation_disposition(metadata) is None

    def test_bind_returns_none_for_non_direct_deepseek_model(self) -> None:
        metadata = ModelHarnessMetadata(
            provider_name="deepseek",
            model_name="openrouter-deepseek",
            capability_tier="standard",
            context_budget=65536,
            prompt_payload_budget=57344,
            trust_state="candidate",
            requires_external_review=True,
            deepseek_candidate_state={
                "validation_evidence_ref": "deepseek-validation:level-0:metadata-only",
                "variant_label": "deepseek-v4-pro",
            },
        )
        assert bind_deepseek_validation_disposition(metadata) is None

    def test_disposition_to_dict_is_stable(self) -> None:
        metadata = deepseek_candidate_metadata_preset("fast")
        disposition = bind_deepseek_validation_disposition(metadata)
        assert disposition is not None
        rendered = disposition.to_dict()
        assert tuple(rendered.keys()) == (
            "validation_level",
            "direct_dispatch_id",
            "variant_labels",
            "transport_cleared",
            "blocked_authority_tags",
            "validation_evidence_ref",
            "direct_endpoint_evidence_ref",
            "external_review_evidence_ref",
            "autonomous_implementation_authorized",
            "review_clearing_authorized",
            "branch_movement_authorized",
            "live_coding_authority_authorized",
            "relay_bypass_authorized",
            "serialization_only",
        )
        assert rendered["direct_dispatch_id"] == "deepseek-chat"
        assert rendered["transport_cleared"] is False
        assert rendered["autonomous_implementation_authorized"] is False

    def test_disposition_is_frozen(self) -> None:
        metadata = deepseek_candidate_metadata_preset("fast")
        disposition = bind_deepseek_validation_disposition(metadata)
        assert disposition is not None
        with pytest.raises(FrozenInstanceError):
            disposition.transport_cleared = True  # type: ignore[misc]

    def test_validation_cleared_validation_ref_marks_transport_cleared(self) -> None:
        metadata = ModelHarnessMetadata(
            provider_name="deepseek",
            model_name="deepseek-chat",
            capability_tier="candidate-quality",
            context_budget=65536,
            prompt_payload_budget=57344,
            trust_state="validation_cleared",
            requires_external_review=False,
            deepseek_candidate_state={
                "validation_evidence_ref": "deepseek-validation:level-1:validation-cleared",
                "variant_label": "deepseek-v4-pro",
                "blocked_authorities": "review_clearance,branch_movement,autonomous_coding",
                "direct_endpoint_evidence_ref": (
                    "deepseek-direct-endpoint:"
                    "https://api.deepseek.com/v1/chat/completions"
                ),
                "external_review_evidence_ref": (
                    "external-review:deepseek:deepseek-chat:passed"
                ),
            },
        )
        disposition = bind_deepseek_validation_disposition(metadata)
        assert disposition is not None
        assert disposition.validation_level == "level-1:validation-cleared"
        assert disposition.transport_cleared is True
        assert disposition.autonomous_implementation_authorized is False
        assert disposition.review_clearing_authorized is False
        assert disposition.branch_movement_authorized is False
        assert disposition.live_coding_authority_authorized is False
        assert disposition.relay_bypass_authorized is False
        assert disposition.serialization_only is True

    def test_unknown_validation_ref_marks_transport_blocked(self) -> None:
        metadata = ModelHarnessMetadata(
            provider_name="deepseek",
            model_name="deepseek-chat",
            capability_tier="candidate-quality",
            context_budget=65536,
            prompt_payload_budget=57344,
            trust_state="candidate",
            requires_external_review=True,
            deepseek_candidate_state={
                "validation_evidence_ref": "deepseek-validation:level-99:unknown",
                "variant_label": "deepseek-v4-pro",
            },
        )
        disposition = bind_deepseek_validation_disposition(metadata)
        assert disposition is not None
        assert disposition.validation_level == "level-unknown"
        assert disposition.transport_cleared is False


_DEEPSEEK_AUTHORITY_TAGS = (
    "autonomous_implementation",
    "review_clearance",
    "branch_movement",
    "live_coding",
    "relay_bypass",
)


def _verified_proof(
    *, human: bool = True, prime: bool = True
) -> DeepSeekValidationGateProof:
    return DeepSeekValidationGateProof(
        proof_state=DeepSeekValidationProofState.PROOF_VERIFIED,
        proof_evidence_refs=("deepseek-proof:run-id:abc",),
        review_evidence_ref="external-review:deepseek:deepseek-chat:passed",
        proof_observed_at="2026-06-09T10:00:00+00:00",
        proof_max_age_seconds=86400,
        human_gate_satisfied=human,
        prime_authority_satisfied=prime,
    )


class TestDeepSeekValidationProofState:
    def test_enum_advertises_full_proof_ladder(self) -> None:
        assert DeepSeekValidationProofState.NONE.value == "none"
        assert (
            DeepSeekValidationProofState.CANDIDATE_METADATA_ONLY.value
            == "candidate-metadata-only"
        )
        assert (
            DeepSeekValidationProofState.PROOF_SUBMITTED_PENDING_REVIEW.value
            == "proof-submitted-pending-review"
        )
        assert DeepSeekValidationProofState.PROOF_STALE.value == "proof-stale"
        assert DeepSeekValidationProofState.PROOF_PARTIAL.value == "proof-partial"
        assert DeepSeekValidationProofState.PROOF_REVOKED.value == "proof-revoked"
        assert DeepSeekValidationProofState.PROOF_VERIFIED.value == "proof-verified"


class TestDeepSeekValidationGateProof:
    def test_default_proof_is_fail_closed(self) -> None:
        proof = DeepSeekValidationGateProof(
            proof_state=DeepSeekValidationProofState.NONE,
        )
        assert proof.proof_evidence_refs == ()
        assert proof.review_evidence_ref is None
        assert proof.proof_observed_at is None
        assert proof.proof_max_age_seconds is None
        assert proof.human_gate_satisfied is False
        assert proof.prime_authority_satisfied is False

    def test_rejects_negative_max_age(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="proof_max_age_seconds"):
            DeepSeekValidationGateProof(
                proof_state=DeepSeekValidationProofState.PROOF_VERIFIED,
                proof_max_age_seconds=-1,
            )

    def test_to_dict_is_display_safe(self) -> None:
        proof = _verified_proof()
        rendered = proof.to_dict()
        assert rendered["proof_state"] == "proof-verified"
        assert rendered["proof_evidence_refs"] == ["deepseek-proof:run-id:abc"]
        assert rendered["review_evidence_ref"] == (
            "external-review:deepseek:deepseek-chat:passed"
        )
        assert rendered["proof_observed_at"] == "2026-06-09T10:00:00+00:00"
        assert rendered["proof_max_age_seconds"] == 86400
        assert rendered["human_gate_satisfied"] is True
        assert rendered["prime_authority_satisfied"] is True
        flat = " ".join(str(v) for v in rendered.values()).lower()
        assert "credential" not in flat
        assert "api_key" not in flat

    def test_is_frozen(self) -> None:
        proof = DeepSeekValidationGateProof(
            proof_state=DeepSeekValidationProofState.NONE,
        )
        with pytest.raises(FrozenInstanceError):
            proof.human_gate_satisfied = True  # type: ignore[misc]


class TestDeepSeekTransportAuthorityConstruction:
    def _verified_authority(self) -> DeepSeekTransportAuthority:
        return evaluate_deepseek_transport_authority(_verified_proof())

    def test_verified_proof_with_both_gates_authorizes_transport(self) -> None:
        auth = self._verified_authority()
        assert auth.status is DeepSeekTransportAuthorityStatus.AUTHORIZED_TRANSPORT_ONLY
        assert auth.transport_authorized is True
        assert auth.direct_dispatch_id == "deepseek-chat"

    def test_authorized_transport_never_grants_autonomous_authority(self) -> None:
        auth = self._verified_authority()
        assert auth.autonomous_implementation_authorized is False
        assert auth.review_clearing_authorized is False
        assert auth.branch_movement_authorized is False
        assert auth.live_coding_authority_authorized is False
        assert auth.relay_bypass_authorized is False
        for marker in _DEEPSEEK_AUTHORITY_TAGS:
            assert marker in auth.blocked_authority_tags

    def test_construction_rejects_autonomous_authority_bit(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="autonomous authority"):
            DeepSeekTransportAuthority(
                direct_dispatch_id="deepseek-chat",
                proof=_verified_proof(),
                status=DeepSeekTransportAuthorityStatus.AUTHORIZED_TRANSPORT_ONLY,
                transport_authorized=True,
                blocker_tags=(),
                blocked_authority_tags=_DEEPSEEK_AUTHORITY_TAGS,
                autonomous_implementation_authorized=True,
            )

    def test_construction_rejects_non_deepseek_chat_dispatch_id(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="deepseek-chat"):
            DeepSeekTransportAuthority(
                direct_dispatch_id="claude-opus",
                proof=_verified_proof(),
                status=DeepSeekTransportAuthorityStatus.AUTHORIZED_TRANSPORT_ONLY,
                transport_authorized=True,
                blocker_tags=(),
                blocked_authority_tags=_DEEPSEEK_AUTHORITY_TAGS,
            )

    def test_construction_rejects_non_serialization_only(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="serialization-only"):
            DeepSeekTransportAuthority(
                direct_dispatch_id="deepseek-chat",
                proof=_verified_proof(),
                status=DeepSeekTransportAuthorityStatus.AUTHORIZED_TRANSPORT_ONLY,
                transport_authorized=True,
                blocker_tags=(),
                blocked_authority_tags=_DEEPSEEK_AUTHORITY_TAGS,
                serialization_only=False,
            )

    def test_construction_rejects_status_authorized_mismatch_true(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="transport_authorized must equal"):
            DeepSeekTransportAuthority(
                direct_dispatch_id="deepseek-chat",
                proof=_verified_proof(),
                status=DeepSeekTransportAuthorityStatus.BLOCKED_NO_PROOF,
                transport_authorized=True,
                blocker_tags=("deepseek_proof_missing",),
                blocked_authority_tags=_DEEPSEEK_AUTHORITY_TAGS,
            )

    def test_construction_rejects_status_authorized_mismatch_false(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="transport_authorized must equal"):
            DeepSeekTransportAuthority(
                direct_dispatch_id="deepseek-chat",
                proof=_verified_proof(),
                status=DeepSeekTransportAuthorityStatus.AUTHORIZED_TRANSPORT_ONLY,
                transport_authorized=False,
                blocker_tags=(),
                blocked_authority_tags=_DEEPSEEK_AUTHORITY_TAGS,
            )

    def test_construction_rejects_missing_blocked_authority_tag(self) -> None:
        with pytest.raises(ModelAdapterConfigError, match="blocked-authority tag"):
            DeepSeekTransportAuthority(
                direct_dispatch_id="deepseek-chat",
                proof=_verified_proof(),
                status=DeepSeekTransportAuthorityStatus.AUTHORIZED_TRANSPORT_ONLY,
                transport_authorized=True,
                blocker_tags=(),
                blocked_authority_tags=("autonomous_implementation",),
            )

    def test_to_dict_is_display_safe_and_stable(self) -> None:
        auth = self._verified_authority()
        rendered = auth.to_dict()
        assert rendered == auth.to_dict()
        assert tuple(rendered.keys()) == (
            "direct_dispatch_id",
            "proof",
            "status",
            "transport_authorized",
            "blocker_tags",
            "blocked_authority_tags",
            "autonomous_implementation_authorized",
            "review_clearing_authorized",
            "branch_movement_authorized",
            "live_coding_authority_authorized",
            "relay_bypass_authorized",
            "serialization_only",
        )
        assert rendered["direct_dispatch_id"] == "deepseek-chat"
        assert rendered["transport_authorized"] is True
        assert rendered["status"] == "authorized:transport-only"
        flat = " ".join(str(v) for v in rendered.values()).lower()
        assert "credential" not in flat
        assert "api_key" not in flat


class TestEvaluateDeepSeekTransportAuthority:
    def test_none_proof_blocks_with_no_proof_marker(self) -> None:
        auth = evaluate_deepseek_transport_authority(
            DeepSeekValidationGateProof(
                proof_state=DeepSeekValidationProofState.NONE
            )
        )
        assert auth.status is DeepSeekTransportAuthorityStatus.BLOCKED_NO_PROOF
        assert auth.transport_authorized is False
        assert "deepseek_proof_missing" in auth.blocker_tags

    def test_candidate_only_proof_blocks_with_candidate_marker(self) -> None:
        auth = evaluate_deepseek_transport_authority(
            DeepSeekValidationGateProof(
                proof_state=DeepSeekValidationProofState.CANDIDATE_METADATA_ONLY
            )
        )
        assert auth.status is DeepSeekTransportAuthorityStatus.BLOCKED_CANDIDATE_ONLY
        assert auth.transport_authorized is False
        assert "deepseek_proof_candidate_only" in auth.blocker_tags

    def test_partial_proof_blocks_with_partial_marker(self) -> None:
        auth = evaluate_deepseek_transport_authority(
            DeepSeekValidationGateProof(
                proof_state=DeepSeekValidationProofState.PROOF_PARTIAL
            )
        )
        assert auth.status is DeepSeekTransportAuthorityStatus.BLOCKED_PROOF_PARTIAL
        assert auth.transport_authorized is False
        assert "deepseek_proof_partial" in auth.blocker_tags

    def test_stale_proof_blocks_with_stale_marker(self) -> None:
        auth = evaluate_deepseek_transport_authority(
            DeepSeekValidationGateProof(
                proof_state=DeepSeekValidationProofState.PROOF_STALE
            )
        )
        assert auth.status is DeepSeekTransportAuthorityStatus.BLOCKED_PROOF_STALE
        assert auth.transport_authorized is False
        assert "deepseek_proof_stale" in auth.blocker_tags

    def test_revoked_proof_blocks_with_revoked_marker(self) -> None:
        auth = evaluate_deepseek_transport_authority(
            DeepSeekValidationGateProof(
                proof_state=DeepSeekValidationProofState.PROOF_REVOKED
            )
        )
        assert auth.status is DeepSeekTransportAuthorityStatus.BLOCKED_PROOF_REVOKED
        assert auth.transport_authorized is False
        assert "deepseek_proof_revoked" in auth.blocker_tags

    def test_pending_review_proof_blocks_with_pending_marker(self) -> None:
        auth = evaluate_deepseek_transport_authority(
            DeepSeekValidationGateProof(
                proof_state=DeepSeekValidationProofState.PROOF_SUBMITTED_PENDING_REVIEW
            )
        )
        assert (
            auth.status is DeepSeekTransportAuthorityStatus.BLOCKED_PROOF_PENDING_REVIEW
        )
        assert auth.transport_authorized is False
        assert "deepseek_proof_pending_review" in auth.blocker_tags

    def test_verified_proof_without_human_gate_blocks(self) -> None:
        auth = evaluate_deepseek_transport_authority(
            _verified_proof(human=False, prime=True)
        )
        assert (
            auth.status is DeepSeekTransportAuthorityStatus.BLOCKED_HUMAN_GATE_REQUIRED
        )
        assert auth.transport_authorized is False
        assert "deepseek_human_gate_required" in auth.blocker_tags

    def test_verified_proof_with_human_gate_but_no_prime_blocks(self) -> None:
        auth = evaluate_deepseek_transport_authority(
            _verified_proof(human=True, prime=False)
        )
        assert (
            auth.status
            is DeepSeekTransportAuthorityStatus.BLOCKED_PRIME_AUTHORITY_REQUIRED
        )
        assert auth.transport_authorized is False
        assert "deepseek_prime_authority_required" in auth.blocker_tags

    def test_verified_proof_with_both_gates_authorizes_transport_only(self) -> None:
        auth = evaluate_deepseek_transport_authority(_verified_proof())
        assert auth.status is DeepSeekTransportAuthorityStatus.AUTHORIZED_TRANSPORT_ONLY
        assert auth.transport_authorized is True
        assert auth.blocker_tags == ()
        for marker in _DEEPSEEK_AUTHORITY_TAGS:
            assert marker in auth.blocked_authority_tags

    def test_every_evaluation_preserves_all_five_blocked_authority_tags(self) -> None:
        for state in DeepSeekValidationProofState:
            proof = DeepSeekValidationGateProof(proof_state=state)
            auth = evaluate_deepseek_transport_authority(proof)
            for marker in _DEEPSEEK_AUTHORITY_TAGS:
                assert marker in auth.blocked_authority_tags
            assert auth.autonomous_implementation_authorized is False
            assert auth.review_clearing_authorized is False
            assert auth.branch_movement_authorized is False
            assert auth.live_coding_authority_authorized is False
            assert auth.relay_bypass_authorized is False


class TestBindDeepSeekTransportAuthority:
    def test_bind_returns_none_when_metadata_missing(self) -> None:
        assert bind_deepseek_transport_authority(None) is None

    def test_bind_returns_none_for_non_deepseek_provider(self) -> None:
        meta = ModelHarnessMetadata(
            provider_name="anthropic",
            model_name="claude-opus",
            capability_tier="primary",
            context_budget=200000,
            prompt_payload_budget=150000,
            trust_state="trusted",
            requires_external_review=False,
        )
        assert bind_deepseek_transport_authority(meta) is None

    def test_bind_returns_none_for_non_deepseek_chat_model(self) -> None:
        meta = ModelHarnessMetadata(
            provider_name="deepseek",
            model_name="openrouter-deepseek",
            capability_tier="standard",
            context_budget=65536,
            prompt_payload_budget=57344,
            trust_state="candidate",
            requires_external_review=True,
            deepseek_candidate_state={
                "validation_evidence_ref": "deepseek-validation:level-0:metadata-only",
            },
        )
        assert bind_deepseek_transport_authority(meta) is None

    def test_bind_emits_blocked_no_proof_for_deepseek_chat_without_candidate_state(
        self,
    ) -> None:
        """Direct DeepSeek metadata with no candidate_state must fail-closed,
        not silently return None — consumers need to distinguish "no DeepSeek
        record" from "DeepSeek record with no proof"."""
        meta = ModelHarnessMetadata(
            provider_name="deepseek",
            model_name="deepseek-chat",
            capability_tier="standard",
            context_budget=65536,
            prompt_payload_budget=57344,
            trust_state="candidate",
            requires_external_review=True,
        )
        auth = bind_deepseek_transport_authority(meta)
        assert auth is not None
        assert auth.status is DeepSeekTransportAuthorityStatus.BLOCKED_NO_PROOF
        assert auth.transport_authorized is False
        assert "deepseek_proof_missing" in auth.blocker_tags
        assert auth.proof.proof_state is DeepSeekValidationProofState.NONE
        assert auth.proof.proof_evidence_refs == ()
        assert auth.proof.review_evidence_ref is None
        assert auth.proof.human_gate_satisfied is False
        assert auth.proof.prime_authority_satisfied is False
        for marker in _DEEPSEEK_AUTHORITY_TAGS:
            assert marker in auth.blocked_authority_tags

    def test_bind_returns_candidate_blocked_authority_for_current_metadata(self) -> None:
        meta = deepseek_candidate_metadata_preset("fast")
        auth = bind_deepseek_transport_authority(meta)
        assert auth is not None
        assert auth.status is DeepSeekTransportAuthorityStatus.BLOCKED_CANDIDATE_ONLY
        assert auth.transport_authorized is False
        assert "deepseek_proof_candidate_only" in auth.blocker_tags
        assert auth.proof.proof_state is DeepSeekValidationProofState.CANDIDATE_METADATA_ONLY
        assert auth.proof.human_gate_satisfied is False
        assert auth.proof.prime_authority_satisfied is False
        for marker in _DEEPSEEK_AUTHORITY_TAGS:
            assert marker in auth.blocked_authority_tags

    def test_bind_carries_validation_and_review_refs_into_proof(self) -> None:
        meta = deepseek_candidate_metadata_preset("default_quality")
        auth = bind_deepseek_transport_authority(meta)
        assert auth is not None
        assert auth.proof.proof_evidence_refs == (
            "deepseek-validation:level-0:metadata-only",
        )
        assert auth.proof.review_evidence_ref == (
            "external-review:deepseek:deepseek-chat:pending"
        )

    def test_bind_never_grants_transport_for_current_candidate_metadata(self) -> None:
        for lane in ("default_quality", "fast"):
            meta = deepseek_candidate_metadata_preset(lane)
            auth = bind_deepseek_transport_authority(meta)
            assert auth is not None
            assert auth.transport_authorized is False
            assert (
                auth.status
                is DeepSeekTransportAuthorityStatus.BLOCKED_CANDIDATE_ONLY
            )

    def _level_one_metadata(
        self,
        *,
        human_gate: str | None = "true",
        prime_authority: str | None = "true",
        validation_ref: str = "deepseek-validation:level-1:validation-cleared",
        review_ref: str = "external-review:deepseek:deepseek-chat:passed",
    ) -> ModelHarnessMetadata:
        candidate_state: dict[str, str] = {
            "validation_evidence_ref": validation_ref,
            "external_review_evidence_ref": review_ref,
        }
        if human_gate is not None:
            candidate_state["human_gate_satisfied"] = human_gate
        if prime_authority is not None:
            candidate_state["prime_authority_satisfied"] = prime_authority
        return ModelHarnessMetadata(
            provider_name="deepseek",
            model_name="deepseek-chat",
            capability_tier="standard",
            context_budget=65536,
            prompt_payload_budget=57344,
            trust_state="candidate",
            requires_external_review=False,
            deepseek_candidate_state=candidate_state,
        )

    def test_bind_level_one_validation_with_both_gates_yields_authorized_transport_only(
        self,
    ) -> None:
        """Repair: level-1 validation ref + both gates explicitly true is the
        only path that lifts the binder out of fail-closed."""
        meta = self._level_one_metadata(human_gate="true", prime_authority="true")
        auth = bind_deepseek_transport_authority(meta)
        assert auth is not None
        assert (
            auth.status
            is DeepSeekTransportAuthorityStatus.AUTHORIZED_TRANSPORT_ONLY
        )
        assert auth.transport_authorized is True
        assert auth.proof.proof_state is DeepSeekValidationProofState.PROOF_VERIFIED
        assert auth.proof.human_gate_satisfied is True
        assert auth.proof.prime_authority_satisfied is True
        assert auth.proof.proof_evidence_refs == (
            "deepseek-validation:level-1:validation-cleared",
        )
        assert auth.proof.review_evidence_ref == (
            "external-review:deepseek:deepseek-chat:passed"
        )
        assert auth.autonomous_implementation_authorized is False
        assert auth.review_clearing_authorized is False
        assert auth.branch_movement_authorized is False
        assert auth.live_coding_authority_authorized is False
        assert auth.relay_bypass_authorized is False
        for marker in _DEEPSEEK_AUTHORITY_TAGS:
            assert marker in auth.blocked_authority_tags

    def test_bind_level_one_validation_without_human_gate_blocks(self) -> None:
        meta = self._level_one_metadata(human_gate="false", prime_authority="true")
        auth = bind_deepseek_transport_authority(meta)
        assert auth is not None
        assert (
            auth.status
            is DeepSeekTransportAuthorityStatus.BLOCKED_HUMAN_GATE_REQUIRED
        )
        assert auth.transport_authorized is False
        assert "deepseek_human_gate_required" in auth.blocker_tags
        assert auth.proof.human_gate_satisfied is False
        assert auth.proof.prime_authority_satisfied is True

    def test_bind_level_one_validation_without_prime_authority_blocks(self) -> None:
        meta = self._level_one_metadata(human_gate="true", prime_authority="false")
        auth = bind_deepseek_transport_authority(meta)
        assert auth is not None
        assert (
            auth.status
            is DeepSeekTransportAuthorityStatus.BLOCKED_PRIME_AUTHORITY_REQUIRED
        )
        assert auth.transport_authorized is False
        assert "deepseek_prime_authority_required" in auth.blocker_tags
        assert auth.proof.human_gate_satisfied is True
        assert auth.proof.prime_authority_satisfied is False

    def test_bind_level_one_validation_without_either_gate_blocks(self) -> None:
        meta = self._level_one_metadata(human_gate=None, prime_authority=None)
        auth = bind_deepseek_transport_authority(meta)
        assert auth is not None
        # Human gate is checked first; both gates being absent surfaces the
        # human-gate blocker so the human-gate requirement is reported first.
        assert (
            auth.status
            is DeepSeekTransportAuthorityStatus.BLOCKED_HUMAN_GATE_REQUIRED
        )
        assert auth.transport_authorized is False
        assert auth.proof.human_gate_satisfied is False
        assert auth.proof.prime_authority_satisfied is False

    def test_bind_level_one_validation_with_non_true_gate_strings_blocks(self) -> None:
        """Only an explicit lowercase ``"true"`` string opens the gate —
        empty, ``"True"`` casing variants must still fail closed if the
        downstream toggle is the bare boolean ``"true"`` contract."""
        meta = self._level_one_metadata(human_gate="yes", prime_authority="1")
        auth = bind_deepseek_transport_authority(meta)
        assert auth is not None
        assert auth.transport_authorized is False
        assert auth.status in {
            DeepSeekTransportAuthorityStatus.BLOCKED_HUMAN_GATE_REQUIRED,
            DeepSeekTransportAuthorityStatus.BLOCKED_PRIME_AUTHORITY_REQUIRED,
        }

    def test_bind_non_level_one_validation_ref_stays_candidate_metadata_only(
        self,
    ) -> None:
        """Even if both gate flags are explicitly true, a non-level-1
        validation ref must keep the proof state at CANDIDATE_METADATA_ONLY —
        gate flags alone cannot bypass the validation-level ladder."""
        meta = self._level_one_metadata(
            validation_ref="deepseek-validation:level-0:metadata-only",
            human_gate="true",
            prime_authority="true",
        )
        auth = bind_deepseek_transport_authority(meta)
        assert auth is not None
        assert (
            auth.status
            is DeepSeekTransportAuthorityStatus.BLOCKED_CANDIDATE_ONLY
        )
        assert auth.transport_authorized is False
        assert auth.proof.proof_state is DeepSeekValidationProofState.CANDIDATE_METADATA_ONLY
        assert auth.proof.human_gate_satisfied is False
        assert auth.proof.prime_authority_satisfied is False

    def test_bind_level_one_validation_with_uppercase_true_stays_blocked(self) -> None:
        """Codex Review A MEDIUM fix: only the exact lowercase string ``"true"``
        opens a gate. ``"True"`` must keep ``human_gate_satisfied`` False, so
        the binder surfaces ``BLOCKED_HUMAN_GATE_REQUIRED`` even though the
        validation ref is level-1 and prime authority is satisfied."""
        meta = self._level_one_metadata(human_gate="True", prime_authority="true")
        auth = bind_deepseek_transport_authority(meta)
        assert auth is not None
        assert (
            auth.status
            is DeepSeekTransportAuthorityStatus.BLOCKED_HUMAN_GATE_REQUIRED
        )
        assert auth.transport_authorized is False
        assert auth.proof.human_gate_satisfied is False
        assert auth.proof.prime_authority_satisfied is True

    def test_bind_level_one_validation_with_all_uppercase_true_stays_blocked(
        self,
    ) -> None:
        """``"TRUE"`` for both gates must keep both flags False — the contract
        is the exact lowercase string, never a case-insensitive match."""
        meta = self._level_one_metadata(human_gate="TRUE", prime_authority="TRUE")
        auth = bind_deepseek_transport_authority(meta)
        assert auth is not None
        # Human gate is checked first in evaluate_deepseek_transport_authority,
        # so the human-gate blocker is the surfaced status.
        assert (
            auth.status
            is DeepSeekTransportAuthorityStatus.BLOCKED_HUMAN_GATE_REQUIRED
        )
        assert auth.transport_authorized is False
        assert auth.proof.human_gate_satisfied is False
        assert auth.proof.prime_authority_satisfied is False

    def test_bind_level_one_validation_with_mixed_case_true_stays_blocked(self) -> None:
        """A mixed-case ``"tRuE"`` on the prime-authority gate (with human
        gate satisfied) must surface ``BLOCKED_PRIME_AUTHORITY_REQUIRED``."""
        meta = self._level_one_metadata(human_gate="true", prime_authority="tRuE")
        auth = bind_deepseek_transport_authority(meta)
        assert auth is not None
        assert (
            auth.status
            is DeepSeekTransportAuthorityStatus.BLOCKED_PRIME_AUTHORITY_REQUIRED
        )
        assert auth.transport_authorized is False
        assert auth.proof.human_gate_satisfied is True
        assert auth.proof.prime_authority_satisfied is False

    def test_bind_level_one_validation_with_whitespace_true_authorizes(self) -> None:
        """Surrounding whitespace is stripped before the equality check, so
        ``"  true  "`` is treated the same as the exact lowercase ``"true"``."""
        meta = self._level_one_metadata(
            human_gate="  true  ", prime_authority=" true"
        )
        auth = bind_deepseek_transport_authority(meta)
        assert auth is not None
        assert (
            auth.status
            is DeepSeekTransportAuthorityStatus.AUTHORIZED_TRANSPORT_ONLY
        )
        assert auth.transport_authorized is True
        assert auth.proof.human_gate_satisfied is True
        assert auth.proof.prime_authority_satisfied is True
