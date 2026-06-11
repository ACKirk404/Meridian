# Meridian

Meridian is a local orchestrator for agentic software work.

You talk to the orchestrator. The orchestrator drives worker sessions, harnesses, proof, and project motion.

## Meridian UI

The Meridian user interface is the Electron app. That is the app to run, demo,
test, document, and build against.

Root `index.html` is the current renderer source file loaded by the Electron
app. It is not a separate Meridian UI and it is not the app identity by itself.
Edits to that file are edits to the Electron app's visible UI because Electron
loads it into the desktop window. It is part of the app today: not obsolete,
detached, merely historical, or independent from the app. It also must not be
treated as a standalone browser demo, a separate product target, or a
replacement identity for the Electron app. `npm start` launches
`electron/main.js`, which opens the Meridian Electron app with this renderer
source. Startup must not regenerate or substitute `bifrost/preview.html`.

`bifrost/preview.html` is a generated backend/render proof artifact created by `bifrost/preview.py`. It is not the product UI entrypoint.

### App runtime

`npm start` launches the Meridian Electron app runtime. Electron now owns the
local model bridge lifecycle: it checks `127.0.0.1:8767`, starts
`scripts/meridian-model-bridge.js` when the bridge is not already running, and
stops only the bridge process that this app launched when Meridian exits.

To build a Windows portable app:

```bash
npm run build:win
```

The generated app is written to `dist/Meridian-0.1.0-x64.exe`.

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

## Current State

Meridian now has a working Electron cockpit app as its UI, root `index.html` as that app's current renderer source file, and a local model bridge in `scripts/meridian-model-bridge.js`. The Python core continues to provide deterministic backend/runtime logic for the visible harness surfaces.

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
- Public model setup flow: Scott's local Max/Claude and Codex CLI logins are already configured for this development machine, but a public Meridian build must not assume that. If a selected model CLI is missing or not authenticated, Meridian should tell the user to install the relevant CLI and log in to their account instead of showing raw process errors.
- Model routing intent: each project's Prime/orchestrator should normally choose the model automatically through Relay harness logic. Manual model selection may be exposed for direct use and testing, but the expected operating mode is automated Prime/Relay decision-making.
- Real session injection (modeled only)
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
