"""
In-memory event recorder.

Records decision, bottleneck, and injection events during a kernel run.
No persistence yet — SQLite comes later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .models import Decision, ScottBottleneck, SessionInjection


class EventKind(Enum):
    DECISION_MADE = "decision_made"
    BOTTLENECK_CREATED = "bottleneck_created"
    INJECTION_GENERATED = "injection_generated"


@dataclass
class Event:
    kind: EventKind
    payload: Any
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EventRecorder:
    def __init__(self) -> None:
        self._events: list[Event] = []

    def record_decision(self, decision: Decision) -> None:
        self._events.append(Event(kind=EventKind.DECISION_MADE, payload=decision))

    def record_bottleneck(self, bottleneck: ScottBottleneck) -> None:
        self._events.append(Event(kind=EventKind.BOTTLENECK_CREATED, payload=bottleneck))

    def record_injection(self, injection: SessionInjection) -> None:
        self._events.append(Event(kind=EventKind.INJECTION_GENERATED, payload=injection))

    def all_events(self) -> list[Event]:
        return list(self._events)

    def events_of_kind(self, kind: EventKind) -> list[Event]:
        return [e for e in self._events if e.kind == kind]
