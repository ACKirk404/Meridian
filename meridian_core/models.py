"""
Meridian domain objects.

These are the native types the local brain reasons over. Not JSON dicts.
All definitions align with the vocabulary in context.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class HeartbeatStatus(Enum):
    ALIVE = "alive"
    BUSY = "busy"
    BLOCKED = "blocked"
    FAILED = "failed"
    SLEEPING = "sleeping"
    STALE = "stale"


class InjectionMode(Enum):
    """How a directive is delivered to a target session or harness."""
    USER_MESSAGE = "user_message"
    DIRECTIVE = "directive"
    RESUME_CONTEXT = "resume_context"
    SYSTEM_PROMPT = "system_prompt"


class AdapterTier(Enum):
    """Provider adapter compliance tier for public/private distinction."""
    OFFICIAL_API_SUPPORTED = "official_api_supported"
    OFFICIAL_CLI_SUPPORTED = "official_cli_supported"
    LOCAL_MODEL_SUPPORTED = "local_model_supported"
    EXPERIMENTAL_USER_CONFIGURED = "experimental_user_configured"
    PRIVATE_ONLY = "private_only"
    DISABLED_FOR_PUBLIC_BUILD = "disabled_for_public_build"


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MoveKind(Enum):
    """Whether a next move requires Scott's judgment or can proceed autonomously."""
    AUTONOMOUS = "autonomous"
    SCOTT_REQUIRED = "scott_required"


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"


class ProofType(Enum):
    TEST = "test"
    SCREENSHOT = "screenshot"
    BROWSER_CHECK = "browser_check"
    DIFF = "diff"
    REVIEW = "review"
    WAIVER = "waiver"


class ArtifactKind(Enum):
    CODE = "code"
    SCREENSHOT = "screenshot"
    PR = "pr"
    DOCUMENT = "document"


class SteeringCapability(Enum):
    NONE = "none"
    USER_MESSAGE = "user_message"
    DIRECTIVE = "directive"
    RESUME_CONTEXT = "resume_context"
    SYSTEM_PROMPT = "system_prompt"


# ---------------------------------------------------------------------------
# Evidence and artifacts
# ---------------------------------------------------------------------------


@dataclass
class Proof:
    """Evidence that a claim or result is trustworthy enough to proceed."""
    id: str
    description: str
    proof_type: ProofType
    command: Optional[str] = None
    result: Optional[str] = None
    verified: bool = False


@dataclass
class Artifact:
    """A durable output Meridian created, modified, verified, or shipped."""
    id: str
    kind: ArtifactKind
    path: str
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Work objects
# ---------------------------------------------------------------------------


@dataclass
class Objective:
    """A concrete desired outcome inside an initiative."""
    id: str
    title: str
    description: str
    success_criteria: list[str] = field(default_factory=list)
    proof: list[Proof] = field(default_factory=list)


@dataclass
class NextMove:
    """The smallest useful action Meridian can take to advance an objective."""
    id: str
    description: str
    kind: MoveKind
    objective_id: str
    proof_required: bool = False
    proof: Optional[Proof] = None
    reason: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class Task:
    """A bounded unit of work — execution unit, not strategy unit."""
    id: str
    title: str
    description: str
    objective_id: str
    status: TaskStatus = TaskStatus.PENDING


@dataclass
class Initiative:
    """A directional push inside a venture or project with objectives and next moves."""
    id: str
    title: str
    description: str
    objectives: list[Objective] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    next_moves: list[NextMove] = field(default_factory=list)


@dataclass
class Project:
    """An organized body of work with a concrete outcome."""
    id: str
    title: str
    description: str
    repo_url: Optional[str] = None
    local_path: Optional[str] = None
    initiatives: list[Initiative] = field(default_factory=list)


@dataclass
class Venture:
    """A value-seeking container with business, audience, or strategic identity."""
    id: str
    title: str
    description: str
    projects: list[Project] = field(default_factory=list)


@dataclass
class Portfolio:
    """The full set of ventures and projects Meridian is aware of."""
    ventures: list[Venture] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)

    def all_initiatives(self) -> list[Initiative]:
        initiatives: list[Initiative] = []
        for venture in self.ventures:
            for project in venture.projects:
                initiatives.extend(project.initiatives)
        for project in self.projects:
            initiatives.extend(project.initiatives)
        return initiatives

    def all_next_moves(self) -> list[NextMove]:
        moves: list[NextMove] = []
        for initiative in self.all_initiatives():
            moves.extend(initiative.next_moves)
        return moves


# ---------------------------------------------------------------------------
# Harness and heartbeat
# ---------------------------------------------------------------------------


@dataclass
class Harness:
    """A capability surface Meridian can use to sense or act."""
    id: str
    name: str
    capabilities: list[str] = field(default_factory=list)
    steering_capability: SteeringCapability = SteeringCapability.NONE


@dataclass
class Heartbeat:
    """A live state report from a harness or worker session."""
    harness_id: str
    status: HeartbeatStatus
    current_work: Optional[str] = None
    last_event: Optional[str] = None
    blockers: list[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------


@dataclass
class Workflow:
    """Coordinated motion over time — a path the orchestrator can choose or abandon."""
    id: str
    title: str
    steps: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Decision, bottleneck, injection
# ---------------------------------------------------------------------------


@dataclass
class Decision:
    """A committed choice with a reason, recorded in the decision journal."""
    id: str
    next_action: str
    reason: str
    evidence_needed: list[str] = field(default_factory=list)
    hard_policies_checked: list[str] = field(default_factory=list)
    alternatives_considered: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ScottBottleneck:
    """A decision or judgment only Scott should make."""
    id: str
    title: str
    description: str
    priority: Priority
    initiative_id: Optional[str] = None
    move_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SessionInjection:
    """A targeted instruction Meridian sends into an active worker session or harness."""
    id: str
    target_session_id: str
    instruction: str
    reason: str
    priority: Priority
    mode: InjectionMode
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Provider adapters
# ---------------------------------------------------------------------------


@dataclass
class ProviderAdapter:
    """Metadata about a model provider adapter and its compliance tier."""
    id: str
    name: str
    provider: str
    tier: AdapterTier
    description: str = ""
    enabled_for_public_build: bool = True

    def is_public_safe(self) -> bool:
        """True if this adapter can appear in a public build without compliance risk."""
        if not self.enabled_for_public_build:
            return False
        unsafe = {AdapterTier.PRIVATE_ONLY, AdapterTier.DISABLED_FOR_PUBLIC_BUILD}
        return self.tier not in unsafe
