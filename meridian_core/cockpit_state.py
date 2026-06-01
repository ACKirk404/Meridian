"""Prime cockpit snapshot and event domain types for V1 Bifrost.

Pure data model — no filesystem, no CLI, no UI code.
All structures are immutable frozen dataclasses; helpers return new objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class CockpitStatus(Enum):
    ONLINE = "online"
    THINKING = "thinking"
    WAITING_ON_SCOTT = "waiting_on_scott"
    BLOCKED = "blocked"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class QueuePolicy(Enum):
    ON = "on"
    OFF = "off"
    PAUSED = "paused"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


class ProgressEventCategory(Enum):
    ROUTINE_PROGRESS = "routine_progress"
    BLOCKER = "blocker"
    REVIEW_RESULT = "review_result"
    PROOF_SUMMARY = "proof_summary"
    REPAIR_ROUTED = "repair_routed"
    COMPLETION = "completion"
    HUMAN_GATE = "human_gate"
    SYSTEM_HEALTH = "system_health"


class EventSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class LaneCockpitStatus(Enum):
    RUNNING = "running"
    POLLING = "polling"
    IDLE = "idle"
    BLOCKED = "blocked"
    STALE = "stale"
    OFFLINE = "offline"


_LANE_STATUS_ORDER: dict[LaneCockpitStatus, int] = {
    LaneCockpitStatus.RUNNING: 0,
    LaneCockpitStatus.POLLING: 1,
    LaneCockpitStatus.IDLE: 2,
    LaneCockpitStatus.BLOCKED: 3,
    LaneCockpitStatus.STALE: 4,
    LaneCockpitStatus.OFFLINE: 5,
}


@dataclass(frozen=True)
class LaneSummary:
    """Immutable cockpit row for a single worker lane."""

    lane_id: str
    role: str
    status: LaneCockpitStatus
    last_poll_at: str
    last_commit: str
    attention: bool


@dataclass(frozen=True)
class ProgressEvent:
    """Single typed progress event emitted by Prime."""

    category: ProgressEventCategory
    severity: EventSeverity
    timestamp: str
    message: str


@dataclass(frozen=True)
class PrimeCockpitSnapshot:
    """Immutable snapshot of Prime state for the V1 cockpit."""

    project: str
    bearing: str
    risk_tier: str
    prime_status: CockpitStatus
    queue_policy: QueuePolicy
    lanes: tuple[LaneSummary, ...]
    progress_events: tuple[ProgressEvent, ...]
    review_gate_count: int

    def __post_init__(self) -> None:
        """Enforce tuple conversion for lanes and progress_events to guarantee immutability."""
        if not isinstance(self.lanes, tuple):
            object.__setattr__(self, "lanes", tuple(self.lanes))
        if not isinstance(self.progress_events, tuple):
            object.__setattr__(self, "progress_events", tuple(self.progress_events))


def sort_lanes(lanes: Sequence[LaneSummary]) -> list[LaneSummary]:
    """Return lanes sorted: attention=True first, then running/polling/idle/offline order."""
    return sorted(
        lanes,
        key=lambda lane: (
            0 if lane.attention else 1,
            _LANE_STATUS_ORDER.get(lane.status, 99),
        ),
    )


def filter_events(
    snapshot: PrimeCockpitSnapshot,
    *,
    category: ProgressEventCategory | None = None,
    severity: EventSeverity | None = None,
) -> list[ProgressEvent]:
    """Return events matching optional filters; snapshot is not mutated."""
    events: list[ProgressEvent] = list(snapshot.progress_events)
    if category is not None:
        events = [e for e in events if e.category == category]
    if severity is not None:
        events = [e for e in events if e.severity == severity]
    return events


def lane_summary_counts(snapshot: PrimeCockpitSnapshot) -> dict[str, int]:
    """Return summary counts: total, attention, blocked, stale."""
    lanes = snapshot.lanes
    return {
        "total": len(lanes),
        "attention": sum(1 for lane in lanes if lane.attention),
        "blocked": sum(1 for lane in lanes if lane.status == LaneCockpitStatus.BLOCKED),
        "stale": sum(1 for lane in lanes if lane.status == LaneCockpitStatus.STALE),
    }
