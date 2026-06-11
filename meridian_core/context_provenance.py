"""Display-safe Atlas/Echo context provenance records for V2.5.

This module models already-collected retrieval and memory provenance. It does
not read files, call models, persist memory, or expose raw prompts, transcripts,
provider responses, or local paths in display dictionaries.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum


class ProvenanceState(Enum):
    PRESENT = "present"
    MISSING = "missing"


class StaleKnowledgeState(Enum):
    CURRENT = "current"
    STALE = "stale"
    UNKNOWN = "unknown"


class MemoryConflictState(Enum):
    NONE = "none"
    CONFLICTING = "conflicting"


class MemoryDecayState(Enum):
    ACTIVE = "active"
    DECAYING = "decaying"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class MistakeCaptureMode(Enum):
    DISPLAY_ONLY = "display_only"
    WRITE_DISABLED = "write_disabled"


_UNSAFE_PATTERN = re.compile(
    r"(?is)(?:"
    r"[A-Z]:\\|\\\\[^\\\s]+\\[^\\\s]+\\|/(?:Users|home|var|tmp|mnt|Volumes)/|"
    r"\b(?:raw|full|complete)\s+prompt\s*:|"
    r"\b(?:raw|full|complete)\s+transcript\s*:|"
    r"\b(?:provider|model)\s+(?:response|output)\s*:|"
    r"\b(?:api[_-]?key|secret|token|password|credential)\s*[:=]\s*\S{8,}|"
    r"sk-(?:proj-)?[A-Za-z0-9_-]{16,}|"
    r"gh[pousr]_[A-Za-z0-9_]{20,}"
    r")"
)


@dataclass(frozen=True)
class CitationRankingMetadata:
    rank: int
    retrieval_score: float
    rerank_score: float | None = None
    tie_breaker: str = ""

    def to_display_dict(self) -> dict[str, object]:
        return {
            "rank": max(0, int(self.rank)),
            "retrieval_score": _bounded_score(self.retrieval_score),
            "rerank_score": None
            if self.rerank_score is None
            else _bounded_score(self.rerank_score),
            "tie_breaker": _safe_text(self.tie_breaker),
        }


@dataclass(frozen=True)
class ChunkLineage:
    source_ref: str
    document_ref: str
    chunk_ref: str
    chunk_index: int
    chunk_count: int
    embedding_model_ref: str = ""
    index_ref: str = ""

    @property
    def provenance_state(self) -> ProvenanceState:
        required = (
            self.source_ref,
            self.document_ref,
            self.chunk_ref,
        )
        if all(str(value).strip() for value in required):
            return ProvenanceState.PRESENT
        return ProvenanceState.MISSING

    def to_display_dict(self) -> dict[str, object]:
        return {
            "source_ref": _safe_ref(self.source_ref, "source:missing"),
            "document_ref": _safe_ref(self.document_ref, "document:missing"),
            "chunk_ref": _safe_ref(self.chunk_ref, "chunk:missing"),
            "chunk_index": max(0, int(self.chunk_index)),
            "chunk_count": max(0, int(self.chunk_count)),
            "embedding_model_ref": _safe_ref(
                self.embedding_model_ref,
                "embedding_model:missing",
            ),
            "index_ref": _safe_ref(self.index_ref, "index:missing"),
            "provenance_state": self.provenance_state.value,
        }


@dataclass(frozen=True)
class StaleKnowledgeDetection:
    state: StaleKnowledgeState
    reason: str
    source_updated_at: str = ""
    knowledge_cutoff: str = ""
    stale_after: str = ""

    def to_display_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "reason": _safe_text(self.reason),
            "source_updated_at": _safe_date(self.source_updated_at),
            "knowledge_cutoff": _safe_date(self.knowledge_cutoff),
            "stale_after": _safe_date(self.stale_after),
        }


@dataclass(frozen=True)
class RetrievalExplanation:
    strategy: str
    match_signals: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    limitation_notes: tuple[str, ...] = ()

    def to_display_dict(self) -> dict[str, object]:
        return {
            "strategy": _safe_text(self.strategy),
            "match_signals": tuple(_safe_text(signal) for signal in self.match_signals),
            "reason_codes": tuple(_safe_ref(code, "reason:unsafe") for code in self.reason_codes),
            "limitation_notes": tuple(_safe_text(note) for note in self.limitation_notes),
        }


@dataclass(frozen=True)
class RetrievalEvidence:
    evidence_id: str
    query_ref: str
    citation: CitationRankingMetadata
    lineage: ChunkLineage
    explanation: RetrievalExplanation
    retrieved_at: str = ""
    source_updated_at: str = ""
    knowledge_cutoff: str = ""
    stale_after: str = ""

    @property
    def stale_knowledge(self) -> StaleKnowledgeDetection:
        return _stale_knowledge_detection(
            source_updated_at=self.source_updated_at,
            knowledge_cutoff=self.knowledge_cutoff,
            stale_after=self.stale_after,
            retrieved_at=self.retrieved_at,
        )

    @property
    def provenance_state(self) -> ProvenanceState:
        if (
            self.evidence_id.strip()
            and self.query_ref.strip()
            and self.lineage.provenance_state is ProvenanceState.PRESENT
        ):
            return ProvenanceState.PRESENT
        return ProvenanceState.MISSING

    def to_display_dict(self) -> dict[str, object]:
        return {
            "evidence_id": _safe_ref(self.evidence_id, "retrieval:missing"),
            "query_ref": _safe_ref(self.query_ref, "query:missing"),
            "provenance_state": self.provenance_state.value,
            "citation": self.citation.to_display_dict(),
            "chunk_lineage": self.lineage.to_display_dict(),
            "stale_knowledge": self.stale_knowledge.to_display_dict(),
            "retrieval_explanation": self.explanation.to_display_dict(),
        }


@dataclass(frozen=True)
class MemoryDecayPolicyNote:
    state: MemoryDecayState
    policy_ref: str
    expires_at: str = ""
    decay_reason: str = ""

    def to_display_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "policy_ref": _safe_ref(self.policy_ref, "memory_policy:missing"),
            "expires_at": _safe_date(self.expires_at),
            "decay_reason": _safe_text(self.decay_reason),
        }


@dataclass(frozen=True)
class MemoryConflictRecord:
    conflict_id: str
    memory_ref: str
    conflicting_memory_ref: str
    field: str
    resolution_state: str = "unresolved"
    evidence_refs: tuple[str, ...] = ()

    def to_display_dict(self) -> dict[str, object]:
        return {
            "conflict_id": _safe_ref(self.conflict_id, "memory_conflict:missing"),
            "memory_ref": _safe_ref(self.memory_ref, "memory:missing"),
            "conflicting_memory_ref": _safe_ref(
                self.conflicting_memory_ref,
                "memory:missing",
            ),
            "field": _safe_ref(self.field, "field:missing"),
            "resolution_state": _safe_ref(self.resolution_state, "resolution:missing"),
            "evidence_refs": tuple(_safe_ref(ref, "evidence:unsafe") for ref in self.evidence_refs),
        }


@dataclass(frozen=True)
class MistakeMemoryCaptureShape:
    capture_id: str
    mistake_ref: str
    correction_ref: str
    evidence_refs: tuple[str, ...] = ()
    mode: MistakeCaptureMode = MistakeCaptureMode.WRITE_DISABLED

    @property
    def autonomous_write_enabled(self) -> bool:
        return False

    def to_display_dict(self) -> dict[str, object]:
        return {
            "capture_id": _safe_ref(self.capture_id, "mistake_capture:missing"),
            "mistake_ref": _safe_ref(self.mistake_ref, "mistake:missing"),
            "correction_ref": _safe_ref(self.correction_ref, "correction:missing"),
            "evidence_refs": tuple(_safe_ref(ref, "evidence:unsafe") for ref in self.evidence_refs),
            "mode": self.mode.value,
            "autonomous_write_enabled": self.autonomous_write_enabled,
        }


@dataclass(frozen=True)
class MemoryProvenance:
    memory_id: str
    subject_ref: str
    source_ref: str
    observed_at: str = ""
    confidence: float = 0.0
    evidence_refs: tuple[str, ...] = ()
    conflict_records: tuple[MemoryConflictRecord, ...] = ()
    decay_policy_note: MemoryDecayPolicyNote = MemoryDecayPolicyNote(
        state=MemoryDecayState.UNKNOWN,
        policy_ref="memory_policy:unknown",
    )
    mistake_capture: MistakeMemoryCaptureShape | None = None

    @property
    def provenance_state(self) -> ProvenanceState:
        if self.memory_id.strip() and self.subject_ref.strip() and self.source_ref.strip():
            return ProvenanceState.PRESENT
        return ProvenanceState.MISSING

    @property
    def conflict_state(self) -> MemoryConflictState:
        if self.conflict_records:
            return MemoryConflictState.CONFLICTING
        return MemoryConflictState.NONE

    def to_display_dict(self) -> dict[str, object]:
        return {
            "memory_id": _safe_ref(self.memory_id, "memory:missing"),
            "subject_ref": _safe_ref(self.subject_ref, "subject:missing"),
            "source_ref": _safe_ref(self.source_ref, "source:missing"),
            "observed_at": _safe_date(self.observed_at),
            "confidence": _bounded_score(self.confidence),
            "provenance_state": self.provenance_state.value,
            "evidence_refs": tuple(_safe_ref(ref, "evidence:unsafe") for ref in self.evidence_refs),
            "conflict_state": self.conflict_state.value,
            "conflict_records": tuple(
                record.to_display_dict() for record in self.conflict_records
            ),
            "decay_policy_note": self.decay_policy_note.to_display_dict(),
            "mistake_capture": None
            if self.mistake_capture is None
            else self.mistake_capture.to_display_dict(),
        }


def _stale_knowledge_detection(
    *,
    source_updated_at: str,
    knowledge_cutoff: str,
    stale_after: str,
    retrieved_at: str,
) -> StaleKnowledgeDetection:
    source_date = _date_key(source_updated_at)
    cutoff_date = _date_key(knowledge_cutoff)
    stale_after_date = _date_key(stale_after)
    retrieved_date = _date_key(retrieved_at)

    if source_date and cutoff_date and source_date > cutoff_date:
        return StaleKnowledgeDetection(
            state=StaleKnowledgeState.STALE,
            reason="source update is newer than knowledge cutoff",
            source_updated_at=source_updated_at,
            knowledge_cutoff=knowledge_cutoff,
            stale_after=stale_after,
        )
    if stale_after_date and retrieved_date and retrieved_date > stale_after_date:
        return StaleKnowledgeDetection(
            state=StaleKnowledgeState.STALE,
            reason="retrieval happened after stale-after boundary",
            source_updated_at=source_updated_at,
            knowledge_cutoff=knowledge_cutoff,
            stale_after=stale_after,
        )
    if not source_date or not cutoff_date:
        return StaleKnowledgeDetection(
            state=StaleKnowledgeState.UNKNOWN,
            reason="insufficient dated provenance",
            source_updated_at=source_updated_at,
            knowledge_cutoff=knowledge_cutoff,
            stale_after=stale_after,
        )
    return StaleKnowledgeDetection(
        state=StaleKnowledgeState.CURRENT,
        reason="source update is within knowledge cutoff",
        source_updated_at=source_updated_at,
        knowledge_cutoff=knowledge_cutoff,
        stale_after=stale_after,
    )


def _bounded_score(value: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return round(max(0.0, min(1.0, number)), 4)


def _safe_ref(value: str, fallback: str) -> str:
    clean = str(value).strip()
    if not clean:
        return fallback
    if _UNSAFE_PATTERN.search(clean) or "\n" in clean or "\r" in clean:
        digest = hashlib.sha256(clean.encode("utf-8")).hexdigest()[:10]
        return f"{fallback}:{digest}"
    return clean


def _safe_text(value: str) -> str:
    clean = re.sub(r"\s+", " ", str(value).strip())
    if not clean:
        return ""
    if _UNSAFE_PATTERN.search(clean):
        return "[redacted]"
    return clean[:160]


def _safe_date(value: str) -> str:
    clean = str(value).strip()
    if _date_key(clean):
        return _date_key(clean)
    if clean:
        return "unknown"
    return ""


def _date_key(value: str) -> str:
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", str(value).strip())
    if not match:
        return ""
    return match.group(1)
