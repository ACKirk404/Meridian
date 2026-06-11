"""
Review Console -- promptable review/gating surface for Meridian.

The Review Console is where Prime places artifacts, proof, cross-check
findings, plan reviews, system findings, comparisons, and approval gates
outside the main Orchestrator Queue. It is a prompt window, not a passive log.

Scott can respond directly to any item Prime places here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .prompt_metrics import PromptMetricSummary, PromptPerformanceStatus


class ReviewConsoleItemType(Enum):
    CROSS_CHECK = "cross_check"
    PLAN_REVIEW = "plan_review"
    PROOF = "proof"
    SYSTEM_FINDING = "system_finding"
    ARTIFACT = "artifact"
    APPROVAL_GATE = "approval_gate"
    COMPARISON = "comparison"


class ReviewConsoleSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ReviewConsoleAction(Enum):
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    INSPECT = "inspect"
    ACKNOWLEDGE = "acknowledge"


class ReviewConsoleItemStatus(Enum):
    PENDING = "pending"
    RESPONDED = "responded"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"


@dataclass
class ReviewConsoleItem:
    id: str
    item_type: ReviewConsoleItemType
    severity: ReviewConsoleSeverity
    title: str
    content: str
    promptable: bool
    is_automatic: bool
    requires_response: bool
    owner_harness: str = "Prime"
    suggested_actions: list[ReviewConsoleAction] = field(default_factory=list)
    status: ReviewConsoleItemStatus = field(default=ReviewConsoleItemStatus.PENDING)
    sequence: int = field(default=-1)


@dataclass(frozen=True)
class ReviewConsoleResponse:
    item_id: str
    action: ReviewConsoleAction
    note: str = ""


@dataclass
class ReviewConsoleQueue:
    items: list[ReviewConsoleItem] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._next_sequence: int = max((i.sequence for i in self.items), default=-1) + 1

    def enqueue(self, item: ReviewConsoleItem) -> None:
        """Add an item and assign its position in insertion order."""
        item.sequence = self._next_sequence
        self._next_sequence += 1
        self.items.append(item)

    def pending(self) -> list[ReviewConsoleItem]:
        """All pending items in deterministic insertion order."""
        return sorted(
            [i for i in self.items if i.status is ReviewConsoleItemStatus.PENDING],
            key=lambda i: i.sequence,
        )

    def pending_gates(self) -> list[ReviewConsoleItem]:
        """Pending items that require a user response before Prime can proceed."""
        return [i for i in self.pending() if i.requires_response]

    def informational(self) -> list[ReviewConsoleItem]:
        """Pending items that are informational and do not require a response."""
        return [i for i in self.pending() if not i.requires_response]

    def get(self, item_id: str) -> ReviewConsoleItem | None:
        """Return an item by id, or None if it is not present."""
        return next((i for i in self.items if i.id == item_id), None)

    def require(self, item_id: str) -> ReviewConsoleItem:
        """Return an item by id. Raises KeyError if it is not present."""
        item = self.get(item_id)
        if item is None:
            raise KeyError(f"No Review Console item for {item_id!r}")
        return item

    def respond(
        self,
        item_id: str,
        action: ReviewConsoleAction,
        note: str = "",
    ) -> ReviewConsoleResponse:
        """
        Record a response to a promptable item.

        ACKNOWLEDGE maps to ACKNOWLEDGED. Other allowed actions map to
        RESPONDED, leaving interpretation to Prime.
        """
        item = self.require(item_id)
        if not item.promptable:
            raise ValueError(f"Review Console item {item_id!r} is not promptable")
        if action not in item.suggested_actions:
            raise ValueError(f"Action {action.value!r} is not allowed for {item_id!r}")

        item.status = (
            ReviewConsoleItemStatus.ACKNOWLEDGED
            if action is ReviewConsoleAction.ACKNOWLEDGE
            else ReviewConsoleItemStatus.RESPONDED
        )
        return ReviewConsoleResponse(item_id=item_id, action=action, note=note.strip())

    def acknowledge(self, item_id: str, note: str = "") -> ReviewConsoleResponse:
        """Acknowledge a promptable informational item."""
        return self.respond(item_id, ReviewConsoleAction.ACKNOWLEDGE, note)

    def dismiss(self, item_id: str) -> ReviewConsoleItem:
        """Dismiss an item without treating it as a substantive response."""
        item = self.require(item_id)
        item.status = ReviewConsoleItemStatus.DISMISSED
        return item


# ---------------------------------------------------------------------------
# Item factories -- canonical defaults per item type
# ---------------------------------------------------------------------------


def make_cross_check_item(
    id: str,
    title: str,
    content: str,
    severity: ReviewConsoleSeverity = ReviewConsoleSeverity.INFO,
    is_automatic: bool = True,
    owner_harness: str = "Aegis",
) -> ReviewConsoleItem:
    """Automatic cross-check finding. Promptable, informational by default."""
    return ReviewConsoleItem(
        id=id,
        item_type=ReviewConsoleItemType.CROSS_CHECK,
        severity=severity,
        title=title,
        content=content,
        owner_harness=owner_harness,
        promptable=True,
        is_automatic=is_automatic,
        requires_response=False,
        suggested_actions=[ReviewConsoleAction.INSPECT, ReviewConsoleAction.ACKNOWLEDGE],
    )


def make_plan_review_item(
    id: str,
    title: str,
    content: str,
    severity: ReviewConsoleSeverity = ReviewConsoleSeverity.INFO,
    owner_harness: str = "Prime",
) -> ReviewConsoleItem:
    """Plan review placed by Prime for Scott to inspect or approve."""
    return ReviewConsoleItem(
        id=id,
        item_type=ReviewConsoleItemType.PLAN_REVIEW,
        severity=severity,
        title=title,
        content=content,
        owner_harness=owner_harness,
        promptable=True,
        is_automatic=False,
        requires_response=False,
        suggested_actions=[ReviewConsoleAction.INSPECT, ReviewConsoleAction.APPROVE, ReviewConsoleAction.MODIFY],
    )


def make_approval_gate(
    id: str,
    title: str,
    content: str,
    severity: ReviewConsoleSeverity = ReviewConsoleSeverity.WARNING,
    owner_harness: str = "Aegis",
) -> ReviewConsoleItem:
    """Approval gate. Promptable and requires a response before Prime proceeds."""
    return ReviewConsoleItem(
        id=id,
        item_type=ReviewConsoleItemType.APPROVAL_GATE,
        severity=severity,
        title=title,
        content=content,
        owner_harness=owner_harness,
        promptable=True,
        is_automatic=False,
        requires_response=True,
        suggested_actions=[ReviewConsoleAction.APPROVE, ReviewConsoleAction.REJECT, ReviewConsoleAction.MODIFY],
    )


def make_comparison_item(
    id: str,
    title: str,
    content: str,
    severity: ReviewConsoleSeverity = ReviewConsoleSeverity.WARNING,
    owner_harness: str = "Relay",
) -> ReviewConsoleItem:
    """Comparison item for visible disagreement between independent lanes."""
    return ReviewConsoleItem(
        id=id,
        item_type=ReviewConsoleItemType.COMPARISON,
        severity=severity,
        title=title,
        content=content,
        owner_harness=owner_harness,
        promptable=True,
        is_automatic=True,
        requires_response=False,
        suggested_actions=[ReviewConsoleAction.INSPECT, ReviewConsoleAction.ACKNOWLEDGE],
    )


def make_system_finding(
    id: str,
    title: str,
    content: str,
    severity: ReviewConsoleSeverity = ReviewConsoleSeverity.INFO,
    owner_harness: str = "Beacon",
) -> ReviewConsoleItem:
    """Informational system finding from Prime or a harness. Not a prompt window."""
    return ReviewConsoleItem(
        id=id,
        item_type=ReviewConsoleItemType.SYSTEM_FINDING,
        severity=severity,
        title=title,
        content=content,
        owner_harness=owner_harness,
        promptable=False,
        is_automatic=True,
        requires_response=False,
        suggested_actions=[ReviewConsoleAction.ACKNOWLEDGE],
    )


# ---------------------------------------------------------------------------
# Module-level default console + Prime-facing routing helper
# ---------------------------------------------------------------------------

_CONSOLE: ReviewConsoleQueue = ReviewConsoleQueue()


def route_to_console(
    item_type: ReviewConsoleItemType | str,
    summary: str,
    provenance: str = "",
    *,
    console: ReviewConsoleQueue | None = None,
) -> ReviewConsoleItem:
    """Create and enqueue a console item routed from Prime or a harness."""
    if isinstance(item_type, str):
        item_type = ReviewConsoleItemType(item_type)
    q = console if console is not None else _CONSOLE
    item_id = f"rc-{len(q.items):04d}"
    item = ReviewConsoleItem(
        id=item_id,
        item_type=item_type,
        severity=ReviewConsoleSeverity.INFO,
        title=summary,
        content=provenance,
        owner_harness="Prime",
        promptable=False,
        is_automatic=True,
        requires_response=False,
        suggested_actions=[ReviewConsoleAction.ACKNOWLEDGE],
    )
    q.enqueue(item)
    return item


_METRICS_SEVERITY: dict[PromptPerformanceStatus, ReviewConsoleSeverity] = {
    PromptPerformanceStatus.HEALTHY: ReviewConsoleSeverity.INFO,
    PromptPerformanceStatus.WATCH: ReviewConsoleSeverity.WARNING,
    PromptPerformanceStatus.DEGRADED: ReviewConsoleSeverity.ERROR,
}


def make_prompt_metrics_finding(
    id: str,
    summary: PromptMetricSummary,
) -> ReviewConsoleItem:
    """Automatic system finding from a PromptMetricSummary. Not promptable, not response-required."""
    parts = [
        f"Samples: {summary.sample_count}",
        f"Avg tokens: {summary.avg_prompt_tokens:.0f}",
        f"Avg construction: {summary.avg_construction_time_ms:.1f}ms",
        f"Avg response: {summary.avg_total_response_time_ms:.1f}ms",
    ]
    if summary.avg_overhead_delta_ms is not None:
        parts.append(f"Avg overhead: {summary.avg_overhead_delta_ms:.1f}ms")
    content = " | ".join(parts)

    return ReviewConsoleItem(
        id=id,
        item_type=ReviewConsoleItemType.SYSTEM_FINDING,
        severity=_METRICS_SEVERITY[summary.status],
        title=f"Prompt performance: {summary.status.value}",
        content=content,
        owner_harness="Relay",
        promptable=False,
        is_automatic=True,
        requires_response=False,
        suggested_actions=[ReviewConsoleAction.ACKNOWLEDGE],
    )
