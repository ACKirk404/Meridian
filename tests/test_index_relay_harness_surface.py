"""Regression checks for the visible Relay harness surface in index.html."""

from __future__ import annotations

from pathlib import Path


INDEX = Path(__file__).resolve().parents[1] / "index.html"


def _html() -> str:
    return INDEX.read_text(encoding="utf-8")


def test_relay_harness_click_renders_logic_surface() -> None:
    html = _html()
    assert "button.dataset.harness === 'Relay'" in html
    assert "renderRelayHarness()" in html
    assert "harness-logic-surface" in html


def test_relay_harness_hides_prompt_interface() -> None:
    html = _html()
    assert ".session-window-right.is-harness-mode .session-interface" in html
    assert ".session-window-right.is-harness-mode .session-prompt-input" in html
    assert ".session-window-right.is-harness-mode .session-response-output" in html
    assert ".session-window-right.is-harness-mode .session-text-slider" in html
    assert "display: none;" in html


def test_relay_harness_logic_body_scrolls() -> None:
    html = _html()
    assert ".harness-logic-body" in html
    assert "overflow: auto;" in html


def test_relay_harness_shows_backend_audit_contract() -> None:
    html = _html()
    for expected in (
        "meridian_core/relay.py RelayRouteAudit",
        "account_session",
        "local_cli",
        "direct_api",
        "aggregator_api",
        "aggregator_cannot_be_authoritative",
        "independent_dual_model_lanes",
        "prompt_payload_budget",
        "Auto disabled",
    ):
        assert expected in html
