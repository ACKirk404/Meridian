"""Provider Balance / Usage domain model for Relay and the Model Harness.

Pure-Python, deterministic, dependency-free, provider-neutral. Owns
structured provider health, route kind, quota/credit state, token usage,
estimated spend label, cost-pressure state, selected-provider policy
state, and display-safe evidence refs.

The summary mapping produced by ``ProviderBalanceSummary.to_mapping()`` is
compatible with the Bifrost cockpit adapter
``bifrost.cockpit.provider_balance_view_from_summary`` (same keys, same
value contracts), but this module does **not** import Bifrost. Bifrost
remains a consumer of the summary mapping, not the owner of
provider-balance policy.

Hard rules enforced here:

- No network calls, no credentials, no account probing, no provider SDKs,
  no live model calls, no UI/Electron behavior, no shared-main writes.
- Unknown provider balances serialize as ``unknown`` / ``unavailable`` —
  never as ``ok`` / ``available`` / zero-cost by default.
- Cost pressure is bounded and deterministic; missing or invalid pressure
  falls back to ``UNKNOWN``.
- Raw prompt text, raw provider response text, credentials, filesystem
  paths, branch/worktree movement text, and arbitrary free-form blocker
  prose are rejected or redacted to a fixed sentinel before they can
  reach the serialized summary.
- Evidence refs are structured short refs (``kind:id`` form recommended).
  Unsafe or oversized refs are redacted to a fixed sentinel.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


# ---------------------------------------------------------------------------
# Display-safety constants
# ---------------------------------------------------------------------------

_UNSAFE_DISPLAY_MARKERS = (
    "raw_prompt",
    "raw_transcript",
    "raw_response",
    "raw_provider_response",
    "raw_context",
    "provider_response",
    "provider_request",
    "free_form_context",
    "serialized_prompt",
    "model_payload",
    "transcript:",
    "conversation:",
    "secret",
    "api_key",
    "apikey",
    "bearer ",
    "authorization:",
    "credential",
    "password",
    "process_id",
    "git checkout",
    "git rebase",
    "git merge",
    "git reset",
    "git push",
    "worktree",
    "branch_movement",
)

_UNSAFE_DISPLAY_REDACTION = "unsafe_metadata_redacted"
_UNSAFE_EVIDENCE_REDACTION = "unsafe_evidence_ref_redacted"

_MAX_LABEL_LENGTH = 96
_MAX_NOTES_LENGTH = 160
_MAX_EVIDENCE_REF_LENGTH = 96
_MAX_PROVIDER_ID_LENGTH = 48
_MAX_EVIDENCE_REFS_PER_RECORD = 16

_PROVIDER_ID_ALLOWED_EXTRA = ("-", "_", ".")

# Absolute-path prefixes that, if embedded in a display string, mean the
# string is leaking a real filesystem location. Matched case-insensitively
# so case-variant Unix paths (``/users/...`` as well as ``/Users/...``)
# trip the check.
_FILESYSTEM_PATH_PREFIXES = (
    "/tmp/",
    "/etc/",
    "/var/",
    "/usr/",
    "/home/",
    "/Users/",
    "/opt/",
    "/Library/",
    "/Volumes/",
    "/proc/",
    "/dev/",
    "/root/",
    "/mnt/",
    "/srv/",
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ProviderHealth(Enum):
    """Coarse provider health state.

    ``UNKNOWN`` means we have no live signal — the fail-safe default.
    ``UNAVAILABLE`` means we have evidence the provider cannot serve.
    """

    UNKNOWN = "unknown"
    OK = "ok"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    UNAVAILABLE = "unavailable"


class ProviderRouteKind(Enum):
    """Provider-neutral route family.

    Covers direct provider routes (Claude, OpenAI, DeepSeek), aggregators
    (OpenRouter and similar reseller front-ends), and local-only adapters.
    """

    UNKNOWN = "unknown"
    DIRECT = "direct"
    AGGREGATOR = "aggregator"
    LOCAL = "local"


class ProviderCostPressure(Enum):
    """Bounded cost-pressure ladder.

    ``UNKNOWN`` is fail-safe (no live signal). ``NONE`` means we have a
    live signal and no pressure was detected. The remaining values form an
    ordered ladder; ``DEGRADED`` is reserved for aggregator-level cost
    visibility loss.
    """

    UNKNOWN = "unknown"
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"
    DEGRADED = "degraded"


class ProviderQuotaState(Enum):
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    LIMITED = "limited"
    METERED = "metered"
    EXHAUSTED = "exhausted"
    UNAVAILABLE = "unavailable"


class ProviderCreditStatus(Enum):
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    LIMITED = "limited"
    EXHAUSTED = "exhausted"
    UNAVAILABLE = "unavailable"


class ProviderTrustState(Enum):
    """Trust class for the provider/model relationship.

    ``CANDIDATE`` is used by DeepSeek-style candidate-only metadata.
    ``AGGREGATOR`` covers OpenRouter-style reseller routes. ``LOCAL``
    covers local adapters.
    """

    UNKNOWN = "unknown"
    TRUSTED = "trusted"
    CANDIDATE = "candidate"
    AGGREGATOR = "aggregator"
    LOCAL = "local"


class ProviderPolicyState(Enum):
    """Summary-level routing policy state."""

    OK = "ok"
    WARNING = "warning"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class ProviderRoutingOwner(Enum):
    """Which subsystem owns the current routing decision."""

    UNKNOWN = "unknown"
    RELAY = "Relay"
    BIFROST = "Bifrost"
    AEGIS = "Aegis"


# ---------------------------------------------------------------------------
# Validation error
# ---------------------------------------------------------------------------

class ProviderBalanceValidationError(ValueError):
    """Raised when a ProviderBalanceSnapshot or Summary fails validation."""


# ---------------------------------------------------------------------------
# Safety helpers
# ---------------------------------------------------------------------------

def _contains_unsafe_marker(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in _UNSAFE_DISPLAY_MARKERS)


def _looks_like_filesystem_path(value: str) -> bool:
    """Detect raw filesystem path content unsuitable for display surfaces.

    Display labels and notes must never carry filesystem paths — they leak
    deployment topology, may embed user names, worktree locations, or
    credential file paths, and create indirect cross-host attack surface.

    Rejects: Windows drive-letter starts (``C:\\...`` / ``C:/...``), any
    string containing a backslash (legitimate display content never does),
    any POSIX absolute path (leading ``/``), and any string with a common
    absolute-path prefix embedded mid-text (``/tmp/``, ``/etc/``, ``/Users/``,
    etc., case-insensitive).

    Legitimate slash usage in non-path contexts (e.g. ``$5/day``,
    ``3/4 capacity``) is preserved — only path-shaped content is rejected.
    """
    if not value:
        return False
    if (
        len(value) >= 3
        and value[0].isalpha()
        and value[1] == ":"
        and value[2] in ("\\", "/")
    ):
        return True
    if "\\" in value:
        return True
    if value.startswith("/"):
        return True
    lowered = value.lower()
    for prefix in _FILESYSTEM_PATH_PREFIXES:
        if prefix.lower() in lowered:
            return True
    return False


def _is_safe_display_value(value: str) -> bool:
    if "\n" in value or "\r" in value or "\t" in value:
        return False
    if _contains_unsafe_marker(value):
        return False
    if _looks_like_filesystem_path(value):
        return False
    return True


def safe_display_label(value: object, *, max_length: int = _MAX_LABEL_LENGTH) -> str:
    """Return a display-safe label, or the redaction sentinel if unsafe.

    Empty/None inputs collapse to ``""``. Oversized, marker-bearing, or
    filesystem-path-shaped inputs become :data:`_UNSAFE_DISPLAY_REDACTION`.

    Filesystem-path detection is enforced both here (explicit guard) and
    inside :func:`_is_safe_display_value` so the contract holds even if
    one path is altered in the future.
    """
    if value is None:
        return ""
    text = str(value)
    if not text:
        return ""
    if len(text) > max_length:
        return _UNSAFE_DISPLAY_REDACTION
    if _looks_like_filesystem_path(text):
        return _UNSAFE_DISPLAY_REDACTION
    if not _is_safe_display_value(text):
        return _UNSAFE_DISPLAY_REDACTION
    return text


def safe_display_notes(value: object) -> str:
    """Display-safe short notes field. Mirrors :func:`safe_display_label`
    with a larger length cap for short multi-clause notes.

    Like :func:`safe_display_label`, filesystem-path-shaped inputs are
    redacted both via an explicit guard here and via
    :func:`_is_safe_display_value`.
    """
    if value is None:
        return ""
    text = str(value)
    if not text:
        return ""
    if len(text) > _MAX_NOTES_LENGTH:
        return _UNSAFE_DISPLAY_REDACTION
    if _looks_like_filesystem_path(text):
        return _UNSAFE_DISPLAY_REDACTION
    if not _is_safe_display_value(text):
        return _UNSAFE_DISPLAY_REDACTION
    return text


def safe_provider_id(value: object) -> str:
    """Display-safe provider id, restricted to a slug character set.

    Returns ``""`` for empty/None input. Returns the redaction sentinel
    when the value contains unsafe markers, path separators, whitespace,
    or characters outside ``[a-zA-Z0-9 - _ .]``.
    """
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if len(text) > _MAX_PROVIDER_ID_LENGTH:
        return _UNSAFE_DISPLAY_REDACTION
    if not _is_safe_display_value(text):
        return _UNSAFE_DISPLAY_REDACTION
    for ch in text:
        if not (ch.isalnum() or ch in _PROVIDER_ID_ALLOWED_EXTRA):
            return _UNSAFE_DISPLAY_REDACTION
    return text


def safe_evidence_ref(value: object) -> str | None:
    """Display-safe evidence ref, or ``None`` if the input is empty.

    Returns the :data:`_UNSAFE_EVIDENCE_REDACTION` sentinel for refs that
    are oversized, contain unsafe markers, contain path separators
    (``/`` or ``\\``), or contain whitespace. Refs are expected to be in
    ``kind:id`` form (e.g. ``adapter:claude``) but bare slugs are also
    accepted.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) > _MAX_EVIDENCE_REF_LENGTH:
        return _UNSAFE_EVIDENCE_REDACTION
    if not _is_safe_display_value(text):
        return _UNSAFE_EVIDENCE_REDACTION
    if "/" in text or "\\" in text:
        return _UNSAFE_EVIDENCE_REDACTION
    if any(ch.isspace() for ch in text):
        return _UNSAFE_EVIDENCE_REDACTION
    return text


def _normalize_evidence_refs(refs: Iterable[object] | None) -> tuple[str, ...]:
    if not refs:
        return ()
    out: list[str] = []
    for ref in refs:
        safe = safe_evidence_ref(ref)
        if safe is None:
            continue
        out.append(safe)
        if len(out) >= _MAX_EVIDENCE_REFS_PER_RECORD:
            break
    return tuple(out)


def _coerce_int(
    value: object,
    default: int = 0,
    *,
    allow_negative: bool = False,
) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    try:
        result = int(value)
    except (TypeError, ValueError):
        return default
    if not allow_negative and result < 0:
        return default
    return result


def _coerce_float(
    value: object,
    default: float = 0.0,
    *,
    clamp_percent: bool = False,
) -> float:
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if clamp_percent:
        if result < 0.0:
            return 0.0
        if result > 100.0:
            return 100.0
    return result


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProviderBalanceSnapshot:
    """Deterministic per-provider balance / usage / health snapshot.

    Frozen at construction. Fail-safe defaults are ``unknown`` /
    ``unavailable``. Display-only: must never carry raw prompt/response
    text, credentials, filesystem paths, or branch/worktree movement
    prose. Direct construction with unsafe values raises
    :class:`ProviderBalanceValidationError`; callers that need defensive
    redaction should use :func:`build_provider_balance_snapshot`.
    """

    provider_id: str
    display_name: str = ""
    model_name: str = ""
    trust_state: ProviderTrustState = ProviderTrustState.UNKNOWN
    health: ProviderHealth = ProviderHealth.UNKNOWN
    route_kind: ProviderRouteKind = ProviderRouteKind.UNKNOWN
    context_budget_tokens: int = 0
    prompt_budget_tokens: int = 0
    current_prompt_tokens: int = 0
    prompt_budget_percent: float = 0.0
    prompt_delta_tokens: int = 0
    cost_pressure: ProviderCostPressure = ProviderCostPressure.UNKNOWN
    quota_state: ProviderQuotaState = ProviderQuotaState.UNKNOWN
    remaining_credit_label: str = ""
    credit_status: ProviderCreditStatus = ProviderCreditStatus.UNKNOWN
    estimated_spend_label: str = ""
    notes: str = ""
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.provider_id, str) or not self.provider_id:
            raise ProviderBalanceValidationError(
                "provider_id must be a non-empty string"
            )
        if safe_provider_id(self.provider_id) != self.provider_id:
            raise ProviderBalanceValidationError(
                "provider_id is not display-safe"
            )
        if not isinstance(self.trust_state, ProviderTrustState):
            raise ProviderBalanceValidationError(
                "trust_state must be a ProviderTrustState"
            )
        if not isinstance(self.health, ProviderHealth):
            raise ProviderBalanceValidationError(
                "health must be a ProviderHealth"
            )
        if not isinstance(self.route_kind, ProviderRouteKind):
            raise ProviderBalanceValidationError(
                "route_kind must be a ProviderRouteKind"
            )
        if not isinstance(self.cost_pressure, ProviderCostPressure):
            raise ProviderBalanceValidationError(
                "cost_pressure must be a ProviderCostPressure"
            )
        if not isinstance(self.quota_state, ProviderQuotaState):
            raise ProviderBalanceValidationError(
                "quota_state must be a ProviderQuotaState"
            )
        if not isinstance(self.credit_status, ProviderCreditStatus):
            raise ProviderBalanceValidationError(
                "credit_status must be a ProviderCreditStatus"
            )
        for name, val in (
            ("context_budget_tokens", self.context_budget_tokens),
            ("prompt_budget_tokens", self.prompt_budget_tokens),
            ("current_prompt_tokens", self.current_prompt_tokens),
        ):
            if not isinstance(val, int) or isinstance(val, bool):
                raise ProviderBalanceValidationError(
                    f"{name} must be an int"
                )
            if val < 0:
                raise ProviderBalanceValidationError(
                    f"{name} must be non-negative"
                )
        if not isinstance(self.prompt_delta_tokens, int) or isinstance(
            self.prompt_delta_tokens, bool
        ):
            raise ProviderBalanceValidationError(
                "prompt_delta_tokens must be an int"
            )
        if not isinstance(self.prompt_budget_percent, (int, float)) or isinstance(
            self.prompt_budget_percent, bool
        ):
            raise ProviderBalanceValidationError(
                "prompt_budget_percent must be numeric"
            )
        if self.prompt_budget_percent < 0.0 or self.prompt_budget_percent > 100.0:
            raise ProviderBalanceValidationError(
                "prompt_budget_percent must lie within [0, 100]"
            )
        for name, val in (
            ("display_name", self.display_name),
            ("model_name", self.model_name),
            ("remaining_credit_label", self.remaining_credit_label),
            ("estimated_spend_label", self.estimated_spend_label),
        ):
            if not isinstance(val, str):
                raise ProviderBalanceValidationError(
                    f"{name} must be a string"
                )
            if val and safe_display_label(val) != val:
                raise ProviderBalanceValidationError(
                    f"{name} is not display-safe"
                )
        if not isinstance(self.notes, str):
            raise ProviderBalanceValidationError("notes must be a string")
        if self.notes and safe_display_notes(self.notes) != self.notes:
            raise ProviderBalanceValidationError("notes is not display-safe")
        if not isinstance(self.evidence_refs, tuple):
            raise ProviderBalanceValidationError(
                "evidence_refs must be a tuple"
            )
        if len(self.evidence_refs) > _MAX_EVIDENCE_REFS_PER_RECORD:
            raise ProviderBalanceValidationError(
                "evidence_refs exceeds per-record cap"
            )
        for ref in self.evidence_refs:
            if not isinstance(ref, str) or not ref:
                raise ProviderBalanceValidationError(
                    "evidence_refs entries must be non-empty strings"
                )
            if safe_evidence_ref(ref) != ref:
                raise ProviderBalanceValidationError(
                    "evidence_refs entry is not display-safe"
                )

    def to_mapping(self) -> dict[str, object]:
        """Return a per-provider mapping shaped for the Bifrost adapter.

        Keys match exactly what
        ``bifrost.cockpit.provider_balance_view_from_summary`` consumes
        via its per-provider projection.
        """
        return {
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "model_name": self.model_name,
            "trust_state": self.trust_state.value,
            "health": self.health.value,
            "route_kind": self.route_kind.value,
            "context_budget_tokens": self.context_budget_tokens,
            "prompt_budget_tokens": self.prompt_budget_tokens,
            "current_prompt_tokens": self.current_prompt_tokens,
            "prompt_budget_percent": float(self.prompt_budget_percent),
            "prompt_delta_tokens": self.prompt_delta_tokens,
            "cost_pressure": self.cost_pressure.value,
            "quota_state": self.quota_state.value,
            "remaining_credit_label": self.remaining_credit_label,
            "credit_status": self.credit_status.value,
            "estimated_spend_label": self.estimated_spend_label,
            "notes": self.notes,
            "evidence_refs": list(self.evidence_refs),
        }


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProviderBalanceSummary:
    """Combined deterministic provider balance summary.

    Frozen at construction. Snapshot order is deterministic via
    :meth:`ordered_snapshots` — when a ``selected_provider`` is set its
    snapshot appears first and the rest follow in alphabetical
    ``provider_id`` order. With no selection, snapshots are returned in
    alphabetical order.
    """

    snapshots: tuple[ProviderBalanceSnapshot, ...] = ()
    selected_provider: str = ""
    routing_owner: ProviderRoutingOwner = ProviderRoutingOwner.UNKNOWN
    policy_state: ProviderPolicyState = ProviderPolicyState.OK
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.snapshots, tuple):
            raise ProviderBalanceValidationError(
                "snapshots must be a tuple"
            )
        seen_ids: set[str] = set()
        for snap in self.snapshots:
            if not isinstance(snap, ProviderBalanceSnapshot):
                raise ProviderBalanceValidationError(
                    "snapshots entries must be ProviderBalanceSnapshot"
                )
            if snap.provider_id in seen_ids:
                raise ProviderBalanceValidationError(
                    "duplicate provider_id in snapshots"
                )
            seen_ids.add(snap.provider_id)

        if not isinstance(self.selected_provider, str):
            raise ProviderBalanceValidationError(
                "selected_provider must be a string"
            )
        if self.selected_provider:
            if safe_provider_id(self.selected_provider) != self.selected_provider:
                raise ProviderBalanceValidationError(
                    "selected_provider is not display-safe"
                )
            if self.selected_provider not in seen_ids:
                raise ProviderBalanceValidationError(
                    "selected_provider is not present in snapshots"
                )

        if not isinstance(self.routing_owner, ProviderRoutingOwner):
            raise ProviderBalanceValidationError(
                "routing_owner must be a ProviderRoutingOwner"
            )
        if not isinstance(self.policy_state, ProviderPolicyState):
            raise ProviderBalanceValidationError(
                "policy_state must be a ProviderPolicyState"
            )

        if not isinstance(self.evidence_refs, tuple):
            raise ProviderBalanceValidationError(
                "evidence_refs must be a tuple"
            )
        if len(self.evidence_refs) > _MAX_EVIDENCE_REFS_PER_RECORD:
            raise ProviderBalanceValidationError(
                "evidence_refs exceeds per-record cap"
            )
        for ref in self.evidence_refs:
            if not isinstance(ref, str) or not ref:
                raise ProviderBalanceValidationError(
                    "evidence_refs entries must be non-empty strings"
                )
            if safe_evidence_ref(ref) != ref:
                raise ProviderBalanceValidationError(
                    "evidence_refs entry is not display-safe"
                )

    def ordered_snapshots(self) -> tuple[ProviderBalanceSnapshot, ...]:
        """Return snapshots in deterministic display order.

        Selected provider first (if set), then remaining snapshots in
        alphabetical ``provider_id`` order.
        """
        if not self.snapshots:
            return ()
        if not self.selected_provider:
            return tuple(sorted(self.snapshots, key=lambda s: s.provider_id))
        selected: ProviderBalanceSnapshot | None = None
        rest: list[ProviderBalanceSnapshot] = []
        for snap in self.snapshots:
            if snap.provider_id == self.selected_provider and selected is None:
                selected = snap
            else:
                rest.append(snap)
        rest_sorted = sorted(rest, key=lambda s: s.provider_id)
        if selected is None:
            return tuple(rest_sorted)
        return (selected,) + tuple(rest_sorted)

    def to_mapping(self) -> dict[str, object]:
        """Return a summary mapping shaped for the Bifrost adapter.

        Compatible with ``bifrost.cockpit.provider_balance_view_from_summary``.
        Deterministic and side-effect-free. Providers are emitted via
        :meth:`ordered_snapshots`, so callers always see the selected
        provider in the first position.
        """
        return {
            "providers": [snap.to_mapping() for snap in self.ordered_snapshots()],
            "selected_provider": self.selected_provider,
            "routing_owner": self.routing_owner.value,
            "policy_state": self.policy_state.value,
            "evidence_refs": list(self.evidence_refs),
        }


# ---------------------------------------------------------------------------
# Constructor helpers
# ---------------------------------------------------------------------------

def unknown_provider_snapshot(
    provider_id: str,
    *,
    display_name: str = "",
    model_name: str = "",
) -> ProviderBalanceSnapshot:
    """Return a fail-safe ``unknown`` / ``unavailable`` snapshot.

    Use when no live balance data is available for a provider. Every
    state defaults to ``unknown``; numeric fields default to zero. The
    snapshot is constructable, queryable, and serializable, but it never
    reports ``ok`` or ``available`` so consumers cannot mistake absence
    of data for a healthy provider.
    """
    if safe_provider_id(provider_id) != provider_id:
        raise ProviderBalanceValidationError(
            "provider_id is not display-safe"
        )
    return ProviderBalanceSnapshot(
        provider_id=provider_id,
        display_name=safe_display_label(display_name),
        model_name=safe_display_label(model_name),
        trust_state=ProviderTrustState.UNKNOWN,
        health=ProviderHealth.UNKNOWN,
        route_kind=ProviderRouteKind.UNKNOWN,
        context_budget_tokens=0,
        prompt_budget_tokens=0,
        current_prompt_tokens=0,
        prompt_budget_percent=0.0,
        prompt_delta_tokens=0,
        cost_pressure=ProviderCostPressure.UNKNOWN,
        quota_state=ProviderQuotaState.UNKNOWN,
        remaining_credit_label="",
        credit_status=ProviderCreditStatus.UNKNOWN,
        estimated_spend_label="",
        notes="",
        evidence_refs=(),
    )


def build_provider_balance_snapshot(
    provider_id: str,
    *,
    display_name: object = "",
    model_name: object = "",
    trust_state: ProviderTrustState = ProviderTrustState.UNKNOWN,
    health: ProviderHealth = ProviderHealth.UNKNOWN,
    route_kind: ProviderRouteKind = ProviderRouteKind.UNKNOWN,
    context_budget_tokens: object = 0,
    prompt_budget_tokens: object = 0,
    current_prompt_tokens: object = 0,
    prompt_budget_percent: object = 0.0,
    prompt_delta_tokens: object = 0,
    cost_pressure: ProviderCostPressure = ProviderCostPressure.UNKNOWN,
    quota_state: ProviderQuotaState = ProviderQuotaState.UNKNOWN,
    remaining_credit_label: object = "",
    credit_status: ProviderCreditStatus = ProviderCreditStatus.UNKNOWN,
    estimated_spend_label: object = "",
    notes: object = "",
    evidence_refs: Iterable[object] | None = None,
) -> ProviderBalanceSnapshot:
    """Construct a snapshot with defensive coercion and redaction.

    Numeric inputs are coerced via :func:`_coerce_int` / :func:`_coerce_float`
    with fail-safe defaults; non-numeric or negative balances collapse to
    zero, percent values clamp to ``[0, 100]``. String labels and notes
    are routed through :func:`safe_display_label` / :func:`safe_display_notes`,
    so unsafe inputs become the redaction sentinel instead of raising.
    Evidence refs are normalized through :func:`_normalize_evidence_refs`.

    ``provider_id`` is **not** silently redacted — an unsafe provider id
    raises, because a routing identity must never be invented or hidden.
    """
    return ProviderBalanceSnapshot(
        provider_id=provider_id,
        display_name=safe_display_label(display_name),
        model_name=safe_display_label(model_name),
        trust_state=trust_state,
        health=health,
        route_kind=route_kind,
        context_budget_tokens=_coerce_int(context_budget_tokens),
        prompt_budget_tokens=_coerce_int(prompt_budget_tokens),
        current_prompt_tokens=_coerce_int(current_prompt_tokens),
        prompt_budget_percent=_coerce_float(
            prompt_budget_percent, clamp_percent=True
        ),
        prompt_delta_tokens=_coerce_int(prompt_delta_tokens, allow_negative=True),
        cost_pressure=cost_pressure,
        quota_state=quota_state,
        remaining_credit_label=safe_display_label(remaining_credit_label),
        credit_status=credit_status,
        estimated_spend_label=safe_display_label(estimated_spend_label),
        notes=safe_display_notes(notes),
        evidence_refs=_normalize_evidence_refs(evidence_refs),
    )


def build_provider_balance_summary(
    snapshots: Iterable[ProviderBalanceSnapshot] = (),
    *,
    selected_provider: str = "",
    routing_owner: ProviderRoutingOwner = ProviderRoutingOwner.UNKNOWN,
    policy_state: ProviderPolicyState = ProviderPolicyState.OK,
    evidence_refs: Iterable[object] | None = None,
) -> ProviderBalanceSummary:
    """Construct a summary with defensive evidence-ref normalization."""
    return ProviderBalanceSummary(
        snapshots=tuple(snapshots),
        selected_provider=selected_provider,
        routing_owner=routing_owner,
        policy_state=policy_state,
        evidence_refs=_normalize_evidence_refs(evidence_refs),
    )


__all__ = (
    "ProviderHealth",
    "ProviderRouteKind",
    "ProviderCostPressure",
    "ProviderQuotaState",
    "ProviderCreditStatus",
    "ProviderTrustState",
    "ProviderPolicyState",
    "ProviderRoutingOwner",
    "ProviderBalanceValidationError",
    "ProviderBalanceSnapshot",
    "ProviderBalanceSummary",
    "safe_display_label",
    "safe_display_notes",
    "safe_provider_id",
    "safe_evidence_ref",
    "unknown_provider_snapshot",
    "build_provider_balance_snapshot",
    "build_provider_balance_summary",
)
