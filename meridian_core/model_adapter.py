"""Provider-neutral model adapter boundary for the Model Harness.

Adapters receive only approved prompt payload text. Provider credentials,
models, account/session details, and transport concerns stay inside the
adapter implementation and outside Relay's dispatch payload.
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping, Protocol

from .relay import ModelRole


class ModelAdapterConfigError(RuntimeError):
    """Raised when a live model adapter is missing required configuration."""


@dataclass(frozen=True)
class ModelHarnessMetadata:
    """Provider-neutral Model Harness metadata for capability and budget tracking."""

    provider_name: str
    model_name: str
    capability_tier: str
    context_budget: int
    prompt_payload_budget: int
    trust_state: str
    requires_external_review: bool
    deepseek_candidate_state: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        if self.deepseek_candidate_state is not None:
            object.__setattr__(
                self,
                "deepseek_candidate_state",
                MappingProxyType(dict(self.deepseek_candidate_state)),
            )


@dataclass(frozen=True)
class ModelCandidateRoutePreset:
    """Provider-neutral candidate-route metadata before a live adapter is wired."""

    provider_name: str
    dispatch_model: str
    variant_label: str
    lane: str
    api_mode: str
    trust_state: str
    requires_external_review: bool
    external_review_status: str
    direct_api_endpoint: str
    capability_tier: str
    context_budget: int
    prompt_payload_budget: int
    allowed_task_types: tuple[str, ...]
    blocked_task_types: tuple[str, ...]
    max_risk_tier: int
    q_mode_flat: bool
    can_clear_reviews: bool
    can_move_branches: bool
    bypasses_relay_aegis: bool
    autonomous_coding_allowed: bool
    known_authorities: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.provider_name == "deepseek" and self.dispatch_model != DEEPSEEK_DIRECT_MODEL:
            raise ModelAdapterConfigError(
                "DeepSeek direct candidate presets must dispatch with deepseek-chat"
            )
        if self.variant_label == self.dispatch_model:
            raise ModelAdapterConfigError("variant_label must not masquerade as dispatch_model")

    def to_metadata(self) -> ModelHarnessMetadata:
        """Return the legacy adapter metadata surface for this candidate preset."""
        return ModelHarnessMetadata(
            provider_name=self.provider_name,
            model_name=self.dispatch_model,
            capability_tier=self.capability_tier,
            context_budget=self.context_budget,
            prompt_payload_budget=self.prompt_payload_budget,
            trust_state=self.trust_state,
            requires_external_review=self.requires_external_review,
            deepseek_candidate_state={
                "api_mode": self.api_mode,
                "variant_label": self.variant_label,
                "lane": self.lane,
                "direct_api_endpoint": self.direct_api_endpoint,
                "external_review_status": self.external_review_status,
                "allowed_task_types": ",".join(self.allowed_task_types),
                "blocked_task_types": ",".join(self.blocked_task_types),
                "max_risk_tier": str(self.max_risk_tier),
                "q_mode_flat": str(self.q_mode_flat).lower(),
                "can_clear_reviews": str(self.can_clear_reviews).lower(),
                "can_move_branches": str(self.can_move_branches).lower(),
                "bypasses_relay_aegis": str(self.bypasses_relay_aegis).lower(),
                "autonomous_coding_allowed": str(self.autonomous_coding_allowed).lower(),
                "known_authorities": ",".join(self.known_authorities),
            },
        )


DEEPSEEK_DIRECT_MODEL = "deepseek-chat"
DEEPSEEK_DIRECT_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_CONTEXT_BUDGET = 65536
DEEPSEEK_PROMPT_PAYLOAD_BUDGET = 57344


def deepseek_candidate_route_presets() -> tuple[ModelCandidateRoutePreset, ...]:
    """Return direct-provider DeepSeek candidate presets without creating live calls."""
    shared = {
        "provider_name": "deepseek",
        "dispatch_model": DEEPSEEK_DIRECT_MODEL,
        "api_mode": "direct",
        "trust_state": "candidate",
        "requires_external_review": True,
        "external_review_status": "pending",
        "direct_api_endpoint": DEEPSEEK_DIRECT_ENDPOINT,
        "context_budget": DEEPSEEK_CONTEXT_BUDGET,
        "prompt_payload_budget": DEEPSEEK_PROMPT_PAYLOAD_BUDGET,
        "allowed_task_types": ("verify", "explain"),
        "blocked_task_types": (
            "build",
            "review",
            "release",
            "destructive",
            "branch_movement",
            "review_clearance",
            "autonomous_coding",
        ),
        "max_risk_tier": 1,
        "q_mode_flat": True,
        "can_clear_reviews": False,
        "can_move_branches": False,
        "bypasses_relay_aegis": False,
        "autonomous_coding_allowed": False,
        "known_authorities": ("deepseek-official-endpoint", "direct-api-only"),
    }
    return (
        ModelCandidateRoutePreset(
            **shared,
            variant_label="deepseek-v4-pro",
            lane="default_quality",
            capability_tier="candidate-quality",
        ),
        ModelCandidateRoutePreset(
            **shared,
            variant_label="deepseek-v4-flash",
            lane="fast",
            capability_tier="candidate-fast",
        ),
    )


def deepseek_candidate_metadata_preset(lane: str = "default_quality") -> ModelHarnessMetadata:
    """Return Model Harness metadata for a named DeepSeek direct candidate lane."""
    for preset in deepseek_candidate_route_presets():
        if preset.lane == lane:
            return preset.to_metadata()
    raise ModelAdapterConfigError(f"Unknown DeepSeek candidate lane: {lane}")


@dataclass(frozen=True)
class ModelRouteMetadataBinding:
    """Provider-neutral route/capability/budget snapshot for Relay evidence."""

    provider_name: str
    model_name: str
    capability_tier: str
    route_risk_tier: int
    route_cost_posture: str
    route_latency_posture: str
    context_budget: int
    prompt_payload_budget: int
    trust_state: str
    requires_external_review: bool
    prompt_payload_status: str | None = None
    prompt_payload_estimated_tokens: int | None = None
    prompt_payload_budget_percent: float | None = None
    prompt_payload_growth_tokens: int | None = None
    prompt_payload_growth_percent: float | None = None

    def __post_init__(self) -> None:
        if self.route_risk_tier < 0:
            raise ModelAdapterConfigError("route_risk_tier must be non-negative")
        if self.context_budget < 0:
            raise ModelAdapterConfigError("context_budget must be non-negative")
        if self.prompt_payload_budget < 0:
            raise ModelAdapterConfigError("prompt_payload_budget must be non-negative")

    def to_dict(self) -> dict[str, object]:
        """Return a stable, serializable shape for Relay/Bifrost evidence."""
        return {
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "capability_tier": self.capability_tier,
            "route_risk_tier": self.route_risk_tier,
            "route_cost_posture": self.route_cost_posture,
            "route_latency_posture": self.route_latency_posture,
            "context_budget": self.context_budget,
            "prompt_payload_budget": self.prompt_payload_budget,
            "trust_state": self.trust_state,
            "requires_external_review": self.requires_external_review,
            "prompt_payload_status": self.prompt_payload_status,
            "prompt_payload_estimated_tokens": self.prompt_payload_estimated_tokens,
            "prompt_payload_budget_percent": self.prompt_payload_budget_percent,
            "prompt_payload_growth_tokens": self.prompt_payload_growth_tokens,
            "prompt_payload_growth_percent": self.prompt_payload_growth_percent,
        }


def _metadata_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def bind_model_route_metadata(
    adapter_metadata: ModelHarnessMetadata,
    *,
    route_risk_tier: int,
    route_cost_posture: Any,
    route_latency_posture: Any,
    payload_snapshot: Any | None = None,
) -> ModelRouteMetadataBinding:
    """Bind adapter capability metadata to a Relay route without vendor branching."""
    return ModelRouteMetadataBinding(
        provider_name=adapter_metadata.provider_name,
        model_name=adapter_metadata.model_name,
        capability_tier=adapter_metadata.capability_tier,
        route_risk_tier=route_risk_tier,
        route_cost_posture=_metadata_value(route_cost_posture),
        route_latency_posture=_metadata_value(route_latency_posture),
        context_budget=adapter_metadata.context_budget,
        prompt_payload_budget=adapter_metadata.prompt_payload_budget,
        trust_state=adapter_metadata.trust_state,
        requires_external_review=adapter_metadata.requires_external_review,
        prompt_payload_status=(
            _metadata_value(payload_snapshot.status)
            if payload_snapshot is not None and hasattr(payload_snapshot, "status")
            else None
        ),
        prompt_payload_estimated_tokens=(
            payload_snapshot.estimated_tokens if payload_snapshot is not None else None
        ),
        prompt_payload_budget_percent=(
            payload_snapshot.budget_percent if payload_snapshot is not None else None
        ),
        prompt_payload_growth_tokens=(
            payload_snapshot.growth_tokens if payload_snapshot is not None else None
        ),
        prompt_payload_growth_percent=(
            payload_snapshot.growth_percent if payload_snapshot is not None else None
        ),
    )


class ModelAdapter(Protocol):
    """Callable boundary: receive approved payload text, return model text."""

    def __call__(self, payload: str) -> str: ...

    @property
    def metadata(self) -> ModelHarnessMetadata:
        """Return Model Harness metadata for this adapter."""
        ...


@dataclass(frozen=True)
class ModelAdapterConfig:
    """Environment-backed configuration for a live provider adapter."""

    provider: str
    model: str
    api_key_env_var: str

    def require_api_key(self, env: Mapping[str, str] | None = None) -> str:
        """Return the configured API key or raise before any live call."""
        source = os.environ if env is None else env
        key = source.get(self.api_key_env_var, "").strip()
        if not key:
            raise ModelAdapterConfigError(
                f"Missing required API key environment variable: {self.api_key_env_var}"
            )
        return key


class FakeModelAdapter:
    """Deterministic test adapter that records payload-only calls."""

    def __init__(
        self,
        response: str = "fake model response",
        metadata: ModelHarnessMetadata | None = None,
    ) -> None:
        self.response = response
        self.received_payloads: list[str] = []
        self._metadata = metadata or ModelHarnessMetadata(
            provider_name="fake",
            model_name="fake-model",
            capability_tier="test",
            context_budget=4096,
            prompt_payload_budget=2048,
            trust_state="test",
            requires_external_review=False,
        )

    def __call__(self, payload: str) -> str:
        self.received_payloads.append(payload)
        return self.response

    @property
    def metadata(self) -> ModelHarnessMetadata:
        return self._metadata


class MissingAdapterError(RuntimeError):
    """Raised when no adapter is registered for a lane role or model before any call."""


class AdapterRegistry:
    """Provider-neutral registry: register adapters by exact model or role default.

    Each registration method returns a new registry instance (immutable builder).
    Resolution order: exact model match first, role default second, error if neither.
    """

    def __init__(
        self,
        by_model: Mapping[str, ModelAdapter] | None = None,
        by_role: Mapping[ModelRole, ModelAdapter] | None = None,
    ) -> None:
        self._by_model: Mapping[str, ModelAdapter] = MappingProxyType(dict(by_model or {}))
        self._by_role: Mapping[ModelRole, ModelAdapter] = MappingProxyType(dict(by_role or {}))

    def register_model(self, model: str, adapter: ModelAdapter) -> AdapterRegistry:
        """Return new registry with an exact-model adapter registered."""
        return AdapterRegistry(
            by_model={**self._by_model, model: adapter},
            by_role=dict(self._by_role),
        )

    def register_role_default(self, role: ModelRole, adapter: ModelAdapter) -> AdapterRegistry:
        """Return new registry with a role-default adapter registered."""
        return AdapterRegistry(
            by_model=dict(self._by_model),
            by_role={**self._by_role, role: adapter},
        )

    def resolve(self, role: ModelRole, model: str) -> ModelAdapter:
        """Return the adapter for model (exact) or role (default), or raise MissingAdapterError."""
        if model in self._by_model:
            return self._by_model[model]
        if role in self._by_role:
            return self._by_role[role]
        raise MissingAdapterError(
            f"No adapter registered for model={model!r} or role={role.value!r}"
        )


class EnvConfiguredModelAdapter:
    """Env-safe wrapper for a future live provider transport.

    The transport is injected so this module has no vendor SDK dependency.
    Missing credentials fail before the transport is called.
    """

    def __init__(
        self,
        config: ModelAdapterConfig,
        transport: Callable[[str, ModelAdapterConfig, str], str],
        *,
        env: Mapping[str, str] | None = None,
        metadata: ModelHarnessMetadata | None = None,
    ) -> None:
        self.config = config
        self._transport = transport
        self._env = env
        self._metadata = metadata or ModelHarnessMetadata(
            provider_name=config.provider,
            model_name=config.model,
            capability_tier="standard",
            context_budget=4096,
            prompt_payload_budget=2048,
            trust_state="unknown",
            requires_external_review=False,
        )

    def __call__(self, payload: str) -> str:
        api_key = self.config.require_api_key(self._env)
        return self._transport(payload, self.config, api_key)

    @property
    def metadata(self) -> ModelHarnessMetadata:
        return self._metadata


@dataclass(frozen=True)
class HttpModelAdapterConfig:
    """Environment-backed configuration for an HTTP JSON provider adapter."""

    provider: str
    model: str
    api_key_env_var: str
    endpoint_url: str

    def require_api_key(self, env: Mapping[str, str] | None = None) -> str:
        """Return the configured API key or raise before any network call."""
        source = os.environ if env is None else env
        key = source.get(self.api_key_env_var, "").strip()
        if not key:
            raise ModelAdapterConfigError(
                f"Missing required API key environment variable: {self.api_key_env_var}"
            )
        return key

    def require_endpoint(self) -> str:
        """Return the configured endpoint URL or raise before any network call."""
        url = self.endpoint_url.strip()
        if not url:
            raise ModelAdapterConfigError(
                f"Missing required endpoint_url for provider={self.provider!r}"
            )
        return url


def _stdlib_http_post(
    payload: str,
    endpoint: str,
    provider: str,
    model: str,
    api_key: str,
) -> str:
    """POST approved payload to endpoint using only stdlib urllib. No SDK dependency."""
    body = json.dumps(
        {"provider": provider, "model": model, "input": payload}
    ).encode()
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        raw = resp.read().decode()
    decoded = json.loads(raw)
    if not isinstance(decoded, dict) or not isinstance(decoded.get("text"), str):
        raise ModelAdapterConfigError("HTTP JSON model adapter response missing text")
    return decoded["text"]


class HttpJsonModelAdapter:
    """HTTP JSON adapter for V0 Relay dispatch; validates config before any call.

    Accepts an injectable http_post for testing — no live network calls in tests.
    The request body carries only approved payload text, provider, and model name.
    API key is set as an Authorization header and never echoed into response/error text.
    """

    def __init__(
        self,
        config: HttpModelAdapterConfig,
        *,
        env: Mapping[str, str] | None = None,
        http_post: Callable[[str, str, str, str, str], str] | None = None,
        metadata: ModelHarnessMetadata | None = None,
    ) -> None:
        self._config = config
        self._env = env
        self._http_post = http_post if http_post is not None else _stdlib_http_post
        self._metadata = metadata or ModelHarnessMetadata(
            provider_name=config.provider,
            model_name=config.model,
            capability_tier="standard",
            context_budget=4096,
            prompt_payload_budget=2048,
            trust_state="unknown",
            requires_external_review=False,
        )

    def __call__(self, payload: str) -> str:
        api_key = self._config.require_api_key(self._env)
        endpoint = self._config.require_endpoint()
        return self._http_post(
            payload,
            endpoint,
            self._config.provider,
            self._config.model,
            api_key,
        )

    @property
    def metadata(self) -> ModelHarnessMetadata:
        return self._metadata
