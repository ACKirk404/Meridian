# V2 Package API Surface Note

Meridian V2 introduces four new harnesses (Echo, Atlas, Session Lifecycle, Bifrost) plus Prime Autonomy extensions. Each harness has stable domain objects that should eventually become root package exports once their implementation and proof contracts mature.

## Surface Design Principles

V2 objects follow the same export criteria as V0/V1:
- stable domain objects callers directly instantiate or receive
- primary loader/builder functions
- small enums that are part of public decision contracts

Experimental internals, dispatch mechanics, and harness-internal helpers remain module-level imports until proof review is complete.

## Proposed V2 Public Surface

### Echo Harness

**Intended public exports:**
- `MemoryRecord` — domain object representing a single episode of conversation, action, or observation
- `MemoryQuery` — domain object for querying the memory store
- `MemoryHit` — domain object representing a memory match result

**Rationale:** Echo callers (Prime, Relay, Session) need to reason about what the memory system knows. These objects form the contract boundary between Echo and the rest of the system.

**Status:** awaiting implementation and proof review (see `docs/v2-progress-tracker.md`)

### Atlas Harness

**Intended public exports:**
- `AtlasQuery` — domain object for spatial/semantic queries
- `AtlasHit` — domain object representing a spatial match result
- `AtlasResult` — aggregate result from a query (collection of hits)

**Rationale:** Callers instantiate `AtlasQuery` to ask spatial questions and consume `AtlasHit`/`AtlasResult` to interpret responses. These form the harness boundary.

**Status:** awaiting implementation and proof review (see `docs/v2-progress-tracker.md`)

### Prime Autonomy

**Intended public exports:**
- `PrimeNextAction` — domain object representing Prime's decision about what to do next

**Rationale:** Relay and workflow dispatch use `PrimeNextAction` to understand Prime's guidance. This is the output contract of Prime's autonomy layer.

**Status:** awaiting implementation and proof review (see `docs/v2-progress-tracker.md`)

### Session Lifecycle Harness

**Intended public exports:** TBD after harness implementation begins. Likely candidates include session state and transition contracts.

**Status:** blocked on harness design (see `docs/v2-progress-tracker.md`)

### Workflow Dispatch

**Intended public exports:** TBD after workflow model is finalized. Likely candidates include dispatch requests and action routing contracts.

**Status:** blocked on design phase (see `docs/v2-detailed-build-plan.md`)

## What Stays Internal (V2)

**Harness internals** — Echo indexing strategies, Atlas spatial algorithms, Prime decision reasoning paths, Session state machines, and Workflow routing logic all remain module-level imports. Expose only the domain objects callers need to reason about decisions, not the machinery that makes them.

**Sub-agent orchestration** — any V2 workflow sub-agent framework internals stay internal until the framework pattern is proven across at least two harnesses.

## Timeline

Public surface export decisions for each harness will be made during that harness's proof review cycle (rule 23 of v2-detailed-build-plan.md). Until then, all V2 exports remain candidates pending evidence.

See `docs/v2-progress-tracker.md` for harness-by-harness build status and `docs/package-api-surface-note.md` for V0/V1 export history and rationale.
