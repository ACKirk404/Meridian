"""
Session injection factory.

Builds SessionInjection objects. Does not perform real injection yet —
that belongs to the agent harness once it exists.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from .models import InjectionMode, Priority, SessionInjection


def make_injection(
    target_session_id: str,
    instruction: str,
    reason: str,
    priority: Priority = Priority.MEDIUM,
    mode: InjectionMode = InjectionMode.DIRECTIVE,
) -> SessionInjection:
    return SessionInjection(
        id=str(uuid.uuid4()),
        target_session_id=target_session_id,
        instruction=instruction,
        reason=reason,
        priority=priority,
        mode=mode,
        created_at=datetime.now(),
    )
