# Meridian

Meridian is a local orchestrator for agentic software work.

You talk to the orchestrator. The orchestrator drives worker sessions, harnesses, proof, and project motion.

## What It Is

Meridian is a proactive portfolio orchestrator and builder. It advances projects, businesses, websites, tools, and experiments until Scott's judgment is the bottleneck — not execution.

The intended model:

```
Scott → Orchestrator
Orchestrator → Workers
Workers → Harnesses
Harnesses → Heartbeat / Events
Orchestrator → Scott only for judgment bottlenecks
```

## Current State: V0 Local Brain Skeleton

This first slice makes the core concepts real in code. It does not yet include real model integrations, UI, persistence, or agent harness wiring.

### Package: `meridian_core`

```
meridian_core/
  models.py         — domain objects: Portfolio, Venture, Initiative, Objective,
                      NextMove, Harness, Heartbeat, Decision, ScottBottleneck,
                      SessionInjection, ProviderAdapter, and supporting types
  sample_state.py   — sample portfolio (Meridian, Advanced AI Concepts, CareGuide),
                      heartbeats, and provider adapters
  decisions.py      — deterministic kernel decision loop
  events.py         — in-memory event recorder
  injections.py     — SessionInjection factory
```

### What the skeleton proves

- Portfolio state → harness heartbeat → kernel decision → session injection → Scott bottleneck queue
- Blocked harnesses with known blockers produce targeted directive injections
- Scott-required next moves become bottlenecks and are never auto-advanced
- Autonomous moves with unverified proof produce verification injections
- Provider adapters carry compliance tier metadata (public-safe vs. private/disabled)

## Install and run tests

Requires Python 3.12+.

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Not built yet

- Real Claude / Codex / OpenRouter model integrations
- Real session injection (modeled only)
- UI or Electron shell
- SQLite or other persistence
- Git / worktree harness
- Browser automation
- Full workflow engine
- Public packaging

## Primary docs

- [`context.md`](context.md) — shared vocabulary and canonical project anchors
- [`docs/meridian-v0-build-brief.md`](docs/meridian-v0-build-brief.md) — V0 target and first build slice
- [`docs/polaris-lessons-for-meridian.md`](docs/polaris-lessons-for-meridian.md) — what Polaris proved and what Meridian carries forward
- [`docs/polaris-ui-lessons-for-meridian.md`](docs/polaris-ui-lessons-for-meridian.md) — UI carry-forward notes
- [`docs/meridian-provider-compliance.md`](docs/meridian-provider-compliance.md) — provider adapter compliance strategy
