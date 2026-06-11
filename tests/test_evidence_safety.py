"""Tests for V2.5 evidence safety and redaction proof baseline."""

from __future__ import annotations

from meridian_core.evidence_safety import (
    EvidenceSafetyCategory,
    EvidenceSafetyFinding,
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


def test_direct_evidence_safety_finding_display_sanitizes_unsafe_fields():
    finding = EvidenceSafetyFinding(
        artifact_id=r"C:\Users\scott\Code\Meridian\artifact.log",
        category=EvidenceSafetyCategory.SECRET,
        severity=EvidenceSafetySeverity.CRITICAL,
        reason=r"traceback at C:\Users\scott\Code\Meridian\secret.log with token=sk-proj-this-must-not-leak-1234567890",
    )

    display = finding.to_display_dict()
    rendered = str(display)

    assert display["artifact_id"] == "artifact:unsafe-id"
    assert display["reason"] == "[redacted]"
    assert r"C:\Users\scott" not in rendered
    assert "this-must-not-leak" not in rendered


def test_direct_evidence_safety_finding_display_redacts_credential_artifact_id():
    finding = EvidenceSafetyFinding(
        artifact_id="artifact:api_key=abcdef1234567890",
        category=EvidenceSafetyCategory.SECRET,
        severity=EvidenceSafetySeverity.CRITICAL,
        reason="credential pattern observed",
    )

    display = finding.to_display_dict()
    rendered = str(display)

    assert display["artifact_id"] == "artifact:unsafe-id"
    assert "abcdef1234567890" not in rendered
    assert "api_key=" not in rendered


def test_direct_evidence_safety_finding_display_redacts_raw_prompt_artifact_id():
    finding = EvidenceSafetyFinding(
        artifact_id="artifact:raw prompt: hidden body",
        category=EvidenceSafetyCategory.RAW_PROMPT,
        severity=EvidenceSafetySeverity.ERROR,
        reason="raw prompt marker detected",
    )

    display = finding.to_display_dict()
    rendered = str(display)

    assert display["artifact_id"] == "artifact:unsafe-id"
    assert "hidden body" not in rendered


def test_direct_evidence_safety_finding_display_redacts_provider_output_artifact_id():
    finding = EvidenceSafetyFinding(
        artifact_id="artifact:provider output: confidential payload",
        category=EvidenceSafetyCategory.PROVIDER_RESPONSE,
        severity=EvidenceSafetySeverity.ERROR,
        reason="raw provider response marker detected",
    )

    display = finding.to_display_dict()
    rendered = str(display)

    assert display["artifact_id"] == "artifact:unsafe-id"
    assert "confidential payload" not in rendered


def test_scan_redacts_unsafe_credential_artifact_id_in_finding_records():
    proof = scan_evidence_artifacts(
        (
            (
                "artifact:api_key=abcdef1234567890",
                "raw prompt: hidden body",
            ),
        )
    )

    assert proof.status is EvidenceSafetyStatus.FAIL
    for finding in proof.findings:
        assert finding.artifact_id == "artifact:unsafe-id"
    rendered = str(proof.to_display_dict())
    assert "abcdef1234567890" not in rendered
    assert "api_key=" not in rendered


def test_scan_redacts_full_prompt_artifact_id_and_raw_prompt_reason_body():
    proof = scan_evidence_artifact(
        artifact_id="artifact:full prompt: hidden body",
        text="raw prompt: separate unsafe text",
    )

    display = proof.to_display_dict()
    rendered = str(display)
    assert proof.status is EvidenceSafetyStatus.FAIL
    for finding in display["findings"]:
        assert finding["artifact_id"] == "artifact:unsafe-id"
    assert "full prompt" not in rendered
    assert "hidden body" not in rendered
    assert "separate unsafe text" not in rendered


def test_direct_finding_redacts_full_prompt_reason_body():
    finding = EvidenceSafetyFinding(
        artifact_id="proof:full-prompt-reason",
        category=EvidenceSafetyCategory.RAW_PROMPT,
        severity=EvidenceSafetySeverity.ERROR,
        reason="full prompt: hidden body",
    )

    display = finding.to_display_dict()
    assert display["reason"] == "[redacted]"
    assert "hidden body" not in str(display)


def test_direct_finding_redacts_complete_prompt_and_complete_transcript_reason_bodies():
    for reason in (
        "complete prompt: confidential plan",
        "complete transcript: confidential plan",
        "full transcript: confidential plan",
    ):
        finding = EvidenceSafetyFinding(
            artifact_id="proof:reason-variant",
            category=EvidenceSafetyCategory.RAW_PROMPT,
            severity=EvidenceSafetySeverity.ERROR,
            reason=reason,
        )
        display = finding.to_display_dict()
        assert display["reason"] == "[redacted]"
        assert "confidential plan" not in str(display)


def test_direct_finding_redacts_github_token_shaped_artifact_id():
    for prefix in ("ghp_", "gho_", "ghu_", "ghs_", "ghr_"):
        token = f"artifact:{prefix}abcdefghijklmnopqrstuvwxyz0123456789"
        finding = EvidenceSafetyFinding(
            artifact_id=token,
            category=EvidenceSafetyCategory.SECRET,
            severity=EvidenceSafetySeverity.CRITICAL,
            reason="possible credential or secret token detected",
        )
        display = finding.to_display_dict()
        rendered = str(display)
        assert display["artifact_id"] == "artifact:unsafe-id"
        assert prefix not in rendered
        assert "abcdefghijklmnopqrstuvwxyz0123456789" not in rendered


def test_direct_finding_redacts_fine_grained_github_pat_artifact_id():
    pat = "github_pat_abcdefghijklmnopqrstuvwxyz0123456789_ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    finding = EvidenceSafetyFinding(
        artifact_id=f"artifact:{pat}",
        category=EvidenceSafetyCategory.SECRET,
        severity=EvidenceSafetySeverity.CRITICAL,
        reason=f"possible credential or secret token detected {pat}",
    )
    display = finding.to_display_dict()
    rendered = str(display)
    assert display["artifact_id"] == "artifact:unsafe-id"
    assert display["reason"] == "[redacted]"
    assert "github_pat_" not in rendered
    assert "abcdefghijklmnopqrstuvwxyz0123456789" not in rendered
    assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in rendered


def test_scan_evidence_artifact_flags_fine_grained_github_pat_secret():
    pat = "github_pat_abcdefghijklmnopqrstuvwxyz0123456789_ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    proof = scan_evidence_artifact(
        artifact_id="proof:fine-grained-pat",
        text=f"leaked credential value {pat} should be flagged",
    )

    assert proof.status is EvidenceSafetyStatus.FAIL
    categories = tuple(f.category for f in proof.findings)
    assert EvidenceSafetyCategory.SECRET in categories
    rendered = str(proof.to_display_dict())
    assert "github_pat_" not in rendered
    assert "abcdefghijklmnopqrstuvwxyz0123456789" not in rendered
    assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in rendered
