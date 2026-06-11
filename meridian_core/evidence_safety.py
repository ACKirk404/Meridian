"""Display-safe evidence safety checks for V2.5 backend hardening.

The scanner is intentionally conservative. It reports categories and stable
artifact ids, but never returns the matched unsafe text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class EvidenceSafetyCategory(Enum):
    SECRET = "secret"
    LOCAL_PATH = "local_path"
    RAW_PROMPT = "raw_prompt"
    RAW_TRANSCRIPT = "raw_transcript"
    PROVIDER_RESPONSE = "provider_response"
    MISSING_TEXT = "missing_text"


class EvidenceSafetySeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EvidenceSafetyStatus(Enum):
    PASS = "pass"
    FAIL = "fail"


_CHECKED_CATEGORIES: tuple[EvidenceSafetyCategory, ...] = (
    EvidenceSafetyCategory.SECRET,
    EvidenceSafetyCategory.LOCAL_PATH,
    EvidenceSafetyCategory.RAW_PROMPT,
    EvidenceSafetyCategory.RAW_TRANSCRIPT,
    EvidenceSafetyCategory.PROVIDER_RESPONSE,
)


@dataclass(frozen=True)
class EvidenceSafetyFinding:
    artifact_id: str
    category: EvidenceSafetyCategory
    severity: EvidenceSafetySeverity
    reason: str

    def to_display_dict(self) -> dict[str, str]:
        return {
            "artifact_id": _safe_artifact_id(self.artifact_id),
            "category": self.category.value,
            "severity": self.severity.value,
            "reason": _safe_reason(self.reason),
        }


@dataclass(frozen=True)
class EvidenceSafetyProof:
    status: EvidenceSafetyStatus
    artifact_count: int
    checked_categories: tuple[EvidenceSafetyCategory, ...]
    findings: tuple[EvidenceSafetyFinding, ...]

    @property
    def summary(self) -> str:
        if self.status is EvidenceSafetyStatus.PASS:
            return "evidence safety passed"
        return f"evidence safety failed with {len(self.findings)} finding(s)"

    def to_display_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "artifact_count": self.artifact_count,
            "checked_categories": tuple(category.value for category in self.checked_categories),
            "finding_count": len(self.findings),
            "summary": self.summary,
            "findings": tuple(finding.to_display_dict() for finding in self.findings),
        }


@dataclass(frozen=True)
class _PatternRule:
    category: EvidenceSafetyCategory
    severity: EvidenceSafetySeverity
    reason: str
    pattern: re.Pattern[str]


_RULES: tuple[_PatternRule, ...] = (
    _PatternRule(
        category=EvidenceSafetyCategory.SECRET,
        severity=EvidenceSafetySeverity.CRITICAL,
        reason="possible credential or secret token detected",
        pattern=re.compile(
            r"(?i)\b("
            r"(?:api[_-]?key|secret|token|password|credential)\s*[:=]\s*\S{8,}"
            r"|sk-(?:proj-)?[A-Za-z0-9_-]{16,}"
            r"|gh[pousr]_[A-Za-z0-9_]{20,}"
            r"|github_pat_[A-Za-z0-9_]{20,}"
            r")"
        ),
    ),
    _PatternRule(
        category=EvidenceSafetyCategory.LOCAL_PATH,
        severity=EvidenceSafetySeverity.ERROR,
        reason="local absolute filesystem path detected",
        pattern=re.compile(
            r"(?i)(?:[A-Z]:\\(?:Users|My Drive|Code|ProgramData|Windows|Temp)\\|"
            r"\\\\[^\\\s]+\\[^\\\s]+\\|"
            r"/(?:Users|home|var|tmp|mnt|Volumes)/)"
        ),
    ),
    _PatternRule(
        category=EvidenceSafetyCategory.RAW_PROMPT,
        severity=EvidenceSafetySeverity.ERROR,
        reason="raw prompt marker detected",
        pattern=re.compile(r"(?i)\b(raw|full|complete)\s+prompt\s*:"),
    ),
    _PatternRule(
        category=EvidenceSafetyCategory.RAW_TRANSCRIPT,
        severity=EvidenceSafetySeverity.ERROR,
        reason="raw transcript marker detected",
        pattern=re.compile(r"(?i)\b(raw|full|complete)\s+transcript\s*:"),
    ),
    _PatternRule(
        category=EvidenceSafetyCategory.PROVIDER_RESPONSE,
        severity=EvidenceSafetySeverity.ERROR,
        reason="raw provider response marker detected",
        pattern=re.compile(r"(?i)\b(provider|model)\s+(response|output)\s*:"),
    ),
)


def scan_evidence_artifact(artifact_id: str, text: object) -> EvidenceSafetyProof:
    """Scan one evidence artifact and return a display-safe proof."""
    artifact_key = _clean_artifact_id(artifact_id)
    findings = _findings_for_artifact(artifact_key, text)
    return EvidenceSafetyProof(
        status=EvidenceSafetyStatus.FAIL if findings else EvidenceSafetyStatus.PASS,
        artifact_count=1,
        checked_categories=_CHECKED_CATEGORIES,
        findings=findings,
    )


def scan_evidence_artifacts(
    artifacts: Iterable[tuple[str, object]],
) -> EvidenceSafetyProof:
    """Scan multiple evidence artifacts and aggregate a display-safe proof."""
    all_findings: list[EvidenceSafetyFinding] = []
    artifact_count = 0
    for artifact_id, text in artifacts:
        artifact_count += 1
        artifact_key = _clean_artifact_id(artifact_id)
        all_findings.extend(_findings_for_artifact(artifact_key, text))

    findings = tuple(all_findings)
    return EvidenceSafetyProof(
        status=EvidenceSafetyStatus.FAIL if findings else EvidenceSafetyStatus.PASS,
        artifact_count=artifact_count,
        checked_categories=_CHECKED_CATEGORIES,
        findings=findings,
    )


def _clean_artifact_id(artifact_id: str) -> str:
    clean = artifact_id.strip()
    if not clean:
        raise ValueError("artifact_id must not be empty")
    if _looks_like_local_path(clean) or _looks_like_unsafe_reason(clean):
        return "artifact:unsafe-id"
    return clean


def _findings_for_artifact(artifact_id: str, text: object) -> tuple[EvidenceSafetyFinding, ...]:
    if text is None:
        return (
            EvidenceSafetyFinding(
                artifact_id=artifact_id,
                category=EvidenceSafetyCategory.MISSING_TEXT,
                severity=EvidenceSafetySeverity.ERROR,
                reason="artifact text is missing",
            ),
        )

    content = str(text)
    findings: list[EvidenceSafetyFinding] = []
    for rule in _RULES:
        if rule.pattern.search(content):
            findings.append(
                EvidenceSafetyFinding(
                    artifact_id=artifact_id,
                    category=rule.category,
                    severity=rule.severity,
                    reason=rule.reason,
                )
            )
    return tuple(findings)


def _looks_like_local_path(value: str) -> bool:
    return bool(
        re.search(
            r"(?i)(?:[A-Z]:\\|\\\\[^\\\s]+\\[^\\\s]+\\|/(?:Users|home|var|tmp|mnt|Volumes)/)",
            value,
        )
    )


def _safe_artifact_id(value: str) -> str:
    clean = str(value).strip()
    if not clean:
        return "artifact:unknown-id"
    if _looks_like_local_path(clean):
        return "artifact:unsafe-id"
    if _looks_like_unsafe_reason(clean):
        return "artifact:unsafe-id"
    return clean[:120]


def _safe_reason(value: str) -> str:
    clean = re.sub(r"\s+", " ", str(value).strip())
    if not clean:
        return "[redacted]"
    if _looks_like_local_path(clean):
        return "[redacted]"
    if _looks_like_unsafe_reason(clean):
        return "[redacted]"
    return clean[:240]


def _looks_like_unsafe_reason(value: str) -> bool:
    return bool(
        re.search(
            r"(?i)(?:traceback|exception:|"
            r"(?:raw|full|complete)\s+(?:prompt|transcript|content|log)|"
            r"provider\s+(?:response|output)|model\s+(?:response|output)|"
            r"\b(?:api[_-]?key|secret|token|password|credential)\s*[:=]\s*\S{8,}|"
            r"sk-(?:proj-)?[A-Za-z0-9_-]{16,}|"
            r"gh[pousr]_[A-Za-z0-9_]{20,}|"
            r"github_pat_[A-Za-z0-9_]{20,})",
            value,
        )
    )
