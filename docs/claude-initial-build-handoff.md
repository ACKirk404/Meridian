# Claude Initial Build Handoff

## Role

You are the builder for Meridian's first implementation slice.

Codex will review your work after you finish. Optimize for clarity, testability, and staying inside scope.

## Objective

Build a small, tested Meridian local-brain skeleton.

This first slice should make the core concepts real in code without building the full orchestrator, UI, agent harness, model adapters, SQLite persistence, or public packaging.

## Read First

Read these files before editing:

- `context.md`
- `docs/meridian-v0-build-brief.md`
- `docs/polaris-lessons-for-meridian.md`
- `docs/polaris-ui-lessons-for-meridian.md`
- `docs/meridian-provider-compliance.md`

## Core Product Idea

Meridian is a proactive portfolio orchestrator and builder.

Scott should mainly talk to the orchestrator. The orchestrator should drive worker sessions, harnesses, proof, and project motion. Worker sessions are managed execution surfaces, not places Scott should normally have to coordinate manually.

V0 should prove the shape:

```text
portfolio state
  -> harness heartbeat
  -> local kernel decision
  -> session/directive injection
  -> event/proof/artifact record
  -> Scott bottleneck queue
```

## Build Scope

Create a Python package skeleton with native domain objects and deterministic tests.

Suggested structure:

```text
meridian_core/
  __init__.py
  models.py
  sample_state.py
  decisions.py
  events.py
  injections.py
tests/
  test_decisions.py
  test_injections.py
pyproject.toml
```

You may adjust names if there is a clear reason, but keep the architecture small and obvious.

## Required Domain Objects

Define native Python objects for:

- `Portfolio`
- `Venture`
- `Project`
- `Initiative`
- `Objective`
- `Task`
- `NextMove`
- `Harness`
- `Heartbeat`
- `Workflow`
- `Decision`
- `ScottBottleneck`
- `Proof`
- `Artifact`
- `SessionInjection`

Use dataclasses, enums, and typed fields. Pydantic is optional, but do not introduce it unless the benefit is clear.

Do not make JSON dictionaries the internal architecture.

## Required Behavior

### 1. Sample Portfolio

Create sample state with at least three initiatives.

Each initiative should have at least one objective and one next move.

At least one initiative should represent Meridian itself.

### 2. Harness Heartbeat

Represent harness heartbeat state.

Include at least these statuses:

```text
alive
busy
blocked
failed
sleeping
stale
```

Sample state should include at least:

- one alive harness
- one busy harness
- one blocked or stale harness

### 3. Decision Engine

Create a deterministic decision function that accepts portfolio state and heartbeat state.

It should return a result containing:

- safe next moves Meridian can take
- Scott bottlenecks
- decisions made
- generated session injections

This is not an LLM planner. Keep it rule-light and inspectable.

Example cases:

- If a worker/session is blocked and has a known blocker, generate a session injection or Scott bottleneck.
- If proof is missing for a next move that claims completion, generate a verification-oriented injection.
- If a next move requires Scott judgment, create a Scott bottleneck instead of auto-advancing it.

### 4. Session Injection

Create a `SessionInjection` object that includes:

- target session or harness id
- instruction text
- reason
- priority
- injection mode
- created timestamp

Injection modes should include:

```text
user_message
directive
resume_context
system_prompt
```

Do not implement real session injection yet. Only model it and generate sample injections.

### 5. Events

Create an event record object and simple in-memory event recorder.

Events should cover:

- decision made
- bottleneck created
- injection generated

Do not add SQLite yet.

### 6. Provider Adapter Awareness

Represent provider/adapter support only at a basic metadata level.

Do not build real adapters.

Include enough structure to mark an adapter as:

```text
official_api_supported
local_model_supported
experimental_user_configured
private_only
disabled_for_public_build
```

This should stay small.

## Tests Required

Add tests proving:

1. Sample portfolio contains at least three initiatives.
2. Blocked/stale heartbeat produces a decision, injection, or Scott bottleneck.
3. Scott-only next moves become Scott bottlenecks and are not auto-advanced.
4. Missing proof produces a verification-oriented injection.
5. Generated session injection includes target, instruction, reason, priority, and mode.
6. Provider adapter metadata can mark account-based/private adapters as disabled for public build.

Use `pytest`.

## README Update

Update `README.md` with:

- What Meridian is
- How to install/run tests
- What the initial skeleton includes
- What is intentionally not built yet

Keep it concise.

## Do Not Build Yet

Do not build:

- real Claude/Codex/OpenRouter integrations
- real account-based automation
- real UI
- real Electron wrapper
- real browser automation
- real git/worktree operations
- real SQLite/Postgres persistence
- real public packaging
- full workflow engine
- large plugin system

Do not over-design the harness architecture yet.

This first slice is only the local-brain skeleton.

## Review Expectations

Codex will review for:

- fidelity to `context.md`
- clean domain object boundaries
- native Python state, not JSON-shaped internals
- small deterministic decision logic
- no premature provider/model architecture
- tests that prove the intended V0 behavior
- no accidental private secrets or account automation

## Delivery

When complete, report:

- files changed
- tests run
- what works
- what is intentionally stubbed
- any questions or design tradeoffs

