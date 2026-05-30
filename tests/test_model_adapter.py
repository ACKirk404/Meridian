"""Tests for provider-neutral Model Harness adapters."""

from __future__ import annotations

import pytest

from meridian_core.model_adapter import (
    AdapterRegistry,
    EnvConfiguredModelAdapter,
    FakeModelAdapter,
    MissingAdapterError,
    ModelAdapterConfig,
    ModelAdapterConfigError,
)
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
