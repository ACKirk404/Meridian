# Meridian File Map

This is the living knowledge tracker for important Meridian files.

Use it to quickly understand what each file owns, which harness or architecture area it belongs to, and where to look before editing.

This file should eventually feed Echo/Atlas memory injection so Prime and worker sessions can start with the right repository context instead of rediscovering the codebase every time.

Canonical repo path:

```text
C:\Users\scott\Code\Meridian\docs\FileMap.md
```

Obsidian mirror path:

```text
G:\My Drive\Aesop Academy\Obsidian\Meridian_Build\FileMap.md
```

## Core Authority And Context

| File | Area | Purpose | Related Tests | Notes |
| --- | --- | --- | --- | --- |
| `MISSION.md` | Mission / Prime authority | Prime's first boot authority file: directives, harness boot order, current mission objective, queue guidance. | `tests/test_mission.py` | Prime should read this before meaningful action. |
| `context.md` | Architecture memory | Working architecture vocabulary, product rules, Prime directives, UI decisions, harness naming, collaboration rules. | n/a | Update when major architecture decisions are made. |
| `docs/meridian-capabilities.md` | Product recall | Plain-language recall sheet for major Meridian capabilities. | n/a | Useful for explaining why Meridian is different. |
| `docs/meridian-pillars.md` | Prime Directives | Load-bearing Meridian ideas, currently named Prime Directives. | n/a | Public-safe fallback name: Meridian Pillars. |

## Core Package

| File | Area | Purpose | Related Tests | Notes |
| --- | --- | --- | --- | --- |
| `meridian_core/__init__.py` | Package API | Intentional root exports for stable public package surface. | import smoke checks, full suite | Do not export every internal helper automatically. |
| `meridian_core/models.py` | Domain model | Native Python objects for portfolio, projects, harnesses, heartbeat, proof, tasks, moves, adapters. | `tests/test_decisions.py`, others | Foundation for all higher-level slices. |
| `meridian_core/sample_state.py` | Demo/sample data | Deterministic sample portfolio and heartbeat state for CLI/demo/tests. | many tests | Keep realistic but small. |
| `meridian_core/cli.py` | Demo CLI | Prints mission load, wake sequence, progress intention, objectives, heartbeat, decisions, injections. | full suite + CLI smoke | Demo surface only, not the final UI. |

## Prime Decision Loop

| File | Area | Purpose | Related Tests | Notes |
| --- | --- | --- | --- | --- |
| `meridian_core/decisions.py` | Local decision loop | Deterministic local brain decisions from portfolio + heartbeat. | `tests/test_decisions.py` | No model calls. |
| `meridian_core/injections.py` | Session/directive modeling | Builds session injection objects. | `tests/test_injections.py` | Models future worker steering, not live automation yet. |
| `meridian_core/events.py` | Event recording | Records structured events. | currently light coverage | Future proof/history input. |

## Mission, Wake, Compass

| File | Area | Purpose | Related Tests | Notes |
| --- | --- | --- | --- | --- |
| `meridian_core/mission.py` | Mission boot | Loads/parses `MISSION.md` into native objects. | `tests/test_mission.py` | Required before Prime acts. |
| `meridian_core/wake.py` | Wake sequence | Builds structured wake brief from harness heartbeat state. | `tests/test_wake.py` | NASA-style Go calls are UI/audio concerns later. |
| `meridian_core/intention.py` | Progress Intention / Compass | Builds stage/objective/risk-tier view from portfolio and decision state. | `tests/test_intention.py` | Functional seed for Prime's work intention. |
| `meridian_core/objectives.py` | Mission Objectives recall | Stable on-demand API for Compass-derived mission objectives. | `tests/test_objectives.py` | Future cockpit Mission Objectives button uses this. |

## Risk, Relay, Review

| File | Area | Purpose | Related Tests | Notes |
| --- | --- | --- | --- | --- |
| `meridian_core/risk.py` | Risk Tier Engine | First-class risk assessment and requirements for tiers 0-4. | `tests/test_risk.py` | Decision engine foundation. |
| `meridian_core/relay.py` | Relay routing | Deterministic model/session routing plan from risk tier. | `tests/test_relay.py` | No real model calls yet. |
| `meridian_core/review_console.py` | Review Console | Promptable review/gating surface for cross-check, proof, artifacts, plans, gates. | `tests/test_review_console.py` | Replaces "non-orchestrator window" name. |

## Build And Maturity

| File | Area | Purpose | Related Tests | Notes |
| --- | --- | --- | --- | --- |
| `meridian_core/builds.py` | Build/maturity registry | Tracks Meridian build number plus per-harness build and maturity. | `tests/test_builds.py` | `register` rejects duplicates; use `upsert` for intentional replacement. |

## File Map

| File | Area | Purpose | Related Tests | Notes |
| --- | --- | --- | --- | --- |
| `meridian_core/filemap.py` | File map / knowledge tracker | Domain-level knowledge tracker: `FileMapEntry`, `FileMap`, `make_default_map()`. | `tests/test_filemap.py` | Feed to Echo/Atlas for session memory injection. |
| `docs/FileMap.md` | File map / knowledge tracker | Human-readable living knowledge tracker for important Meridian files. | n/a | Obsidian mirror: `G:\My Drive\Aesop Academy\Obsidian\Meridian_Build\FileMap.md` |

## Planning And Handoffs

| File | Area | Purpose | Related Tests | Notes |
| --- | --- | --- | --- | --- |
| `docs/claude-handoff-completion-protocol.md` | Build process | Standard test/commit/push/Obsidian completion protocol for Claude handoffs. | n/a | Include in every build handoff unless local-only. |
| `docs/package-api-surface-note.md` | Package API policy | Guidance for intentional root exports. | n/a | Keep root API deliberate. |
| `docs/cross-check-aegis-integration-brief.md` | Future Aegis planning | How automatic cross-check should feed Aegis and Review Console. | n/a | Planning only. |
| `docs/build-next-aegis-cross-check-handoff.md` | Future handoff | Next slice after Review Console: Aegis cross-check evidence. | n/a | Do not run until Review Console is committed. |

## Visual Assets

| File | Area | Purpose | Related Tests | Notes |
| --- | --- | --- | --- | --- |
| `docs/diagram-deck.html` | Architecture visuals | Click-through local HTML diagram deck. | visual/manual | Used for architecture visualization discussions. |
| `docs/assets/diagrams/` | Diagram assets | Generated architecture diagrams and variants. | visual/manual | Some are exploratory; not all are canonical. |

## Update Rule

When adding an important source file, domain slice, harness, or major architecture document, update this file in the same slice.
