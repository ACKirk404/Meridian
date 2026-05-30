"""
Session injection factory.

Builds SessionInjection objects. Does not perform real injection yet —
that belongs to the agent harness once it exists.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from .models import InjectionMode, Priority, SessionInjection


def make_injection(
    target_session_id: str,
    instruction: str,
    reason: str,
    priority: Priority = Priority.MEDIUM,
    mode: InjectionMode = InjectionMode.DIRECTIVE,
    stable_key: Optional[str] = None,
) -> SessionInjection:
    inj_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, stable_key)) if stable_key else str(uuid.uuid4())
    return SessionInjection(
        id=inj_id,
        target_session_id=target_session_id,
        instruction=instruction,
        reason=reason,
        priority=priority,
        mode=mode,
        created_at=datetime.now(timezone.utc),
    )
