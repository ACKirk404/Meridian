"""Tests for the prime_wake, prime_console, prime_status CLI commands."""

from __future__ import annotations

from pathlib import Path

from meridian_core.cli import prime_approve, prime_console, prime_status, prime_wake
from meridian_core.review_console import (
    ReviewConsoleItemType,
    ReviewConsoleQueue,
    make_approval_gate,
    route_to_console,
)

_VALID_MISSION = """\
# Meridian Mission

## Prime Directives

1. Logic, not rules.
2. Prime reads this mission file before meaningful action.
3. Prime states progress intention before meaningful work.

## Harness Boot Order

1. Bifrost
2. Beacon
3. Echo

## Current Mission Objective

Build the V0 prime wake surface.

## Queue Display Guidance

Orchestrator Queue:
Prime's conversational messages.

Non-Orchestrator Queue:
System messages and harness health.
"""


class TestPrimeWakeSuccess:
    def test_output_includes_mission_objective(self, tmp_path: Path, capsys) -> None:
        f = tmp_path / "MISSION.md"
        f.write_text(_VALID_MISSION, encoding="utf-8")
        prime_wake(mission_path=f)
        out = capsys.readouterr().out
        assert "Build the V0 prime wake surface" in out

    def test_output_includes_prime_online_title(self, tmp_path: Path, capsys) -> None:
        f = tmp_path / "MISSION.md"
        f.write_text(_VALID_MISSION, encoding="utf-8")
        prime_wake(mission_path=f)
        out = capsys.readouterr().out
        assert "Prime online." in out

    def test_output_includes_canonical_harness_statuses(self, tmp_path: Path, capsys) -> None:
        f = tmp_path / "MISSION.md"
        f.write_text(_VALID_MISSION, encoding="utf-8")
        prime_wake(mission_path=f)
        out = capsys.readouterr().out
        for harness in ("Bifrost", "Beacon", "Relay", "Groot"):
            assert harness in out, f"{harness} missing from wake output"

    def test_output_is_deterministic(self, tmp_path: Path, capsys) -> None:
        f = tmp_path / "MISSION.md"
        f.write_text(_VALID_MISSION, encoding="utf-8")
        prime_wake(mission_path=f)
        first = capsys.readouterr().out
        prime_wake(mission_path=f)
        second = capsys.readouterr().out
        assert first == second


class TestPrimeWakeMissionFailure:
    def test_missing_mission_prints_readable_failure(self, tmp_path: Path, capsys) -> None:
        prime_wake(mission_path=tmp_path / "MISSION.md")
        out = capsys.readouterr().out
        assert "Mission load failed" in out

    def test_corrupt_mission_prints_readable_failure(self, tmp_path: Path, capsys) -> None:
        f = tmp_path / "MISSION.md"
        f.write_text("# Broken\nNo sections here.", encoding="utf-8")
        prime_wake(mission_path=f)
        out = capsys.readouterr().out
        assert "Mission load failed" in out

    def test_missing_mission_does_not_raise(self, tmp_path: Path) -> None:
        prime_wake(mission_path=tmp_path / "MISSION.md")

    def test_corrupt_mission_does_not_raise(self, tmp_path: Path) -> None:
        f = tmp_path / "MISSION.md"
        f.write_text("garbage", encoding="utf-8")
        prime_wake(mission_path=f)


class TestPrimeConsole:
    def test_empty_console_is_deterministic(self, capsys) -> None:
        q = ReviewConsoleQueue()
        prime_console(console=q)
        first = capsys.readouterr().out
        prime_console(console=q)
        second = capsys.readouterr().out
        assert first == second

    def test_empty_console_prints_readable_message(self, capsys) -> None:
        q = ReviewConsoleQueue()
        prime_console(console=q)
        out = capsys.readouterr().out
        assert "no pending items" in out

    def test_pending_item_appears_in_output(self, capsys) -> None:
        q = ReviewConsoleQueue()
        route_to_console(ReviewConsoleItemType.SYSTEM_FINDING, "Test finding", "from harness", console=q)
        prime_console(console=q)
        out = capsys.readouterr().out
        assert "Test finding" in out

    def test_item_status_appears_in_output(self, capsys) -> None:
        q = ReviewConsoleQueue()
        route_to_console(ReviewConsoleItemType.CROSS_CHECK, "Check result", console=q)
        prime_console(console=q)
        out = capsys.readouterr().out
        assert "pending" in out

    def test_item_type_appears_in_output(self, capsys) -> None:
        q = ReviewConsoleQueue()
        route_to_console(ReviewConsoleItemType.APPROVAL_GATE, "Approve release", console=q)
        prime_console(console=q)
        out = capsys.readouterr().out
        assert "approval_gate" in out

    def test_item_provenance_appears_in_output(self, capsys) -> None:
        q = ReviewConsoleQueue()
        route_to_console(ReviewConsoleItemType.SYSTEM_FINDING, "Summary", "provenance-source", console=q)
        prime_console(console=q)
        out = capsys.readouterr().out
        assert "provenance-source" in out


class TestPrimeStatus:
    def test_includes_prime_online_header(self, tmp_path: Path, capsys) -> None:
        f = tmp_path / "MISSION.md"
        f.write_text(_VALID_MISSION, encoding="utf-8")
        q = ReviewConsoleQueue()
        prime_status(mission_path=f, console=q)
        out = capsys.readouterr().out
        assert "Prime online." in out

    def test_includes_console_section(self, tmp_path: Path, capsys) -> None:
        f = tmp_path / "MISSION.md"
        f.write_text(_VALID_MISSION, encoding="utf-8")
        q = ReviewConsoleQueue()
        prime_status(mission_path=f, console=q)
        out = capsys.readouterr().out
        assert "Review Console" in out

    def test_console_items_appear_in_status(self, tmp_path: Path, capsys) -> None:
        f = tmp_path / "MISSION.md"
        f.write_text(_VALID_MISSION, encoding="utf-8")
        q = ReviewConsoleQueue()
        route_to_console(ReviewConsoleItemType.PLAN_REVIEW, "Pending approval", console=q)
        prime_status(mission_path=f, console=q)
        out = capsys.readouterr().out
        assert "Pending approval" in out

    def test_console_still_renders_after_mission_load_failure(self, tmp_path: Path, capsys) -> None:
        q = ReviewConsoleQueue()
        route_to_console(ReviewConsoleItemType.SYSTEM_FINDING, "Console item", console=q)
        prime_status(mission_path=tmp_path / "MISSION.md", console=q)
        out = capsys.readouterr().out
        assert "Mission load failed" in out
        assert "Review Console" in out


class TestRouteToConsole:
    def test_creates_item_with_correct_type(self) -> None:
        q = ReviewConsoleQueue()
        item = route_to_console(ReviewConsoleItemType.CROSS_CHECK, "x", console=q)
        assert item.item_type is ReviewConsoleItemType.CROSS_CHECK

    def test_creates_item_with_correct_summary(self) -> None:
        q = ReviewConsoleQueue()
        item = route_to_console(ReviewConsoleItemType.SYSTEM_FINDING, "my summary", console=q)
        assert item.title == "my summary"

    def test_creates_item_with_correct_provenance(self) -> None:
        q = ReviewConsoleQueue()
        item = route_to_console(ReviewConsoleItemType.SYSTEM_FINDING, "s", "my-harness", console=q)
        assert item.content == "my-harness"

    def test_item_is_enqueued(self) -> None:
        q = ReviewConsoleQueue()
        route_to_console(ReviewConsoleItemType.SYSTEM_FINDING, "s", console=q)
        assert len(q.pending()) == 1

    def test_accepts_string_item_type(self) -> None:
        q = ReviewConsoleQueue()
        item = route_to_console("system_finding", "s", console=q)
        assert item.item_type is ReviewConsoleItemType.SYSTEM_FINDING

    def test_item_id_is_deterministic(self) -> None:
        q = ReviewConsoleQueue()
        item = route_to_console(ReviewConsoleItemType.SYSTEM_FINDING, "s", console=q)
        assert item.id == "rc-0000"

class TestPrimeApprove:
    def _gate(self, q, item_id="rc-0000"):
        item = make_approval_gate(item_id, "Release approval", "Approve the v0.1 release")
        q.enqueue(item)

    def test_approve_gate_item_prints_confirmation(self, capsys):
        q = ReviewConsoleQueue()
        self._gate(q, "rc-0000")
        prime_approve("rc-0000", console=q)
        out = capsys.readouterr().out
        assert "Approved" in out
        assert "rc-0000" in out

    def test_approve_gate_item_shows_resulting_status(self, capsys):
        q = ReviewConsoleQueue()
        self._gate(q, "rc-0000")
        prime_approve("rc-0000", console=q)
        out = capsys.readouterr().out
        assert "responded" in out

    def test_approve_gate_item_changes_domain_status(self):
        q = ReviewConsoleQueue()
        self._gate(q, "rc-0000")
        prime_approve("rc-0000", console=q)
        assert q.get("rc-0000").status.value == "responded"

    def test_approve_unknown_id_prints_not_found(self, capsys):
        q = ReviewConsoleQueue()
        prime_approve("rc-9999", console=q)
        out = capsys.readouterr().out
        assert "Not found" in out
        assert "rc-9999" in out

    def test_approve_unknown_id_does_not_raise(self):
        q = ReviewConsoleQueue()
        prime_approve("rc-9999", console=q)

    def test_approve_non_promptable_item_prints_error(self, capsys):
        q = ReviewConsoleQueue()
        route_to_console(ReviewConsoleItemType.SYSTEM_FINDING, "Finding", console=q)
        prime_approve("rc-0000", console=q)
        out = capsys.readouterr().out
        assert "Cannot approve" in out

    def test_approve_item_without_approve_action_prints_error(self, capsys):
        q = ReviewConsoleQueue()
        route_to_console(ReviewConsoleItemType.CROSS_CHECK, "Check", console=q)
        prime_approve("rc-0000", console=q)
        out = capsys.readouterr().out
        assert "Cannot approve" in out
