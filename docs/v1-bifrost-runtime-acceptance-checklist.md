# V1 Bifrost Cockpit Runtime Acceptance Checklist

**Owner:** Build 4 (architecture)
**Status:** Draft — V1 runtime in progress
**Date:** 2026-05-31
**Depends on:** `docs/v1-bifrost-live-data-contract.md`, `docs/v1-bifrost-integration-sequence.md`, Build 1 `6c9a397` (Prime cockpit provider/factory)

---

## Purpose

This checklist is the gate document for declaring the V1 cockpit runtime "ready to use." Each item must be checked before the V1 cockpit is opened to general session use. Items are organized by harness owner. An item is not cleared until its proof expectation is met.

---

## Prime Harness

| # | Item | Proof Expectation | Status |
|---|------|-------------------|--------|
| P1 | `CockpitSnapshotProvider` emits a `PrimeCockpitSnapshot` on each `PromptPacket` dispatch | Unit test: dispatch mock packet, assert snapshot emitted with correct `prime_intention` fields | ☐ |
| P2 | `prime_intention` panel in cockpit shows current session intention and model | Integration smoke: send a turn, verify cockpit `prime_intention` panel updates within 2s | ☐ |
| P3 | Snapshot content does not appear in subsequent `PromptPacket.context` | Prompt-drag check: confirm no snapshot string appears in the following turn's context payload | ☐ |
| P4 | Provider factory wired in `prime_session.py` session loop | Code review: confirm `6c9a397` factory call present in session startup path | ☐ |
| P5 | Staleness badge appears if no snapshot event for >60s | Manual: suppress dispatch for 70s, confirm badge visible on `prime_intention` panel | ☐ |

---

## Bifrost Harness

| # | Item | Proof Expectation | Status |
|---|------|-------------------|--------|
| B1 | `pnpm dev` renders cockpit without errors | `pnpm dev` exits clean; no console errors; all six surface panels visible | ☐ |
| B2 | `CockpitSnapshot` → `CockpitViewModel` render model compiles without TypeScript errors | `tsc --noEmit` passes; unit test with stub snapshot produces expected panel props | ☐ |
| B3 | `pnpm preview:cockpit` renders all panels with mock data, no blank slots | All six panels non-empty; mock values visible in each slot | ☐ |
| B4 | Tabs and shell controls render and respond to interaction | Manual browser check: tab switching works; shell controls visible and clickable | ☐ |
| B5 | Degraded/unknown fallback renders for any missing snapshot field | Unit test: pass snapshot with one field null; confirm degraded badge shows, layout does not break | ☐ |
| B6 | No raw queue file content or session log text appears in any rendered panel | Visual inspection + code review: panels render only typed summaries from `CockpitViewModel` | ☐ |

---

## Review Console Harness

| # | Item | Proof Expectation | Status |
|---|------|-------------------|--------|
| RC1 | `review_gates` panel shows current `ReviewCard` list with severity and status | Integration smoke: create a `ReviewCard`, confirm it appears in cockpit `review_gates` panel | ☐ |
| RC2 | Gate status updates in panel on `ReviewCard` state change | Mutation test: change card status, confirm panel reflects update within refresh cadence | ☐ |
| RC3 | Action routing (approve / defer / escalate) does not write back into Prime prompt context | Code review: confirm no gate disposition text crosses the Bifrost/Prime boundary | ☐ |
| RC4 | Stale warning appears if no gate event for >120s | Manual: pause `ReviewCard` updates for 130s, confirm "gates stale" warning visible | ☐ |

---

## Beacon Harness

| # | Item | Proof Expectation | Status |
|---|------|-------------------|--------|
| BN1 | Liveness provider emits `{last_seen_at, age_seconds, is_stale}` on each heartbeat tick | Unit test: advance mock clock past stale threshold, assert `is_stale = True` | ☐ |
| BN2 | Staleness badge appears on each surface panel when `is_stale = True` | Integration smoke: suppress heartbeat for >stale threshold, confirm badges appear on all panels | ☐ |
| BN3 | Badge clears when heartbeat resumes | Resume heartbeat; confirm badges clear within one tick | ☐ |

---

## Relay Harness

| # | Item | Proof Expectation | Status |
|---|------|-------------------|--------|
| RL1 | `lane_strip` provider emits lane entry on each `RelayRoute` dispatch | Unit test: dispatch a route, assert lane strip entry created with correct `lane_id` and `status` | ☐ |
| RL2 | Lane strip panel updates on dispatch; shows active lane and session | Integration smoke: dispatch a route, confirm lane strip panel updates | ☐ |
| RL3 | No relay route payload text (directives, branch names) appears in Prime prompt context | Prompt-drag check: dispatch a route, verify no relay content in subsequent `PromptPacket.context` | ☐ |

---

## Aegis Harness

| # | Item | Proof Expectation | Status |
|---|------|-------------------|--------|
| AG1 | Proof provider emits pass/fail counts on each Aegis tick | Unit test: log a proof failure, assert `review_pending_count` increments | ☐ |
| AG2 | Proof/gate badge in instrumentation band shows correct pending count | Integration smoke: fail a proof gate, badge goes red with count | ☐ |
| AG3 | Failed-check detail is visible in cockpit without surfacing to Prime context | Code review: confirm Aegis finding summaries never cross the Bifrost/Prime boundary | ☐ |
| AG4 | Aegis findings must pass before any V1 wire step merges | Review gate: `AG2` badge green (0 pending) before V1 PR opens | ☐ |

---

## FileMap Harness

| # | Item | Proof Expectation | Status |
|---|------|-------------------|--------|
| FM1 | All new V1 runtime files registered in `docs/FileMap.md` | `FileMap.md` contains entries for: `bifrost/cockpit/`, render model, snapshot providers, liveness/lane/proof providers | ☐ |
| FM2 | All new V1 test files registered | `FileMap.md` entries present for all unit and integration test files added in V1 scope | ☐ |
| FM3 | FileMap registration committed before any wire step merges | Review gate: Build 3 FileMap commit hash present in lane's `Ready for Codex Review` marker | ☐ |

---

## Instrumentation Band

| # | Item | Proof Expectation | Status |
|---|------|-------------------|--------|
| IB1 | `prompt_budget_remaining` displays in bottom band; dims to `--` when unknown | Manual: run a session, confirm budget label updates; cut connection, confirm `--` fallback | ☐ |
| IB2 | `review_pending_count` and `review_cleared_count` update on ReviewCard state change | Integration smoke: clear a gate, confirm cleared count increments | ☐ |
| IB3 | `session_turn_count` increments on each turn | Send 3 turns, confirm count reaches 3 | ☐ |
| IB4 | No instrumentation band values appear in Prime prompt context | Hard stop check: verify `prompt_budget_remaining`, counts, and label strings are absent from `PromptPacket.context` | ☐ |

---

## Stop Conditions

The following conditions must trigger an immediate pause. Do not merge the V1 PR while any stop condition is active.

| Condition | Action |
|---|---|
| Any cockpit snapshot field found in a subsequent `PromptPacket.context` | **Hard stop** — prompt-drag detected; audit provider boundary before continuing |
| Any panel renders raw queue file text, commit message text, or session log excerpt | **Hard stop** — Bifrost must only render typed summaries |
| Any instrumentation band metric (budget %, session count, review count) found in Prime prompt context | **Hard stop** — instrumentation data must not cross the Bifrost/Prime boundary |
| A wire step produces a blank panel with no degraded/unknown fallback | **Pause** — add stale/unknown fallback before merging |
| Aegis proof gate fails (AG4 not green) | **Pause** — do not open V1 PR until Aegis clears |
| Bifrost TypeScript errors (`tsc --noEmit` fails) | **Stop** — fix before wiring any new surface |
| Shared worktree collision: two lanes edit the same `bifrost/cockpit/` file concurrently | **Pause** — coordinate via orchestrator branch-request before continuing |
| Any `Ready for Codex Review` marker missing a FileMap registration hash | **Hold** — FileMap registration must precede merge |

---

## Out of Scope for V1

The following are explicitly deferred and must not be included in the V1 cockpit PR:

- **Echo memory engine** — conversation memory retrieval, long-term context indexing
- **Atlas / RAG** — document retrieval, embedding search, knowledge-base surfaces
- **Multi-user federation** — multi-tenant session routing, shared cockpit views
- **Public / account adapter strategy** — external user auth, billing, tier-gating
- **Vendor-specific model presets** — provider-specific configuration panels, model benchmarking surfaces
- **Cockpit write-back** — V1 cockpit is read-only; no action dispatch to Prime or harness systems
- **Persistent cockpit state across Prime restarts** — V1 is session-scoped only

---

## Clearance Record

Append entries here as items are checked off.

```text
YYYY-MM-DD HH:MM TZ - <Harness> <item#> cleared; proof: <short note>; commit: <hash>
```
