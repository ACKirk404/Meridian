# Meridian UI Integration Checklist

**Owner:** Prime / Bifrost coordination
**Status:** Active checklist
**Date:** 2026-06-01

## Purpose

This checklist is the gate for plugging live behavior into the Meridian UI. Use it whenever a button, panel, prompt surface, harness control, model bridge, or session behavior is added or changed.

The goal is simple: every visible UI piece must either work, clearly show that it is not available yet, or stay out of the interface.

Show a compact checklist status roughly every three UI/build prompts while active UI integration work is underway, and immediately when a stop condition is hit.

Working cadence: respond to the user's latest message, state the next checklist intent with presumed alignment answers, then continue on those assumptions unless the user corrects direction.

## Control Inventory

Use this as the working UI checklist. Every visible icon, selector, session control, and harness button gets its own row. Status values:

- `wired`: expected behavior exists and has at least one verification path.
- `partial`: visible and partly interactive, but not fully connected to the intended feature.
- `planned`: visible by design, but should not pretend to be complete.
- `blocked`: do not advance until fixed.

### Session Panels

| ID | Control / Feature | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| SP1 | Prime panel | User types directly to Prime/orchestrator. | partial | Send prompt from left panel; response appears below prompt in left panel. |
| SP2 | Right interaction panel | Shows either User Session prompt UI, Settings configuration items, or Harness logic items. | partial | Active mode changes panel title, layout, and interaction model. |
| SP3 | Prime prompt input | Two-line scrollable prompt input. Enter sends; Shift+Enter newline. | wired | Type three lines; Enter sends and clears. |
| SP4 | User Session prompt input | Same prompt behavior as Prime panel, but only in User Session mode. | wired | In User Session mode, type three lines; Enter sends and clears. |
| SP5 | Prime response window | Displays Prime/model output below Prime prompt. | partial | Prompt text remains yellow; response text appears below it. |
| SP6 | User Session response window | Displays routed session/model output below User prompt only in User Session mode. | partial | User Session mode shows prompt/response; Settings/Harness modes do not. |
| SP7 | Prime text-size slider | Single shared slider starts at minimum on first load, persists the chosen size, and controls Prime, User, and harness/Relay panel text. | wired | Drag Prime slider right, reload/reset, and confirm visible panel text keeps the chosen size. |
| SP8 | User text-size slider | Removed as a duplicate control; text size is owned by the Prime slider. | wired | Right panel has no separate slider, and the Prime slider still controls right-panel text. |
| SP9 | User prompt color | User-entered transcript text is bright yellow anywhere it appears. | wired | Send prompt from either panel; transcript prompt is yellow. |
| SP10 | Path/file highlighting | File paths and filenames in output render bright orange. | wired | Ask model for working directory; path is orange. |
| SP11 | Model/source label | Shows the model/source used for a response when known. | partial | Send prompt; confirm model label appears near/below response. |

### Top Session Buttons

| ID | Control / Feature | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| TB1 | Prime Confirm icon | Injects `Confirm` into active prompt; does not submit. | wired | Click icon; word appears at cursor. |
| TB2 | Prime Continue icon | Injects `Continue` into active prompt; does not submit. | wired | Click icon; word appears at cursor. |
| TB3 | Prime No icon | Injects `No` into active prompt; does not submit. | wired | Click icon; word appears at cursor. |
| TB4 | Prime Yes icon | Injects `Yes` into active prompt; does not submit. | wired | Click icon; word appears at cursor. |
| TB5 | User Yes icon | Injects `Yes` into active prompt; does not submit. | wired | Click icon; word appears at cursor. |
| TB6 | User No icon | Injects `No` into active prompt; does not submit. | wired | Click icon; word appears at cursor. |
| TB7 | User Continue icon | Injects `Continue` into active prompt; does not submit. | wired | Click icon; word appears at cursor. |
| TB8 | User Confirm icon | Injects `Confirm` into active prompt; does not submit. | wired | Click icon; word appears at cursor. |

### Selectors

| ID | Control / Feature | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| SEL1 | Model selector | Manual model selection. Defaults to Codex. Auto stays disabled until Prime/Relay logic exists. | partial | Served page has Codex selected and Auto disabled. |
| SEL2 | Projects selector | Selects active project context for Prime and project-scoped UI state. | planned | Track `PRJ-*` subitems before wiring the selector. |
| SEL3 | User Sessions selector | Selects from all open live sessions when the right panel is in User Session mode. | planned | Dropdown shows project groups, including hidden and test-waiting sessions, and selection routes User prompt immediately. |

### Projects Selector Subitems

The Prime panel's Projects dropdown selects the active project context for Prime. It is paired with the User panel's Sessions dropdown, but it does not automatically select or route a User session by itself.

| ID | Projects Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| PRJ1 | Project dropdown placement | Keeps the Projects dropdown in the approved Prime panel position. | partial | Dropdown sits above the Prime line with right edge aligned to the line. |
| PRJ2 | Active project context | Sets the active project for Prime/orchestrator context. | planned | Prime prompt metadata names selected project. |
| PRJ3 | Alphabetical project sort | Sorts project options alphabetically by project name. | planned | Project list order is alphabetical. |
| PRJ4 | Current project label | Displays the selected project name clearly. | partial | Selected project remains visible after selection. |
| PRJ5 | Last project restore | Restores last selected project when allowed by Settings. | planned | Reload restores project only when persistence is enabled. |
| PRJ6 | Project-scoped surfaces | Updates project-scoped backlog, review, progress, and session lists. | planned | Changing project updates dependent surfaces together. |
| PRJ7 | User session independence | Does not silently route User prompts until a User session is selected. | planned | Changing project alone does not send or retarget a User prompt. |
| PRJ8 | Session list filtering | User Sessions dropdown filters/group-emphasizes sessions for selected project while still showing all live sessions by project. | planned | Session dropdown grouping remains complete and project-aware. |
| PRJ9 | Missing project state | Handles project with no live sessions or no loaded metadata clearly. | planned | Empty project state is readable and non-fake. |
| PRJ10 | Project metadata | Shows or links working directory, repo, branch, and project status when that surface exists. | planned | Metadata comes from project state, not hard-coded labels. |
| PRJ11 | Project switch guard | Warns before switching away from unsaved prompt/session edits if needed. | planned | Dirty prompt/session state is preserved or explicitly discarded. |
| PRJ12 | Portfolio boundary | Keeps repo, project, initiative, and venture concepts distinct. | planned | Project selector does not pretend repo equals project. |

### User Sessions Selector Subitems

The right panel needs a Sessions dropdown when it is in User Session mode. Prime selects project context; User Session mode selects the specific live session to interact with. Other right-panel modes, such as Settings or a harness surface, replace this session target with their own scoped target.

| ID | User Sessions Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| USE1 | Sessions dropdown placement | Adds a Sessions dropdown to the User panel in the equivalent position to Prime's Projects dropdown. | planned | User panel shows Sessions selector without moving approved layout. |
| USE2 | Live sessions only | Lists only currently open/live sessions. | planned | Archived/reloadable sessions do not appear here. |
| USE3 | Hidden sessions included | Includes hidden live sessions and marks them as hidden. | planned | Hidden live session appears with hidden state label. |
| USE4 | Test-waiting sessions included | Includes sessions waiting for user test/try-it-out state and marks that state. | planned | Test-waiting session appears with test/waiting label. |
| USE5 | Project grouping | Groups sessions under project headers. | planned | Dropdown visually groups sessions by project. |
| USE6 | Alphabetical project sort | Sorts project groups alphabetically by project name. | planned | Project group order is alphabetical. |
| USE7 | Alphabetical session sort | Sorts sessions alphabetically within each project group. | planned | Session order inside project group is alphabetical. |
| USE8 | Session title update | Changes the User panel title to the selected session name. | planned | Selecting a session updates the panel title immediately. |
| USE9 | Immediate prompt routing | Selecting a session immediately sets that session as the User prompt target. | planned | Next User prompt is routed to selected session without extra confirmation. |
| USE10 | Selection state persistence | Remembers selected live session during current UI session when possible. | planned | Reload/refresh behavior is explicit and does not silently route to stale session. |
| USE11 | Session status display | Shows concise status such as live, hidden, waiting for test, blocked, or done if still open. | planned | Status is visible in selector label or row. |
| USE12 | Stale target guard | If selected session closes or becomes unavailable, User prompt is blocked with a readable target warning. | planned | Sending to closed session shows setup/target error instead of disappearing. |
| USE13 | User mode restore | Returning from Settings/Harness mode restores prior selected live session if still available. | planned | Toggle away and back; previous session target returns or shows stale warning. |

### Spark Ring Icons

| ID | Icon / Feature | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| SK1 | Spark center image | Visual voice/core of Prime and entry point for right-panel surface focus. | partial | Track `SPK-*` subitems before changing Spark focus behavior. |
| SK2 | Toggle session panels | Switches the right panel between User Session, Settings, and harness-scoped surfaces. | partial | Track `SUR-*` subitems before changing panel toggle behavior. |
| SK3 | Settings | Opens settings surface for UI/model/project/session options. | planned | Track `SET-*` subitems before wiring the surface. |
| SK4 | Filter | Controls how much data is included in a session prompt/context stream. | planned | Track `FIL-*` subitems before wiring the surface. |
| SK5 | Models | Opens model selector/settings surface. | planned | Until wired, model selection remains in explicit selector. |
| SK6 | Backlog | Opens backlog/task surface. | planned | Until wired, it must not show fake backlog items. |
| SK7 | Skills | Opens searchable skill/capability registry by model, project, and global scope. | planned | Track `SKL-*` subitems before wiring the surface. |
| SK8 | Crosscheck | Starts or opens review/cross-check surface. | planned | Until wired, it must not claim review is complete. |
| SK9 | Close | Closes targeted session/surface after forcing write-through and Obsidian capture when applicable. | planned | Track `CLS-*` subitems before wiring the surface. |
| SK10 | Archive | Opens reloadable session archive and preserves context for future session revival. | planned | Track `ARC-*` subitems before wiring the surface. |
| SK11 | Reset | Confirms, clears session-window prompts/transcripts, then hard reloads UI. | partial | Track `RST-*` subitems before changing reset behavior. |
| SK12 | Reload | Hard reloads UI/cache without clearing session-window state. | partial | Track `RLD-*` subitems before changing reload behavior. |
| SK13 | Routines | Opens routine/automation surface. | planned | Until wired, no fake routine status. |
| SK14 | Balance | Opens balance/provider/routing view. | planned | Until wired, it must not make routing claims. |

### Spark Surface Subitems

Spark is Prime's voice/core and the visual focus point for moving between right-panel surfaces. It may change what the user is interacting with, but it must not lose the previous target state.

| ID | Spark Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| SPK1 | Prime voice/core identity | Keeps Spark visually tied to Prime, speech, and system focus. | partial | Center image remains visible and labeled as Spark/Prime voice. |
| SPK2 | Surface focus entry | Acts as the visual entry point for changing right-panel surface focus. | planned | Interaction can open/switch surfaces without layout drift. |
| SPK3 | Listening/thinking/speaking state | Reflects Prime/Spark voice state once voice is wired. | planned | State is visible and not faked. |
| SPK4 | Surface mode indication | Makes it clear whether the right panel is User Session, Settings, or a harness. | planned | Active surface label/title changes with mode. |
| SPK5 | Preserve prior session target | Switching away from User Session mode preserves the selected live session target. | planned | Return to User Session restores previous target if live. |
| SPK6 | Stale target warning | If prior session target closes while away, returning shows a readable warning. | planned | Stale target is not silently reused. |
| SPK7 | No implicit reset | Spark surface interaction does not clear prompts/transcripts. | planned | Toggle modes and return; prior panel state remains unless reset was confirmed. |
| SPK8 | No implicit archive/close | Spark surface interaction does not archive, close, stop, or delete sessions. | planned | Session/archive counts unchanged after surface switches. |
| SPK9 | Active mode visibility | Active right-panel mode is visible before interaction. | planned | Surface shows User Session, Settings, or Harness mode clearly. |
| SPK10 | Surface transition animation | Any transition animation preserves readability and does not hide state changes. | planned | Surface switch is visually clear, not disorienting. |
| SPK11 | Keyboard accessibility | Surface switching can be done without mouse-only interaction. | planned | Keyboard focus reaches surface controls. |
| SPK12 | Recovery on bad surface | If a surface cannot load, return to prior usable surface with error. | planned | Failed surface load does not blank the right panel. |

### Right Panel Surface Toggle Subitems

The right panel is not always a User session. User Session mode has a prompt/response interface; Settings and Harness modes replace it with full-panel item lists and scoped actions.

Mode meanings:

- User Session mode: work with Prime on plans, reviews, and decisions Prime has decided should be presented to the user, usually inside a project-specific context such as `Prime-Meridian`, `Prime-Polaris`, `Prime-Mojo`, or `Prime-Experts`.
- Settings mode: use the full right panel for Meridian configuration items; no prompt window.
- Harness mode: use the full right panel for a list of harness logic items; no prompt window. Prime reviews those logic items when interacting with models through Relay.

| ID | Surface Toggle Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| SUR1 | User Session mode | Right panel targets user review/decision work Prime has surfaced in a project-specific context. | planned | Title and routing target match selected project/session context. |
| SUR2 | Settings mode | Right panel uses full panel for Meridian configuration items, with no prompt window. | planned | Settings title replaces User session target and prompt UI is absent. |
| SUR3 | Harness mode | Right panel uses full panel for selected harness logic items, with no prompt window. | planned | Harness title replaces User session target and displays logic list. |
| SUR4 | Immediate interaction switch | Switching surface immediately changes the right-panel interaction model. | planned | User Session shows prompt; Settings/Harness show item lists. |
| SUR5 | Prior target memory | Each surface remembers its last selected target where applicable. | planned | Return to prior surface restores previous target. |
| SUR6 | Surface-specific layout | Layout reflects active surface: prompt/response for User Session, full-panel items for Settings/Harness. | planned | User can tell what mode is active before interacting. |
| SUR7 | Surface state preservation | Unsaved drafts or item edits are preserved per surface unless reset/close confirms otherwise. | planned | Switch away/back preserves relevant surface state. |
| SUR8 | Surface close behavior | Closing an overlay/surface returns to previous valid right-panel mode. | planned | Close does not destroy previous session target. |
| SUR9 | Harness item actions | Harness mode actions apply only to selected harness logic items. | planned | Unsupported harness action is blocked with readable warning. |
| SUR10 | Settings item actions | Settings mode actions mutate only explicit settings items. | planned | Settings interaction does not send to live session accidentally. |
| SUR11 | User session stale guard | If selected session is no longer live, User Session mode blocks send with warning. | planned | Prompt does not disappear into a dead target. |
| SUR12 | Visual baseline preservation | Surface switching does not move approved project/session selector layout or center image. | planned | Visual regression check passes after switches. |

### Reset Surface Subitems

Reset is a UI/session-window recovery control. It clears visible prompt/transcript state for the Prime and User panels, then reloads the interface. It must not archive, delete, close, or mutate live worker/session ownership.

| ID | Reset Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| RST1 | Clear Prime prompt draft | Clears unsent Prime prompt input. | partial | Type draft, click Reset, draft is gone after reload. |
| RST2 | Clear User prompt draft | Clears unsent User prompt input. | partial | Type draft, click Reset, draft is gone after reload. |
| RST3 | Clear Prime transcript view | Clears visible Prime session-window transcript. | partial | Send Prime text, click Reset, Prime window is empty after reload. |
| RST4 | Clear User transcript view | Clears visible User session-window transcript. | partial | Send User text, click Reset, User window is empty after reload. |
| RST5 | Confirmation gate | Requires confirmation before clearing non-empty prompt/transcript state; may skip confirmation when both panels are already empty. | planned | Non-empty panels prompt for confirmation; empty panels reset directly. |
| RST6 | Clear model status labels | Clears transient sending/ready/setup labels in the session windows. | planned | Reset removes stale model status text. |
| RST7 | Preserve selected project policy | Preserves or restores selected project according to Settings persistence, not transcript reset. | planned | Reset behavior matches project persistence setting. |
| RST8 | Preserve live sessions | Does not close, archive, delete, or stop live sessions. | planned | Live session list is unchanged after Reset. |
| RST9 | Preserve archive | Does not modify archived sessions. | planned | Archive count/state unchanged after Reset. |
| RST10 | Cache-bust reload | Performs hard reload with cache-bust after clearing UI session state. | partial | URL/cache marker changes and page reloads. |
| RST11 | Reset failure visibility | Shows readable error if reset storage clearing fails. | planned | Failure does not silently pretend reset succeeded. |
| RST12 | No extra Reset UI button | Reset remains the spark-ring control; no duplicate bottom button. | wired | Visual check shows no duplicate Reset UI button. |
| RST13 | Reset is not Clear Memory | Does not claim to clear model memory, long-term knowledge, or archived context. | planned | UI language avoids "clear memory" unless that feature exists. |
| RST14 | Restart model bridge | Reset asks the local Meridian bridge to restart before reloading the UI, so stale bridge code does not survive reset. | wired | Click Reset; `/api/models` returns `visibleTranscriptContext: true` after reload. |

### Reload Surface Subitems

Reload is a UI/cache recovery control. It refreshes the page and assets without promising to clear prompts, transcripts, live sessions, archives, or model memory.

| ID | Reload Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| RLD1 | Hard reload UI | Reloads the current UI page. | partial | Click Reload; page refreshes. |
| RLD2 | Cache-bust assets | Busts stale browser/Live Server cache where possible. | partial | Reload URL/marker changes or assets refresh. |
| RLD3 | Preserve prompts | Does not intentionally clear prompt drafts. | planned | Drafts remain if stored state says they should remain. |
| RLD4 | Preserve transcripts | Does not intentionally clear session-window transcripts. | planned | Transcript state remains after reload. |
| RLD5 | Preserve selected project | Keeps or restores selected project according to project persistence. | planned | Selected project behavior is deterministic. |
| RLD6 | Preserve selected User session | Keeps selected live session if still available; otherwise shows target warning. | planned | Closed target does not silently route prompts. |
| RLD7 | Preserve model selector | Keeps selected model if valid; invalid/Auto falls back to Codex. | partial | Saved Auto becomes Codex; valid model remains. |
| RLD8 | Do not archive | Reload does not archive or close any session. | planned | Archive/session counts unchanged. |
| RLD9 | Do not reset model memory | Reload does not claim to reset CLI/model/session memory. | planned | UI copy distinguishes reload from reset/clear-memory. |
| RLD10 | Bridge health recheck | Rechecks bridge/model readiness after reload. | partial | `/api/models` readiness updates after page reload. |
| RLD11 | Visual baseline check | Reload preserves center image and approved layout. | partial | Center image and panel alignment remain after reload. |
| RLD12 | Reload failure visibility | If reload cannot complete or served file is wrong, diagnose cache/root mismatch before more UI edits. | planned | Wrong served file triggers stop condition. |

### Settings Surface Subitems

These are the first-pass settings subitems carried forward from Meridian's Polaris-import notes and Bifrost configuration briefs. The Settings icon is not complete until these are either wired, explicitly deferred, or removed by product decision.

| ID | Settings Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| SET1 | Project focus | Switches active project context across Prime panel, Review Console, lane/progress state, and instrumentation. | planned | Change project; all project-scoped surfaces update together. |
| SET2 | Last project persistence | Remembers the last active project across UI sessions. | planned | Reload; previous project is restored. |
| SET3 | Risk tier override | Lets Prime propose risk tier while user can pin/override for a session. | planned | Override appears in UI state and affects future routing/proof requirements. |
| SET4 | Progress pin list | Persists pinned progress/session items. | planned | Pin item, reload, pin remains. |
| SET5 | Progress mute list | Persists muted progress/session categories or items. | planned | Mute item/category, reload, muted state remains. |
| SET6 | Progress collapse state | Persists collapsed progress surface state. | planned | Collapse surface, reload, collapse state remains. |
| SET7 | Progress filter defaults | Configures default filter/severity visibility for progress items. | planned | New progress items respect chosen defaults. |
| SET8 | Progress redirect defaults | Configures default routing by category when Prime surfaces progress or review items. | planned | Category route appears in routing metadata, not prompt text. |
| SET9 | Progress retention window | Controls how long visible progress/proof items stay in the UI. | planned | Old items expire/archive according to setting. |
| SET10 | Quiet mode | Reduces non-critical UI noise and routine progress surfacing. | planned | Routine updates are suppressed; blockers/proof gates still show. |
| SET11 | Focus mode | Collapses portfolio noise to the active project. | planned | Only active project surfaces remain prominent. |
| SET12 | Lane band side | Chooses lane/session band side when that band exists. | planned | Change side; layout moves without panel drift. |
| SET13 | Bottom band visibility | Chooses which instrumentation cells are visible within a fixed cap. | planned | Toggle cells; layout remains stable and capped. |
| SET14 | Role/model mapping | Shows role-to-model mapping and allows per-role override/pin. | planned | Builder/reviewer/etc. mapping persists and does not enable Auto without Relay logic. |
| SET15 | Wake mode | Selects full wake, fast wake, or silent wake. | planned | Reload/start session; selected wake mode is used. |
| SET16 | Quick reply order | Chooses which prompt macro buttons appear and their order. | planned | Buttons update order without changing injection semantics. |
| SET17 | Session card defaults | Carries forward useful Polaris card defaults: hide/minimize/expand/pin/archive/transfer/rerun/size behavior. | planned | New session surfaces inherit defaults. |
| SET18 | Diagnostic log visibility | Controls whether per-session diagnostic event logs are visible by default. | planned | Toggle setting; diagnostic log opens/closes without losing events. |
| SET19 | Public CLI setup guidance | Exposes setup status/help for Codex and Max/Claude CLIs in public builds. | planned | Missing CLI/auth shows install/login guidance. |
| SET20 | Non-exposed harness internals | Confirms heartbeat thresholds, capability toggles, and cross-harness routing internals stay hidden unless explicitly promoted. | planned | Settings surface does not expose these controls. |

### Filter Surface Subitems

Filter is not primarily for finding session cards in this interface. It controls how much information Prime or another session receives in prompt/context, from sparse response-only mode to verbose work/debug mode.

| ID | Filter Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| FIL1 | Response visibility | Include/exclude model response text from the session context view. | planned | Toggle changes context preview without deleting transcript. |
| FIL2 | Tool visibility | Include/exclude tool calls and tool results. | planned | Tool details appear only when enabled. |
| FIL3 | Token usage visibility | Include/exclude token usage and budget telemetry. | planned | Token data appears as telemetry, not prose injected into the prompt. |
| FIL4 | Inbound messages | Include/exclude inbound user/session messages. | planned | Context preview marks inbound content separately. |
| FIL5 | Outbound messages | Include/exclude outbound model/session messages. | planned | Context preview marks outbound content separately. |
| FIL6 | Work statements | Include/exclude work statements, intentions, and status summaries. | planned | Work statements can be shown without raw logs. |
| FIL7 | Proof/evidence summaries | Include/exclude proof links and compact evidence summaries. | planned | Evidence links appear without dumping full artifacts. |
| FIL8 | Diagnostic events | Include/exclude error/info diagnostic events. | planned | Diagnostic events are structured and filterable. |
| FIL9 | Verbosity preset | Provides compact, normal, verbose, and debug presets. | planned | Presets change multiple filter toggles predictably. |
| FIL10 | Scope target | Applies filter to Prime, User/session panel, selected harness, or current project. | planned | Filter state clearly names its target scope. |
| FIL11 | Context preview | Shows what would be included before sending or saving context. | planned | Preview changes with toggles and does not send automatically. |
| FIL12 | No destructive filtering | Filtering limits visibility/context but never deletes source session data. | planned | Turning filter off restores hidden content. |

### Models Surface Subitems

The Models icon owns model visibility and manual override. It must not silently become Prime/Relay auto-routing before that harness logic exists.

| ID | Models Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| MOD1 | Available backends | Shows detected Codex, Max/Claude, and future model backends. | partial | `/api/models` populates backend availability without raw CLI errors. |
| MOD2 | Default backend | Defaults manual prompt sends to Codex until Prime/Relay auto-routing exists. | wired | Fresh page load selects Codex. |
| MOD3 | Auto routing disabled state | Shows Auto as unavailable until Relay owns the decision logic. | wired | Auto option is disabled or clearly unavailable. |
| MOD4 | Per-role mapping | Lists planned roles such as orchestrator, builder, reviewer, verifier, researcher, and release operator. | planned | Roles appear as mappings, not as provider-first choices. |
| MOD5 | Manual role override | Allows user to pin a model for a role once role routing exists. | planned | Override persists and is visible in routing metadata. |
| MOD6 | Provider setup status | Shows missing CLI/auth setup guidance for each backend. | partial | Missing backend gives install/login guidance. |
| MOD7 | Capability metadata | Shows backend strengths, limits, steering mode, context limits, and supported tools. | planned | Metadata comes from Model Harness, not hand-written UI claims. |
| MOD8 | Trust state | Shows candidate/trusted/restricted/degraded state for each backend. | planned | Trust state comes from Aegis/Relay evidence. |
| MOD9 | Prompt payload impact | Shows prompt size/budget pressure for recent dispatches. | planned | Uses Relay prompt payload metrics, not transcript length guesses. |
| MOD10 | Recent model calls | Shows recent call metadata without prompt text. | partial | Uses `/api/recent-calls`; no prompt content stored. |
| MOD11 | Model label display | Response UI shows actual backend/model label when known. | partial | Send prompt; label appears below/near response. |
| MOD12 | Public model setup help | Public build explains required CLI installs/logins and account boundaries. | planned | Missing setup path is readable and non-technical enough to act on. |

### Balance Surface Subitems

The Balance icon owns provider balance, cost pressure, prompt payload, and routing pressure visibility. It observes; it does not secretly reroute work.

| ID | Balance Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| BAL1 | Provider health | Shows whether each configured provider/backend is reachable. | planned | Health comes from bridge/harness checks. |
| BAL2 | CLI/account readiness | Shows CLI installed/authenticated state for local backends. | partial | Codex and Max readiness match `/api/models`. |
| BAL3 | Token usage | Shows token use when a backend reports it. | planned | Unknown usage displays as unknown, not zero. |
| BAL4 | Estimated spend | Shows estimated spend only when usage/cost data is trustworthy. | planned | Missing data produces no fake cost. |
| BAL5 | Remaining credit/quota | Shows remaining balance/quota where provider exposes it. | planned | Unknown quota displays as unavailable. |
| BAL6 | Cost pressure warning | Warns when cost, quota, or budget pressure should influence routing. | planned | Warning is visible without changing routing by itself. |
| BAL7 | Prompt payload size | Shows Relay prompt payload size and budget percentage. | planned | Uses `PromptPayloadSnapshot` style metrics. |
| BAL8 | Prompt drag warning | Flags growing prompt overhead or degraded queue-mode payload growth. | planned | Growth warning appears from Relay metrics. |
| BAL9 | Provider comparison | Compares backend cost/availability/trust for Prime visibility. | planned | Comparison separates evidence from recommendation. |
| BAL10 | Routing recommendation | Shows Prime/Relay recommendation once routing logic exists. | planned | Recommendation is labeled as recommendation, not automatic action. |
| BAL11 | Manual override handoff | Links to Models/Settings for explicit user override. | planned | Override path is visible but does not bypass Relay policy. |
| BAL12 | Public account warning | Explains public users need their own provider accounts or configured keys/CLIs. | planned | Missing account state is user-readable. |

### Backlog Surface Subitems

The Backlog icon owns visible work intake, priority, and conversion into Prime-owned objectives/tasks.

| ID | Backlog Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| BAK1 | Backlog list | Shows queued ideas/tasks/objectives for the active project. | planned | List is project-scoped and not fake-filled. |
| BAK2 | Priority order | Shows priority and why an item is next. | planned | Priority rationale links to Compass/Prime state. |
| BAK3 | Intake capture | Captures a new backlog item from user text. | planned | New item appears with source and timestamp. |
| BAK4 | Modify item | Allows user or Prime to refine title, scope, and acceptance criteria. | planned | Edit is persisted and visible after reload. |
| BAK5 | Approve item | Moves an item into active planning/build consideration. | planned | Approved item creates/updates objective/task state. |
| BAK6 | Deny/defer item | Marks item rejected/deferred without deleting history. | planned | Deferred/rejected item remains auditable. |
| BAK7 | Convert to task | Converts backlog item into executable task with proof expectation. | planned | Task includes owner/harness/proof fields. |
| BAK8 | Link to project/initiative | Attaches backlog item to project, initiative, or venture. | planned | Item appears in the correct scoped view. |
| BAK9 | Import candidate list | Holds Polaris-derived feature candidates for approve/deny/modify review. | planned | Candidate source is recorded without touching Polaris. |
| BAK10 | Archive backlog item | Archives item intentionally without destructive deletion. | planned | Archived item can be inspected later. |
| BAK11 | Search/filter backlog | Filters backlog by project, state, priority, owner, and blocked status. | planned | Filter state is session-only unless promoted to Settings. |
| BAK12 | Prime recommendation | Prime can recommend next backlog item but must expose rationale. | planned | Recommendation appears with reason and proof/risk context. |

### Crosscheck Surface Subitems

The Crosscheck icon owns review, proof, Aegis findings, and independent validation. It should surface issues before normal work continues.

| ID | Crosscheck Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| XCK1 | Run crosscheck | Starts a bounded review/check for current work or selected artifact. | planned | Crosscheck creates a review/proof event. |
| XCK2 | Review findings | Shows current findings with severity, owner, and status. | planned | Findings are structured, not raw logs. |
| XCK3 | Proof status | Shows pass/fail/waived proof state for active work. | planned | Proof state comes from Aegis/review data. |
| XCK4 | Repair routing | Routes validated findings ahead of normal build work. | planned | Repair task points to target lane/owner. |
| XCK5 | Approve finding | Allows user/Prime to accept a finding as valid. | planned | Finding status changes and records actor. |
| XCK6 | Dismiss/waive finding | Allows explicit waiver with rationale. | planned | Waiver stores reason and scope. |
| XCK7 | Re-run verification | Rechecks a repaired finding or proof item. | planned | Result links to prior finding. |
| XCK8 | Compare model lanes | Shows independent model/reviewer disagreement where available. | planned | Disagreement is visible without dumping full transcripts. |
| XCK9 | Gate irreversible actions | Sends public/financial/account-risking decisions through review gate. | planned | Action cannot proceed without required gate state. |
| XCK10 | Recent review ledger | Shows recent reviews and repair routing history. | planned | Ledger is concise and chronological. |
| XCK11 | Open evidence | Opens proof artifacts, commands, or summaries. | planned | Evidence opens without injecting raw logs into Prime prompt. |
| XCK12 | Stop condition alert | Highlights active hard-stop conditions from this checklist. | planned | Stop condition blocks further UI wiring until cleared. |

### Routines Surface Subitems

The Routines icon owns recurring or repeatable work patterns. It should make routine automation visible without turning the user into the scheduler.

| ID | Routine Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| ROU1 | Routine list | Shows configured routines for active project/system. | planned | List is real or empty; no fake routines. |
| ROU2 | Create routine | Creates a new repeatable workflow or monitor with explicit scope. | planned | Routine has name, scope, cadence/trigger, and owner. |
| ROU3 | Enable/disable routine | Toggles routine active state. | planned | Disabled routine does not run. |
| ROU4 | Routine trigger | Supports manual run-now once routine execution exists. | planned | Run creates a visible event/result. |
| ROU5 | Cadence/trigger view | Shows schedule, heartbeat, or event trigger. | planned | Display uses concrete time/trigger data. |
| ROU6 | Last run result | Shows last run status, duration, and proof/evidence link. | planned | Failed run is visible and actionable. |
| ROU7 | Next run preview | Shows next expected run or waiting condition. | planned | Unknown next run displays as unknown. |
| ROU8 | Failure handling | Shows retry/escalation behavior for routine failures. | planned | Failure state does not silently disappear. |
| ROU9 | Prime-owned routine review | Prime reviews routine outputs and only escalates meaningful user gates. | planned | Routine result can be accepted/routed without user micromanagement. |
| ROU10 | Quiet routine mode | Routine noise respects Quiet mode while preserving blockers. | planned | Quiet mode suppresses normal success chatter. |
| ROU11 | Routine archive/history | Shows previous runs and outcomes without cluttering main panels. | planned | History is inspectable by routine. |
| ROU12 | Public automation boundary | Public build explains what automation needs local permissions/accounts. | planned | Missing permission/account gets readable setup state. |

### Skills Surface Subitems

Skills is a searchable registry of available skills and capabilities. It should explain what each skill does, what arguments it needs, and where it is available: globally, for a project, or for a specific model/backend.

| ID | Skills Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| SKL1 | Search skills | Dynamically search skills by name, purpose, provider, project, or keyword. | planned | Search narrows results while typing. |
| SKL2 | Global skills | Shows skills available across all projects. | planned | Global scope is clearly labeled. |
| SKL3 | Project skills | Shows skills available for the active project. | planned | Switching project changes project-scoped skills. |
| SKL4 | Model/backend skills | Shows which skills are available by Codex, Max/Claude, or other backend. | planned | Skill availability names the backend. |
| SKL5 | Skill description | Explains what each skill does in user-readable language. | planned | Description is concise and not raw config. |
| SKL6 | Arguments schema | Shows required and optional arguments for each skill. | planned | Arguments are named with type/meaning/defaults where known. |
| SKL7 | Usage example | Shows a short example command or prompt pattern. | planned | Example does not execute automatically. |
| SKL8 | Permission boundary | Shows whether the skill reads files, writes files, uses network, or affects accounts. | planned | Risk/account effects are visible before use. |
| SKL9 | Install/setup status | Shows missing dependencies or login/setup requirements. | planned | Missing setup gives actionable guidance. |
| SKL10 | Run/request path | Provides a clear path to invoke or request the skill when supported. | planned | Invocation target is explicit and scoped. |
| SKL11 | Skill provenance | Shows whether skill is built-in, project-local, plugin-provided, or user-defined. | planned | Provenance is visible in detail view. |
| SKL12 | Favorite/pin skill | Allows important skills to be pinned for the active project/user. | planned | Pinned skills persist in the correct scope. |

### Archive Surface Subitems

Archive preserves reloadable sessions. It differs from long-term knowledge because the user expects a session may be reopened and run again, while Echo/Atlas knowledge is extracted memory or retrieval context.

| ID | Archive Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| ARC1 | Session archive list | Shows archived sessions that can be inspected later. | planned | Archive list is real or empty; no fake sessions. |
| ARC2 | Reload session | Restores an archived session into an active/reopened state where supported. | planned | Reloaded session preserves identity/source metadata. |
| ARC3 | Run again | Allows rerun/resume/restart from archived session context where backend supports it. | planned | Action names the actual steering mode used. |
| ARC4 | Archive metadata | Stores project, model/backend, role, timestamps, status, and source session id. | planned | Metadata is visible without opening full transcript. |
| ARC5 | Context reference | Allows Prime/session to reference archived context intentionally. | planned | Reference creates explicit context link, not hidden prompt drag. |
| ARC6 | Search archived sessions | Searches archive by project, role, model, status, date, and text summary. | planned | Search results are scoped and fast. |
| ARC7 | Archive summary | Stores compact session summary for scanability. | planned | Summary is visible without loading full transcript. |
| ARC8 | Transcript access | Allows full transcript access when available and authorized. | planned | Full transcript opens on demand only. |
| ARC9 | Archive to knowledge handoff | Allows extracting durable lessons/memory into Echo/Atlas separately. | planned | Extraction is explicit and does not replace archive. |
| ARC10 | Restore proof/artifacts | Links archived session to proof, files, or artifacts created. | planned | Evidence links remain inspectable. |
| ARC11 | Archive retention | Supports retention/archive policy once storage model exists. | planned | Retention state is visible and reversible where possible. |
| ARC12 | Safe deletion boundary | Deleting an archive is separate from closing or filtering and requires explicit intent. | planned | No archive deletion from one-click close. |

### Close Surface Subitems

Close is a targeted session-control action, not merely closing a panel. It should preserve the useful Polaris behavior: target a session, force write-through, update Obsidian where applicable, then close intentionally.

| ID | Close Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| CLS1 | Target selection | Lets user/Prime choose the session or surface to close. | planned | Target is explicit before action runs. |
| CLS2 | Write-through before close | Forces pending session state/transcript/metadata write before closing. | planned | Close records a final saved state event. |
| CLS3 | Obsidian capture | Writes or queues an Obsidian update before close when applicable. | planned | Obsidian result is visible as success/failure. |
| CLS4 | Close summary | Captures concise close summary with status, next action, blockers, and proof refs. | planned | Summary appears in archive/session history. |
| CLS5 | Archive option | Offers archive-on-close for sessions worth reopening. | planned | Archived close appears in Archive list. |
| CLS6 | No silent data loss | Blocks close or warns when write-through fails. | planned | Failed write-through leaves session open or visibly recoverable. |
| CLS7 | Stop-before-close check | Detects running work before close and asks for stop/archive/leave-running path. | planned | Running session cannot be silently killed. |
| CLS8 | Close overlay mode | Closes transient UI overlays without affecting sessions. | planned | Overlay close is visually distinct from session close. |
| CLS9 | Close status event | Emits structured event for session lifecycle/history. | planned | Event is visible to Beacon/Session Lifecycle. |
| CLS10 | Restore after close | Closed sessions can be found through recent/Archive where applicable. | planned | Recently closed item is recoverable. |
| CLS11 | Permission gate | Higher-risk close actions require explicit confirmation. | planned | Public/account/build-critical sessions do not close accidentally. |
| CLS12 | Orchestrator-led close | Prime can propose routine close but must expose reason and saved state. | planned | Proposed close includes reason and target. |

### Speech / Voice

| ID | Control / Feature | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| VO1 | Speech mode icon | Enables/disables first-class spoken interaction with Prime through Spark. | planned | Track `VOC-*` subitems before wiring the surface. |

### Speech / Voice Subitems

Speech/Voice is first-class planning now. The user should be able to speak with Prime and be spoken to through Spark, with clear listening/thinking/speaking states.

| ID | Voice Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| VOC1 | Push-to-talk | Lets user hold/click to speak to Prime. | planned | Speech capture starts/stops with visible state. |
| VOC2 | Wake/listening state | Shows when Spark is listening, idle, thinking, or speaking. | planned | State changes are visible and not faked. |
| VOC3 | Speech-to-text | Converts spoken user input into prompt text before send. | planned | Transcribed text is visible/editable before or after send by mode. |
| VOC4 | Voice submit mode | Supports spoken prompt submission to Prime. | planned | Voice prompt follows same routing as typed Prime prompt. |
| VOC5 | Read-aloud response | Speaks Prime/model responses through Spark. | planned | Response can be heard and muted. |
| VOC6 | Mute output | Mutes spoken responses without disabling typed responses. | planned | Mute state persists in UI session. |
| VOC7 | Interrupt speech | Allows user to stop current spoken response. | planned | Speech stops without losing transcript. |
| VOC8 | Voice selection | Chooses Spark voice once voice provider exists. | planned | Selected voice is visible and persistent. |
| VOC9 | Dictation correction | Allows correction of misheard text before/after sending. | planned | Correction updates prompt/transcript metadata. |
| VOC10 | Voice command intents | Recognizes command families such as reset, reload, open, close, filter, and crosscheck. | planned | Recognized command previews intended action before risky execution. |
| VOC11 | Privacy indicator | Makes microphone capture state obvious. | planned | Capture state cannot be hidden or ambiguous. |
| VOC12 | Public setup guidance | Explains microphone/browser permissions and speech provider setup in public builds. | planned | Missing permission/provider shows readable setup guidance. |

### Harness Dock Buttons

Harness buttons switch the right panel into Harness mode. They are not merely labels or shortcuts. The right panel becomes a full-panel harness logic list, with previous User Session mode preserved for return.

| ID | Harness Button | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| HN1 | Prime | Opens/focuses Prime core session surface. | partial | Click updates session title/focus without fake status text. |
| HN2 | Bifrost | Opens/focuses UI/Bifrost surface. | partial | Click updates session title/focus without fake status text. |
| HN3 | Relay | Opens/focuses model-routing surface. | partial | Click updates session title/focus; does not enable Auto routing yet. |
| HN4 | Beacon | Opens/focuses heartbeat/liveness surface. | partial | Click updates session title/focus without fake heartbeat details. |
| HN5 | Security | Reserved TBD harness identity; replaces generic TBD. | planned | Button label/icon should become Security before wiring actions. |
| HN6 | Aegis | Opens/focuses proof/cross-check surface. | partial | Click updates session title/focus without fake proof status. |
| HN7 | Compass | Opens/focuses mission/project bearing surface. | partial | Click updates session title/focus. |
| HN8 | Vulcan / Session Lifecycle | Opens/focuses session lifecycle controls. | partial | Click updates session title/focus; no live worker control until wired. |
| HN9 | Atlas | Opens/focuses knowledge/context retrieval surface. | planned | Until wired, no fake retrieved context. |
| HN10 | Charon / FileMap | Opens/focuses navigation/FileMap surface. | partial | Click updates session title/focus; future view should read FileMap. |
| HN11 | Arbiter / Codex Reviews | Opens/focuses review queue surface. | partial | Click updates session title/focus; no fake review findings. |
| HN12 | Workflow | Opens/focuses workflow/sub-agent surface. | planned | Until wired, no fake sub-agent state. |
| HN13 | Federation | Opens/focuses federation/network surface. | planned | Until wired, no fake network state. |
| HN14 | Echo | Opens/focuses memory surface. | planned | Until wired, no fake memory recall. |
| HN15 | Ratchet / Tool | Opens/focuses tool execution surface. | planned | Until wired, no fake tool execution. |
| HN16 | Source / Git | Opens/focuses git/source-control surface. | planned | Until wired, no branch movement from UI. |
| HN17 | Vision / Browser | Opens/focuses browser/vision surface. | planned | Until wired, no fake browser state. |
| HN18 | Autonomy / Release | Opens/focuses release/autonomy surface. | planned | Until wired, no public release action. |

### Harness Mode Subitems

Harness mode is for reviewing and updating harness logic items. It may expose diagnostics and scoped controls, but model interaction goes through Prime and Relay; it should not pretend a harness can receive arbitrary direct commands until that harness target is defined.

| ID | Harness Mode Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| HMS1 | Enter harness mode | Clicking a harness button switches the right panel into Harness mode. | planned | Right panel title/target changes to selected harness. |
| HMS2 | Preserve User Session mode | Previous User Session target is preserved when entering Harness mode. | planned | Return to User Session restores prior session or stale warning. |
| HMS3 | Harness logic list | Shows a full-panel list of logic items for the selected harness. | planned | Harness mode opens with logic items, not a prompt window or blank chat. |
| HMS4 | Prime review path | Prime reviews harness logic items before model interaction. | planned | Logic item has Prime review state before dispatch. |
| HMS5 | Relay-mediated model interaction | Model calls for harness logic go through Relay routing. | planned | Dispatch metadata names Relay route/model target. |
| HMS6 | Harness-specific actions | Right-panel actions target selected harness logic item. | planned | Action metadata names selected harness and logic item. |
| HMS7 | Unsupported action guard | If harness logic action is not supported yet, action is blocked with readable warning. | planned | Unsupported harness action does not disappear. |
| HMS8 | Logic update framing | Harness mode language frames work as updating/adding harness logic. | planned | No wording implies arbitrary project session control. |
| HMS9 | Harness state summary | Shows concise harness status once real state exists. | planned | Status is real or absent; no fake health values. |
| HMS10 | Harness diagnostics | Shows harness diagnostic events when available. | planned | Diagnostics are structured and filterable. |
| HMS11 | Harness proof link | Links harness changes to proof/checks when applicable. | planned | Harness update has verification path. |
| HMS12 | Harness permission boundary | High-risk harness actions require explicit approval. | planned | Source/Git/Release actions cannot run silently. |
| HMS13 | Harness mode close | Closing Harness mode returns to previous valid right-panel mode. | planned | Close does not lose User Session target. |
| HMS14 | Harness edit preservation | Unsaved harness-mode item edits are preserved per harness where useful. | planned | Switch harness away/back; edits remain or warning is shown. |
| HMS15 | No cross-harness leakage | Logic item edits/actions for one harness do not silently route to another harness. | planned | Active harness and logic item are explicit before action. |

### Bridge / Backend Features

| ID | Feature | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| BR1 | Meridian model bridge | Receives UI prompts and routes to selected local CLI backend. | wired | `/health` returns ok. |
| BR2 | Codex backend | Sends selected prompts to Codex CLI. | wired | Select Codex; prompt returns Codex CLI response or readable setup error. |
| BR3 | Max backend | Sends selected prompts to Claude CLI when available. | partial | Select Max; prompt returns Claude response or readable setup error. |
| BR4 | CLI setup detection | Detects missing CLI/auth and gives install/login guidance. | wired | `/api/models` and failed calls return setup guidance. |
| BR5 | Recent call diagnostics | Stores metadata only, never prompt text. | wired | `/api/recent-calls` returns request id/channel/backend/status only. |
| BR6 | Prime/Relay Auto routing | Future: Prime chooses model through Relay harness logic. | planned | Auto remains disabled until this contract exists. |

## Integration Rules

| # | Rule | Proof |
|---|------|-------|
| UI1 | Do not add decorative or mock explanatory text unless the user asks for it. | Visual check: no new unrequested labels, descriptions, status prose, or placeholder cards. |
| UI2 | Preserve the approved layout while wiring behavior. | Visual check after refresh: center image remains visible, project selector stays aligned, Prime/User panels do not drift. |
| UI3 | Prompt input is two visible lines by default, scrollable when needed. | Manual: type three lines; prompt area scrolls without resizing the panel. |
| UI4 | Enter submits; Shift+Enter inserts a newline. | Manual: Enter sends and clears prompt; Shift+Enter keeps editing. |
| UI5 | User-entered prompt text renders bright yellow wherever it appears in transcripts. | Manual: send a prompt and confirm transcript prompt color. |
| UI6 | File paths and filenames render bright orange in model output. | Manual: ask for the working directory or a file path and confirm path styling. |
| UI7 | Response window stays below the prompt and owns model output. | Visual/manual: prompt text does not replace response area and response does not appear in prompt input. |
| UI8 | Text size slider controls Prime, User, and harness/Relay panel text together and persists across reload/reset. | Manual: drag the Prime slider right; session and harness text resize from the shared value and stay after reload. |
| UI9 | Prompt macro buttons inject their literal word into the active prompt. | Manual: Yes, No, Continue, Confirm insert text at cursor and do not submit by themselves. |
| UI10 | Reset clears session transcripts and prompts, then hard reloads the UI. | Manual: send text, click Reset, confirm both panels empty after reload. |
| UI11 | Reload hard reloads the UI without promising to clear session state. | Manual: click Reload and confirm page reloads. |

## Model Bridge Rules

| # | Rule | Proof |
|---|------|-------|
| MB1 | Model selector defaults to Codex until Prime/Relay auto-routing exists. | Served page contains `value="codex" selected`; saved `auto` falls back to Codex. |
| MB2 | Auto remains unavailable until Prime/Relay harness logic owns routing. | Served page contains disabled Auto option or equivalent unavailable state. |
| MB3 | Selecting Codex sends through the Meridian bridge, not Polaris. | Request goes to `http://127.0.0.1:8767/api/message`; no Polaris path or process is touched. |
| MB4 | Selecting Max sends through the Meridian bridge when the Claude CLI is available. | `/api/models` reports Max availability before sending; unavailable state gives setup guidance. |
| MB5 | Public setup errors are readable. | Missing CLI or auth failure returns install/login guidance instead of a silent hang. |
| MB6 | Request metadata is tracked without logging prompt text. | `/api/recent-calls` shows request id, channel, backend, model label, duration, status, and visible-context counts only. |
| MB7 | Model/context label appears below or near the response area when known. | Manual: send a follow-up request and confirm displayed model/source plus visible context count. |
| MB8 | Visible session continuity | Follow-up prompts carry the visible panel transcript as bounded context, with no hidden backend memory. | Response metadata and `/api/recent-calls` record nonzero `sessionContextEntries` after a follow-up prompt. |
| MB9 | Bridge capability guard | UI blocks prompt sends when the running bridge does not advertise visible transcript context support. | Old bridge shows restart-required status instead of silently sending stateless follow-ups. |
| MB10 | Bridge restart endpoint | Local bridge exposes a same-port restart endpoint for Reset recovery. | `POST /api/restart` returns accepted, then `/api/models` comes back with visible-context capability. |

## Harness UI Rules

| # | Rule | Proof |
|---|------|-------|
| H1 | Harness buttons do not pretend to be complete before a harness surface exists. | Click behavior is either wired to a real panel or visibly inactive/coming soon by design. |
| H2 | User/session panels follow rules; orchestrator/Prime panels follow logic. | UI copy and behavior keep Prime logic separate from user/session rules. |
| H3 | Security is the reserved icon/identity for the TBD security harness. | Harness map lists Security for the TBD slot before wiring actions. |
| H4 | Prime/Relay model routing remains a future gate until harness logic is defined. | No UI default to Auto and no hidden automatic routing without an explicit Prime/Relay contract. |
| H5 | Any new harness surface exposes scoped logic-item actions only when that harness can receive them. | Manual/code review: harness/action target is explicit and does not leak into the wrong session channel. |

## Visual Regression Checks

| # | Check | Proof |
|---|-------|-------|
| V1 | Central spark image is present after refresh. | Visual check or served HTML references `spark-center-final.png`. |
| V2 | Prime/User panels remain empty until user/model transcript content exists. | Visual check: no unrequested instructional blocks inside the panels. |
| V3 | Project selector sits above the Prime line and aligns with the line's right edge. | Visual check after refresh at desktop width. |
| V4 | Prime and User prompt/response areas fill their internal panel space with low padding. | Visual check: no large dead margins inside session frames. |
| V5 | Reset and Reload icons remain in the spark ring, not as extra bottom buttons. | Visual check: no duplicate Reset UI button. |

## Verification Commands

Run these before committing UI/bridge changes:

```powershell
$html = Get-Content -Raw index.html
$scripts = [regex]::Matches($html, '<script>([\s\S]*?)</script>') | ForEach-Object { $_.Groups[1].Value }
$tmp = Join-Path $env:TEMP 'meridian-inline-check.js'
[IO.File]::WriteAllText($tmp, ($scripts -join "`n"))
node --check $tmp
node --check scripts\meridian-model-bridge.js
node scripts\meridian-model-bridge.js --self-test
Invoke-RestMethod http://127.0.0.1:8767/health -TimeoutSec 3
Invoke-RestMethod http://127.0.0.1:8767/api/models -TimeoutSec 5
```

For VS Code Live Server checks:

```powershell
$r = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5500/index.html -TimeoutSec 5
@(
  'session-prompt-input',
  'session-response-output',
  'value="codex" selected',
  'value="auto" disabled',
  '/api/models',
  'spark-center-final.png'
) | ForEach-Object {
  if ($r.Content.Contains($_)) { "served has: $_" } else { "served missing: $_" }
}
```

## Stop Conditions

Pause and fix before continuing if any of these happen:

| Condition | Action |
|---|---|
| Main branch becomes dirty with worker implementation files | Stop UI work; quarantine/preserve contamination; reset main clean to `origin/main` only after preserving evidence. |
| Any change touches Polaris | Stop; revert the Meridian task path and restart from Meridian-only context. |
| A page refresh serves different UI than the edited `index.html` | Diagnose cache, Live Server root, browser cache, or service worker before editing more UI. |
| Reset does not clear visible session transcripts | Fix reset/session storage behavior before adding new controls. |
| A prompt disappears without a response or setup error | Check bridge health, `/api/models`, browser console, and recent call diagnostics before changing layout. |
| Center image disappears while wiring behavior | Restore visual baseline before continuing behavior work. |
| Model selector defaults to Auto before Prime/Relay routing exists | Revert to Codex default and keep Auto disabled. |
| New button label conflicts with AI/session semantics | Rename or remove it before wiring. Example: do not use Clear for a visual wipe unless it really clears model/session memory. |

## Clearance Record

Append entries here as items are verified.

```text
YYYY-MM-DD HH:MM TZ - <item#> cleared; proof: <short note>; commit: <hash>
```
