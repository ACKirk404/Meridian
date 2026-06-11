"""Pure dry-run contracts for V2.5 tool and browser evidence previews.

The builders in this module describe planned work and already-collected
browser evidence in deterministic, display-safe records. They do not perform
IO, launch browsers, call tools, or execute any external mutation.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable
from urllib.parse import urlsplit


class DryRunSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DryRunReviewState(Enum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


class VisualDiffStatus(Enum):
    NOT_PROVIDED = "not_provided"
    MATCH = "match"
    CHANGED = "changed"
    BLOCKED = "blocked"


_SAFE_NAVIGATION_SCHEMES: frozenset[str] = frozenset({"http", "https", "about"})
_UNSAFE_NAVIGATION_SCHEMES: frozenset[str] = frozenset(
    {"data", "file", "ftp", "javascript", "mailto"}
)


@dataclass(frozen=True)
class ToolActionInput:
    tool_name: str
    action_label: str
    target_ref: str = ""
    mutation_kind: str = "read"
    reversible: bool = True
    rollback_plan_ref: str = ""


@dataclass(frozen=True)
class ToolFailureInput:
    route_id: str
    failure_kind: str
    severity: DryRunSeverity | str = DryRunSeverity.ERROR
    retryable: bool = False
    next_route: str = "manual_review"
    evidence_ref: str = ""


@dataclass(frozen=True)
class BrowserNavigationInput:
    request_id: str
    requested_url: str
    user_initiated: bool = True


@dataclass(frozen=True)
class ScreenshotEvidenceInput:
    evidence_ref: str
    thumbnail_ref: str = ""
    viewport_label: str = "desktop"


@dataclass(frozen=True)
class VisualDiffInput:
    baseline_ref: str
    candidate_ref: str
    diff_ref: str
    changed_region_count: int = 0
    threshold: float = 0.0


@dataclass(frozen=True)
class SafeNavigationPolicySummary:
    status: DryRunReviewState
    allowed_schemes: tuple[str, ...]
    blocked_schemes: tuple[str, ...]
    warning_count: int
    warnings: tuple[str, ...]

    def to_display_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "allowed_schemes": tuple(
                _safe_label(scheme, "scheme") for scheme in self.allowed_schemes
            ),
            "blocked_schemes": tuple(
                _safe_label(scheme, "scheme") for scheme in self.blocked_schemes
            ),
            "warning_count": self.warning_count,
            "warnings": tuple(_safe_label(warning, "navigation_warning") for warning in self.warnings),
        }


@dataclass(frozen=True)
class ReversibleActionPlan:
    action_ref: str
    tool_ref: str
    action_label: str
    target_ref: str
    mutation_kind: str
    reversible: bool
    rollback_plan_ref: str
    would_execute: bool = False
    external_mutation_blocked: bool = True

    def to_display_dict(self) -> dict[str, object]:
        return {
            "action_ref": _safe_ref(self.action_ref, "action:unsafe"),
            "tool_ref": _safe_ref(self.tool_ref, "tool:unsafe"),
            "action_label": _safe_label(self.action_label, "planned action"),
            "target_ref": _safe_ref(self.target_ref, "target:unsafe") if self.target_ref else "",
            "mutation_kind": _safe_label(self.mutation_kind, "mutation"),
            "reversible": self.reversible,
            "rollback_plan_ref": (
                _safe_ref(self.rollback_plan_ref, "rollback:unsafe")
                if self.rollback_plan_ref
                else ""
            ),
            "would_execute": self.would_execute,
            "external_mutation_blocked": self.external_mutation_blocked,
        }


@dataclass(frozen=True)
class ToolFailureRoutingRecord:
    route_ref: str
    failure_kind: str
    severity: DryRunSeverity
    retryable: bool
    next_route: str
    evidence_ref: str

    def to_display_dict(self) -> dict[str, object]:
        return {
            "route_ref": _safe_ref(self.route_ref, "failure-route:unsafe"),
            "failure_kind": _safe_label(self.failure_kind, "tool_failure"),
            "severity": self.severity.value,
            "retryable": self.retryable,
            "next_route": _safe_label(self.next_route, "manual_review"),
            "evidence_ref": (
                _safe_ref(self.evidence_ref, "evidence:unsafe") if self.evidence_ref else ""
            ),
        }


@dataclass(frozen=True)
class ScreenshotEvidenceLink:
    evidence_ref: str
    thumbnail_ref: str
    viewport_label: str
    raw_content_available: bool = False

    def to_display_dict(self) -> dict[str, object]:
        return {
            "evidence_ref": _safe_ref(self.evidence_ref, "screenshot:unsafe"),
            "thumbnail_ref": (
                _safe_ref(self.thumbnail_ref, "thumbnail:unsafe") if self.thumbnail_ref else ""
            ),
            "viewport_label": _safe_label(self.viewport_label, "viewport"),
            "raw_content_available": self.raw_content_available,
        }


@dataclass(frozen=True)
class VisualDiffProof:
    status: VisualDiffStatus
    baseline_ref: str
    candidate_ref: str
    diff_ref: str
    changed_region_count: int
    threshold: float

    def to_display_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "baseline_ref": (
                _safe_ref(self.baseline_ref, "visual-baseline:unsafe")
                if self.baseline_ref
                else ""
            ),
            "candidate_ref": (
                _safe_ref(self.candidate_ref, "visual-candidate:unsafe")
                if self.candidate_ref
                else ""
            ),
            "diff_ref": (
                _safe_ref(self.diff_ref, "visual-diff:unsafe") if self.diff_ref else ""
            ),
            "changed_region_count": self.changed_region_count,
            "threshold": self.threshold,
        }


@dataclass(frozen=True)
class ReviewAffordanceState:
    state: DryRunReviewState
    can_approve: bool
    can_reject: bool
    requires_human_review: bool
    blocked_reason: str = ""

    def to_display_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "can_approve": self.can_approve,
            "can_reject": self.can_reject,
            "requires_human_review": self.requires_human_review,
            "blocked_reason": (
                _safe_label(self.blocked_reason, "review_blocked") if self.blocked_reason else ""
            ),
        }


@dataclass(frozen=True)
class ToolDryRunPlan:
    plan_ref: str
    safe_navigation: SafeNavigationPolicySummary
    reversible_actions: tuple[ReversibleActionPlan, ...]
    failure_routing: tuple[ToolFailureRoutingRecord, ...]
    review: ReviewAffordanceState
    dry_run_only: bool = True

    def to_display_dict(self) -> dict[str, object]:
        return {
            "plan_ref": _safe_ref(self.plan_ref, "plan:unsafe"),
            "dry_run_only": self.dry_run_only,
            "safe_navigation": self.safe_navigation.to_display_dict(),
            "reversible_actions": tuple(
                action.to_display_dict() for action in self.reversible_actions
            ),
            "failure_routing": tuple(route.to_display_dict() for route in self.failure_routing),
            "review": self.review.to_display_dict(),
        }


@dataclass(frozen=True)
class BrowserEvidence:
    evidence_ref: str
    safe_navigation: SafeNavigationPolicySummary
    screenshot_links: tuple[ScreenshotEvidenceLink, ...]
    visual_diff: VisualDiffProof
    review: ReviewAffordanceState
    dry_run_only: bool = True

    def to_display_dict(self) -> dict[str, object]:
        return {
            "evidence_ref": _safe_ref(self.evidence_ref, "browser-evidence:unsafe"),
            "dry_run_only": self.dry_run_only,
            "safe_navigation": self.safe_navigation.to_display_dict(),
            "screenshot_links": tuple(link.to_display_dict() for link in self.screenshot_links),
            "visual_diff": self.visual_diff.to_display_dict(),
            "review": self.review.to_display_dict(),
        }


def build_tool_dry_run_plan(
    plan_id: str,
    actions: Iterable[ToolActionInput],
    *,
    navigations: Iterable[BrowserNavigationInput] = (),
    failure_routes: Iterable[ToolFailureInput] = (),
) -> ToolDryRunPlan:
    """Build a display-safe dry-run plan without executing planned actions."""
    safe_navigation = summarize_safe_navigation(navigations)
    reversible_actions = tuple(
        _action_plan(index, action) for index, action in enumerate(actions, start=1)
    )
    routing = tuple(_failure_route(route) for route in failure_routes)
    review = _review_state(
        has_warnings=bool(safe_navigation.warning_count)
        or any(not action.reversible for action in reversible_actions),
        has_blockers=any(not action.reversible for action in reversible_actions),
    )
    return ToolDryRunPlan(
        plan_ref=_safe_ref(plan_id, "plan:unsafe"),
        safe_navigation=safe_navigation,
        reversible_actions=reversible_actions,
        failure_routing=routing,
        review=review,
    )


def build_browser_evidence(
    evidence_id: str,
    *,
    navigations: Iterable[BrowserNavigationInput] = (),
    screenshots: Iterable[ScreenshotEvidenceInput] = (),
    visual_diff: VisualDiffInput | None = None,
) -> BrowserEvidence:
    """Build browser evidence display records without browser automation."""
    safe_navigation = summarize_safe_navigation(navigations)
    screenshot_links = tuple(_screenshot_link(item) for item in screenshots)
    diff_proof = _visual_diff_proof(visual_diff, safe_navigation.status)
    review = _review_state(
        has_warnings=bool(safe_navigation.warning_count)
        or diff_proof.status is VisualDiffStatus.CHANGED,
        has_blockers=safe_navigation.status is DryRunReviewState.BLOCKED,
    )
    return BrowserEvidence(
        evidence_ref=_safe_ref(evidence_id, "browser-evidence:unsafe"),
        safe_navigation=safe_navigation,
        screenshot_links=screenshot_links,
        visual_diff=diff_proof,
        review=review,
    )


def summarize_safe_navigation(
    navigations: Iterable[BrowserNavigationInput],
) -> SafeNavigationPolicySummary:
    warnings: list[str] = []
    blocked_schemes: set[str] = set()
    for navigation in navigations:
        scheme = _url_scheme(navigation.requested_url)
        if scheme in _UNSAFE_NAVIGATION_SCHEMES or scheme not in _SAFE_NAVIGATION_SCHEMES:
            blocked_schemes.add(scheme or "missing")
            warnings.append(
                f"navigation request {_safe_ref(navigation.request_id, 'nav:unsafe')} "
                "is blocked by dry-run policy"
            )

    status = DryRunReviewState.BLOCKED if warnings else DryRunReviewState.READY
    return SafeNavigationPolicySummary(
        status=status,
        allowed_schemes=tuple(sorted(_SAFE_NAVIGATION_SCHEMES)),
        blocked_schemes=tuple(sorted(blocked_schemes)),
        warning_count=len(warnings),
        warnings=tuple(warnings),
    )


def _action_plan(index: int, action: ToolActionInput) -> ReversibleActionPlan:
    tool_ref = _safe_ref(action.tool_name, "tool:unsafe")
    target_ref = _safe_ref(action.target_ref, "target:unsafe") if action.target_ref else ""
    rollback_ref = (
        _safe_ref(action.rollback_plan_ref, "rollback:unsafe")
        if action.rollback_plan_ref
        else "rollback:required" if action.reversible else ""
    )
    return ReversibleActionPlan(
        action_ref=f"dry-run-action:{index}",
        tool_ref=tool_ref,
        action_label=_safe_label(action.action_label, "planned action"),
        target_ref=target_ref,
        mutation_kind=_safe_label(action.mutation_kind, "mutation"),
        reversible=bool(action.reversible),
        rollback_plan_ref=rollback_ref,
    )


def _failure_route(route: ToolFailureInput) -> ToolFailureRoutingRecord:
    return ToolFailureRoutingRecord(
        route_ref=_safe_ref(route.route_id, "failure-route:unsafe"),
        failure_kind=_safe_label(route.failure_kind, "tool_failure"),
        severity=_severity(route.severity),
        retryable=bool(route.retryable),
        next_route=_safe_label(route.next_route, "manual_review"),
        evidence_ref=_safe_ref(route.evidence_ref, "evidence:unsafe") if route.evidence_ref else "",
    )


def _screenshot_link(item: ScreenshotEvidenceInput) -> ScreenshotEvidenceLink:
    return ScreenshotEvidenceLink(
        evidence_ref=_safe_ref(item.evidence_ref, "screenshot:unsafe"),
        thumbnail_ref=_safe_ref(item.thumbnail_ref, "thumbnail:unsafe")
        if item.thumbnail_ref
        else "",
        viewport_label=_safe_label(item.viewport_label, "viewport"),
    )


def _visual_diff_proof(
    visual_diff: VisualDiffInput | None,
    navigation_status: DryRunReviewState,
) -> VisualDiffProof:
    if navigation_status is DryRunReviewState.BLOCKED:
        return VisualDiffProof(
            status=VisualDiffStatus.BLOCKED,
            baseline_ref="",
            candidate_ref="",
            diff_ref="",
            changed_region_count=0,
            threshold=0.0,
        )
    if visual_diff is None:
        return VisualDiffProof(
            status=VisualDiffStatus.NOT_PROVIDED,
            baseline_ref="",
            candidate_ref="",
            diff_ref="",
            changed_region_count=0,
            threshold=0.0,
        )
    changed_regions = max(0, int(visual_diff.changed_region_count))
    return VisualDiffProof(
        status=VisualDiffStatus.CHANGED if changed_regions else VisualDiffStatus.MATCH,
        baseline_ref=_safe_ref(visual_diff.baseline_ref, "visual-baseline:unsafe"),
        candidate_ref=_safe_ref(visual_diff.candidate_ref, "visual-candidate:unsafe"),
        diff_ref=_safe_ref(visual_diff.diff_ref, "visual-diff:unsafe"),
        changed_region_count=changed_regions,
        threshold=max(0.0, float(visual_diff.threshold)),
    )


def _review_state(has_warnings: bool, has_blockers: bool) -> ReviewAffordanceState:
    if has_blockers:
        return ReviewAffordanceState(
            state=DryRunReviewState.BLOCKED,
            can_approve=False,
            can_reject=True,
            requires_human_review=True,
            blocked_reason="dry-run policy requires revision before approval",
        )
    if has_warnings:
        return ReviewAffordanceState(
            state=DryRunReviewState.NEEDS_REVIEW,
            can_approve=True,
            can_reject=True,
            requires_human_review=True,
        )
    return ReviewAffordanceState(
        state=DryRunReviewState.READY,
        can_approve=True,
        can_reject=True,
        requires_human_review=False,
    )


def _severity(value: DryRunSeverity | str) -> DryRunSeverity:
    if isinstance(value, DryRunSeverity):
        return value
    clean = str(value).strip().lower()
    try:
        return DryRunSeverity(clean)
    except ValueError:
        return DryRunSeverity.ERROR


def _url_scheme(url: str) -> str:
    return urlsplit(str(url).strip()).scheme.lower()


def _safe_label(value: object, fallback: str) -> str:
    clean = re.sub(r"\s+", " ", str(value).strip())
    if not clean:
        return fallback
    if _looks_like_unsafe_content(clean):
        return fallback
    return clean[:80]


def _safe_ref(value: str, fallback: str) -> str:
    clean = value.strip()
    if not clean:
        return fallback
    if _looks_like_unsafe_content(clean):
        digest = hashlib.sha256(clean.encode("utf-8")).hexdigest()[:10]
        return f"{fallback}:{digest}"
    return clean


def _looks_like_unsafe_content(value: str) -> bool:
    return bool(
        re.search(
            r"(?i)(?:[A-Z]:\\|\\\\[^\\\s]+\\[^\\\s]+\\|/(?:Users|home|var|tmp|mnt|Volumes)/|"
            r"\n|traceback|exception:|"
            r"(?:raw|full|complete)\s+(?:prompt|transcript|content|log)|"
            r"(?:provider|model)\s+(?:response|output)|"
            r"api[_-]?key|secret|token|password|sk-(?:proj-)?[A-Za-z0-9_-]{16,}|"
            r"gh[pousr]_[A-Za-z0-9_]{20,})",
            value,
        )
    )
