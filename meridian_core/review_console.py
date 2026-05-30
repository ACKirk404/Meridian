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
    suggested_actions: list[ReviewConsoleAction] = field(default_factory=list)
    status: ReviewConsoleItemStatus = field(default=ReviewConsoleItemStatus.PENDING)
    sequence: int = field(default=-1)


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


# ---------------------------------------------------------------------------
# Item factories -- canonical defaults per item type
# ---------------------------------------------------------------------------


def make_cross_check_item(
    id: str,
    title: str,
    content: str,
    severity: ReviewConsoleSeverity = ReviewConsoleSeverity.INFO,
    is_automatic: bool = True,
) -> ReviewConsoleItem:
    """Automatic cross-check finding. Promptable, informational by default."""
    return ReviewConsoleItem(
        id=id,
        item_type=ReviewConsoleItemType.CROSS_CHECK,
        severity=severity,
        title=title,
        content=content,
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
) -> ReviewConsoleItem:
    """Plan review placed by Prime for Scott to inspect or approve."""
    return ReviewConsoleItem(
        id=id,
        item_type=ReviewConsoleItemType.PLAN_REVIEW,
        severity=severity,
        title=title,
        content=content,
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
) -> ReviewConsoleItem:
    """Approval gate. Promptable and requires a response before Prime proceeds."""
    return ReviewConsoleItem(
        id=id,
        item_type=ReviewConsoleItemType.APPROVAL_GATE,
        severity=severity,
        title=title,
        content=content,
        promptable=True,
        is_automatic=False,
        requires_response=True,
        suggested_actions=[ReviewConsoleAction.APPROVE, ReviewConsoleAction.REJECT, ReviewConsoleAction.MODIFY],
    )


def make_system_finding(
    id: str,
    title: str,
    content: str,
    severity: ReviewConsoleSeverity = ReviewConsoleSeverity.INFO,
) -> ReviewConsoleItem:
    """Informational system finding from Prime or a harness. Not a prompt window."""
    return ReviewConsoleItem(
        id=id,
        item_type=ReviewConsoleItemType.SYSTEM_FINDING,
        severity=severity,
        title=title,
        content=content,
        promptable=False,
        is_automatic=True,
        requires_response=False,
        suggested_actions=[ReviewConsoleAction.ACKNOWLEDGE],
    )
