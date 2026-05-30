# Bifrost Session Queue Activation Brief

**Status:** Strategic / design-only — no runtime code
**Lane owner:** Build 5 (Bifrost / session-harness product lane)
**Audience:** Prime, Bifrost, Beacon, Relay, future session-harness implementers

This brief describes how Meridian should eventually turn queue polling on from the UI and session harness. It captures the product intent so that when a real session harness exists, queue activation does not get rebuilt the way Polaris built it.

The Polaris **Q button** is a useful prototype. It proved that "force this session to poll its queue now" is a real user action. It is **not** the final architecture. Meridian should treat queue activation as a first-class harness capability, owned by Prime and surfaced by Bifrost, not as a per-card button Scott clicks one at a time.

---

## 1. Why This Brief Exists

Today, live build lanes (Build 1–5) are kept polling by pasting a strict active-polling command into each session at start, and by Scott manually nudging cards when they drift. This works for the current build phase but does not scale once Meridian has:

- multiple concurrent worker sessions per project
- multiple projects in flight
- Prime making routine assignment decisions
- Beacon reporting per-lane liveness
- a real session-harness runtime under Bifrost

The intermediate `docs/live-build-active-polling-contract.md` already names the worker-side contract. This brief covers the **operator-side** contract: how polling gets turned on, how it gets turned off, who decides, and how it shows up in the cockpit.

---

## 2. Global Queue Activation Control

Meridian should have one global queue-activation control, owned by Prime and surfaced by Bifrost.

It should be able to:

- **Enable** queue polling for the current project / portfolio
- **Disable** queue polling globally (kill-switch for hung-lane storms, runaway cost, or human override)
- **Pause** polling without losing per-lane state (resumable)
- **Force a single poll cycle** across every active lane (the "everyone check now" action)
- **Snapshot** current polling state into the Review Console as a single legible record

It is not a "start the queue worker" button. It is a **policy switch**: when on, Prime is permitted to dispatch lanes against their queue files; when off, Prime must not start polling work and must stop ongoing polling cleanly.

The control must be:

- heartbeat-backed (Beacon confirms each lane actually changed state)
- observable (the cockpit shows the new state immediately, not "press and hope")
- reversible without re-pasting commands into every session
- gated for tier-3+ actions (e.g. resuming after a kill-switch may require an approval gate, not just a click)

---

## 3. Per-Session Q State

Each worker session should have its own `Q` state. The Polaris Q button collapses several distinct things into one click; Meridian should separate them.

Per-session Q state fields:

| Field | Meaning |
|---|---|
| `assigned_queue` | The queue file/object this session is bound to (e.g. `docs/live-build-5.md`). Set by Prime, not inferred. |
| `polling_enabled` | Whether this session is allowed to poll right now. |
| `polling_state` | `enabled` / `disabled` / `running` / `blocked` / `stale` / `unknown`. |
| `last_poll_at` | Last successful pull + read of the assigned queue. |
| `last_commit` | Last commit hash this session reported back. |
| `pending_directive` | A queued directive from Prime (e.g. "stop after current task", "force poll now"). |
| `steering_mode` | The backend's actual steering capability for this session: `none`, `user-message`, `directive`, `resume-context`, `system-prompt`. |

Per-session actions:

- **Activate Q** — start polling against `assigned_queue`
- **Deactivate Q** — stop polling, but keep the session alive and inspectable
- **Force poll** — single-shot pull + read + execute-if-task without enabling the timer
- **Reassign queue** — change `assigned_queue` (rare; logged in Review Console)
- **Transfer** — hand polling responsibility to another session, preserving last-commit and last-poll state

Per-session Q is the **mechanism**. Global activation is the **policy**. The two must be decoupled so Prime can disable a single lane without flipping the global switch, and Scott can flip the global switch without losing per-lane assignments.

---

## 4. How Active Sessions Are Discovered

The current pattern guesses which sessions should poll which queue by reading card names ("Build 5"). This is fragile. Meridian should never infer assignment from a UI label.

Discovery should be explicit and harness-driven:

1. **Session registration.** When a worker session starts under the session harness, it registers itself with a stable session id, the project it belongs to, and its declared role (builder / reviewer / verifier / lane-N).
2. **Queue assignment is a separate step.** Prime (or Scott via Bifrost) assigns a queue file/object to that session id. Assignment is durable across restarts.
3. **Sessions enumerate from the harness, not the UI.** Bifrost asks the harness "which sessions exist for this project, and what queue is each assigned to?" rather than scanning visible cards.
4. **Unassigned sessions are visible but inert.** A registered session with no queue assignment shows up in the cockpit as `unassigned` and does not poll until Prime gives it a queue.
5. **Orphaned queues are surfaced.** A queue file with no assigned session is reported to the Review Console; the orchestrator must either assign one or mark the queue complete.

The product invariant: **assignment is data, not naming convention**. Renaming a card must never silently change which queue a session polls.

---

## 5. UI States: enabled / disabled / running / blocked

Bifrost must distinguish these states clearly. Polaris collapsed too many of them into "card is colored". Meridian should not.

Minimum visible states per session:

| State | Meaning | Indicator hint |
|---|---|---|
| `unassigned` | Session is registered but has no queue. | Neutral / gray |
| `disabled` | Queue assigned, polling switched off. | Dim / off |
| `enabled-idle` | Polling on, last poll succeeded, no active task. | Cool steady |
| `running` | Polling on, currently executing an active task. | Active accent |
| `blocked` | Polling on, but cannot proceed (e.g. merge conflict, denied permission, missing allowed file). | Amber |
| `stale` | Polling on, but last poll is older than the heartbeat threshold. | Amber / warning |
| `failed` | Polling on, but the last cycle errored (pull failed, write failed, etc.). | Error accent |
| `paused` | Globally paused; per-session config preserved. | Muted |

Rules:

- The state shown in the UI must come from Beacon's heartbeat, not from the last streamed message in the session.
- A session that has not heartbeat in N seconds is `stale`, regardless of what its card text says.
- The Review Console — not the worker card — is where Scott confirms or overrides state.
- A blocked session must surface **why** it is blocked when inspected, with the actionable next step (e.g. "queue file modified by another lane; pull required").

---

## 6. Queue File Assignment Without Card-Name Guessing

The product rule: **never derive queue assignment from a card title.**

Concretely:

- Assignment is a stored field on the session, set deliberately by Prime, Scott, or a harness API call.
- The harness exposes an explicit `assign_queue(session_id, queue_ref)` operation. The UI calls this operation; it does not write to a session's display name and hope a worker reads it.
- Queue refs are typed (`queue_file_path`, eventually `queue_object_id`), not freeform strings parsed from UI labels.
- A session whose `assigned_queue` is absent does not start polling, even if its card name contains a number that looks like a lane id.
- Re-assignment is an event: it appears in the Review Console as `session X reassigned from queue A to queue B by <actor>`.
- If the underlying queue is renamed or moved, the harness updates the assignment by id; it does not rely on the session re-reading a card title.

This protects against the recurring Polaris failure mode where renaming, re-coloring, or duplicating a card changed coordination behavior in ways that were invisible until something broke.

---

## 7. Prime Controls This, Not Scott Clicking Cards

Scott should not be the queue dispatcher. That role is Prime's.

Prime's responsibilities for queue activation:

1. **Decide which sessions get polling enabled** based on portfolio state, current objectives, and lane availability.
2. **Assign queue files to sessions** at startup or at re-plan.
3. **Force a poll cycle on a specific lane** when Prime knows new work has arrived (e.g. a task was just written into a queue) without waiting for the timer.
4. **Disable a lane** that is hung, conflicting, or no longer needed, and surface the reason in the Review Console.
5. **Pause all polling** when a global condition warrants it (cost ceiling reached, conflict detected, Aegis gate failed, Scott requested hold).
6. **Resume polling** under Aegis gating where appropriate.
7. **Issue directives** to active sessions ("stop after current task", "switch queue", "transfer to session Y") through the agent harness's steering mechanism, honoring per-backend `steering_mode`.

Scott's role becomes:

- final authority on enabling/disabling globally
- gate for irreversible or high-cost activations
- inspection of lane state when Prime surfaces a bottleneck
- override when Prime is wrong

Scott should not need to click "poll now" on five worker cards to get the build moving. That is a Prime action.

---

## 8. Beacon Reports Liveness and Stale Polling

Beacon owns "is this lane actually alive?" Queue activation must be heartbeat-backed; otherwise the UI is showing intentions, not reality.

Beacon responsibilities:

- Record a heartbeat each time a session completes a poll cycle (pull, read, decide).
- Distinguish **poll heartbeat** from **task heartbeat**: a lane can be polling fine but stuck on a long task, or working hard but not polling.
- Flag `stale` when the last poll heartbeat exceeds the configured threshold (default ≤ 60s for a 30s poll cadence — i.e. one missed cycle is tolerated, two is not).
- Flag `failed` when the last cycle reported an error (pull failure, write failure, permission denial).
- Report **per-lane** liveness as a structured event, not as colored text.
- Feed Bifrost the data it renders; never let Bifrost infer liveness from session card output.
- Surface stale or failed lanes to the Review Console so Prime can take routine recovery action (force poll, restart, reassign) without Scott noticing first.

The product invariant: **a lane's visible health = Beacon's last heartbeat for that lane.** No other source.

---

## 9. Bifrost Surfaces Human-Readable Status — Without Becoming The Worker Wall

Bifrost must avoid Polaris's failure mode where session cards became the primary interface.

Bifrost's job for queue activation:

- Surface a **compact, scannable** view of polling state across the project: how many lanes are enabled, running, blocked, stale.
- Provide a single clear control for global activation (on / off / pause / force-poll-all).
- Provide per-session detail **on demand** when Scott explicitly opens a session — not as a permanent wall.
- Route detail-level queue events (assignments, reassignments, failures, recoveries) to the Review Console rather than into the orchestrator conversation.
- Use Beacon's state, not session text, for every indicator.
- Show the actual `steering_mode` per session so Scott knows whether a "force poll" directive will land as a system update, a user message, or a resume.

What Bifrost must not do:

- Recreate Polaris's grid of always-visible session cards as the main view.
- Let queue state be inferred from per-card colors that Scott has to scan visually.
- Hide blocked lanes in a way that makes them forgettable; blocked/stale must always be summarizable in a single number on the cockpit instrumentation.
- Become the place where assignment happens via drag-and-drop card titles. Assignment goes through the explicit harness call.

The Polaris instinct was: "show every worker, all the time." The Meridian inversion is: **Prime tells Scott what matters; Bifrost makes the rest inspectable but quiet.**

---

## 10. How This Differs From The Current Polaris Implementation

| Concern | Polaris today | Meridian target |
|---|---|---|
| Activation control | Per-card Q button click; Scott clicks each one. | Global activation owned by Prime; per-session Q is mechanism, not policy. |
| Assignment | Inferred from card title/name conventions. | Explicit, stored, typed assignment via harness API. |
| Discovery | Look at visible cards in the UI. | Session harness enumerates registered sessions with declared roles and assignments. |
| Liveness | Inferred from streamed text and card color. | Beacon heartbeat events; UI is a renderer, not a source. |
| Force-poll | Scott clicks Q on each card. | Single Prime/Bifrost action that fans out, with per-lane backend-appropriate steering. |
| Stop polling | Stop button on each card (often fails). | Global pause + per-session disable, with confirmed `stopping → stopped` heartbeat. |
| Blocked / stale state | Often invisible until Scott notices. | First-class state surfaced via Beacon, summarized in instrumentation, detailed in Review Console. |
| Primary surface | Wall of session cards. | Orchestrator Queue + Review Console; session detail is on-demand. |
| Naming as coordination | Renaming a card can change behavior. | Renaming is cosmetic; assignment is data. |
| Steering capability | Treated as uniform across backends. | Reported honestly per session: `none | user-message | directive | resume-context | system-prompt`. |
| Cost of operating queues | Scales linearly with Scott's clicks. | Scales with Prime's decisions; Scott intervenes only at gates. |

---

## 11. Do Not Build Yet

The following should remain **design-only** until Meridian has a real session harness with registered sessions, structured queue state, and Beacon heartbeats. Building any of them earlier risks re-encoding the Polaris pattern this brief is trying to retire.

- **Per-card Q button in the Meridian UI.** Do not port the Polaris button as the activation surface. The button is fine as a prototype reference; reproducing it as the primary control would lock in the per-card paradigm.
- **Card-name → queue inference.** No string parsing, no "Build N" → `live-build-N.md` heuristic. Wait for explicit assignment.
- **Polling enabled/disabled inferred from session text or card color.** Wait for Beacon to feed state.
- **A persistent grid of every worker session.** Wait for the inversion (Prime-centric main view) to be the default, then add inspect-on-demand panels.
- **Force-poll fan-out as a UI primitive without a steering capability report.** Honor per-backend `steering_mode` first; a directive that silently degrades from system-prompt to user-message must say so.
- **Global pause/resume as a UI toggle without an audit record.** When a real harness exists, pause/resume must land in the Review Console with actor, reason, and affected lanes.
- **Drag-and-drop reassignment.** Reassignment must be an explicit, logged event; convenient gestures can come after the data model is durable.
- **Worker-side polling loops written into prompts as the long-term solution.** The current paste-the-active-polling-command pattern is intermediate. The harness should drive the loop externally once it exists (see `docs/live-build-active-polling-contract.md` § Harness Requirement).

What **is** safe to do in parallel with the docs lane:

- Continue maturing the flat-file queue conventions in `docs/live-build-N.md`.
- Continue surfacing what is needed to register sessions, queues, and assignments as typed objects (Build 2 / Build 3 territory).
- Continue defining Beacon's heartbeat event shape so the UI has something real to render when Bifrost arrives.

---

## 12. Open Questions

- Should the global activation control live in the top nav, in bottom instrumentation, or as a Review Console gate item?
- Should `force poll all` require an Aegis gate, or is it always low-risk enough to be a one-click action for Scott / a routine action for Prime?
- How should Bifrost present a mixed-state portfolio (some lanes running, some stale, some unassigned) in one summary glyph without re-introducing the Polaris card wall?
- When a session's backend `steering_mode` is `none`, what is the user-facing message for a force-poll request? "Queued for next natural poll" is honest; better wording may exist.
- How does queue activation interact with the Compass/objective surface? When Prime changes the active objective, should assigned queues automatically follow, or should reassignment always be explicit?

These should be resolved before any queue-activation UI is built — but resolving them does not require building UI to answer.

---

## 13. Summary

- Queue activation is a Prime-owned policy, surfaced by Bifrost, heartbeat-backed by Beacon.
- Per-session Q state is a mechanism with explicit fields and explicit actions, not a single button.
- Assignment is data, not card-name convention.
- Bifrost summarizes, the Review Console explains, and the worker wall does not come back.
- Until a real session harness exists, do not build the UI; mature the data model and the conventions instead.

This brief is docs-only and strategic. It does not authorize runtime code, FileMap edits, or package-API changes.
