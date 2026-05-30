# Bifrost Cockpit Queue Status Surface Brief

**Status:** Strategic / design-only — no runtime code
**Lane owner:** Build 5 (Bifrost / session-harness product lane)
**Audience:** Prime, Bifrost, Beacon, Aegis, Review Console designers, future cockpit implementers
**Companion brief:** `docs/bifrost-session-queue-activation-brief.md` (queue activation policy + per-session Q mechanism)

This brief is about **display**, not activation. It describes how the Meridian cockpit should show queue-driven worker activity so Scott can read system state at a glance — without rebuilding the Polaris worker-card wall, and without dragging every worker event into the Orchestrator Queue conversation.

The previous brief covered how polling is turned on, who controls assignment, and what state each lane carries. This one covers what the cockpit does with that state once it exists.

---

## 1. Why This Brief Exists

The current live build lanes (Build 1–5) already produce a useful event stream: pulls, polls, commits, blocks, idle heartbeats, cross-check findings, Codex reviews. That stream is rich enough to render a real cockpit panel today — and rich enough to flood it.

Polaris solved this badly. It showed every session as a permanent card, gave each card a status color, and let Scott infer activity from the wall. The wall worked at three lanes and broke at seven.

Meridian needs a cockpit that:

- shows enough queue/worker state for Scott to trust the system at a glance,
- routes routine events to Prime and Beacon (not to Scott's eyes),
- surfaces only what genuinely needs attention,
- preserves Scott's ability to drill into any lane when he chooses, without that path being the default.

---

## 2. Global Queue Activation State

The cockpit must always answer one question instantly: **is the queue system on?**

A single compact indicator, owned by Bifrost and fed by the activation policy (see companion brief), should show:

| Visible value | Meaning |
|---|---|
| `Queue: ON` | Global activation enabled; lanes are permitted to poll. |
| `Queue: OFF` | Global activation disabled; lanes must not poll. |
| `Queue: PAUSED` | Global pause; per-lane state preserved, polling halted. |
| `Queue: DEGRADED` | Activation on, but Beacon reports one or more lanes stale/failed. |
| `Queue: BLOCKED` | Activation on, but a gate (Aegis, conflict, human approval) is preventing dispatch. |

Rules:

- This indicator lives in bottom-edge cockpit instrumentation, near Beacon health and Compass bearing, not in the Orchestrator Queue conversation.
- Clicking it opens the global activation control with reason and last-changed-by (Prime / Scott).
- It must never be inferred from session text. It comes from the activation policy state, with Beacon confirming.
- `DEGRADED` and `BLOCKED` are not the same as `OFF`. The cockpit must distinguish "we chose to stop" from "we cannot start."

---

## 3. Per-Lane State for Build 1 Through Build 5

The cockpit should render one compact row per active lane — not a card grid, not a wall. A row is roughly: `lane | role | status | last-poll | last-commit | attention?`.

Sketch:

```text
Build 1  builder    running     11:38  7792243  -
Build 2  builder    polling     11:38  09f73a8  -
Build 3  builder    blocked     11:32  3acd8a8  needs attention
Build 4  reviewer   idle        11:37  951a6ed  -
Build 5  bifrost    running     11:39  11d78f6  -
```

Rules for the per-lane row:

- The `status` value is the canonical state from §4. Bifrost renders it; Beacon supplies it; the lane does not get to name its own color.
- `last-poll` and `last-commit` are timestamps/short hashes, not prose. They tell Scott whether the heartbeat is fresh without him reading any logs.
- `attention?` is a flag, not a long string. Set when the lane is `blocked`, `needs review`, `needs human gate`, or `stale`. Empty otherwise.
- Rows are sorted: lanes needing attention first, then running, then polling, then idle, then offline.
- Clicking a row expands into the on-demand lane detail panel (see §10). It does not open a permanent card.
- The lane list must compress gracefully: at 5 lanes it is a panel, at 20 it is still a panel (scroll + filter), never a card wall.

The lane is identified by harness session id, not by card title — consistent with the explicit-assignment rule in the companion brief.

---

## 4. Canonical Lane Status Set

The cockpit recognizes exactly these per-lane statuses. Anything else is a display bug.

| Status | Meaning | Source of truth |
|---|---|---|
| `idle` | Polling enabled, last poll succeeded, no active task assigned. | Beacon (poll heartbeat) + queue (no Active Task or task already complete in log). |
| `polling` | Polling enabled, last poll succeeded, waiting for next tick. | Beacon (recent poll heartbeat). Equivalent to "enabled-idle" from the activation brief. |
| `running` | Lane is executing an active task right now. | Beacon (task heartbeat) + queue (Active Task present, not yet logged complete). |
| `blocked` | Lane is alive but cannot proceed (conflict, denied permission, missing allowed file, scope gap). | Lane reports; cockpit must show the reason on hover/expand. |
| `needs review` | Lane has completed 3 task-changing commits and is awaiting Codex review per cadence. | Codex Review Cadence section + commit count rule. |
| `needs human gate` | Lane has produced a result that requires Scott's explicit decision (irreversible, public, account-risking, or escalated by Aegis). | Aegis / Prime escalation. |
| `stale` | Polling enabled but last poll heartbeat exceeds the threshold (default: 2 missed cycles). | Beacon. |
| `offline` | Lane is registered but not currently running (process exited, session closed, deliberately deactivated). | Session harness registry. |

Rules:

- `running` and `polling` are different. A lane mid-task is not the same as a lane mid-tick. Color, glyph, and sort order must reflect that.
- `needs review` and `needs human gate` are both "attention" states, but only `needs human gate` should ever generate a notification toward Scott. `needs review` is a Prime/Codex routine.
- `blocked` requires a `because:` reason exposed in the lane detail panel. No silent blocks.
- `stale` is not a fault on its own. It is a signal that Beacon and Prime should attempt recovery (force-poll, restart, reassign) before Scott sees it as a problem.

---

## 5. Orchestrator Queue vs. Review Console — Prime's Routing Rules

The cockpit has two prompt surfaces (see `docs/cockpit-ui-architecture.md`). Prime decides which surface each event goes to.

Heuristic rules Prime should follow:

| Event type | Default surface | Reason |
|---|---|---|
| Routine pull/poll heartbeat | Neither (only the per-lane row updates) | Heartbeats are instrumentation, not conversation. |
| Task assigned | Lane row + brief Orchestrator Queue line if user-facing | Scott sees the lane go `running`; Prime may say one sentence if it changes Scott's expectations. |
| Task completed (no review yet) | Lane row update (commit hash, status) | Completion is a state transition, not news. |
| Task completed (third-of-three; review cadence triggers) | Review Console | Prime is about to run a Codex review; Scott may want to see findings. |
| Codex review found nothing | Lane row + Review Console "no findings" entry | Audit trail, no interruption. |
| Codex review found issues | Review Console | Findings are gate items, not chat. |
| Lane blocked | Lane row `attention?` + Review Console entry if Prime cannot self-resolve | Routine recovery is Prime's job; Scott sees only if Prime cannot fix it. |
| Lane stale | Lane row `attention?` | Beacon and Prime should attempt force-poll/restart first. Scott sees only after escalation. |
| Cross-check finding addressed to the lane | Review Console | Cross-check is a gate surface item. |
| Aegis proof result | Review Console | Proof is always a gate surface. |
| Prime decision about portfolio direction | Orchestrator Queue | Conversation with Scott. |
| Scott-facing question or approval prompt | Orchestrator Queue | Conversation with Scott. |
| Lane needs human gate | Both: Orchestrator Queue (one-line ask) + Review Console (the gate item itself) | Scott must see the ask; Review Console holds the artifact and the decision controls. |

The Orchestrator Queue should not become a worker activity log. The Review Console should not become a chat. The cockpit instrumentation row is the third surface — the place where lane state lives and stays out of both prompt windows.

---

## 6. What Scott Can Click Or Command From The Cockpit

Cockpit interactions should serve Scott bottlenecks, not recreate the Polaris per-card pipeline. The minimum useful set:

**Global controls (instrumentation row, always visible):**

- Toggle global queue activation (`ON / OFF / PAUSE / RESUME`).
- Force poll all lanes (single action, fan-out via harness; honors per-backend `steering_mode`).
- Open Review Console (when there are queued items).

**Per-lane row (on hover / expand, not always visible):**

- Open lane detail panel.
- Force-poll this lane.
- Pause / resume this lane.
- Open the lane's queue file.
- Open the lane's last commit / PR.
- Transfer this lane's work to another session (rare; logged).
- Mark "I'm watching this" (pin equivalent — biases summaries, prevents auto-archive).

**Lane detail panel (drilldown only, not persistent):**

- The current Active Task text.
- The latest Read Checks / Write Log entries.
- Last commit hash + diff link.
- Reason for `blocked` / `stale` if applicable.
- Steering capability for the underlying backend.

**Review Console items (per item):**

- Approve / hold / reject / ask Prime.
- Open the artifact (proof, diff, finding, plan).
- Send a directive back to the originating lane.

What Scott should **not** need to click:

- A "poll now" button on every individual card.
- A "stop" button that may or may not work.
- A color shifter, lock toggle, reset-size, or preview control.
- Anything that requires reading prose to confirm completion.

---

## 7. What Should Be Hidden Until There Is A Problem

Default-hidden surfaces (revealed by attention state, drilldown, or explicit toggle):

- The lane detail panel (only on click).
- Per-lane Codex review findings while clean (rolled up as "no findings" on the row).
- Routine pull/poll heartbeats (instrumentation row updates count, but no chat line).
- Per-backend `steering_mode` details (visible in lane detail; not on the row itself).
- Cost and latency telemetry (available in lane detail; never on the row).
- Sessions in `offline` state for projects other than the active one.
- Completed tasks older than the current session window (rolled into Vault / Compass history).

Default-visible:

- Global queue activation indicator.
- Per-lane row for every active lane in the current project.
- Any lane in `blocked`, `needs review`, `needs human gate`, or `stale`.
- Beacon health summary.
- Review Console badge with count of pending items.
- Aegis gate badge when a tier-3+ action is pending.

Principle: visibility budget. The cockpit has limited Scott-eye real estate. Routine activity should consume zero of it; problems should consume exactly enough to be acted on.

---

## 8. How Beacon Supplies Liveness And Staleness Signals

Bifrost is a renderer. Beacon is the source of truth for whether a lane is alive.

Beacon's contract to the cockpit:

- Emits a structured event per lane on every successful poll cycle (poll heartbeat).
- Emits a separate structured event per lane on every task progress signal (task heartbeat).
- Distinguishes the two so the cockpit can show "polling fine but stuck on a task" or "working hard but not polling."
- Flags `stale` when poll heartbeat is older than the threshold (default ≤ 60s for a 30s cadence; 2 missed cycles triggers stale).
- Flags `failed` when the lane reports an error.
- Emits a structured `recovered` event when a previously stale/failed lane resumes — the cockpit clears attention without Scott needing to dismiss it manually.
- Surfaces lane heartbeat history (last N events) on demand for the lane detail panel.

Cockpit rules anchored to Beacon:

- The lane row's `status` and `last-poll` values come from Beacon, not from the lane card's own text.
- The `attention?` flag is set by the cockpit based on Beacon's flags, not by lane self-report.
- A lane with no Beacon heartbeat in the last threshold is `stale` regardless of what its session is currently printing.
- "Recovered" must clear `attention` automatically; Scott should never have to chase down a green light.

This is the Polaris failure mode being explicitly retired: status was inferred from streamed text and stuck on stale messages. In Meridian, the only thing that turns a status green is a fresh Beacon event.

---

## 9. How Aegis / Cross-Check Results Surface Without Hijacking The Main Conversation

Cross-check findings, Codex review outputs, and Aegis proof results are gate items. They belong in the Review Console, not in the Orchestrator Queue.

Rules:

- A finding produces a Review Console entry with: source (Codex / Aegis / cross-check), severity, affected lane, summary, suggested repair, and a disposition action set (acknowledge / accept / reject / send-back-to-lane).
- The cockpit shows a single rolled-up Review Console badge with the count of unaddressed items.
- For `low` / `info` severity: the badge updates; no chat line.
- For `medium`: the badge updates; the affected lane row gets `attention?`; no chat line.
- For `high` / `critical`: the lane gets `attention?` and `needs human gate`; Prime drops one short line into the Orchestrator Queue ("Lane 3 has a critical Aegis finding; review it in the Review Console") and nothing more.
- Aegis can hold a result open as a gate; the cockpit shows that gate as a badge with a clear "what is gated" tooltip.

What this prevents:

- The Polaris failure of every review finding becoming a conversation interruption.
- Cross-check noise from drowning the gate surface with low-severity items (badge counts those without shouting).
- Critical findings hiding behind a green health bar (lane `attention?` is set independently of overall health).

Routine review cadences (e.g. "Build 5 completed 3 commits, run a Codex review") run automatically and report back to the Review Console. Scott sees the summary, not the review itself, unless he opens it.

---

## 10. What Polaris Taught Us About Too Many Visible Worker Cards

Documented findings, restated as cockpit constraints:

- **A wall of session cards is a diagnostic surface, not a primary surface.** Sessions belong behind drilldowns. The cockpit's primary view is Prime, instrumentation, and gates — not workers.
- **Status inferred from text is unreliable.** If the cockpit cannot point to a structured event (Beacon, harness, Aegis, Codex), it must not paint a status color.
- **Color overload defeats color signaling.** Status colors should be reserved for canonical states. `blocked`, `needs review`, `needs human gate`, and `stale` should look distinct from each other and from `running`. Everything else stays cool/neutral.
- **Per-card buttons that fail silently destroy trust.** A button that may or may not stop a process is worse than no button. Cockpit actions must report acknowledged/applied/failed states.
- **Session card names drift and become coordination identity.** Cards are display objects. Identity is the harness session id. Renaming a card must change nothing functional.
- **Hide/minimize is essential, but hidden state can be forgotten.** The cockpit must keep summary counts of hidden state visible (e.g. "3 lanes hidden; 1 needs attention"). No important state should be reachable only by remembering to look.
- **Bottom metrics (tokens, latency, cost) were ignored.** Move them out of the lane row entirely. Keep them in lane detail and in analytics.
- **The orchestrator session, not the worker grid, is the primary relationship surface.** Workers are machinery. The cockpit should reflect that hierarchy in every layout decision.

The single-sentence Meridian rule:

> **Sessions are machinery. Show enough of them to trust the system, route the rest to Beacon and the Review Console, and never recreate the wall.**

---

## 11. Do Not Build Yet

The following should remain **design-only** until the session harness, Beacon heartbeats, and Review Console are real. Building any of them earlier risks re-encoding the Polaris card-wall pattern this brief is trying to prevent.

- **A per-lane card grid as the primary cockpit view.** Even if it looks like a sleeker Polaris, it is still the wall.
- **Status painted from session text or card name.** Wait for Beacon events.
- **Force-poll-all without per-backend `steering_mode` reporting.** A silent degrade is worse than no fan-out.
- **Stop / pause buttons on lane rows that lack the harness-side stop semantics described in `docs/polaris-ui-lessons-for-meridian.md`.** A button that may fail is worse than no button.
- **Cost/latency in the lane row.** Document them now; surface them only in lane detail.
- **Cross-check finding popups, toasts, or modal interrupts.** Findings go to the Review Console; severity gates whether Prime says anything in the Orchestrator Queue.
- **Drag-and-drop lane reassignment, transfer, or scope edits.** Reassignment is an explicit, logged harness action (see companion brief).
- **A combined "all events" log surface.** The cockpit is not a tail. Lane detail and Review Console replace that.

What **is** safe to do in parallel with the docs lane:

- Continue typing per-lane state fields so the cockpit has structured data to render once it exists.
- Continue maturing Beacon's heartbeat event shape.
- Continue defining the Review Console item schema so cross-check / Codex / Aegis can populate it consistently.

---

## 12. Open Questions

- Should the per-lane row sit in the bottom instrumentation band, in a dedicated left/right panel, or only appear on Harness drilldown? (Suggested default: bottom instrumentation in compressed form, dedicated panel on Harness button.)
- Should `needs review` ever produce a Orchestrator Queue line, or always stay in the Review Console badge? (Current lean: badge only, unless Prime needs Scott's input.)
- How many lanes before the row list needs filtering and grouping by project/portfolio? (Probably ≥ 8.)
- What is the visual treatment of a lane that has been `stale` long enough that Prime gave up trying to recover it?
- Should `attention?` accumulate across sessions (so Scott returning next day sees "3 lanes blocked since yesterday"), or be session-scoped?
- How does the cockpit handle a lane that is registered to a project Scott is not currently focused on? (Likely: visible only in Harness view, with portfolio-wide summary badge.)

These should be resolved before any cockpit UI is built. Resolving them does not require building UI.

---

## 13. Summary

- The cockpit answers three questions at a glance: is the queue on, which lanes need attention, and are there items waiting in the Review Console.
- Lanes appear as compressed rows driven by Beacon events, not as cards driven by session text.
- Routine activity routes to lane rows and the Review Console. The Orchestrator Queue stays a conversation.
- Cross-check, Codex, and Aegis findings live in the Review Console with severity-gated visibility.
- Polaris's worker wall is the failure mode being explicitly retired; sessions are machinery, not the primary surface.
- Until the harness is real, this brief is design constraint, not implementation.

This brief is docs-only and strategic. It does not authorize runtime code, FileMap edits, or package-API changes.
