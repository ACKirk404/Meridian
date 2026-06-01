# Bifrost Right-Panel Mode Contract

**Owner:** Prime / Bifrost coordination  
**Status:** Product contract  
**Date:** 2026-06-01  
**Based on:** `docs/ui-integration-checklist.md` (SP2, SUR1-SUR12, USE1-USE13), `docs/relay-heartbeat-model-routing-logic.md`, `docs/relay-completeness-audit.md`, current `index.html`

## Purpose

Define the three right-panel surface modes for Bifrost and their interaction contracts with Prime, Sessions, and Harness domain logic. The right panel is not always a User session; it switches between User Session mode (for prompt/response work), Settings mode (for Meridian configuration), and Harness mode (for searchable/editable harness logic).

This is a **product/UI contract only**. Do not implement runtime code or Harness logic internals here.

---

## Right-Panel Modes

The right panel supports three mutually exclusive modes, switchable via the Spark ring icon:

### 1. User Session Mode (Default)

**Intent:** Work with Prime on plans, reviews, and decisions Prime has surfaced in a project-specific context (e.g., Prime-Meridian, Prime-Polaris).

**Panel Layout:**
- Sessions dropdown selector at top (equivalent position to Prime's Projects dropdown)
- Prompt input area (same two-line scrollable behavior as Prime panel)
- Response display area below prompt
- All text controls (Yes, No, Continue, Confirm icons) present and active

**Sessions Dropdown Requirements:**
- **Live sessions only:** Lists only currently open/live sessions
- **Include hidden sessions:** Includes hidden live sessions with readable "hidden" label
- **Include test-waiting sessions:** Includes sessions waiting for user test/try-it-out with "waiting" label
- **Project grouping:** Groups sessions under project headers (e.g., "Meridian", "Polaris", "Experts")
- **Alphabetical sort (projects):** Project group headers sorted A-Z by project name
- **Alphabetical sort (sessions):** Sessions within each project group sorted A-Z by session name
- **Panel title:** Displays selected session name; updates immediately when selection changes
- **Immediate routing:** Selecting a session immediately sets that session as the User prompt target (next User prompt routes to selected session without extra confirmation)
- **Selection state:** Remembers selected live session during current UI session when possible
- **Status display:** Shows concise status label (live, hidden, waiting, blocked, or done) if still open
- **Stale target guard:** If selected session closes/becomes unavailable, User prompt is blocked with readable target warning instead of sending to dead target
- **Mode restoration:** Returning from Settings/Harness mode restores prior selected live session if still available; shows stale warning if session closed

**Prompt/Response Interaction:**
- Prompt text persists on panel (does not auto-clear unless Reset is confirmed)
- Prompt routing target is displayed/labeled
- Model response appears below the User prompt
- Unsent prompt drafts are preserved per User Session mode across surface switches (unless Reset/Close confirms otherwise)
- Text-size slider (shared with Prime panel) controls User panel text size
- User-entered transcript text appears in bright yellow
- File paths in output render bright orange
- Model/source label (if known) appears near/below response

**User Session Mode Subitems (from UI Integration Checklist):**
- SUR1: Right panel targets user review/decision work Prime has surfaced in project-specific context
- SUR4: Immediate interaction switch — switching to User Session immediately shows prompt/response interface
- SUR5: Prior target memory — remembers selected session when returning from Settings/Harness
- SUR6: Surface-specific layout — prompt/response layout is visible before interaction
- SUR7: Surface state preservation — unsent prompt drafts are preserved unless reset/close confirms otherwise
- SUR11: User session stale guard — if selected session is no longer live, User Session mode blocks send with warning
- USE1: Sessions dropdown placement (equivalent to Prime's Projects dropdown position)
- USE2–USE13: Sessions dropdown requirements (listed above)

---

### 2. Settings Mode

**Intent:** Use the full right panel for Meridian configuration items. No prompt window; no session targeting.

**Panel Layout:**
- Full-panel settings item list (replaces prompt/response interface entirely)
- Settings title replaces User session target label
- Scoped actions apply only to settings items, not to live sessions
- Scroll area for configuration items

**Settings Interaction:**
- Unsaved setting edits are preserved when switching away from Settings mode (unless Reset/Close confirms otherwise)
- Settings actions mutate only explicit settings items
- Settings surface does not accidentally send prompts to live sessions
- Settings persist according to client-side storage and Settings persistence policy

**Settings Mode Subitems (from UI Integration Checklist):**
- SUR2: Settings mode uses full panel for Meridian configuration items, with no prompt window
- SUR4: Immediate interaction switch — switching to Settings immediately hides prompt/response
- SUR5: Prior target memory — Settings remembers its scrolled position/edit state when returning
- SUR6: Surface-specific layout — Settings title and full-panel items are visible before interaction
- SUR7: Surface state preservation — unsaved edits are preserved unless reset/close confirms otherwise
- SUR10: Settings item actions — Settings interactions do not send to live session accidentally
- SK3: Settings icon (from Spark ring) opens Settings surface

**Settings Items Reference (from UI Integration Checklist SET1-SET20):**
- Project focus, last project persistence
- Risk tier override
- Progress pin/mute lists, collapse state, filter defaults, redirect defaults, retention window
- Quiet mode, focus mode
- Lane band side, bottom band visibility, role/model mapping
- Wake mode, quick reply order, session card defaults
- Diagnostic log visibility
- Public CLI setup guidance (Codex, Max/Claude CLIs)
- Non-exposed harness internals (heartbeat, capability toggles, cross-harness routing remain hidden)

---

### 3. Harness Mode

**Intent:** Use the full right panel for searchable/editable harness logic items. No prompt window; no session targeting.

**Panel Layout:**
- Full-panel harness logic item list (replaces prompt/response interface entirely)
- Harness title replaces User session target label
- Scoped actions apply only to harness logic items
- Scroll area for searchable logic items

**Harness Interaction:**
- Harness logic items are displayed and searchable by item name/type
- Unsupported harness actions (e.g., live model calls, provider routing decisions) are blocked with readable warnings
- Harness item edits are preserved when switching away from Harness mode (unless Reset/Close confirms otherwise)
- Harness surface does not send prompts to live sessions
- Prime reviews harness logic items when interacting with models through Relay (read-only view from Prime's perspective; editing happens in Harness mode)

**Harness Mode Subitems (from UI Integration Checklist):**
- SUR3: Harness mode uses full panel for selected harness logic items, with no prompt window
- SUR4: Immediate interaction switch — switching to Harness immediately hides prompt/response
- SUR5: Prior target memory — Harness remembers selected logic category/filter when returning
- SUR6: Surface-specific layout — Harness title and logic list are visible before interaction
- SUR7: Surface state preservation — unsaved edits are preserved unless reset/close confirms otherwise
- SUR9: Harness item actions — Harness mode actions apply only to selected harness logic items
- SK9: No implicit close — Harness surface interaction does not archive, close, stop, or delete sessions

**Harness Logic Scope (Render-Only in Bifrost):**
- Bifrost displays deterministic sample harness logic data and does not make Relay routing decisions
- Harness items reflect configuration from `meridian_core/harness.py` (once defined in Build phase)
- Read-only preview from Prime's perspective; editing/mutation happens only in Harness mode
- Unsupported operations (live model calls, rerunning with different models, provider overrides) show "not supported in UI" warnings

---

## Surface Toggle / Spark Ring Integration

**Visual Entry Point:** Spark ring icon at center, paired with right-panel title

**Mode Switching:**
- Clicking Spark ring or right-panel title button cycles between User Session, Settings, and Harness modes
- Active mode is visually labeled (User Session, Settings, or Harness) before interaction
- Surface transition is immediate and non-blocking

**No Implicit State Loss:**
- Switching modes does not clear prompts, transcripts, archives, or live session counts
- Switching modes does not close, archive, delete, or stop sessions
- Unsent prompt drafts and unsaved settings/harness edits are preserved unless Reset/Close confirms otherwise

**Surface Recovery:**
- If a surface fails to load, return to prior usable surface with readable error message
- Right panel does not go blank on surface load failure

**Keyboard Accessibility:**
- Surface switching can be done without mouse-only interaction
- Keyboard focus reaches surface toggle controls

---

## Project and Session Context

### Prime Projects Dropdown (Left Panel)
**Role:** Sets active project context for Prime and Prime-routed surfaces.

**Behavior:**
- Keeps Projects dropdown in approved Prime panel position (above Prime prompt, right edge aligned to prompt line)
- Selects active project for Prime/Orchestrator context
- Sorts project options alphabetically by project name
- Displays selected project name clearly; remains visible after selection
- Restores last selected project on reload when enabled by Settings persistence
- Updates project-scoped backlog, review, progress, and session lists together
- Does not silently route User prompts (changing Prime project alone does not send or retarget a User prompt)
- Handles missing projects (no live sessions, no loaded metadata) with readable, non-fake state

### User Sessions Dropdown (Right Panel, User Session Mode Only)
**Role:** Selects the live session to interact with (once in User Session mode).

**Behavior:** (Detailed in "User Session Mode" section above)

**Distinction:** Prime's Projects dropdown sets project context; User Session dropdown selects the specific live session to interact with. Other modes (Settings, Harness) replace this session target with their own scoped target.

---

## Interaction Rules

### Rule: No Prompt Routing to Dead Targets
- If a selected User session closes while User Session mode is active, the prompt send button is blocked with a readable warning ("Selected session no longer available").
- User is not allowed to send a prompt to a session that has closed.
- Returning to User Session mode from another surface with a closed prior session target shows a stale-target warning instead of silently routing to the dead target.

### Rule: Text Size is Global
- Prime text-size slider controls text size in Prime panel, User Session response area, Settings items, and Harness logic items.
- There is no separate slider per surface; text size is shared across all right-panel surfaces.
- Text size persists across surface switches and page reloads (via localStorage with `meridian.session.text-size` key).

### Rule: Color Coding Remains Consistent
- User-entered transcript text: bright yellow (in User Session prompt and response areas)
- File paths in output: bright orange
- Model/source labels: standard text color with clear labeling

### Rule: Reset Does Not Claim to Clear Model Memory
- Reset button clears visible UI session state (prompts, transcripts) and hard reloads the UI.
- Reset asks the local Meridian bridge to restart before reloading (so stale bridge code does not survive reset).
- Reset does **not** claim to clear model memory, long-term knowledge, or archived context.
- UI language carefully avoids "clear memory" phrasing.

### Rule: Reload Does Not Archive or Mutate Sessions
- Reload button refreshes the page and assets.
- Reload does not archive, close, delete, or stop any live session.
- Reload does not mutate live worker/session ownership or lane assignment.
- Archive/session counts remain unchanged after Reload.

---

## Verification Checklist

Before accepting this contract:

- [ ] User Session mode shows prompt/response interface with live session routing
- [ ] Sessions dropdown lists open sessions only, grouped by project, sorted alphabetically
- [ ] Sessions dropdown includes hidden and test-waiting sessions with status labels
- [ ] Selecting a session immediately routes next User prompt to that session
- [ ] Settings mode shows full-panel settings items with no prompt window
- [ ] Harness mode shows full-panel harness logic items with no prompt window
- [ ] Surface switching (Spark ring) cycles between User Session, Settings, and Harness
- [ ] Unsent prompts/drafts are preserved when switching modes (unless Reset/Close)
- [ ] Stale session targets are guarded: blocked with warning instead of silent send
- [ ] Text size slider controls all surfaces (Prime, User, Settings, Harness)
- [ ] Color coding consistent: User text yellow, paths orange, labels standard
- [ ] Reset restarts bridge and hard-reloads UI; does not claim to clear model memory
- [ ] Reload refreshes page; does not archive or close sessions
- [ ] No implicit state loss when switching surfaces
- [ ] Surface recovery: failed surface load returns to prior surface with error message
- [ ] Keyboard accessibility: surface switching works without mouse-only interaction
- [ ] Visual regression: center image and approved layout unchanged across mode switches

---

## Out of Scope

- Runtime Harness logic implementation (harness items data, mutation, state)
- Live model calls or provider routing decisions in Bifrost
- Meridian settings implementation (persistence layer, per-setting validation)
- Session archive/reload UI and orchestration
- Prime orchestrator logic or routing decisions
- Polaris integration or Polaris-specific session sharing

---

## Related Documents

- `docs/ui-integration-checklist.md` — Master UI control inventory and verification paths
- `docs/relay-heartbeat-model-routing-logic.md` — Relay routing context for session targeting
- `docs/relay-completeness-audit.md` — Relay runtime audit and proof gate requirements
- Current `index.html` — Visual baseline for center image and approved layout
