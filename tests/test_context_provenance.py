"""Tests for V2.5 Atlas/Echo context provenance hardening."""

from __future__ import annotations

from meridian_core.context_provenance import (
    ChunkLineage,
    CitationRankingMetadata,
    MemoryConflictRecord,
    MemoryDecayPolicyNote,
    MemoryDecayState,
    MemoryProvenance,
    MistakeCaptureMode,
    MistakeMemoryCaptureShape,
    ProvenanceState,
    RetrievalEvidence,
    RetrievalExplanation,
    StaleKnowledgeDetection,
    StaleKnowledgeState,
)


def _retrieval(**overrides: object) -> RetrievalEvidence:
    values: dict[str, object] = {
        "evidence_id": "retrieval:atlas:rank7",
        "query_ref": "query:rank7-context",
        "citation": CitationRankingMetadata(
            rank=1,
            retrieval_score=0.91,
            rerank_score=0.83,
            tie_breaker="newest-reviewed-source",
        ),
        "lineage": ChunkLineage(
            source_ref="atlas:index:v25",
            document_ref="doc:context-provenance",
            chunk_ref="chunk:context-provenance:003",
            chunk_index=3,
            chunk_count=12,
            embedding_model_ref="embedding:text-small",
            index_ref="index:atlas:v25",
        ),
        "explanation": RetrievalExplanation(
            strategy="hybrid_keyword_vector",
            match_signals=("title match", "proof tag match"),
            reason_codes=("ranked_high_similarity", "fresh_source"),
            limitation_notes=("citation shows summary metadata only",),
        ),
        "retrieved_at": "2026-06-11",
        "source_updated_at": "2026-06-01",
        "knowledge_cutoff": "2026-06-10",
        "stale_after": "2026-07-01",
    }
    values.update(overrides)
    return RetrievalEvidence(**values)


def test_retrieval_evidence_flags_stale_context_when_source_newer_than_cutoff():
    evidence = _retrieval(
        source_updated_at="2026-06-11",
        knowledge_cutoff="2026-06-10",
    )

    assert evidence.stale_knowledge.state is StaleKnowledgeState.STALE
    display = evidence.to_display_dict()
    assert display["stale_knowledge"]["state"] == "stale"
    assert display["stale_knowledge"]["reason"] == (
        "source update is newer than knowledge cutoff"
    )


def test_missing_retrieval_provenance_fails_closed_in_display_shape():
    evidence = _retrieval(
        evidence_id="",
        query_ref="",
        lineage=ChunkLineage(
            source_ref="",
            document_ref="",
            chunk_ref="",
            chunk_index=-4,
            chunk_count=-1,
        ),
    )

    display = evidence.to_display_dict()
    assert evidence.provenance_state is ProvenanceState.MISSING
    assert display["provenance_state"] == "missing"
    assert display["evidence_id"] == "retrieval:missing"
    assert display["query_ref"] == "query:missing"
    assert display["chunk_lineage"]["provenance_state"] == "missing"
    assert display["chunk_lineage"]["chunk_index"] == 0
    assert display["chunk_lineage"]["chunk_count"] == 0


def test_retrieval_explanation_is_deterministic_and_display_safe():
    evidence = _retrieval()

    left = evidence.to_display_dict()
    right = evidence.to_display_dict()

    assert left == right
    assert left["citation"] == {
        "rank": 1,
        "retrieval_score": 0.91,
        "rerank_score": 0.83,
        "tie_breaker": "newest-reviewed-source",
    }
    assert left["retrieval_explanation"] == {
        "strategy": "hybrid_keyword_vector",
        "match_signals": ("title match", "proof tag match"),
        "reason_codes": ("ranked_high_similarity", "fresh_source"),
        "limitation_notes": ("citation shows summary metadata only",),
    }


def test_memory_provenance_surfaces_conflicting_memory_records():
    conflict = MemoryConflictRecord(
        conflict_id="memory-conflict:preferred-editor",
        memory_ref="memory:editor:v1",
        conflicting_memory_ref="memory:editor:v2",
        field="preference.editor",
        resolution_state="unresolved",
        evidence_refs=("proof:memory-review",),
    )
    memory = MemoryProvenance(
        memory_id="memory:editor:v2",
        subject_ref="subject:user-preferences",
        source_ref="echo:explicit-user-correction",
        observed_at="2026-06-11",
        confidence=0.77,
        evidence_refs=("proof:memory-review",),
        conflict_records=(conflict,),
        decay_policy_note=MemoryDecayPolicyNote(
            state=MemoryDecayState.DECAYING,
            policy_ref="memory-policy:preference-decay",
            expires_at="2026-09-11",
            decay_reason="superseded by newer correction",
        ),
    )

    display = memory.to_display_dict()
    assert display["conflict_state"] == "conflicting"
    assert display["conflict_records"][0]["field"] == "preference.editor"
    assert display["decay_policy_note"]["state"] == "decaying"
    assert display["decay_policy_note"]["decay_reason"] == (
        "superseded by newer correction"
    )


def test_mistake_memory_capture_shape_never_enables_autonomous_write():
    capture = MistakeMemoryCaptureShape(
        capture_id="mistake-capture:rank7",
        mistake_ref="mistake:wrong-atlas-source",
        correction_ref="correction:user-confirmed-source",
        evidence_refs=("proof:correction-reviewed",),
        mode=MistakeCaptureMode.DISPLAY_ONLY,
    )
    memory = MemoryProvenance(
        memory_id="memory:atlas-source-correction",
        subject_ref="subject:atlas-routing",
        source_ref="echo:manual-review",
        mistake_capture=capture,
    )

    display = memory.to_display_dict()["mistake_capture"]
    assert display == {
        "capture_id": "mistake-capture:rank7",
        "mistake_ref": "mistake:wrong-atlas-source",
        "correction_ref": "correction:user-confirmed-source",
        "evidence_refs": ("proof:correction-reviewed",),
        "mode": "display_only",
        "autonomous_write_enabled": False,
    }


def test_display_dicts_do_not_leak_paths_prompts_transcripts_or_provider_responses():
    retrieval = _retrieval(
        evidence_id=r"C:\Users\scott\Code\Meridian\raw-retrieval.json",
        query_ref="raw prompt: include private deployment instructions",
        lineage=ChunkLineage(
            source_ref=r"C:\Users\scott\Code\Meridian\atlas.db",
            document_ref="provider response: private customer payload",
            chunk_ref="full transcript: user discussed hidden notes",
            chunk_index=1,
            chunk_count=1,
            embedding_model_ref="sk-proj-this-secret-must-not-leak-123456",
            index_ref="index:atlas:v25",
        ),
        explanation=RetrievalExplanation(
            strategy="provider response: raw text here",
            match_signals=("raw prompt: private prompt body",),
            reason_codes=(r"C:\Users\scott\Code\Meridian\reason.txt",),
            limitation_notes=("full transcript: private utterance",),
        ),
    )
    memory = MemoryProvenance(
        memory_id=r"C:\Users\scott\Code\Meridian\memory.json",
        subject_ref="raw prompt: user profile",
        source_ref="provider response: hidden payload",
        evidence_refs=(r"C:\Users\scott\Code\Meridian\evidence.log",),
        conflict_records=(
            MemoryConflictRecord(
                conflict_id="full transcript: conflict",
                memory_ref=r"C:\Users\scott\Code\Meridian\memory-a.json",
                conflicting_memory_ref="provider response: memory-b",
                field="raw prompt: field",
            ),
        ),
        decay_policy_note=MemoryDecayPolicyNote(
            state=MemoryDecayState.EXPIRED,
            policy_ref=r"C:\Users\scott\Code\Meridian\policy.json",
            decay_reason="provider response: raw response",
        ),
    )

    display_text = str((retrieval.to_display_dict(), memory.to_display_dict()))
    assert r"C:\Users\scott" not in display_text
    assert "private deployment instructions" not in display_text
    assert "private customer payload" not in display_text
    assert "hidden notes" not in display_text
    assert "this-secret-must-not-leak" not in display_text
    assert "raw text here" not in display_text
    assert "private prompt body" not in display_text
    assert "private utterance" not in display_text
    assert "hidden payload" not in display_text
    assert "provider response:" not in display_text.lower()
    assert "raw prompt:" not in display_text.lower()
    assert "full transcript:" not in display_text.lower()


def test_direct_stale_knowledge_detection_display_sanitizes_reason():
    detection = StaleKnowledgeDetection(
        state=StaleKnowledgeState.STALE,
        reason=r"reason embedding C:\Users\scott\Code\Meridian\secret.md",
        source_updated_at="2026-01-01",
        knowledge_cutoff="2025-01-01",
        stale_after="2025-06-01",
    )

    display = detection.to_display_dict()
    rendered = str(display)

    assert display["reason"] == "[redacted]"
    assert r"C:\Users\scott" not in rendered
