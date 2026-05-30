"""
Meridian demo CLI.

Prints the Prime wake sequence followed by a portfolio state snapshot:
- Wake sequence (Prime online, harness status lines, orientation summary)
- Active initiatives
- Harness heartbeat summary
- Safe next moves
- Scott bottlenecks
- Generated session injections
"""

from __future__ import annotations

import os
import sys

from pathlib import Path

from .decisions import run_decision_loop
from .intention import RiskTier
from .mission import MissionLoadError, find_mission_file, load_mission
from .models import Initiative
from .objectives import get_mission_objectives
from .sample_state import make_sample_heartbeats, make_sample_portfolio
from .wake import WakeStatus, build_wake_brief

def _ansi_supported() -> bool:
    return (
        sys.stdout.isatty()
        and os.environ.get("NO_COLOR") is None
        and os.environ.get("TERM") != "dumb"
    )


_C = _ansi_supported()
_RESET = "\033[0m" if _C else ""
_BOLD = "\033[1m" if _C else ""
_CYAN = "\033[96m" if _C else ""
_GREEN = "\033[92m" if _C else ""
_YELLOW = "\033[93m" if _C else ""
_RED = "\033[91m" if _C else ""
_DIM = "\033[2m" if _C else ""

_STATUS_COLOR = {
    "alive": _GREEN,
    "busy": _CYAN,
    "blocked": _RED,
    "stale": _YELLOW,
    "failed": _RED,
    "sleeping": _DIM,
}

_WAKE_STATUS_COLOR = {
    WakeStatus.ONLINE: _GREEN,
    WakeStatus.STABLE: _CYAN,
    WakeStatus.STANDING_BY: _DIM,
    WakeStatus.DEGRADED: _YELLOW,
    WakeStatus.BLOCKED: _RED,
    WakeStatus.OFFLINE: _RED,
    WakeStatus.UNKNOWN: _DIM,
}


def _header(text: str) -> str:
    bar = "=" * (len(text) + 6)
    return f"\n{_BOLD}{_CYAN}{bar}\n   {text}   \n{bar}{_RESET}"


def _bullet(label: str, value: str, color: str = "") -> str:
    return f"  {_DIM}*{_RESET} {_BOLD}{label}:{_RESET} {color}{value}{_RESET if color else ''}"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # ── Mission load (must happen before any action) ──────────────────────
    try:
        mission = load_mission(find_mission_file(Path(__file__).parent.parent))
    except MissionLoadError as exc:
        print(f"{_RED}Mission load failed: {exc}{_RESET}")
        return

    portfolio = make_sample_portfolio()
    heartbeats = make_sample_heartbeats()
    result = run_decision_loop(portfolio, heartbeats)
    brief = build_wake_brief(portfolio, heartbeats, result)
    intention = get_mission_objectives(portfolio, result, heartbeats=heartbeats)

    # Wake sequence
    print()
    print(f"{_DIM}Good morning, Scott. Allow me to check today's mission file.{_RESET}")
    print(f"{_DIM}Mission loaded. {len(mission.directives)} directives. {len(mission.harness_boot_order)} harnesses in boot order.{_RESET}")
    print(f"{_DIM}Objective: {mission.current_objective}{_RESET}")
    print(f"{_BOLD}{brief.title}{_RESET}")
    for line in brief.lines:
        color = _WAKE_STATUS_COLOR.get(line.status, "")
        print(f"{color}{line.message}{_RESET}")
    print()
    print(f"  {brief.summary}")
    if brief.bottlenecks:
        for bn in brief.bottlenecks:
            print(f"  {_YELLOW}!{_RESET} {bn}")
    if brief.recommended_actions:
        for action in brief.recommended_actions:
            print(f"  {_GREEN}>>{_RESET} {action}")
    print()

    # ── Progress intention ────────────────────────────────────────────────
    print(_header("Progress Intention"))
    print(f"\n  {_BOLD}Stage:{_RESET} {intention.current_stage} > {intention.initiating_harness} Initiating")
    print(f"\n  {_BOLD}Mission Objectives:{_RESET}")
    for line in intention.objective_lines:
        tier_color = _RED if line.risk_tier.value >= 4 else (_YELLOW if line.risk_tier.value == 3 else _GREEN)
        print(
            f"    {line.project_name} - {line.initiative_title}"
            f" - Stage {line.stage.value}"
            f" - {tier_color}Risk Tier {line.risk_tier.value}{_RESET}"
            f"  {_DIM}({line.risk_reason}){_RESET}"
        )
    print(f"\n  {_BOLD}Next Stage:{_RESET} {intention.next_stage}")
    print()

    # ── Active initiatives ──────────────────────────────────────────────────
    print(_header("Active Initiatives"))
    all_initiatives: list[tuple[str, Initiative]] = []
    _seen_project_ids: set[str] = set()
    for v in portfolio.ventures:
        for p in v.projects:
            if p.id not in _seen_project_ids:
                _seen_project_ids.add(p.id)
                for init in p.initiatives:
                    all_initiatives.append((f"{v.title} / {p.title}", init))
    for p in portfolio.projects:
        if p.id not in _seen_project_ids:
            _seen_project_ids.add(p.id)
            for init in p.initiatives:
                all_initiatives.append((p.title, init))

    if not all_initiatives:
        print("  (none)")
    for parent_title, init in all_initiatives:
        print(f"\n  {_BOLD}[{parent_title}]{_RESET}  {_CYAN}{init.title}{_RESET}")
        print(f"  {_DIM}{init.description}{_RESET}")
        for obj in init.objectives:
            print(f"    {_YELLOW}Objective:{_RESET} {obj.title}")
            for crit in obj.success_criteria:
                print(f"      {_DIM}[ok] {crit}{_RESET}")

    # ── Harness heartbeat summary ──────────────────────────────────────────
    print(_header("Harness Heartbeat Summary"))
    if not heartbeats:
        print("  (no heartbeats)")
    for hb in heartbeats:
        status_color = _STATUS_COLOR.get(hb.status.value, "")
        print(f"\n  {_BOLD}{hb.harness_id}{_RESET}")
        print(_bullet("Status", hb.status.value.upper(), status_color))
        if hb.current_work:
            print(_bullet("Working on", hb.current_work))
        if hb.last_event:
            print(_bullet("Last event", hb.last_event))
        if hb.blockers:
            print(_bullet("Blockers", ", ".join(hb.blockers), _RED))

    # ── Safe next moves ────────────────────────────────────────────────────
    print(_header("Safe Next Moves"))
    if not result.safe_next_moves:
        print("  (none — all moves require Scott or proof)")
    for move in result.safe_next_moves:
        print(f"\n  {_GREEN}>>  {move.description}{_RESET}")
        print(f"     {_DIM}kind: {move.kind.value}  |  reason: {move.reason or '—'}{_RESET}")

    # ── Scott bottlenecks ──────────────────────────────────────────────────
    print(_header("Scott Bottlenecks"))
    if not result.scott_bottlenecks:
        print("  (none — no blocking decisions needed)")
    for bn in result.scott_bottlenecks:
        print(f"\n  {_YELLOW}!  {bn.title}{_RESET}")
        print(f"     {_DIM}{bn.description}{_RESET}")
        print(f"     priority: {bn.priority.value}")

    # ── Generated session injections ──────────────────────────────────────
    print(_header("Generated Session Injections"))
    if not result.injections:
        print("  (none)")
    for inj in result.injections:
        print(f"\n  {_CYAN}->  target: {inj.target_session_id}{_RESET}  [{inj.priority.value} / {inj.mode.value}]")
        print(f"     {_BOLD}Instruction:{_RESET} {inj.instruction}")
        print(f"     {_DIM}Reason: {inj.reason}{_RESET}")

    print()


if __name__ == "__main__":
    main()
