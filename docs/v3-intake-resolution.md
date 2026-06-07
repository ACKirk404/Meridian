# V3 Intake Resolution

**Source:** `docs/agentic-ai-framework-checklist.md` V3 Intake Rule.
**Trigger:** V2 Needs Build is closed; V3 intake gate now opens.
**Purpose:** Resolve every `[~]` and `[ ]` checklist item into one of the four
required outcomes — **Promote to V3**, **Move earlier**, **Park for later**, or
**Reject** — and name an owner (Prime or a named harness) for each.

This document does not write V3 implementation specs. It is the deterministic
intake artifact that gates V3 spec work.

## Outcome Definitions

- **Promote to V3** — becomes a Prime-owned or harness-owned V3 roadmap item.
  Implementation specs land later, after this gate closes.
- **Move earlier** — required for V2 autonomy; the work is already inside the
  V2 envelope (Echo memory runtime, Atlas retrieval runtime, Prime autonomy
  selector, Session Lifecycle, workflow sub-agent contract, Bifrost V2,
  V2 progress tracker). Tracked there, not here.
- **Park for later** — V4+ or public/product horizon; remains horizon-only and
  may be promoted to V3 only after V3 closes.
- **Reject** — intentionally out of scope for Meridian; documented here as a
  closed decision so future intake passes do not reopen it.

## Resolution Index

Every row below corresponds to a unique `[~]` or `[ ]` item in
`docs/agentic-ai-framework-checklist.md`. Items that appear twice in the
checklist (Speech/audio interfaces, Memory governance and retention, Dynamic
tooling, Video generation, Agent marketplaces and contracts) are resolved once
under the canonical row and the duplicate is cross-referenced so the count
remains exhaustive.

### Gen AI Capabilities (lines 66-73)

| # | Checklist line | Item | Marker | Owner | Outcome | Rationale |
|---|---|---|---|---|---|---|
| 1 | 66 | Retrieval-Augmented Generation (RAG) | `[~]` | Atlas Harness | Move earlier | Atlas runtime retrieval is already inside the V2 envelope; checklist note already says "runtime retrieval engine is V2 work". |
| 2 | 67 | Multimodal generation | `[~]` | Model Harness (primary) / Bifrost | Promote to V3 | Non-text generation surfaces (image/audio preview artifacts) are V3 polish, not V2 autonomy. |
| 3 | 68 | Personalization | `[~]` | Echo Harness | Move earlier | Personalization rides on Echo memory runtime, which is V2 scope. |
| 4 | 69 | Speech interfaces (TTS/ASR) | `[~]` | Bifrost (primary) / Model Harness | Promote to V3 | Wake-sequence audio and TTS/ASR are explicit V3 cockpit polish, not V2 autonomy. |
| 5 | 70 | Audio/music generation | `[ ]` | Model Harness | Park for later | Checklist already marks this as "later horizon only"; no Meridian runtime need until V4+. |
| 6 | 71 | Code generation | `[~]` | Session Lifecycle Harness (primary) / Relay Harness | Move earlier | Native session lifecycle is V2 scope; live build lanes already prove the orchestration. |
| 7 | 72 | Image generation | `[~]` | Model Harness (primary) / Bifrost | Promote to V3 | Diagrams/mockups are useful but not core; promote as a bounded V3 Model Harness capability. |
| 8 | 73 | Video generation | `[ ]` | Model Harness | Park for later | Checklist already marks this as later horizon; no V3 demand identified. |

### Agent Capabilities (lines 81, 89, 91)

| # | Checklist line | Item | Marker | Owner | Outcome | Rationale |
|---|---|---|---|---|---|---|
| 9 | 81 | Multi-agent collaboration | `[~]` | Session Lifecycle Harness | Move earlier | Native lifecycle/review scaling is the V2 Session Lifecycle build. |
| 10 | 89 | Memory systems (short-term + long-term) | `[~]` | Echo Harness (primary) / Atlas Harness | Move earlier | Echo + Atlas runtime is the core V2 build; not a V3 intake item. |
| 11 | 91 | Autonomous execution | `[~]` | Prime (primary) / Session Lifecycle Harness | Move earlier | V2 Prime Autonomy selector + Session Lifecycle deliver native execution. |

### Agent Management (line 97)

| # | Checklist line | Item | Marker | Owner | Outcome | Rationale |
|---|---|---|---|---|---|---|
| 12 | 97 | Self-improvement | `[~]` | Prime (primary) / Echo Harness / Aegis Harness | Promote to V3 | V2 lays the substrate (lessons + review findings → memory); bounded self-improvement loops are a V3 deliverable. |

### Agentic AI Layer (lines 102, 105, 106, 108, 112, 114)

| # | Checklist line | Item | Marker | Owner | Outcome | Rationale |
|---|---|---|---|---|---|---|
| 13 | 102 | Self-improving agents | `[~]` | Prime (primary) / Echo Harness / Aegis Harness | Promote to V3 | Bounded self-modification under proof + memory gates is a V3 capability, not V2. |
| 14 | 105 | Cost and resource management | `[~]` | Relay Harness (primary) / Model Harness / Bifrost | Promote to V3 | Provider balance and usage surfacing is a V3 decision; the specific surface, adapter bindings, and metering shape land in later V3 specs, not in this intake artifact. |
| 15 | 106 | Long-term autonomy and goal chaining | `[~]` | Prime (primary) / Compass Harness / Echo Harness | Promote to V3 | Native Goal Runtime / Goal Harness is a V3 decision; goal-object shape, status lifecycle, telemetry, continuation/resume policy, and proof-trail semantics land in later V3 specs. Already pre-listed in `docs/v3-parking-lot.md`. |
| 16 | 108 | Memory governance and retention policies | `[~]` | Echo Harness | Move earlier | Explicit retention and memory-edit policy are required for V2 Echo to ship; tracked under V2 Echo contract. |
| 17 | 112 | Agent marketplaces and contracts | `[ ]` | Federation Harness (primary) / Release Harness | Park for later | V4+ public/product horizon; already pre-listed under Federation/Release in `docs/v3-parking-lot.md`. |
| 18 | 114 | Dynamic tooling | `[~]` | Tool Harness (primary) / Model Harness | Promote to V3 | Runtime tool registry/catalog is the V3 Tool Harness deliverable. |

### Outputs And Interfaces (lines 120, 123)

| # | Checklist line | Item | Marker | Owner | Outcome | Rationale |
|---|---|---|---|---|---|---|
| 19 | 120 | Video generation (duplicate of row 8) | `[ ]` | Model Harness | Park for later | Duplicate of Gen AI row 8 (line 73). Resolved once; cross-referenced here for count completeness. |
| 20 | 123 | Speech/audio interfaces (duplicate of row 4) | `[~]` | Bifrost (primary) / Model Harness | Promote to V3 | Duplicate of Gen AI row 4 (line 69). Resolved once; cross-referenced here for count completeness. Owner set mirrors canonical row 4 exactly so the duplicate truly collapses to the same owner-anchored decision. |

### Governance And Future (lines 128, 132, 134)

| # | Checklist line | Item | Marker | Owner | Outcome | Rationale |
|---|---|---|---|---|---|---|
| 21 | 128 | Memory governance and retention (duplicate of row 16) | `[~]` | Echo Harness | Move earlier | Duplicate of Agentic AI Layer row 16 (line 108). Resolved once; cross-referenced here. |
| 22 | 132 | Agent marketplaces and contracts (duplicate of row 17) | `[ ]` | Federation Harness / Release Harness | Park for later | Duplicate of Agentic AI Layer row 17 (line 112). Resolved once; cross-referenced here. |
| 23 | 134 | Dynamic tooling (duplicate of row 18) | `[~]` | Tool Harness (primary) / Model Harness | Promote to V3 | Duplicate of Agentic AI Layer row 18 (line 114). Resolved once; cross-referenced here. Owner set mirrors canonical row 18 exactly so the duplicate truly collapses to the same owner-anchored decision. |

### Deep Learning Layer (line 59)

| # | Checklist line | Item | Marker | Owner | Outcome | Rationale |
|---|---|---|---|---|---|---|
| 24 | 59 | Deep belief networks | `[ ]` | Model Harness | Reject | Intentionally out of scope. Meridian does not train or own underlying ML architectures; only relevant if a future ML-specific project requires it, at which point the Model Harness adapter contract covers it without a Meridian roadmap item. |

### Meridian Coverage Summary (lines 139, 140)

| # | Checklist line | Item | Marker | Owner | Outcome | Rationale |
|---|---|---|---|---|---|---|
| 25 | 139 | V2 core build summary roll-up | `[~]` | Prime (coordinator) across Echo / Atlas / Session Lifecycle / Bifrost | Move earlier | Summary line covering the V2 envelope; tracked in `docs/v2-progress-tracker.md`, not a V3 intake item. |
| 26 | 140 | Later horizon summary roll-up | `[ ]` | Federation Harness / Release Harness / Model Harness / Aegis Harness | Park for later | Summary line covering federation/multi-user runtime, marketplace/contracts, video/audio generation, public packaging/account strategy, vector DB, dynamic tool marketplace — all V4+ public/product horizon. Individual items already enumerated in `docs/v3-parking-lot.md`. |

## Outcome Totals

Every `[~]` and `[ ]` item from `docs/agentic-ai-framework-checklist.md` is
resolved exactly once. Duplicate checklist lines are cross-referenced to their
canonical resolution row, so the total count below matches the deterministic
item-prefix grep count.

The authoritative item count comes from the targeted item-prefix grep
`rg -n "^- \[~\] |^- \[ \] " docs/agentic-ai-framework-checklist.md`, which
returns 26 lines (19 `[~]` + 7 `[ ]`). A raw `rg -n "\[~\]|\[ \]"` over the
same file returns 30 lines because four non-item references also match —
the two legend lines (lines 11 and 12) and the two V3 Intake Rule prose
lines (lines 18 and 27) that cite both `[~]` and `[ ]` by name. Only the 26
item lines are resolution targets.

| Outcome | Row count | Rows |
|---|---|---|
| Promote to V3 | 10 | 2, 4, 7, 12, 13, 14, 15, 18, 20, 23 (dup rows 20, 23 collapse to canonical 4, 18) |
| Move earlier | 9 | 1, 3, 6, 9, 10, 11, 16, 21, 25 (dup row 21 collapses to canonical 16) |
| Park for later | 6 | 5, 8, 17, 19, 22, 26 (dup rows 19, 22 collapse to canonical 8, 17) |
| Reject | 1 | 24 |
| **Total resolution rows** | **26** | matches `[~]` (19) + `[ ]` (7) = 26 item-prefix grep lines in checklist body |

Unique-decision totals (after collapsing the five duplicate checklist lines —
Speech/audio, Memory governance, Dynamic tooling, Video generation, and Agent
marketplaces — into single owner-anchored decisions):

| Outcome | Unique decisions |
|---|---|
| Promote to V3 | 8 |
| Move earlier | 8 |
| Park for later | 4 |
| Reject | 1 |
| **Total unique decisions** | **21** |

## Owner Roll-Up

Every resolved row names a Prime or harness owner. Items with co-owners list
the primary owner first in the row's Owner column.

Convention: an entry without an asterisk means the owner is **primary** in
that row (first-listed in the row's Owner column); an asterisk (`*`) means the
owner is a **co-owner** in that row. Every row appears under every owner that
its Owner column names, so every (row, owner) pair in the resolution index is
reachable from this table.

| Owner | Promote to V3 | Move earlier | Park for later | Reject |
|---|---|---|---|---|
| Prime | 12, 13, 15 | 11, 25 | — | — |
| Atlas Harness | — | 1, 10*, 25* | — | — |
| Echo Harness | 12*, 13*, 15* | 3, 10, 16, 21, 25* | — | — |
| Aegis Harness | 12*, 13* | — | 26* | — |
| Compass Harness | 15* | — | — | — |
| Relay Harness | 14 | 6* | — | — |
| Model Harness | 2, 4*, 7, 14*, 18*, 20*, 23* | — | 5, 8, 19, 26* | 24 |
| Bifrost Harness | 2*, 4, 7*, 14*, 20 | 25* | — | — |
| Session Lifecycle Harness | — | 6, 9, 11*, 25* | — | — |
| Tool Harness | 18, 23 | — | — | — |
| Federation Harness | — | — | 17, 22, 26 | — |
| Release Harness | — | — | 17*, 22*, 26* | — |

Per-row coverage cross-check (each of the 26 resolution rows is reachable
from at least one Owner cell above; rows with multiple owners are reachable
from every owner cell that names them):

- Rows with one owner: 1, 3, 5, 8, 9, 16, 19, 21, 24 — 9 rows.
- Rows with two owners: 2, 4, 6, 7, 10, 11, 17, 18, 20, 22, 23 — 11 rows.
- Rows with three owners: 12, 13, 14, 15 — 4 rows.
- Rows with four owners: 26 — 1 row.
- Rows with five owners: 25 — 1 row.
- Total: 9 + 11 + 4 + 1 + 1 = 26 ✓.

Owner-cell totals (Promote / Move / Park / Reject, including co-owner entries):

- Prime: 3 + 2 + 0 + 0 = 5.
- Atlas Harness: 0 + 3 + 0 + 0 = 3.
- Echo Harness: 3 + 5 + 0 + 0 = 8.
- Aegis Harness: 2 + 0 + 1 + 0 = 3.
- Compass Harness: 1 + 0 + 0 + 0 = 1.
- Relay Harness: 1 + 1 + 0 + 0 = 2.
- Model Harness: 7 + 0 + 4 + 1 = 12.
- Bifrost Harness: 5 + 1 + 0 + 0 = 6.
- Session Lifecycle Harness: 0 + 4 + 0 + 0 = 4.
- Tool Harness: 2 + 0 + 0 + 0 = 2.
- Federation Harness: 0 + 0 + 3 + 0 = 3.
- Release Harness: 0 + 0 + 3 + 0 = 3.
- Sum across all owners: 5 + 3 + 8 + 3 + 1 + 2 + 12 + 6 + 4 + 2 + 3 + 3 = 52,
  which equals the sum of owners across all 26 rows
  (9×1 + 11×2 + 4×3 + 1×4 + 1×5 = 9 + 22 + 12 + 4 + 5 = 52) ✓.

## Cross-Checks Against Existing Docs

- `docs/v3-parking-lot.md` already pre-lists the Native Goal Runtime / Goal
  Harness (row 15), Provider compliance modes and Model harness metering (row
  14 substrate), Dynamic tooling registry surface (rows 18 + 23 substrate),
  Federation / Marketplace items (rows 17 + 22), and the public/product
  horizon (row 26). This resolution does not contradict the parking lot; it
  formalizes the intake decisions that bring those items into V3 scope (rows
  14, 15, 18) versus leave them parked (rows 17, 22, 26).
- `docs/v2-progress-tracker.md` is left untouched. The Move-earlier rows (1, 3,
  6, 9, 10, 11, 16, 25) are already inside the V2 envelope per the existing
  V2 closure state, so no contradiction was found and no V2 tracker edits are
  required at this gate.

## What Happens Next

V3 implementation specs may now begin **only for the eight unique Promote-to-V3
owners listed above**. The Move-earlier set is tracked by V2 closure work; the
Park-for-later set stays in `docs/v3-parking-lot.md` until a future intake
gate; the Reject row is closed and should not reappear in V3 intake.

This document is the V3 intake gate's deterministic proof artifact. No V3
implementation spec may cite the framework checklist as its source without
also citing the resolution row in this document.
