"""Tests for V2.5 evidence safety and redaction proof baseline."""

from __future__ import annotations

from meridian_core.evidence_safety import (
    EvidenceSafetyCategory,
    EvidenceSafetySeverity,
    EvidenceSafetyStatus,
    scan_evidence_artifact,
    scan_evidence_artifacts,
)


def test_safe_artifact_passes_with_display_safe_summary():
    proof = scan_evidence_artifact(
        artifact_id="proof:route-summary",
        text="route evidence refs: proof:abc123; status=allow; model_label=trusted",
    )

    assert proof.status is EvidenceSafetyStatus.PASS
    assert proof.findings == ()
    assert proof.summary == "evidence safety passed"
    assert proof.checked_categories == (
        EvidenceSafetyCategory.SECRET,
        EvidenceSafetyCategory.LOCAL_PATH,
        EvidenceSafetyCategory.RAW_PROMPT,
        EvidenceSafetyCategory.RAW_TRANSCRIPT,
        EvidenceSafetyCategory.PROVIDER_RESPONSE,
    )


def test_secret_like_value_fails_without_echoing_secret():
    proof = scan_evidence_artifact(
        artifact_id="proof:unsafe-secret",
        text="OPENAI_API_KEY=sk-proj-this-value-must-not-leak-1234567890",
    )

    assert proof.status is EvidenceSafetyStatus.FAIL
    assert proof.findings[0].category is EvidenceSafetyCategory.SECRET
    assert proof.findings[0].severity is EvidenceSafetySeverity.CRITICAL
    assert "sk-proj-this-value" not in proof.findings[0].reason
    assert "sk-proj-this-value" not in proof.summary
    assert "sk-proj-this-value" not in proof.to_display_dict()["summary"]


def test_windows_local_path_fails_without_echoing_path():
    proof = scan_evidence_artifact(
        artifact_id="proof:unsafe-path",
        text=r"proof was written to C:\Users\scott\Code\Meridian\.env",
    )

    assert proof.status is EvidenceSafetyStatus.FAIL
    assert proof.findings[0].category is EvidenceSafetyCategory.LOCAL_PATH
    assert r"C:\Users\scott" not in proof.findings[0].reason
    assert r"C:\Users\scott" not in str(proof.to_display_dict())


def test_raw_prompt_marker_fails_without_echoing_prompt_body():
    proof = scan_evidence_artifact(
        artifact_id="proof:unsafe-prompt",
        text="raw prompt: please include private deployment credentials in output",
    )

    assert proof.status is EvidenceSafetyStatus.FAIL
    assert proof.findings[0].category is EvidenceSafetyCategory.RAW_PROMPT
    assert "deployment credentials" not in proof.findings[0].reason
    assert "deployment credentials" not in str(proof.to_display_dict())


def test_raw_transcript_marker_fails_without_echoing_transcript_body():
    proof = scan_evidence_artifact(
        artifact_id="proof:unsafe-transcript",
        text="full transcript: user said the private recovery phrase is hidden here",
    )

    assert proof.status is EvidenceSafetyStatus.FAIL
    assert proof.findings[0].category is EvidenceSafetyCategory.RAW_TRANSCRIPT
    assert "recovery phrase" not in proof.findings[0].reason
    assert "recovery phrase" not in str(proof.to_display_dict())


def test_provider_response_marker_fails_without_echoing_response_body():
    proof = scan_evidence_artifact(
        artifact_id="proof:unsafe-provider-response",
        text="provider response: model returned private customer payload",
    )

    assert proof.status is EvidenceSafetyStatus.FAIL
    assert proof.findings[0].category is EvidenceSafetyCategory.PROVIDER_RESPONSE
    assert "customer payload" not in proof.findings[0].reason
    assert "customer payload" not in str(proof.to_display_dict())


def test_multiple_artifacts_aggregate_fail_closed_and_keep_counts():
    proof = scan_evidence_artifacts(
        (
            ("proof:safe", "status=allow; evidence_refs=proof:one"),
            ("proof:secret", "api_key = abcdef1234567890abcdef1234567890"),
            ("proof:path", r"local path: G:\My Drive\Obsidian\secret.md"),
        )
    )

    assert proof.status is EvidenceSafetyStatus.FAIL
    assert proof.artifact_count == 3
    assert len(proof.findings) == 2
    assert {finding.category for finding in proof.findings} == {
        EvidenceSafetyCategory.SECRET,
        EvidenceSafetyCategory.LOCAL_PATH,
    }
    assert "abcdef1234567890" not in str(proof.to_display_dict())
    assert r"G:\My Drive" not in str(proof.to_display_dict())


def test_empty_artifact_id_is_rejected():
    try:
        scan_evidence_artifact(artifact_id=" ", text="safe")
    except ValueError as exc:
        assert "artifact_id" in str(exc)
    else:
        raise AssertionError("empty artifact_id should be rejected")


def test_none_text_fails_closed_as_missing_artifact_text():
    proof = scan_evidence_artifact(artifact_id="proof:missing", text=None)

    assert proof.status is EvidenceSafetyStatus.FAIL
    assert proof.findings[0].category is EvidenceSafetyCategory.MISSING_TEXT
    assert proof.findings[0].severity is EvidenceSafetySeverity.ERROR
