# Meridian V2 Horizon Plan

**Status:** Horizon plan, not active V1 scope
**Trigger:** Start detailed V2 planning only after V1 cockpit scope is locked.
**Purpose:** Preserve the next horizon without letting it distort V1. V1 is cockpit UI. V2 is where Meridian becomes deeper, more durable, more distributed, and more autonomous.

## V2 Definition

V2 begins after Scott can see and operate Prime through the Bifrost cockpit. The V2 job is to make that visible Prime substantially more capable: persistent memory, retrieval, stronger autonomy, richer model harnesses, and eventual collaboration beyond one local cockpit.

V2 should not be allowed to pull V1 away from its purpose. If a V2 idea does not help the cockpit become visible and usable, it waits.

## Candidate V2 Pillars

### 1. Echo Memory Engine

Prime needs durable memory that survives model context windows, app restarts, and project switching.

V2 scope candidates:

- persistent memory records
- project and portfolio memory
- decision history
- user preference memory
- memory ranking and decay
- memory injection into Relay packets

### 2. Atlas Retrieval / RAG Harness

FileMap gives Meridian a map. Atlas gives it ranked retrieval.

V2 scope candidates:

- query API over FileMap, docs, logs, and memory
- ranked context packets
- source-aware citations
- retrieval budget controls
- integration with Relay prompt packets

### 3. Stronger Prime Autonomy

V1 lets Scott see Prime. V2 lets Prime do more without Scott being the bottleneck.

V2 scope candidates:

- proactive backlog selection
- autonomous review routing
- automatic repair routing
- cross-project prioritization
- bottleneck escalation only when Prime cannot resolve the issue

### 4. Dynamic Risk-Tiered Dual-Structured Gated Cognition

The decision engine becomes runtime behavior, not just architecture language.

V2 scope candidates:

- runtime risk-tier selection
- dual-lane deliberation for higher-risk actions
- Aegis gate enforcement by tier
- reviewer/verifier routing by risk
- cost-aware escalation controls

### 5. Model Harness Adapters

V1 can use whatever V0 provides. V2 should clarify and harden the model interface.

V2 scope candidates:

- API-first public adapter path
- compartmentalized account-based automation path
- model capability registry
- prompt drag telemetry
- adapter health checks

### 6. Session Lifecycle Harness

The cockpit should not merely display sessions; Prime should own their lifecycle.

V2 scope candidates:

- spawn session
- steer session
- wait/watch session
- stop session reliably
- transfer/archive session
- recover stale sessions

### 7. Multi-Meridian / Multi-User Federation

Not V1. Worth preserving as a future horizon.

V2 scope candidates:

- trusted Meridian-to-Meridian connection
- shared project state
- cross-user review handoffs
- role/permission model
- conflict and merge coordination

## V2 Non-Goals Until V1 Is Locked

- Do not build Echo before the cockpit can display Prime state.
- Do not build Atlas before FileMap and cockpit surfaces are stable enough to benefit from retrieval.
- Do not build federation before single-user Prime is useful.
- Do not overbuild model adapters before Relay, Aegis, and Bifrost expose the real integration needs.

## First V2 Planning Questions

1. Should V2 start with Echo memory or Prime autonomy?
2. Should Atlas retrieval be file/docs-first before vector search?
3. Which model harness path matters first: API adapters or private account automation?
4. Does session lifecycle belong in V2, or should a minimal version be pulled into late V1?
5. What is the V2 success test: "Prime remembers," "Prime retrieves," or "Prime runs multiple projects with less Scott involvement"?

## Recommended V2 Start After V1 Lock

Once V1 is locked, start V2 planning in this order:

1. Define the V2 success test.
2. Split V2 into memory, retrieval, autonomy, model harness, and session lifecycle tracks.
3. Decide which track is first.
4. Build the smallest vertical slice that improves Prime's real autonomy inside the cockpit.

The cockpit remains the center. V2 makes the cockpit smarter.
