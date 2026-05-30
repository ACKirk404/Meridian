"""Tests for the Aegis proof/evidence slice (meridian_core/aegis.py)."""

from __future__ import annotations

import pytest

from meridian_core.aegis import (
    AegisEvidence,
    EvidenceSeverity,
    EvidenceStatus,
    EvidenceType,
    ProofTrail,
    evidence_from_cross_check,
)
from meridian_core.review_console import (
    ReviewConsoleItemType,
    ReviewConsoleSeverity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cc(
    id: str = "ev-1",
    source: str = "relay.py",
    target: str = "RelayRoute",
    summary: str = "Missing independence flag",
    severity: EvidenceSeverity = EvidenceSeverity.INFO,
) -> AegisEvidence:
    return evidence_from_cross_check(id, source, target, summary, severity)


def _blocking(id: str = "ev-block") -> AegisEvidence:
    return _cc(id=id, severity=EvidenceSeverity.ERROR)


# ---------------------------------------------------------------------------
# Cross-check finding becomes Aegis evidence
# ---------------------------------------------------------------------------


class TestCrossCheckBecomesEvidence:
    def test_evidence_type_is_cross_check(self):
        assert _cc().evidence_type is EvidenceType.CROSS_CHECK

    def test_status_starts_open(self):
        assert _cc().status is EvidenceStatus.OPEN

    def test_source_is_preserved(self):
        ev = _cc(source="risk.py")
        assert ev.source == "risk.py"

    def test_target_is_preserved(self):
        ev = _cc(target="RiskAssessment")
        assert ev.target == "RiskAssessment"

    def test_summary_is_preserved(self):
        ev = _cc(summary="Tier 4 not gated")
        assert ev.summary == "Tier 4 not gated"

    def test_severity_is_preserved(self):
        ev = _cc(severity=EvidenceSeverity.WARNING)
        assert ev.severity is EvidenceSeverity.WARNING

    def test_result_is_aegis_evidence_instance(self):
        assert isinstance(_cc(), AegisEvidence)

    def test_id_is_preserved(self):
        ev = _cc(id="xc-42")
        assert ev.id == "xc-42"

    def test_waiver_reason_empty_by_default(self):
        assert _cc().waiver_reason == ""

    def test_console_item_id_none_by_default(self):
        assert _cc().console_item_id is None


# ---------------------------------------------------------------------------
# Proof-blocking: open + high severity
# ---------------------------------------------------------------------------


class TestProofBlocking:
    def test_open_error_is_proof_blocking(self):
        assert _cc(severity=EvidenceSeverity.ERROR).is_proof_blocking() is True

    def test_open_critical_is_proof_blocking(self):
        assert _cc(severity=EvidenceSeverity.CRITICAL).is_proof_blocking() is True

    def test_open_info_is_not_proof_blocking(self):
        assert _cc(severity=EvidenceSeverity.INFO).is_proof_blocking() is False

    def test_open_warning_is_not_proof_blocking(self):
        assert _cc(severity=EvidenceSeverity.WARNING).is_proof_blocking() is False

    def test_escalated_is_proof_blocking_regardless_of_severity(self):
        ev = _cc(severity=EvidenceSeverity.INFO)
        ev.escalate()
        assert ev.is_proof_blocking() is True

    def test_escalated_critical_is_proof_blocking(self):
        ev = _cc(severity=EvidenceSeverity.CRITICAL)
        ev.escalate()
        assert ev.is_proof_blocking() is True


# ---------------------------------------------------------------------------
# Resolved evidence is no longer proof-blocking
# ---------------------------------------------------------------------------


class TestResolvedNotBlocking:
    def test_resolved_error_is_not_proof_blocking(self):
        ev = _blocking()
        ev.resolve()
        assert ev.is_proof_blocking() is False

    def test_resolved_critical_is_not_proof_blocking(self):
        ev = _cc(severity=EvidenceSeverity.CRITICAL)
        ev.resolve()
        assert ev.is_proof_blocking() is False

    def test_resolve_sets_status_to_resolved(self):
        ev = _blocking()
        ev.resolve()
        assert ev.status is EvidenceStatus.RESOLVED

    def test_resolved_info_is_not_proof_blocking(self):
        ev = _cc(severity=EvidenceSeverity.INFO)
        ev.resolve()
        assert ev.is_proof_blocking() is False


# ---------------------------------------------------------------------------
# Waived evidence records waiver reason
# ---------------------------------------------------------------------------


class TestWaived:
    def test_waived_evidence_is_not_proof_blocking(self):
        ev = _blocking()
        ev.waive("acknowledged by Scott on 2026-05-30")
        assert ev.is_proof_blocking() is False

    def test_waive_sets_status_to_waived(self):
        ev = _blocking()
        ev.waive("accepted risk")
        assert ev.status is EvidenceStatus.WAIVED

    def test_waive_records_reason(self):
        ev = _blocking()
        ev.waive("design decision; intentional omission")
        assert ev.waiver_reason == "design decision; intentional omission"

    def test_waive_preserves_other_fields(self):
        ev = _cc(id="ev-w", source="relay.py", severity=EvidenceSeverity.ERROR)
        ev.waive("accepted")
        assert ev.id == "ev-w"
        assert ev.source == "relay.py"
        assert ev.severity is EvidenceSeverity.ERROR

    def test_waived_info_is_not_proof_blocking(self):
        ev = _cc(severity=EvidenceSeverity.INFO)
        ev.waive("informational only")
        assert ev.is_proof_blocking() is False


# ---------------------------------------------------------------------------
# Evidence produces / references a Review Console item
# ---------------------------------------------------------------------------


class TestToConsoleItem:
    def test_non_blocking_produces_cross_check_item(self):
        item = _cc(severity=EvidenceSeverity.INFO).to_console_item()
        assert item.item_type is ReviewConsoleItemType.CROSS_CHECK

    def test_blocking_produces_approval_gate(self):
        item = _blocking().to_console_item()
        assert item.item_type is ReviewConsoleItemType.APPROVAL_GATE

    def test_console_item_id_derived_from_evidence_id(self):
        item = _cc(id="ev-99").to_console_item()
        assert item.id == "aegis-ev-99"

    def test_console_item_severity_matches_evidence_info(self):
        item = _cc(severity=EvidenceSeverity.INFO).to_console_item()
        assert item.severity is ReviewConsoleSeverity.INFO

    def test_console_item_severity_matches_evidence_error(self):
        item = _blocking().to_console_item()
        assert item.severity is ReviewConsoleSeverity.ERROR

    def test_console_item_severity_matches_evidence_critical(self):
        item = _cc(severity=EvidenceSeverity.CRITICAL).to_console_item()
        assert item.severity is ReviewConsoleSeverity.CRITICAL

    def test_console_item_severity_matches_evidence_warning(self):
        item = _cc(severity=EvidenceSeverity.WARNING).to_console_item()
        assert item.severity is ReviewConsoleSeverity.WARNING

    def test_blocking_gate_requires_response(self):
        item = _blocking().to_console_item()
        assert item.requires_response is True

    def test_non_blocking_does_not_require_response(self):
        item = _cc(severity=EvidenceSeverity.INFO).to_console_item()
        assert item.requires_response is False

    def test_resolved_blocking_produces_cross_check_item(self):
        ev = _blocking()
        ev.resolve()
        item = ev.to_console_item()
        assert item.item_type is ReviewConsoleItemType.CROSS_CHECK

    def test_waived_blocking_produces_cross_check_item(self):
        ev = _blocking()
        ev.waive("accepted")
        item = ev.to_console_item()
        assert item.item_type is ReviewConsoleItemType.CROSS_CHECK

    def test_summary_appears_in_console_item_title(self):
        ev = _cc(summary="Route mismatch detected")
        item = ev.to_console_item()
        assert "Route mismatch detected" in item.title

    def test_source_and_target_appear_in_content(self):
        ev = _cc(source="relay.py", target="RelayRoute")
        item = ev.to_console_item()
        assert "relay.py" in item.content
        assert "RelayRoute" in item.content


# ---------------------------------------------------------------------------
# ProofTrail
# ---------------------------------------------------------------------------


class TestProofTrail:
    def test_empty_trail_is_clean(self):
        assert ProofTrail().is_clean() is True

    def test_add_appends_evidence(self):
        trail = ProofTrail()
        ev = _cc()
        trail.add(ev)
        assert ev in trail.evidence

    def test_blocking_returns_only_blocking_evidence(self):
        trail = ProofTrail()
        trail.add(_cc(id="info", severity=EvidenceSeverity.INFO))
        trail.add(_blocking(id="err"))
        blocking = trail.blocking()
        assert len(blocking) == 1
        assert blocking[0].id == "err"

    def test_trail_with_blocking_evidence_is_not_clean(self):
        trail = ProofTrail()
        trail.add(_blocking())
        assert trail.is_clean() is False

    def test_trail_becomes_clean_after_resolve(self):
        trail = ProofTrail()
        ev = _blocking()
        trail.add(ev)
        ev.resolve()
        assert trail.is_clean() is True

    def test_trail_becomes_clean_after_waive(self):
        trail = ProofTrail()
        ev = _blocking()
        trail.add(ev)
        ev.waive("accepted")
        assert trail.is_clean() is True

    def test_open_findings_returns_open_only(self):
        trail = ProofTrail()
        ev_open = _cc(id="open")
        ev_resolved = _cc(id="resolved")
        ev_resolved.resolve()
        trail.add(ev_open)
        trail.add(ev_resolved)
        open_list = trail.open_findings()
        assert ev_open in open_list
        assert ev_resolved not in open_list

    def test_blocking_preserves_insertion_order(self):
        trail = ProofTrail()
        for i in range(4):
            trail.add(_cc(id=f"ev-{i}", severity=EvidenceSeverity.ERROR))
        ids = [e.id for e in trail.blocking()]
        assert ids == ["ev-0", "ev-1", "ev-2", "ev-3"]


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_is_proof_blocking_is_deterministic(self):
        ev = _blocking()
        assert ev.is_proof_blocking() == ev.is_proof_blocking()

    def test_to_console_item_produces_same_type_each_call(self):
        ev = _blocking()
        assert ev.to_console_item().item_type == ev.to_console_item().item_type

    def test_proof_trail_blocking_is_stable(self):
        trail = ProofTrail()
        trail.add(_blocking(id="a"))
        trail.add(_blocking(id="b"))
        assert [e.id for e in trail.blocking()] == [e.id for e in trail.blocking()]

    @pytest.mark.parametrize("sev", [
        EvidenceSeverity.INFO,
        EvidenceSeverity.WARNING,
        EvidenceSeverity.ERROR,
        EvidenceSeverity.CRITICAL,
    ])
    def test_open_evidence_blocking_is_consistent(self, sev):
        ev = _cc(severity=sev)
        assert ev.is_proof_blocking() == ev.is_proof_blocking()
