# V1 Bifrost Live-Data Integration Contract

**Owner:** Build 4 (architecture)
**Status:** Draft — V1 scaffold pending
**Date:** 2026-05-31

---

## Principle

Bifrost renders typed objects and pre-computed summaries. It never reads raw queue files, full session logs, or any content that would be injected into Prime's prompt context. Every surface binding is a read-only projection of a domain object that Prime or the harness already owns.

---

## Surface Contracts

### 1. Prime Conversation / Current Intention

| Field | Value |
|---|---|
| **Owning harness** | Prime session loop (`prime_session.py`) |
| **Source today** | `PromptPacket.intention`, `PromptPacket.session_id`, `RelayRoute.destination` |
| **V1 domain object** | `CockpitSnapshot.prime_intention` — a short typed struct: `{session_id, intention_text, active_model, turn_count}` |
| **Refresh cadence** | On each `PromptPacket` dispatch; push via harness event |
| **Stale/degraded** | Show last-known value with a staleness badge if no event for >60s |
| **Never inject into Prime** | Rendered cockpit text, Bifrost summaries, any UI label strings |

---

### 2. Review Console Gates

| Field | Value |
|---|---|
| **Owning harness** | Review Console domain (`review_console.py`) |
| **Source today** | `ReviewCard` list, `ReviewStatus` enum, `ReviewSeverity` enum |
| **V1 domain object** | `CockpitSnapshot.review_gates` — `[{card_id, title, severity, status, assignee}]` |
| **Refresh cadence** | On `ReviewCard` state change; push via harness event |
| **Stale/degraded** | Show last-known gate list; surface "gates stale" warning if no event for >120s |
| **Never inject into Prime** | Gate disposition text, reviewer notes, raw card payloads |

---

### 3. Lane Strip / Queue State

| Field | Value |
|---|---|
| **Owning harness** | Polaris session orchestrator / live-build queue files |
| **Source today** | `docs/live-build-*.md` active task sections, harness `orchestrator-active.json` |
| **V1 domain object** | `CockpitSnapshot.lane_strip` — `[{lane_id, lane_name, status, active_task_title, commit_hash}]` |
| **Refresh cadence** | On harness commit push or queue file write; poll fallback every 30s |
| **Stale/degraded** | Show cached lane list with staleness indicator; do not block UI |
| **Never inject into Prime** | Full queue file contents, raw commit messages, session transcript excerpts |

---

### 4. Progress Surface Events

| Field | Value |
|---|---|
| **Owning harness** | Build harness event log (`harness-prototype.md` spec) |
| **Source today** | Commit log, `Write/Completion Log` sections in live-build files |
| **V1 domain object** | `CockpitSnapshot.progress_events` — `[{timestamp, lane_id, event_type, summary, commit_hash}]` where `event_type ∈ {task_started, task_completed, idle_check, review_requested, review_cleared}` |
| **Refresh cadence** | On each harness commit; push via event stream |
| **Stale/degraded** | Show last N events frozen; badge "event stream paused" if quiet >90s |
| **Never inject into Prime** | Full event bodies, file diffs, test output |

---

### 5. Harness Dashboard

| Field | Value |
|---|---|
| **Owning harness** | Polaris session orchestrator |
| **Source today** | `orchestrator-active.json`, session metadata |
| **V1 domain object** | `CockpitSnapshot.harness` — `{active_sessions: int, orchestrator_status, last_directive_at, build_phase}` |
| **Refresh cadence** | On orchestrator tick (default 30s); push on directive write |
| **Stale/degraded** | Show "orchestrator unreachable" badge; hold last known state |
| **Never inject into Prime** | Orchestrator directive text, branch-request payloads |

---

### 6. Bottom Instrumentation Band

| Field | Value |
|---|---|
| **Owning harness** | Composite — pulls from Prime session + Codex Reviews lane |
| **Source today** | `live-codex-reviews.md` pending/cleared counts, `PromptBudgetPlan` fields |
| **V1 domain object** | `CockpitSnapshot.instrumentation` — `{prompt_budget_remaining, review_pending_count, review_cleared_count, session_turn_count, last_commit_hash, last_commit_at}` |
| **Refresh cadence** | On each turn dispatch (budget); on each review state change (counts) |
| **Stale/degraded** | Dim counts; show "--" for budget if unknown; never block layout |
| **Never inject into Prime** | Budget percentages, count displays, any cockpit metric labels |

---

## CockpitSnapshot Shape (V1 Target)

```python
@dataclass
class CockpitSnapshot:
    snapshot_at: str                    # ISO timestamp
    prime_intention: PrimeIntention
    review_gates: list[ReviewGateSummary]
    lane_strip: list[LaneStatus]
    progress_events: list[ProgressEvent]
    harness: HarnessStatus
    instrumentation: InstrumentationBand
```

All fields are typed summaries — no raw log content, no file paths that Bifrost would re-read on render.

---

## Integration Order (Post-Scaffold)

After Build 5 lands the cockpit scaffold and Build 1 delivers the Prime-side domain shape:

1. **Wire `prime_intention`** — simplest binding; single struct off PromptPacket dispatch.
2. **Wire `instrumentation.prompt_budget_remaining`** — one field, already computed in PromptBudgetPlan.
3. **Wire `lane_strip`** — poll harness queue files via a thin reader; convert to typed list.
4. **Wire `review_gates`** — bind to ReviewCard list on ReviewConsole domain.
5. **Wire `progress_events`** — subscribe to commit push events; map to ProgressEvent structs.
6. **Wire `harness`** — read orchestrator-active.json on tick.
7. **Wire `instrumentation` (remaining fields)** — fill counts from codex-reviews state.

Each step is independently shippable. Bifrost can render a partial snapshot; missing fields show as degraded/unknown rather than blocking the surface.

---

## What Must Never Cross Into Prime Prompts

- Any cockpit display string rendered by Bifrost
- Raw queue file contents or log excerpts
- Review card disposition notes
- Budget percentage labels or instrumentation band text
- Session count metrics

Bifrost is a read surface only. It has no write path into Prime's context window.
