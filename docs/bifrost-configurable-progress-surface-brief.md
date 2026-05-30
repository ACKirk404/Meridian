# Bifrost Configurable Progress And Proof Surface Brief

**Status:** Strategic / design-only — no runtime code
**Lane owner:** Build 5 (Bifrost / session-harness product lane)
**Audience:** Prime, Bifrost, Beacon, Aegis, Codex Reviews lanes, future cockpit implementers
**Companion briefs:**
- `docs/bifrost-session-queue-activation-brief.md` — queue activation policy + per-session Q mechanism
- `docs/bifrost-cockpit-queue-status-brief.md` — what queue/lane state is shown and where
- `docs/bifrost-v0-cockpit-layout-brief.md` — V0 cockpit composition
- `docs/bifrost-harness-dashboard-brief.md` — Harness dashboard surface

This brief defines the **configurable progress and proof surface** Scott called out: a right-side window that catches routine progress reports, proof/review updates, and Codex review status — keeping the Orchestrator Queue clean for actual conversation with Prime.

The Codex review lanes also need a structured way to report proof status when they poll, instead of letting their findings land as unstructured chat. This surface is where their structured updates appear.

---

## 1. Why This Brief Exists

Build 1–5 already produce a steady stream of events: 30-second polls, idle heartbeats, Ready-for-Codex-Review markers, Codex review results, repair routings, MEDIUM/LOW findings, boundary-cross notes. Polaris's failure mode was treating that stream as conversation — dropping it into the same prompt window where Scott was trying to talk to the orchestrator.

Meridian's inversion (Pillar 9: Prime-centric workspace, Pillar 10: Orchestrator vs. Non-Orchestrator queues) sets up the structural answer. But the cockpit briefs so far have named two prompt surfaces (Orchestrator Queue, Review Console) plus instrumentation. Scott's actual day-to-day produces a third class of message that fits neither well:

- **Routine progress** (10-minute "Bifrost is healthy, Build 3 shipped, no Aegis gates open"): too quiet for Orchestrator Queue, too unstructured for Review Console as a gate item.
- **Proof status from review sessions** ("Round B2 cleared FileMap repair, tests 47/47"): not a gate decision Scott needs to make, but he should see it land.
- **Codex review findings being routed** ("MEDIUM FileMap gap routed to Build 3"): informational, not actionable for Scott directly.

The progress surface is where this class of message lives, **configurably**, so Scott can tune what surfaces, when, and how loudly.

---

## 2. Right-Side Progress Surface Behavior

A single, persistent right-side surface in the cockpit, distinct from the Prime panel (Orchestrator Queue + Review Console tabs), distinct from the lane side band (compressed lane rows), distinct from the bottom instrumentation band.

V0 behavior:

- **Persistent and visible by default.** Scott can collapse it; not hidden by default.
- **Reverse-chronological feed** of progress entries. Newest at top.
- **Each entry is a card**, not a chat line: source, category, severity, timestamp, summary, optional drilldown link.
- **Auto-trims** to a configurable retention window (default: last 200 entries or last 24 hours, whichever is smaller). Older entries roll to Vault.
- **Receives, does not chat.** No input box on this surface.
- **Filterable in place** by category, severity, source, time window — without modal dialogs.
- **One-glance summary header**: counts by category in the current window. Scott can read system state without scrolling.

Anti-rules:

- Not a tail of every system event. Routine polls and 30-second heartbeats are aggregated, not streamed line-by-line.
- Not a place Scott posts to.
- Not the activity log of one lane — that lives in the lane detail panel (from `bifrost-cockpit-queue-status-brief.md` §6 / `bifrost-v0-cockpit-layout-brief.md` §6).

The naming working hypothesis is **Progress Surface**. Alternate candidates: Progress Pane, Briefing Bar, Status Stream, Heartbeat Feed. Naming is open (§14).

---

## 3. Message Categories

The progress surface accepts a fixed V0 category set. Each category has a default severity, default routing posture, and a glyph.

| Category | What it represents | Default severity | Default routing |
|---|---|---|---|
| `routine progress` | 10-minute Bifrost/Beacon/Compass heartbeat summary | info | Progress Surface only |
| `blocker` | A lane or harness has reported it cannot proceed | warning | Progress Surface + lane row attention; Orchestrator Queue if Prime cannot self-resolve |
| `review result` | A Codex Reviews lane recorded a pass / finding / repair routed | info–warning | Progress Surface + Review Console entry for any actionable finding |
| `proof summary` | Aegis proof completed (pass / partial / fail) | info–warning | Progress Surface; Review Console if waiver or human gate is needed |
| `repair routed` | A Codex Reviews lane wrote a repair task to another lane | info | Progress Surface; lane row attention on the target lane |
| `completion` | A task slice committed and marked ready | info | Progress Surface; Compass updates objective state |
| `human gate` | An action requires Scott's explicit decision | critical | Orchestrator Queue (one short line) + Review Console gate item + Progress Surface card |
| `system health` | Beacon, Relay, or any harness moved between health states | varies | Progress Surface; instrumentation band glyph updates |

Rules:

- Categories are typed. A producer (lane, harness, review session) must emit a category from this set or `other` (deprecated path; logged as a producer-side gap).
- Severity is canonical: `info / warning / critical`. Color discipline matches the cockpit-wide palette (cool / amber / red).
- Each card carries `(source, category, severity, timestamp, summary, drilldown ref)` minimum. Extra fields belong in the drilldown payload.

---

## 4. Routing Rules — Where Each Message Goes

The progress surface is one of four valid destinations. Prime decides which destination(s) each message reaches, by category, severity, and context.

Default routing table:

| Destination | Purpose | Receives by default |
|---|---|---|
| **Orchestrator Queue** | Scott ↔ Prime conversation | `human gate` (one short line); Prime conversational decisions |
| **Review Console** | Promptable review/gating surface (artifacts, proof, plans, findings) | `review result` with findings; `proof summary` requiring waiver; `human gate` artifact + decision controls |
| **Progress Surface** (this brief) | Configurable progress/proof feed | All categories by default; can be muted per category |
| **Session-card diagnostic log** | Per-lane debug evidence | Lane-internal events (poll succeeded, commit hash, error trace, retry count) |
| **Bottom instrumentation band** | One-line current-state cells | `system health` only (cell glyph updates) |

Routing principles:

- **Severity gates Orchestrator Queue access.** Anything below `critical` does not enter the Orchestrator Queue unless Scott has asked for it (override, §6).
- **Routine activity never enters the Orchestrator Queue.** That conversation stays a conversation.
- **Review Console is for items with disposition actions.** A `review result: pass, no findings` lands on the Progress Surface; a `review result: 1 MEDIUM, routed for repair` lands on both Progress Surface and Review Console (the latter has the gate item).
- **Diagnostic log is per-lane and silent.** Lane card drilldown shows it; the progress surface does not duplicate it.
- **System health updates the instrumentation cell.** A degraded-to-recovered transition is a Progress Surface card; the cell color simply returns to nominal.

Per-category default surfaces are listed in §3. Section 5 below covers Prime's decision logic when defaults are ambiguous.

---

## 5. How Prime Decides Where A Message Goes

Prime is the routing authority. Bifrost is the renderer.

Decision inputs Prime weighs:

- **Category and severity** from the producer.
- **Recent context.** If Scott just asked about lane 3, a related lane 3 event may surface as an Orchestrator Queue line; otherwise it stays on the Progress Surface.
- **Time-of-day / focus mode.** If Scott has marked himself focused on a different project, routine activity gets quieter.
- **Per-Scott routing preferences.** Stored mute lists, pin lists, severity thresholds (§6).
- **Burst suppression.** If 12 `routine progress` updates land in 30 seconds, Prime aggregates them into one card (`12 polls, all nominal`) rather than 12 cards.
- **Aegis gate state.** When Aegis is holding a tier-3+ gate open, related findings escalate one level until Scott has dispositioned the gate.

Rules:

- Prime never silently downgrades a `critical` from a producer. A `human gate` reaches the Orchestrator Queue.
- Prime can upgrade severity in context (an `info` blocker becomes a `warning` if it persists past three poll cycles).
- Prime's routing decision is itself logged (as a metadata note on the resulting card), so Scott can ask "why did this surface here?" and inspect.
- When Prime is unsure, default to the Progress Surface — never the Orchestrator Queue.

Anti-rules:

- Prime does not route based on inferred sentiment from session text. Routing is structured: producer → category + severity → rules.
- Prime does not chain-trigger Orchestrator Queue posts for related events. One human gate, one Orchestrator Queue line.

---

## 6. Scott's User Controls

Scott configures the Progress Surface; he does not configure Prime's underlying decision logic directly (Prime owns that). What Scott controls is **how the result is shown to him**.

V0 controls per producer / per category:

| Control | Effect |
|---|---|
| **Pin** | Card stays at top until manually unpinned. Scott does not have to scroll past it. |
| **Mute** | Future cards of this (producer, category) tuple skip the Progress Surface. Still recorded in audit. |
| **Collapse** | Group cards of the same (producer, category) under a single header; click to expand. |
| **Filter** | View only matching cards; the underlying feed is unchanged. |
| **Redirect** | Force-route future cards of this (producer, category) to a different destination. Example: send all Build 3 `completion` cards to Review Console too, not just Progress Surface. |
| **Clear** | Mark cards as read or dismiss them from the visible feed; audit unaffected. |
| **Severity threshold** | Hide cards below a chosen severity (e.g. `warning` and up). Affects the visible feed; underlying audit unaffected. |

V0 globals:

- **Quiet mode** — temporarily suppress all `info` severity Progress Surface entries (still recorded).
- **Focus mode** — narrows the feed to the active project; portfolio-wide info collapses to a single summary header.
- **Retention window** — adjust default 200 entries / 24 hours.
- **Default routing per category** — override the table in §3 once; applies until Scott changes it again.

Rules:

- Scott's controls are **per device / per cockpit session**, but pinned items and routing overrides persist across sessions.
- A muted producer cannot silence `critical` cards. Mute respects severity thresholds.
- All Scott controls have an `undo` and a reset-to-default.
- Controls are surfaced inline on each card (small icons) and in a settings panel reachable from the surface header.

Anti-rules:

- No keyword filters in V0. Categories + severity + producer suffice; keyword search is V1.
- No regex routing rules in V0.
- No cross-Scott controls (e.g. team mute lists); Meridian V0 is single-user.

---

## 7. How Codex Review Sessions Communicate Proof Status

The Codex Reviews lanes (`docs/live-codex-reviews.md`, `docs/live-codex-reviews-2.md`) currently report by editing markdown ledgers. Scott can read the ledger, but the status does not surface anywhere automatic in the cockpit.

The Progress Surface gives those sessions a structured channel:

- When a Reviews lane records a Review Log entry, it should emit a `review result` Progress Surface card with `(commit hash, lane, result, finding count by severity, tests summary)`.
- When a Reviews lane writes to the Repair Routing Log, it emits a `repair routed` card naming the target lane and the finding.
- When a Reviews lane records "no actionable findings" or "pass, cadence pause cleared", it emits a `review result: pass` card with no Review Console gate item.
- When a Reviews lane verifies a prior repair, it emits a `proof summary` card.

For Aegis specifically:

- Aegis proof completions emit `proof summary` cards with `(scope, command run, expected vs actual, waiver applied?)`.
- Aegis-blocked actions emit `human gate` cards if Scott's disposition is required; otherwise `blocker` if Prime can self-resolve.

This is the answer to "how does the review session communicate proof status when it polls": through typed `review result` and `proof summary` cards on the Progress Surface, with a Review Console gate item only when something is actually for Scott to decide.

---

## 8. Relationship To The Non-Orchestrator Prompt Window

`docs/non-orchestrator-surface-naming.md` named the Review Console as the second prompt surface — the place where artifacts, plans, comparisons, and gates land with disposition actions. The Progress Surface is **not** a third prompt surface; it is a **feed**, not a prompt.

| Surface | Type | What lives here |
|---|---|---|
| Orchestrator Queue | Prompt (conversation) | Scott ↔ Prime |
| Review Console | Prompt (gating) | Items with disposition actions (approve / hold / reject / send-back) |
| Progress Surface | Feed (information) | Routine and informational events, configurable by Scott |
| Session-card diagnostic log | Feed (per-lane debug) | Per-lane event traces, only on demand |
| Instrumentation band | State cells | Current health, route, queue ON/OFF, build number, clock |

Rules linking them:

- A Progress Surface card may **link to** a Review Console gate item; the link is one click.
- A Progress Surface card may **link to** the lane detail panel; one click.
- A Review Console disposition may produce a follow-up Progress Surface card ("Scott approved Aegis waiver at 12:33").
- The Orchestrator Queue should never duplicate a card already on the Progress Surface; if Prime drops a one-liner referring to a Progress Surface card, it should link to it.

Anti-rules:

- The Progress Surface does not become a chat (`bifrost-cockpit-queue-status-brief.md` §10 anti-rules apply).
- The Review Console does not become a tail of Progress Surface cards.
- The Orchestrator Queue does not subscribe to Progress Surface event types.

---

## 9. External Notifications (Later)

V0 does not push to email, Slack, SMS, browser notifications, or webhook destinations.

Held for V1+:

- Scott-configurable external destinations per category + severity.
- Quiet hours that route critical events to a different external channel.
- Digest emails summarizing 24-hour Progress Surface activity.
- Per-project subscription URLs for Scott to follow remotely.

V0 contribution toward future external notifications:

- The Progress Surface schema (source, category, severity, timestamp, summary, drilldown ref) is what an external destination would consume. Building it now means V1 external notifications can subscribe without retrofitting the producer side.
- The retention window and audit log establish the data substrate for digests.

---

## 10. V0 Build Discipline (Per Surface Entry)

Before a producer ships entries to the Progress Surface:

1. **Named category.** Producer must declare the V0 category. `other` is a producer-side gap, not a category.
2. **Named severity.** `info / warning / critical`. Must not be inferred from text.
3. **Named summary.** One short sentence; the full payload lives in drilldown.
4. **Named drilldown target.** A lane, a Review Console item, an Aegis proof record, or a commit; not a URL string.
5. **Named producer id.** Stable across renames; identifies the harness session or lane.
6. **Named timestamp.** Local time, with tz; Beacon supplies it when emitting.

A producer that cannot satisfy all six fields does not emit; the gap is logged for the producer's lane.

---

## 11. What V0 Should Intentionally Leave Out

Held for V1+ unless promoted explicitly:

- **External notifications.** Email / Slack / SMS / webhooks (covered §9).
- **Keyword and regex filters.** V0 categories + severity + producer are sufficient.
- **Cross-Scott / team routing rules.** Single-user.
- **Per-card threaded replies.** The surface is a feed, not chat.
- **Drag-and-drop reordering by Scott.** Reverse-chronological with pin is enough.
- **User-defined custom categories.** V0 ships the typed set in §3; new categories require a brief and a producer update.
- **AI-summarized digest cards.** Burst suppression (§5) is structural, not generative, in V0.
- **Cross-project portfolio feed.** Focus mode collapses to active project; portfolio rollup is V1.
- **Sound / haptic alerts.** Critical-only alerts will probably arrive in V1; not in V0.
- **Real-time-streaming session output.** Per-lane streaming belongs in the lane detail panel, not on the Progress Surface.
- **Voice readout.** NASA-style Go calls are wake-only (`bifrost-v0-cockpit-layout-brief.md` §8). The Progress Surface does not speak.

Each item has a clear later home. V0 ships less so Scott can tune what surfaces without first inheriting Polaris's entire notification debt.

---

## 12. Cross-Surface Invariants

These hold across Orchestrator Queue, Review Console, Progress Surface, lane side band, and instrumentation band:

- **Single source of truth per fact.** A finding's severity is the producer's. A lane's health is Beacon's. The Progress Surface renders; it does not invent.
- **Shared color discipline.** `info / warning / critical` maps to cool / amber / red on every surface.
- **Identity is registry id.** Producer renames do not change subscriptions, mute lists, or pins.
- **Drilldowns do not replace Prime.** Every Progress Surface card interaction leaves the Orchestrator Queue intact.
- **Audit trail.** All Progress Surface entries are logged outside the surface (Vault / events.jsonl) so retention-window trimming and mutes never destroy history.
- **One human gate, one Orchestrator Queue line.** Even if a `human gate` produces a Progress Surface card and a Review Console gate item, Prime drops at most one Orchestrator Queue line to summon Scott.

---

## 13. Default Layout Sketch

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│  Settings  Projects  Reset  Close  Cross Check  Backlog  Skills  Harness     │
│  Search  Mission Objectives                                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                ┌────────────────────────────┐│
│ Project: Meridian  ·  Tier: 2  ·  Prime: ok    │ Progress  (filtered: all) ││
│ ┌─────────────────────────────┐ ┌─────────┐    │ ──────────────────────── ││
│ │ [Orchestrator Queue]  [Rev] │ │ Lanes   │    │ 13:09  Build 5 completion ││
│ │                              │ │ ─────── │    │   commit a80760b  ↗      ││
│ │  Prime: Good afternoon.     │ │ B1 run  │    │ ──────────────────────── ││
│ │  Two items in the           │ │ B2 poll │    │ 13:08  Reviews B review   ││
│ │  Review Console.            │ │ B3 blk  │    │   B5 7c34566 PASS         ││
│ │  [scrollable]               │ │ B4 idle │    │   MEDIUM → Build 3  ↗    ││
│ │                              │ │ B5 run  │    │ ──────────────────────── ││
│ │  ┌────────────────────────┐ │ │         │    │ 13:00  Beacon health      ││
│ │  │ > _                    │ │ │ 5 total │    │   all lanes nominal       ││
│ │  └────────────────────────┘ │ │ 1 attn  │    │ ──────────────────────── ││
│ └─────────────────────────────┘ └─────────┘    │ 12:48  Aegis proof        ││
│                                                │   FileMap registry 47/47  ││
│                                                │ ──────────────────────── ││
│                                                │ Filter ▾  Mute ▾  Pin ▾   ││
│                                                └────────────────────────────┘│
├──────────────────────────────────────────────────────────────────────────────┤
│ Beacon ✓  Relay route ✓  Aegis ✓  Compass ✓  Queue ON  Tier 2  v0.X  13:09  │
└──────────────────────────────────────────────────────────────────────────────┘
```

Structural points the sketch carries:

- Right-side Progress Surface is persistent; not a tab, not a modal.
- Cards are scannable: timestamp, source, category, summary, drilldown arrow.
- Per-card and per-surface controls (Filter, Mute, Pin) live in the header, not as floating buttons.
- Prime panel and lane side band remain the dominant cockpit content.
- Bottom instrumentation band stays unchanged.

---

## 14. Open Questions

- Final name. Working hypothesis is `Progress Surface`. Alternates: Progress Pane, Briefing Bar, Status Stream, Heartbeat Feed. Naming should match cockpit voice (instrumentation-honest, not playful).
- Default location. Right side is the working assumption; left side may suit Scott's flow better in practice.
- Does the surface collapse to a glyph in the bottom band when fully closed, or vanish entirely?
- Should pin be sticky across the retention rollover, or only within the current window?
- How loud should `critical` Progress Surface cards be visually, given that they also produce an Orchestrator Queue line?
- Should `burst suppression` (§5) be configurable per category, or globally only?
- Do Codex review `review result: pass, no findings` cards roll up by lane (one card per day per lane) or land individually?
- When Scott `mute`s a producer, should the audit panel surface a "currently muted: 4" indicator so it isn't forgotten?
- Retention defaults: 200 entries / 24 hours — is the right ratio?

These should be resolved before the surface is implemented. Documenting them as open questions is the V0 contribution.

---

## 15. Summary

- The Progress Surface is a persistent right-side feed for routine progress, proof, review, and informational events — everything that shouldn't crowd the Orchestrator Queue or hide in the Review Console.
- Eight typed message categories (`routine progress / blocker / review result / proof summary / repair routed / completion / human gate / system health`), each with default severity and routing.
- Prime decides routing using producer category + severity + context; Scott configures how the result is presented (pin / mute / collapse / filter / redirect / clear / severity threshold).
- Codex Reviews and Aegis lanes get a structured channel for `review result` and `proof summary` cards instead of buried markdown updates.
- The surface is a feed, not a prompt: receives only, never chat.
- Cross-surface invariants keep severity color, identity, and audit consistent with the rest of the cockpit.
- V0 leaves out external notifications, keyword filters, AI digests, voice — keeping the surface a clean instrument first.

This brief is docs-only and strategic. It does not authorize runtime code, FileMap edits, or package-API changes.
