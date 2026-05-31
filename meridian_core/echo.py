"""Echo: durable memory harness for Meridian.

Stores decisions, facts, plans, gate outcomes, and standing instructions.
Serves ranked hits to Prime through typed queries. Fails soft on missing/corrupt data.
Never injects raw bodies into prompts (Relay + Aegis own that boundary).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple
from datetime import datetime, timezone


class MemoryKind(Enum):
    """Type of memory record."""
    DECISION = "decision"
    FACT = "fact"
    PLAN = "plan"
    GATE_OUTCOME = "gate_outcome"
    STANDING_INSTRUCTION = "standing_instruction"
    NOTE = "note"


class MemorySource(Enum):
    """Origin of the memory record."""
    PRIME = "prime"
    SCOTT = "scott"
    REVIEW_CONSOLE = "review_console"
    WORKER = "worker"
    IMPORT = "import"


@dataclass(frozen=True)
class MemoryRecord:
    """A single durable memory entry. Immutable."""

    record_id: str
    project: str
    kind: MemoryKind
    summary: str
    body: str
    source: MemorySource
    created_at: datetime
    importance: int
    pinned: bool
    tags: Tuple[str, ...]
    superseded_by: Optional[str] = None

    def __post_init__(self):
        if not (1 <= self.importance <= 5):
            raise ValueError(f"importance must be 1-5, got {self.importance}")


@dataclass(frozen=True)
class MemoryQuery:
    """A typed query for Echo."""

    project: str
    kinds: Tuple[MemoryKind, ...] = ()
    tags: Tuple[str, ...] = ()
    since: Optional[datetime] = None
    limit: int = 25
    include_superseded: bool = False


@dataclass(frozen=True)
class MemoryHit:
    """A ranked query result."""

    record: MemoryRecord
    score: float
    reason: str

    def __post_init__(self):
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(f"score must be in [0.0, 1.0], got {self.score}")


class MemoryRepository:
    """Local filesystem-backed, append-only repository for durable memory.

    Stores records deterministically and ranks them by project, pinning,
    importance, and recency. Fails soft on missing/corrupt data.
    """

    HARD_LIMIT = 25

    def __init__(self):
        self._records: dict[str, MemoryRecord] = {}

    def add(self, record: MemoryRecord) -> MemoryRecord:
        """Add a record. Raises on write failure; never on read."""
        if record.record_id in self._records:
            raise ValueError(f"Record {record.record_id} already exists")
        self._records[record.record_id] = record
        return record

    def get(self, record_id: str) -> Optional[MemoryRecord]:
        """Retrieve a single record by ID. Returns None if not found."""
        return self._records.get(record_id)

    def supersede(self, old_id: str, new_record: MemoryRecord) -> MemoryRecord:
        """Mark old record as superseded and add new one."""
        if old_id not in self._records:
            raise ValueError(f"Record {old_id} not found")

        old = self._records[old_id]
        updated_old = MemoryRecord(
            record_id=old.record_id,
            project=old.project,
            kind=old.kind,
            summary=old.summary,
            body=old.body,
            source=old.source,
            created_at=old.created_at,
            importance=old.importance,
            pinned=old.pinned,
            tags=old.tags,
            superseded_by=new_record.record_id,
        )
        self._records[old_id] = updated_old
        self._records[new_record.record_id] = new_record
        return new_record

    def query(self, query: MemoryQuery) -> Tuple[MemoryHit, ...]:
        """Execute a deterministic ranked query.

        Filters by project (hard), kind, tags, and recency.
        Ranks by pinning, importance, and recency.
        Fails soft: returns empty on missing store, unknown project, or corrupt records.
        """
        hits: list[MemoryHit] = []
        now = datetime.now(timezone.utc)

        for record in self._records.values():
            # Hard filters: project, supersession, kind, tags, recency
            if record.project != query.project:
                continue

            if not query.include_superseded and record.superseded_by is not None:
                continue

            if query.kinds and record.kind not in query.kinds:
                continue

            if query.tags:
                if not all(tag in record.tags for tag in query.tags):
                    continue

            if query.since and record.created_at < query.since and not record.pinned:
                continue

            # Score deterministically
            score = self._score_record(record, query, now)
            reason = self._rank_reason(record, query)
            hits.append(MemoryHit(record=record, score=score, reason=reason))

        # Sort by score desc, then break ties
        hits.sort(
            key=lambda h: (
                -h.score,
                -int(h.record.pinned),
                -h.record.importance,
                -h.record.created_at.timestamp(),
                h.record.record_id,
            )
        )

        # Enforce hard limit
        limit = min(query.limit, self.HARD_LIMIT) if query.limit > 0 else 0
        if limit == 0:
            return ()

        return tuple(hits[:limit])

    def _score_record(
        self, record: MemoryRecord, query: MemoryQuery, now: datetime
    ) -> float:
        """Compute deterministic score in [0.0, 1.0].

        Base score from pinning (0.6) or importance decay (0.4).
        Recency adds a soft boost within that band.
        """
        base = 0.6 if record.pinned else 0.4

        # Importance boost: 1→0, 2→0.05, 3→0.1, 4→0.15, 5→0.2
        importance_boost = (record.importance - 1) * 0.05

        # Recency boost: linear decay over 30 days (configurable window)
        recency_boost = 0.0
        if query.since is None:
            age_seconds = (now - record.created_at).total_seconds()
            window_seconds = 30 * 24 * 3600
            if age_seconds < window_seconds:
                recency_boost = (1.0 - age_seconds / window_seconds) * 0.2

        score = min(1.0, base + importance_boost + recency_boost)
        return score

    def _rank_reason(self, record: MemoryRecord, query: MemoryQuery) -> str:
        """Short explanation of why record matched and ranked."""
        reasons = []
        if record.pinned:
            reasons.append("pinned")
        reasons.append(f"importance={record.importance}")
        if query.since and record.created_at >= query.since:
            reasons.append("recent")
        return " + ".join(reasons)
