# Prime Orchestration Harness Prototype

**Status:** Active build pattern / future architecture
**Owner:** Prime / orchestration harness
**Source prototype:** live build queues, Codex Reviews queue, Polaris Q polling

The current Meridian live-build process is not just a temporary way to move work faster. It is the first working prototype of Prime's orchestration harness.

Everything below should eventually move from markdown queues and human-pasted session instructions into Prime itself.

## What Prime Owns

Prime should own the coordination loop:

- choose the next build slice
- assign it to an appropriate worker lane
- define allowed files and scope
- require tests and completion evidence
- receive completion signals
- mark the slice ready for independent review
- route review to a specialized review lane
- dynamically spawn additional review lanes when review pressure becomes the bottleneck
- hold checkpoints for what has and has not been reviewed
- route repairs back to the original builder
- clear lanes only after review or repair verification
- keep Scott out of the loop unless there is a human gate, strategic choice, or unresolved block

The human should not need to watch every worker session. The human should talk to Prime.

## Current Prototype Pieces

| Prototype piece | Future Prime capability |
| --- | --- |
| `docs/live-build-1.md` through `docs/live-build-5.md` | Worker-lane task queues and lane state |
| `docs/live-codex-reviews.md` | Independent runtime/code review lane and review checkpoint state |
| `docs/live-codex-reviews-2.md` | Second review lane for docs/architecture review scaling |
| Checkpoint Ledger | Prime memory of reviewed vs. unreviewed work |
| Review Round Scope | Prime's declared review boundary before evaluation |
| `Ready for Codex Review` marker | Completion signal from worker to Prime/review harness |
| Repair Active Task | Prime routing a finding back to the original lane |
| Polaris Q button | Prototype for session harness polling |
| Heartbeat monitor | Prototype for Beacon liveness and coordinator wakeups |

## Prime Rules Implied By The Prototype

1. Builders do not review themselves.
2. Reviewers declare scope before reviewing.
3. A checkpoint is required before a lane can be considered clear.
4. A lane may be idle, running, blocked, ready for review, under review, repair-routed, or cleared.
5. Repair goes back to the original owner unless Prime deliberately reassigns it.
6. Completion is not the same as acceptance.
7. The Review Console receives findings; the Orchestrator Queue receives only what Scott needs to decide.
8. Prime must preserve state outside any one model context window.
9. The harness, not the prompt, should carry most structure.
10. Markdown queues are scaffolding. The target is native orchestration state.
11. Review capacity is elastic: Prime may spawn another review lane when existing reviewers become the bottleneck.
12. Parallel review lanes must declare non-overlapping scope before reviewing.

## What Must Become Native

For V0, Prime does not need a perfect distributed system. It needs native equivalents of the prototype:

- lane registry
- lane state
- active task object
- allowed file scope
- completion evidence
- review checkpoint
- review scope
- review lane registry
- review lane specialization
- finding record
- repair routing record
- liveness heartbeat
- queue polling state

The current markdown files prove the protocol. Meridian should next turn that protocol into Python domain objects, then Bifrost/Beacon surfaces, then live session harness behavior.

## Why This Matters

This is the heart of Meridian:

> Prime is not a chat window that gives advice. Prime is the local orchestration harness that keeps work moving, remembers state, routes judgment, and asks Scott only for gates that matter.

The live queue system is the first visible behavior of that idea.
