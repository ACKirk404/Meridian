# Meridian UI Integration Checklist

**Owner:** Prime / Bifrost coordination
**Status:** Active checklist
**Date:** 2026-06-01

## UI Authority

The Meridian UI is the Electron app. That desktop app is the product surface
Scott has been building and using. Root `index.html` is an implementation
detail of that app: it is the current renderer source file Electron loads into
the desktop window, so edits to that file are edits to the Electron app's
visible UI. It is part of the app today, not obsolete, detached,
historical-only, or independent from the app. It also is not the Meridian UI by
itself, not a standalone browser demo target, and not a separate Meridian UI
target. UI documentation and handoffs must lead with the Electron app, then name
`index.html` only as the current renderer source when needed. `npm start` must
launch `electron/main.js`, which opens the Meridian Electron app; startup must
not regenerate or replace the app with `bifrost/preview.html`.

`bifrost/preview.html` is a generated Bifrost rendering proof artifact. Use it only for deterministic backend/view-model preview proof tasks, not as the operational Meridian UI.

## Purpose

This checklist is the gate for plugging live behavior into the Meridian UI. Use it whenever a button, panel, prompt surface, harness control, model bridge, or session behavior is added or changed.

The goal is simple: every visible UI piece must either work, clearly show that it is not available yet, or stay out of the interface.

Show a compact checklist status roughly every three UI/build prompts while active UI integration work is underway, and immediately when a stop condition is hit.

Working cadence: respond to the user's latest message, state the next checklist intent with presumed alignment answers, then continue on those assumptions unless the user corrects direction.

Scope rule: every UI/build change must name exactly one owning harness or one Spark setting/control before implementation. Work may touch adjacent bridge or session support only when that support is required to make the named harness/control truthful in the visible interface; the checklist entry and build log must record that scope.

Ownership correction: Prime/Orchestrator owns intent, priority, risk tier, proof/human-gate needs, and final coordination. Relay + Model Harness own model-call mechanics, including provider/model identity, prompt payload construction, context-window fit, dispatch/fallback behavior, provider balance, transport gates, and telemetry. Bifrost and Spark surfaces render or request backend-owned state; they do not create route authority from UI labels.

## Control Inventory

Use this as the working UI checklist. Every visible icon, selector, session control, and harness button gets its own row. Status values:

- `wired`: expected behavior exists and has at least one verification path.
- `partial`: visible and partly interactive, but not fully connected to the intended feature.
- `planned`: visible by design, but should not pretend to be complete.
- `blocked`: do not advance until fixed.

### Session Panels

| ID | Control / Feature | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| SP1 | Prime panel | User types directly to Prime/orchestrator. | wired | Prime panel renders its own prompt/response interface, Enter submits through `/bridge/message` as `channel=prime`, stores visible transcript context, clears the prompt draft, and appends model/setup/error output below the Prime prompt. |
| SP2 | Right interaction panel | Shows either User Session prompt UI, Settings configuration items, or Harness logic items. | wired | User Session shows prompt/response controls; Settings and Harness activate full-panel surfaces through the shared right-panel authority path, hide prompt controls, and render backend-backed/status-only sections without sending prompts. |
| SP3 | Prime prompt input | Two-line scrollable prompt input. Enter sends; Shift+Enter newline. | wired | Type three lines; Enter sends and clears. |
| SP4 | User Session prompt input | Same prompt behavior as Prime panel, but only in User Session mode. | wired | In User Session mode, type three lines; Enter sends and clears. |
| SP5 | Prime response window | Displays Prime/model output below Prime prompt. | wired | Prime transcript rendering appends bridge-returned model/setup/error entries to the Prime response output, preserves user prompt text as yellow transcript entries, and shows model/source metadata when available. |
| SP6 | User Session response window | Displays routed session/model output below User prompt only in User Session mode. | wired | User Session mode uses the right-panel prompt/response output only after `/bridge/user-sessions` confirms a live target; Settings/Harness/Spark panel surfaces hide prompt/response controls and do not render or send User prompt output. |
| SP7 | Prime text-size slider | Single shared slider starts at minimum on first load, persists the chosen size on input/change, and controls Prime, User, and harness/Relay panel text. | wired | Drag Prime slider right, release it, reload/reset, and confirm visible panel text keeps the chosen size. |
| SP8 | User text-size slider | Removed as a duplicate control; text size is owned by the Prime slider. | wired | Right panel has no separate slider, and the Prime slider still controls right-panel text. |
| SP9 | User prompt color | User-entered transcript text is bright yellow anywhere it appears. | wired | Send prompt from either panel; transcript prompt is yellow. |
| SP10 | Path/file highlighting | File paths and filenames in output render bright orange. | wired | Ask model for working directory; path is orange. |
| SP11 | Model/source label | Shows the model/source used for a response when known. | wired | Session transcript entries render bridge-returned model labels and resolved/requested backend source below model/setup/error output when available; fallback labels use the selected backend only when the exact model is unknown. |

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
| SEL1 | Model selector | Manual model selection. Defaults to Codex. Auto stays disabled until Prime/Relay logic exists. | wired | Electron renderer injects Codex as the selected manual backend, keeps Auto disabled, coerces any stored `auto` selection back to Codex, and leaves executable auto-routing deferred to Relay/Model Harness. |
| SEL2 | Projects selector | Selects active project context for Prime and project-scoped UI state. | wired | Projects selector writes Compass project context, persists `meridian.session.project`, and does not retarget User Sessions. |
| SEL3 | User Sessions selector | Selects from all open live sessions when the right panel is in User Session mode. | wired | Dropdown is populated from `/bridge/user-sessions`, filters to bridge-confirmed routable targets, persists only reported live targets, marks stale selections unavailable, and routes User prompts with the selected session target id/cwd only after the target is confirmed. |

### Projects Selector Subitems

The Prime panel's Projects dropdown selects the active project context for Prime. It is paired with the User panel's Sessions dropdown, but it does not automatically select or route a User session by itself.

| ID | Projects Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| PRJ1 | Project dropdown placement | Keeps the Projects dropdown in the approved Prime panel position. | wired | Dropdown remains in `.session-project-select` above the Prime line with the approved right-edge alignment. |
| PRJ2 | Active project context | Sets the active project for Prime/orchestrator context. | wired | Prime prompt payload metadata and recent-call metadata include `projectContext`. |
| PRJ3 | Alphabetical project sort | Sorts project options alphabetically by project name. | wired | Seeded project options render as Bifrost, Meridian, Spark after the placeholder. |
| PRJ4 | Current project label | Displays the selected project name clearly. | wired | Selected project stays visible in the dropdown and Prime status reads `Compass project <project>`. |
| PRJ5 | Last project restore | Restores last selected project when allowed by Settings. | wired | Reload restores `meridian.session.project`; invalid/missing stored value falls back to Meridian. |
| PRJ6 | Project-scoped surfaces | Updates project-scoped backlog, review, progress, and session lists. | wired | Project selector changes refresh Compass context, the grouped User Sessions list, Review Console/Crosscheck, Goal Runtime, Workflow Dispatch Status, Spark Backlog, Spark Models, and project-scoped Skills pin/search state through existing GET-only loaders without retargeting User Sessions or posting prompts. |
| PRJ7 | User session independence | Routes User prompts only to a bridge-confirmed live User session target. | wired | Vulcan owns this session lifecycle guard: project change updates Compass context only; User send remains blocked until `/bridge/user-sessions` confirms a live target, either restored from prior selection or selected from the live target list. |
| PRJ8 | Session list filtering | User Sessions dropdown filters/group-emphasizes sessions for selected project while still showing all live sessions by project. | wired | Vulcan owns this session lifecycle grouping: all projects remain visible and the active Compass project optgroup is marked `(active project)`. |
| PRJ9 | Missing project state | Handles project with no live sessions or no loaded metadata clearly. | wired | Vulcan owns this empty live-session state: active project with no sessions shows `No live sessions for active project` without faking a route. |
| PRJ10 | Project metadata | Shows or links working directory, repo, branch, and project status when that surface exists. | wired | Compass renders Project metadata handoff from `/bridge/compass-logic`, showing the active Compass context, reviewed project definition, and project status while pointing repo/path/branch inspection to Vulcan live-state evidence and FileMap relative-path registry; it does not move branches, expose absolute paths, or invent source-control state. |
| PRJ11 | Project switch guard | Warns before switching away from unsaved prompt/session edits if needed. | wired | Project selector checks visible Prime/User prompt drafts before changing Compass context; cancel restores the prior project, confirm preserves draft storage while updating Compass context and the project-grouped session list without retargeting User Sessions. |
| PRJ12 | Portfolio boundary | Keeps repo, project, initiative, and venture concepts distinct. | wired | Compass backend snapshot documents project/repository/initiative/venture boundaries in the visible harness. |

### User Sessions Selector Subitems

The right panel needs a Sessions dropdown when it is in User Session mode. Prime selects project context; User Session mode selects the specific live session to interact with. Other right-panel modes, such as Settings or a harness surface, replace this session target with their own scoped target.

| ID | User Sessions Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| USE1 | Sessions dropdown placement | Adds a Sessions dropdown to the User panel in the equivalent position to Prime's Projects dropdown. | wired | User panel shows Sessions selector without moving approved layout. |
| USE2 | Live sessions only | Lists only currently open/live sessions. | wired | `/bridge/user-sessions` exposes routable Meridian worktree-backed targets and self-test proves shared main is excluded. |
| USE3 | Hidden sessions included | Includes hidden live sessions and marks them as hidden. | wired | Review-lane worktree targets appear with hidden state label and bridge self-test proves hidden classification. |
| USE4 | Test-waiting sessions included | Includes sessions waiting for user test/try-it-out state and marks that state. | wired | Worktree/branch names containing test-waiting or waiting-for-test appear with waiting label. |
| USE5 | Project grouping | Groups sessions under project headers. | wired | Dropdown visually groups sessions by project. |
| USE6 | Alphabetical project sort | Sorts project groups alphabetically by project name. | wired | Project group order is alphabetical. |
| USE7 | Alphabetical session sort | Sorts sessions alphabetically within each project group. | wired | Session order inside project group is alphabetical. |
| USE8 | Session title update | Changes the User panel title to the selected session name. | wired | Selecting a session updates the panel title immediately. |
| USE9 | Immediate prompt routing | Selecting a session immediately sets that session as the User prompt target. | wired | Next User prompt is routed to selected session without extra confirmation. |
| USE10 | Selection state persistence | Remembers selected live session during current UI session when possible. | wired | Reload and mode restore keep `meridian.user-session.target.v1` only if `/bridge/user-sessions` still reports it as routable. |
| USE11 | Session status display | Shows concise status such as live, hidden, waiting for test, blocked, or done if still open. | wired | Live, hidden, and waiting status appear in selector labels, and the User prompt status line names the loaded target after discovery/restore. |
| USE12 | Stale target guard | If selected session closes or becomes unavailable, User prompt is blocked with a readable target warning. | wired | Sending without a bridge-confirmed target shows a target error; stale target loading shows `Selected session unavailable` / `selected session unavailable` instead of silently rerouting. |
| USE13 | User mode restore | Returning from Settings/Harness mode restores prior selected live session if still available. | wired | Toggle away and back; previous routable session target returns. |

### Spark Ring Icons

| ID | Icon / Feature | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| SK1 | Spark center image | Visual voice/core of Prime and entry point for right-panel surface focus. | wired | Spark renders the center image asset as `role="img"` with `aria-label="Spark, voice of Prime"`, `data-name="Spark"`, and `data-role="voice-of-prime"`, plus a focusable Spark core toggle and Spark actions menu for right-panel surface focus. |
| SK2 | Toggle session panels | Switches the right panel between User Session, Settings, and harness-scoped surfaces. | wired | `SUR1`-`SUR13` pin switching, persistence, layout, close, stale-target, settings-action behavior, and display-only harness item action scoping without enabling live harness execution. |
| SK3 | Settings | Opens settings surface for UI/model/project/session options. | wired | Opens a Settings/Spark display-only surface with backend-sourced Voice I/O status from `/bridge/voice-io`; no microphone capture, speech output, read-aloud, mute mutation, raw prompt/response, raw worker history, worker chat, or settings mutation is authorized until an explicit settings backend exists. |
| SK4 | Filter | Controls how much data is included in a session prompt/context stream. | wired | Spark Filter opens a UI-local context filter surface with scope, verbosity presets, visibility toggles, and a non-sending preview; it does not call `/bridge/message`, result recovery, fake filter backends, or delete source session data. |
| SK5 | Models | Opens model readiness and recent-call metadata surface. | wired | Spark Models opens Models Readiness from `/bridge/models` plus metadata-only `/bridge/recent-calls`; it does not enable Auto routing, mutate settings, or render prompt/response bodies. |
| SK6 | Backlog | Opens backlog/task surface. | wired | Spark Backlog opens a display-only Backlog Tasks surface backed by `/bridge/review-console`, `/bridge/goal-runtime`, and `/bridge/workflow-dispatch-status`; it renders empty/unavailable state rather than fake backlog items and does not create tasks, assign workers, mutate queues, start routines, send prompts, recover raw result bodies, or ingest raw worker session history. |
| SK7 | Skills | Opens searchable skill/capability registry by model, project, and global scope. | wired | Spark Skills opens a display-only Skills Registry sourced from `/bridge/filemap` and `/bridge/models`; search is UI-local over loaded metadata and the surface shows global FileMap capabilities, model/backend availability, description, setup posture, permission boundary, provenance, and non-executing usage examples without fake skills backend, install/login/account probing, Auto routing, prompt send, file mutation, or skill execution. |
| SK8 | Crosscheck | Opens display-only review/proof state from existing backend snapshots. | wired | Spark Crosscheck aggregates `/bridge/review-console` and `/bridge/aegis-logic`; it does not start a review run, apply responses, mutate queues, execute providers, or ingest raw worker session history. |
| SK9 | Close | Closes targeted session/surface after forcing write-through and Obsidian capture when applicable. | partial | Transient surface close is wired; session close/write-through remains tracked in `CLS-*`. |
| SK10 | Archive | Opens close/archive proof posture until reloadable archive controls exist. | wired | Spark Archive opens Session Close Archive Proof from `/bridge/session-close-archive-proof`; it is display-only typed state and must not close, archive, delete, reload, run again, replay, POST, call `/bridge/message`, paste raw prompt/worker chat/session history/log/detail, expose live controls, or feed raw detail into Orchestrator. Orchestrator intake is compact typed session state only; raw detail is fetched on demand only. |
| SK11 | Reset | Confirms, clears session-window prompts/transcripts, then hard reloads UI. | wired | `RST-*` subitems are wired: reset clears visible local prompt/transcript state, asks `/bridge/restart`, and does not close live sessions or claim memory deletion. |
| SK12 | Reload | Hard reloads UI/cache without clearing session-window state. | wired | `RLD-*` subitems are wired: reload refreshes the UI/cache while preserving session target and visible prompt/transcript state. |
| SK13 | Routines | Opens current runtime continuity status until a routine automation backend exists. | wired | Spark Routines opens backend-sourced Goal Runtime plus Workflow Dispatch Status; it is display-only typed state and does not run automation, mutate schedulers, paste raw logs/transcripts/details, or self-approve. |
| SK14 | Balance | Opens balance/provider/routing view. | wired | Spark Balance opens Provider Balance from `/bridge/provider-balance` with display-safe provider/routing posture and no raw prompt/response/evidence bodies. |

### Spark Surface Subitems

Spark is Prime's voice/core and the visual focus point for moving between right-panel surfaces. It may change what the user is interacting with, but it must not lose the previous target state.

| ID | Spark Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| SPK1 | Prime voice/core identity | Keeps Spark visually tied to Prime, speech, and system focus. | wired | Electron renderer uses the Spark center image asset with `role="img"`, `aria-label="Spark, voice of Prime"`, `data-name="Spark"`, and `data-role="voice-of-prime"`. |
| SPK2 | Surface focus entry | Acts as the visual entry point for changing right-panel surface focus. | wired | Spark and harness controls call the shared right-panel authority path and expose panel mode/selection data without layout drift. |
| SPK3 | Listening/thinking/speaking state | Reflects Prime/Spark voice state once voice is wired. | wired | Top speech icon and Settings/Spark render compact Voice I/O state from `/bridge/voice-io`; controls remain display-only/disabled and no microphone, speech output, read-aloud, mute mutation, raw prompt/response, or raw worker history is authorized. |
| SPK4 | Surface mode indication | Makes it clear whether the right panel is User Session, Settings, or a harness. | wired | Active title/status plus `data-panel-mode` / `data-right-panel-mode` expose User Session, Spark/Settings, or Harness mode. |
| SPK5 | Preserve prior session target | Switching away from User Session mode preserves the selected live session target. | wired | Return to User Session restores the prior `meridian.user-session.target.v1` target if still live. |
| SPK6 | Stale target warning | If prior session target closes while away, returning shows a readable warning. | wired | Stale target restore shows `Selected session unavailable` / `selected session unavailable` and blocks send. |
| SPK7 | No implicit reset | Spark surface interaction does not clear prompts/transcripts. | wired | Surface switching changes only panel mode/selection; prompt/transcript clearing remains confined to confirmed Reset. |
| SPK8 | No implicit archive/close | Spark surface interaction does not archive, close, stop, or delete sessions. | wired | Surface switching calls no archive/close/delete controls; bridge targets remain read-only until prompt send. |
| SPK9 | Active mode visibility | Active right-panel mode is visible before interaction. | wired | Surface shows User Session, Settings/Spark, or Harness title/status and matching data attributes. |
| SPK10 | Surface transition animation | Any transition animation preserves readability and does not hide state changes. | wired | Right-panel surface containers use a short opacity/translate transition with opacity never below 0.82, no blur/filter/display hiding, and a `prefers-reduced-motion: reduce` path that disables the animation. |
| SPK11 | Keyboard accessibility | Surface switching can be done without mouse-only interaction. | wired | Spark controls are focusable buttons, preserve native Enter/Space activation, and add Arrow/Home/End keyboard navigation across surface controls without changing backend authority or firing hidden routes. |
| SPK12 | Recovery on bad surface | If a surface cannot load, return to prior usable surface with error. | wired | Failed/missing stored surface restores User Session and shows `surface unavailable; User Session restored`. |

### Right Panel Surface Toggle Subitems

The right panel is not always a User session. User Session mode has a prompt/response interface; Settings and Harness modes replace it with full-panel item lists and scoped actions.

Mode meanings:

- User Session mode: work with Prime on plans, reviews, and decisions Prime has decided should be presented to the user, usually inside a project-specific context such as `Prime-Meridian`, `Prime-Polaris`, `Prime-Mojo`, or `Prime-Experts`.
- Settings mode: use the full right panel for Meridian configuration items; no prompt window.
- Harness mode: use the full right panel for a list of harness logic items; no prompt window. Prime reviews those logic items when interacting with models through Relay.

| ID | Surface Toggle Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| SUR1 | User Session mode | Right panel targets user review/decision work Prime has surfaced in a project-specific context. | wired | User mode title reads `User Session` / `User Session: <target>` and the routing target comes from the selected live session. |
| SUR2 | Settings mode | Right panel uses full panel for Meridian configuration items, with no prompt window. | wired | Settings title replaces User session target, prompt UI is absent, `/bridge/voice-io` display state is rendered, and settings/voice mutations are visibly blocked. |
| SUR3 | Harness mode | Right panel uses full panel for selected harness logic items, with no prompt window. | wired | Harness activation calls the shared right-panel surface path, hides the User prompt/response interface with `is-panel-surface`, and renders harness logic/backend-link sections with harness authority state. |
| SUR4 | Immediate interaction switch | Switching surface immediately changes the right-panel interaction model. | wired | User Session shows prompt; Settings/Harness show item lists. |
| SUR5 | Prior target memory | Each surface remembers its last selected target where applicable. | wired | Right-panel mode/selection and User Session target persist independently through storage keys. |
| SUR6 | Surface-specific layout | Layout reflects active surface: prompt/response for User Session, full-panel items for Settings/Harness. | wired | User can tell what mode is active before interacting. |
| SUR7 | Surface state preservation | Unsaved drafts or item edits are preserved per surface unless reset/close confirms otherwise. | wired | Switching surfaces does not call prompt/transcript clearing and User drafts remain keyed by selected target. |
| SUR8 | Surface close behavior | Closing an overlay/surface returns to previous valid right-panel mode. | wired | Close returns Settings/Harness surfaces to User mode without destroying session state. |
| SUR9 | Harness item actions | Harness mode actions apply only to selected harness logic items. | wired | Generic harness surfaces render a Harness item action scope section naming the selected harness, selected logic item, action target, blocked execution state, and no User Session or Prime prompt route; unsupported actions remain display-only until a reviewed backend action exists. |
| SUR10 | Settings item actions | Settings mode actions mutate only explicit settings items. | wired | Settings surface exposes display-only Voice I/O state, blocks mutation until an explicit settings backend exists, and does not send to live sessions, `/bridge/message`, `/bridge/restart`, or result-recovery routes. |
| SUR11 | User session stale guard | If selected session is no longer live, User Session mode blocks send with warning. | wired | Missing/stale selected target shows a readable target warning and send emits a visible target error. |
| SUR12 | Visual baseline preservation | Surface switching does not move approved project/session selector layout or center image. | wired | Surface switching reuses the existing right-panel workspace, hides prompt controls only in surface mode, and preserves Spark media references. |
| SUR13 | Active mode persistence | User, Settings/Spark, and Harness modes persist as the right-panel mode across reload/reset/focus churn. | wired | Open Relay or Settings, reload/reset the UI, and confirm the right panel does not revert to User. |

### Reset Surface Subitems

Reset is a UI/session-window recovery control. It clears visible prompt/transcript state for the Prime and User panels, then reloads the interface. It must not archive, delete, close, or mutate live worker/session ownership.

| ID | Reset Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| RST1 | Clear Prime prompt draft | Clears unsent Prime prompt input. | wired | Reset removes `meridian.session.prompt.prime` before hard reload. |
| RST2 | Clear User prompt draft | Clears unsent User prompt input. | wired | Reset removes scoped `meridian.session.prompt.user.*` keys before hard reload. |
| RST3 | Clear Prime transcript view | Clears visible Prime session-window transcript. | wired | Reset removes `meridian.session.transcript.prime` before hard reload. |
| RST4 | Clear User transcript view | Clears visible User session-window transcript. | wired | Reset removes scoped `meridian.session.transcript.user.*` keys before hard reload. |
| RST5 | Confirmation gate | Requires confirmation before clearing non-empty prompt/transcript state; may skip confirmation when both panels are already empty. | wired | Non-empty state turns the same Spark Reset button into `Confirm Reset`; empty panels reset directly. |
| RST6 | Clear model status labels | Clears transient sending/ready/setup labels in the session windows. | wired | Reset clears model status labels before storage clearing and hard reload. |
| RST7 | Preserve selected project policy | Preserves or restores selected project according to Settings persistence, not transcript reset. | wired | Reset does not clear `meridian.session.project`; project selection persists through reload. |
| RST8 | Preserve live sessions | Does not close, archive, delete, or stop live sessions. | wired | Reset only clears local visible UI state and asks `/bridge/restart`; it does not call session close/archive/delete controls. |
| RST9 | Preserve archive | Does not modify archived sessions. | wired | Reset does not call archive storage or archive controls. |
| RST10 | Cache-bust reload | Performs hard reload with cache-bust after clearing UI session state. | wired | Reset uses the hard reload path with a `meridian_reload` URL marker. |
| RST11 | Reset failure visibility | Shows readable error if reset storage clearing fails. | wired | Storage-clearing failure sets `reset storage error`, shows an alert, and does not reload the page. |
| RST12 | No extra Reset UI button | Reset remains the spark-ring control; no duplicate bottom button. | wired | Visual check shows no duplicate Reset UI button. |
| RST13 | Reset is not Clear Memory | Does not claim to clear model memory, long-term knowledge, or archived context. | wired | Reset confirmation copy names only visible prompts/transcripts and local bridge restart. |
| RST14 | Restart model bridge | Reset asks the local Meridian bridge to restart before reloading the UI, so stale bridge code does not survive reset. | wired | Click Reset; `/bridge/models` returns `version=local-bridge-routes-v2` and `visibleTranscriptContext: true` after reload; repeated clicks do not stack duplicate restart requests. |

### Reload Surface Subitems

Reload is a UI/cache recovery control. It refreshes the page and assets without promising to clear prompts, transcripts, live sessions, archives, or model memory.

| ID | Reload Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| RLD1 | Hard reload UI | Reloads the current UI page. | wired | Click Reload; page refreshes once even if clicked repeatedly. |
| RLD2 | Cache-bust assets | Busts stale browser/Live Server cache where possible. | wired | Reload writes a `meridian_reload` URL marker and removes it after load. |
| RLD3 | Preserve prompts | Does not intentionally clear prompt drafts. | wired | Reload calls the hard reload path without `clearSessions`; stored prompt drafts are left intact. |
| RLD4 | Preserve transcripts | Does not intentionally clear session-window transcripts. | wired | Reload calls the hard reload path without `clearSessions`; stored transcripts are left intact. |
| RLD5 | Preserve selected project | Keeps or restores selected project according to project persistence. | wired | Project selection persists through `meridian.session.project`. |
| RLD6 | Preserve selected User session | Keeps selected live session if still available; otherwise shows target warning. | wired | Closed/stale stored target shows `Selected session unavailable` / `selected session unavailable` instead of silently routing to another session. |
| RLD7 | Preserve model selector | Keeps selected model if valid; invalid/Auto falls back to Codex. | wired | Saved Auto becomes Codex; valid model remains. |
| RLD8 | Do not archive | Reload does not archive or close any session. | wired | Reload only calls the hard reload path and does not call archive/close/delete controls. |
| RLD9 | Do not reset model memory | Reload does not claim to reset CLI/model/session memory. | wired | Reload copy and code only refresh the page/assets. |
| RLD10 | Bridge health recheck | Rechecks bridge/model readiness after reload. | wired | `/bridge/models` readiness updates after page reload and focus/visibility refresh. |
| RLD11 | Visual baseline check | Reload preserves center image and approved layout. | wired | Spark media asset test and served UI markers preserve the center image path and approved panel controls. |
| RLD12 | Reload failure visibility | If reload cannot complete or served file is wrong, diagnose cache/root mismatch before more UI edits. | wired | Reload start failure sets `reload error` and shows a Live Server/root warning. |

### Settings Surface Subitems

These are the first-pass settings subitems carried forward from Meridian's Polaris-import notes and Bifrost configuration briefs. The Settings icon is not complete until these are either wired, explicitly deferred, or removed by product decision.

| ID | Settings Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| SET1 | Project focus | Switches active project context across Prime panel, Review Console, lane/progress state, and instrumentation. | wired | Settings/Spark reflects the existing `.session-project-select` authority, active project, and project-scoped refresh path; changing project preserves prompt drafts through the existing guard, refreshes Compass, User Sessions, Review/Crosscheck, Goal/Workflow, Backlog, Models, and Skills surfaces, and does not retarget sessions, POST prompts, call result recovery, or invoke close/archive controls. |
| SET2 | Last project persistence | Remembers the last active project across UI sessions. | wired | Project selector stores `meridian.session.project`, restores only known project options on reload, and falls back to Meridian for invalid/missing stored values. |
| SET3 | Risk tier override | Lets Prime propose risk tier while user can pin/override for a session. | wired | Settings/Spark exposes UI-local session risk overrides backed by `meridian.risk-tier-overrides.v1`; Prime and the current User session can follow Prime's proposal or pin a preview tier, and the selected override appears in visible future routing/proof metadata without mutating Relay, Aegis, provider routing, prompt payloads, or backend proof gates. |
| SET4 | Progress pin list | Persists pinned progress/session items. | wired | Settings/Spark exposes a UI-local pinned progress/session item list backed by `meridian.progress-state.v1`; pinned ids remain in the local profile across reloads without mutating backend progress, sessions, reviews, prompts, providers, or settings routes. |
| SET5 | Progress mute list | Persists muted progress/session categories or items. | wired | Settings/Spark exposes a UI-local muted progress/session item/category list backed by `meridian.progress-state.v1`; muted ids remain in the local profile across reloads without deleting source progress/session data or mutating backend routes. |
| SET6 | Progress collapse state | Persists collapsed progress surface state. | wired | Settings/Spark exposes a UI-local progress collapse default backed by `meridian.progress-state.v1`; the Filter preview reflects collapsed/expanded state while source progress, proof, session, review, and transcript data remain untouched. |
| SET7 | Progress filter defaults | Configures default filter/severity visibility for progress items. | wired | Settings/Spark exposes UI-local progress severity defaults backed by `meridian.context-filter.v1`; the existing Filter preview reflects info/warning/error visibility defaults for new progress previews without deleting progress source data or calling backend progress, prompt, result-recovery, provider, or settings mutation routes. |
| SET8 | Progress redirect defaults | Configures default routing by category when Prime surfaces progress or review items. | wired | Settings/Spark exposes UI-local progress redirect defaults backed by `meridian.progress-redirects.v1`; category routes for routine progress, blocker, review result, proof summary, repair routed, completion, human gate, and system health appear in Settings and Filter routing metadata without entering prompt text or mutating backend queue/review routing. |
| SET9 | Progress retention window | Controls how long visible progress/proof items stay in the UI. | planned | Old items expire/archive according to setting. |
| SET10 | Quiet mode | Reduces non-critical UI noise and routine progress surfacing. | wired | Settings/Spark exposes a UI-local quiet mode backed by `meridian.quiet-mode.v1`; Runtime Continuity and Workflow Dispatch suppress routine success chatter while failure state, blockers, and proof-gate posture remain visible, with no routine execution, scheduler mutation, archive/delete, or backend settings writes. |
| SET11 | Focus mode | Collapses portfolio noise to the active project. | wired | Settings/Spark exposes a UI-local focus mode backed by `meridian.focus-mode.v1`; active-project Spark surfaces remain prominent, the User Session list suppresses non-active project groups, and a currently selected out-of-project session stays visible as an explicit exception instead of being silently retargeted. |
| SET12 | Lane band side | Chooses lane/session band side when that band exists. | planned | Change side; layout moves without panel drift. |
| SET13 | Bottom band visibility | Chooses which instrumentation cells are visible within a fixed cap. | planned | Toggle cells; layout remains stable and capped. |
| SET14 | Role/model mapping | Shows role-to-model mapping and allows per-role override/pin. | wired | Settings/Spark exposes UI-local per-role model preferences backed by `meridian.role-model-overrides.v1`, and Models renders those overrides as visible role mapping metadata for orchestrator, builder, reviewer, verifier, researcher, and release operator while Auto remains disabled and Relay routing stays unchanged. |
| SET15 | Wake mode | Selects full wake, fast wake, or silent wake. | wired | Settings/Spark exposes a UI-local wake mode backed by `meridian.wake-mode.v1`; startup/reload uses the selected mode by restoring the last visible panel for full/fast wake, restoring the User panel quietly for silent wake, and adding a local Prime wake note only for full wake, without invoking audio capture/output, backend wake routes, prompt send, or session ownership changes. |
| SET16 | Quick reply order | Chooses which prompt macro buttons appear and their order. | wired | Settings/Spark exposes a UI-local quick reply order backed by `meridian.quick-reply-order.v1`; the visible Yes/No/Continue/Confirm macro buttons reorder or hide per local preference while still inserting their literal token into the active prompt without submitting, retargeting sessions, or calling backend settings or prompt routes. |
| SET17 | Session card defaults | Carries forward useful Polaris card defaults: hide/minimize/expand/pin/archive/transfer/rerun/size behavior. | planned | New session surfaces inherit defaults. |
| SET18 | Diagnostic log visibility | Controls whether per-session diagnostic event logs are visible by default. | wired | Settings/Spark exposes a UI-local diagnostic event visibility default backed by `meridian.context-filter.v1`; it opens/closes diagnostic rows in the context/filter preview without deleting source session data and without calling a backend event-log route, `/bridge/message`, result recovery, provider calls, or settings mutation. |
| SET19 | Public CLI setup guidance | Exposes setup status/help for Codex and Max/Claude CLIs in public builds. | wired | Settings/Spark renders public Codex and Claude/Max CLI setup status from `/bridge/models` alongside Voice I/O state; missing CLI/install/login remains setup guidance only, with no software install, sign-in, secret read, provider-account probe, model routing mutation, Auto enablement, or prompt send. |
| SET20 | Non-exposed harness internals | Confirms heartbeat thresholds, capability toggles, and cross-harness routing internals stay hidden unless explicitly promoted. | wired | Settings/Spark surface exposes only display-only Voice I/O state from `/bridge/voice-io`; settings writes, message/restart/result routes, fake backend controls, and hidden harness internals remain blocked. |

### Filter Surface Subitems

Filter is not primarily for finding session cards in this interface. It controls how much information Prime or another session receives in prompt/context, from sparse response-only mode to verbose work/debug mode.

| ID | Filter Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| FIL1 | Response visibility | Include/exclude model response text from the session context view. | wired | Response toggle updates the local context preview as included/hidden without deleting transcript data. |
| FIL2 | Tool visibility | Include/exclude tool calls and tool results. | wired | Tools toggle updates the local preview as tool metadata only and remains hidden unless enabled. |
| FIL3 | Token usage visibility | Include/exclude token usage and budget telemetry. | wired | Token usage toggle renders token data as telemetry in the preview, not prose injected into a prompt. |
| FIL4 | Inbound messages | Include/exclude inbound user/session messages. | wired | Inbound toggle marks inbound content separately in the preview. |
| FIL5 | Outbound messages | Include/exclude outbound model/session messages. | wired | Outbound toggle marks outbound content separately in the preview. |
| FIL6 | Work statements | Include/exclude work statements, intentions, and status summaries. | wired | Work statements toggle shows compact work statements without raw logs. |
| FIL7 | Proof/evidence summaries | Include/exclude proof links and compact evidence summaries. | wired | Evidence toggle shows evidence refs only and does not dump full artifacts. |
| FIL8 | Diagnostic events | Include/exclude error/info diagnostic events. | wired | Diagnostics toggle shows structured diagnostic events only when enabled. |
| FIL9 | Verbosity preset | Provides compact, normal, verbose, and debug presets. | wired | Compact/normal/verbose/debug presets update multiple preview toggles predictably and persist in UI-local state. |
| FIL10 | Scope target | Applies filter to Prime, User/session panel, selected harness, or current project. | wired | Scope selector clearly names prime, user-session, selected-harness, or current-project as the preview target. |
| FIL11 | Context preview | Shows what would be included before sending or saving context. | wired | Preview changes with toggles and explicitly says no prompt is sent or saved. |
| FIL12 | No destructive filtering | Filtering limits visibility/context but never deletes source session data. | wired | No destructive filtering section states toggles affect only preview visibility and turning a toggle back on restores preview rows because source data is not deleted. |

### Models Surface Subitems

The Models icon owns model visibility and manual override. It must not silently become Prime/Relay auto-routing before that harness logic exists, and it must not turn UI taxonomy labels into provider/model dispatch keys.

| ID | Models Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| MOD1 | Available backends | Shows detected Codex, Max/Claude, and future model backends. | wired | Spark Models and the manual selector read `/bridge/models` for backend availability without raw CLI errors. |
| MOD2 | Default backend | Defaults manual prompt sends to Codex until Prime/Relay auto-routing exists. | wired | Fresh page load selects Codex. |
| MOD3 | Auto routing disabled state | Shows Auto as unavailable until Relay + Model Harness own the dispatch decision and evidence path. | wired | Auto option is disabled or clearly unavailable. |
| MOD4 | Per-role mapping | Lists planned roles such as orchestrator, builder, reviewer, verifier, researcher, and release operator. | wired | Spark Models renders display-only Role mapping entries for orchestrator, builder, reviewer, verifier, researcher, and release operator as planned lanes, each marked routing-not-wired; Auto remains disabled and no per-role override, POST, `/bridge/message`, or result-recovery path is exposed. |
| MOD5 | Manual role override | Allows user to pin a model for a role once role routing exists. | wired | Per-role model overrides persist in `meridian.role-model-overrides.v1` and appear in Models as display-only routing metadata labeled as UI-local pins; prompt sends still follow the visible manual selector and no Relay/provider route mutation occurs. |
| MOD6 | Provider setup status | Shows missing CLI/auth setup guidance for each backend. | wired | Spark Models renders display-safe setup guidance from `/bridge/models`; raw stderr and account probing are not exposed. |
| MOD7 | Capability metadata | Shows backend strengths, limits, steering mode, context limits, and supported tools. | wired | Model Harness aspect buttons open display-only surfaces bound to `/bridge/models`, `/bridge/relay-evidence`, `/bridge/provider-balance`, `/bridge/aegis-logic`, and `/bridge/relay-logic`; metadata comes from existing backend snapshots, not hand-written UI authority or taxonomy labels. |
| MOD8 | Trust state | Shows candidate/trusted/restricted/degraded state for each backend. | wired | Model Harness aspect buttons include Trust route and Aegis/Relay evidence from existing backend snapshots; no provider call, Auto enablement, route mutation, prompt payload assembly, POST, `/bridge/message`, `/bridge/call-result`, raw prompt/response/provider output/evidence body, or worker chat is authorized. |
| MOD9 | Prompt payload impact | Shows prompt size/budget pressure for recent dispatches. | wired | Prompt/Payload/Context model-aspect surfaces render Relay evidence and provider-balance posture from existing backend snapshots only; they do not infer budget state from transcript text or assemble model-bound payloads. |
| MOD9A | Per-call GOAL / Intent | Shows the dispatch-scoped goal for a model call when Relay exposes it. | wired | Relay evidence exposes backend-owned `per_call_intent` with requested-by, Prime intent ref, project ref, action type, call goal, expected output shape, risk tier, proof requirement, disallowed outputs, payload budget ref, evidence refs, and authority boundary; Relay/Model Harness UI renders it display-only without inferring user intent from transcript text, creating provider routes, assembling prompts, or mutating Auto routing. |
| MOD10 | Recent model calls | Shows recent call metadata without prompt text. | wired | Spark Models renders request id, channel, backend/model, result state, duration, project, target presence, and visible-context counts from `/bridge/recent-calls`; it does not call `/bridge/call-result` or render recovered bodies. |
| MOD11 | Model label display | Response UI shows actual backend/model label when known. | wired | Response transcripts render bridge-returned model labels plus resolved/requested backend source, and Spark Models renders recent-call backend/model labels from `/bridge/recent-calls` without prompt or response bodies. |
| MOD12 | Public model setup help | Public build explains required CLI installs/logins and account boundaries. | wired | Spark Models renders `/bridge/models` setup hints plus a Public setup boundary explaining local Codex and Claude/Max CLI/account requirements without installing software, signing in, reading secrets, probing accounts, or enabling Auto routing. |

### Balance Surface Subitems

The Balance icon owns provider balance, cost pressure, prompt payload, and routing pressure visibility. It observes Relay/Model Harness evidence; it does not calculate authority, assemble payloads, or secretly reroute work.

| ID | Balance Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| BAL1 | Provider health | Shows whether each configured provider/backend is reachable. | wired | Spark Balance renders display-safe provider health from `/bridge/provider-balance`; missing data remains unknown rather than guessed. |
| BAL2 | CLI/account readiness | Shows CLI installed/authenticated state for local backends. | wired | Spark Balance fetches `/bridge/models` beside `/bridge/provider-balance` and renders CLI/account readiness for local backends as available/setup-required with setup guidance; provider account readiness stays informational only with no install, sign-in, secret read, provider-account probe, route mutation, Auto enablement, prompt send, or result recovery. |
| BAL3 | Token usage | Shows token use when a backend reports it. | wired | Spark Balance renders backend-supplied context budget, current prompt tokens, prompt budget, and prompt budget percent from `/bridge/provider-balance`; missing token numbers display as unknown, not zero. |
| BAL4 | Estimated spend | Shows estimated spend only when usage/cost data is trustworthy. | wired | Spark Balance renders backend-supplied spend posture labels only; missing spend displays as unavailable and no live billing lookup is implied. |
| BAL5 | Remaining credit/quota | Shows remaining balance/quota where provider exposes it. | wired | Spark Balance renders backend-supplied quota state, credit status, and remaining-credit labels only; account balance probing remains unavailable. |
| BAL6 | Cost pressure warning | Warns when cost, quota, or budget pressure should influence routing. | wired | Spark Balance renders backend cost-pressure state from `/bridge/provider-balance` without changing routing by itself. |
| BAL7 | Prompt payload size | Shows Relay prompt payload size and budget percentage. | wired | Prompt Payload Visibility and Visible Prompt Payload Meter render backend-bound Relay payload size, token estimate, context budget, budget percent/status, payload snapshot evidence refs, provider/model/route continuity, and queue-poll adjacency without raw prompt text or payload assembly. |
| BAL8 | Prompt drag warning | Flags growing prompt overhead or degraded queue-mode payload growth. | wired | Backend-bound prompt payload surfaces render growth deltas, `data-growth-state`, Q-mode prompt-drag state, watch/block posture, and warning/blocker tags such as `unexpected_growth_delta` and `q_mode_prompt_drag_degraded` from Relay/Aegis evidence. |
| BAL9 | Provider comparison | Compares backend cost/availability/trust for Prime visibility. | wired | Spark Balance renders a Provider comparison frame backed by `/bridge/provider-balance` and per-provider fields for trust, health, route, cost pressure, quota, credit, estimated spend, and evidence refs; route recommendations remain advisory/display-only and remain Relay/Model Harness-owned. |
| BAL10 | Routing recommendation | Shows Prime intent plus Relay/Model recommendation once routing logic exists. | wired | Spark Balance renders an advisory Routing recommendation frame by joining backend-owned `/bridge/relay-evidence per_call_intent`, `/bridge/provider-balance selected_provider/routing_owner/policy_state`, and `/bridge/relay-logic` lane/proof posture for the current risk tier; it is labeled recommendation-only and does not approve dispatch, mutate routes, or bypass Relay/Aegis policy. |
| BAL11 | Manual override handoff | Links to Models/Settings for explicit user override. | wired | Provider Balance renders Open Models and Open Settings handoff controls that only switch the visible Spark surface; they do not mutate routing, enable Auto, post prompts, call providers, or bypass Relay/Aegis policy. |
| BAL12 | Public account warning | Explains public users need their own provider accounts or configured keys/CLIs. | wired | Spark Balance renders a Public account boundary saying users need their own accounts/keys/subscriptions/CLIs while keeping account/credential probing unavailable; account balance, credential, billing, secret probing, and route mutation stay unavailable. |

### Backlog Surface Subitems

The Backlog icon owns visible work intake, priority, and conversion into Prime-owned objectives/tasks.

| ID | Backlog Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| BAK1 | Backlog list | Shows queued ideas/tasks/objectives for the active project. | wired | Spark Backlog renders a Backlog candidate list from real `/bridge/review-console` queue items in the active Compass project display frame, including project, sequence, id, type, severity, title, state, response need, and suggested actions; empty snapshots render an explicit empty state and no fake items, create/approve/deny/defer/convert/archive controls, owner assignment, priority mutation, prompt send, result recovery, or queue mutation are exposed. |
| BAK2 | Priority order | Shows priority and why an item is next. | wired | Spark Backlog renders an advisory Priority order frame that joins `/bridge/review-console` queue order with the active Compass project frame plus `/bridge/goal-runtime` objective context and `/bridge/prime-logic` owner/action/risk rationale, explaining why the current item is next without mutating backlog priority, creating tasks, or inventing a backlog planning backend. |
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

The Crosscheck icon owns review, proof, Aegis findings, and independent validation. It should surface issues before normal work continues. Orchestrator intake uses compact typed session state by default: worker transcripts are stored, not replayed; worker summaries stay small and update at checkpoints; session state packets are always available; evidence refs are links/ids rather than pasted logs; raw detail is fetched only on demand.

| ID | Crosscheck Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| XCK0 | Review/proof state | Shows current Review Console and Aegis proof posture without running a new check. | wired | Spark Crosscheck renders `/bridge/review-console` and `/bridge/aegis-logic` as display-only typed state with no raw item content, raw evidence bodies, raw prompt/response, raw worker chat, or raw worker session history. |
| XCK1 | Run crosscheck | Starts a bounded review/check for current work or selected artifact. | planned | Crosscheck creates a review/proof event only after an explicit execution backend exists. |
| XCK2 | Review findings | Shows current findings with severity, owner, and status. | partial | Spark Crosscheck renders Review Console pending items from `/bridge/review-console` with id, type, severity, title, suggested actions, and status as structured metadata; owner attribution remains deferred and raw item content stays hidden. |
| XCK3 | Proof status | Shows pass/fail/waived proof state for active work. | wired | Spark Crosscheck renders Aegis proof trail and policy gate state from `/bridge/aegis-logic`; raw evidence bodies and queue mutation controls stay unavailable. |
| XCK4 | Repair routing | Routes validated findings ahead of normal build work. | planned | Repair task points to target lane/owner. |
| XCK5 | Approve finding | Allows user/Prime to accept a finding as valid. | planned | Finding status changes and records actor. |
| XCK6 | Dismiss/waive finding | Allows explicit waiver with rationale. | planned | Waiver stores reason and scope. |
| XCK7 | Re-run verification | Rechecks a repaired finding or proof item. | planned | Result links to prior finding. |
| XCK8 | Compare model lanes | Shows independent model/reviewer disagreement where available. | planned | Disagreement is visible without dumping full transcripts. |
| XCK9 | Gate irreversible actions | Sends public/financial/account-risking decisions through review gate. | planned | Action cannot proceed without required gate state. |
| XCK10 | Recent review ledger | Shows recent reviews and repair routing history. | planned | Ledger is concise and chronological. |
| XCK11 | Open evidence | Opens proof artifacts, commands, or summaries. | wired | Spark Crosscheck renders display-only evidence handoff controls that switch to Aegis proof summaries (`/bridge/aegis-logic`) or Archive command-preview summaries (`/bridge/session-close-archive-proof`); the handoff changes only the visible surface and does not rerun checks, approve findings, execute commands, or inject raw logs into Prime context. |
| XCK12 | Stop condition alert | Highlights active hard-stop conditions from this checklist. | wired | Spark Crosscheck renders a display-only Stop condition alert by joining `/bridge/review-console` gate counts with `/bridge/aegis-logic` proof-blocking, human-gate, and dispatch-block fields; it flags when further UI wiring should pause until review/proof blockers clear, without approving, waiving, rerunning, or mutating any review state. |

### Routines Surface Subitems

The Routines icon owns recurring or repeatable work patterns. It should make routine automation visible without turning the user into the scheduler.

`ROU0` snapshots are compact continuity and workflow-dispatch posture only. They are not evidence of configured routine automation, schedule/trigger ownership, run history, next-run previews, or retry/escalation controls.

| ID | Routine Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| ROU0 | Runtime continuity status | Shows current continuation/goal runtime and workflow dispatch posture until routine automation exists. | wired | Spark Routines opens `/bridge/goal-runtime` and `/bridge/workflow-dispatch-status` as display-only typed state; no routine execution, scheduler mutation, raw artifact/log/transcript/detail paste, raw worker history replay, or self-approval is authorized. |
| ROU1 | Routine list | Shows configured routines for active project/system. | planned | List is real or empty; no fake routines. |
| ROU2 | Create routine | Creates a new repeatable workflow or monitor with explicit scope. | planned | Routine has name, scope, cadence/trigger, and owner. |
| ROU3 | Enable/disable routine | Toggles routine active state. | planned | Disabled routine does not run. |
| ROU4 | Routine trigger | Supports manual run-now once routine execution exists. | planned | Run creates a visible event/result. |
| ROU5 | Cadence/trigger view | Shows schedule, heartbeat, or event trigger. | planned | Display uses concrete time/trigger data. |
| ROU6 | Last run result | Shows last run status, duration, and proof/evidence link. | planned | Failed run is visible and actionable. |
| ROU7 | Next run preview | Shows next expected run or waiting condition. | planned | Unknown next run displays as unknown. |
| ROU8 | Failure handling | Shows retry/escalation behavior for routine failures. | planned | Failure state does not silently disappear. |
| ROU9 | Prime-owned routine review | Prime reviews routine outputs and only escalates meaningful user gates. | planned | Routine result can be accepted/routed without user micromanagement. |
| ROU10 | Quiet routine mode | Routine noise respects Quiet mode while preserving blockers. | wired | Routines reuses the backend-bound Runtime Continuity and Workflow Dispatch renderers under `[data-goal-runtime]` and `[data-workflow-dispatch-status]`, so `meridian.quiet-mode.v1` suppresses routine success chatter in that surface while blockers, proof gates, and failure state remain visible; no automation execution, scheduler mutation, archive/delete, or proof-critical warning suppression is added. |
| ROU11 | Routine archive/history | Shows previous runs and outcomes without cluttering main panels. | planned | History is inspectable by routine. |
| ROU12 | Public automation boundary | Public build explains what automation needs local permissions/accounts. | wired | Spark Routines renders a Public automation boundary beside `/bridge/goal-runtime` and `/bridge/workflow-dispatch-status`; missing permission/account setup is guidance only, with no automation creation, schedule mutation, routine execution, credential request, or self-approval. |

### Skills Surface Subitems

Skills is a searchable registry of available skills and capabilities. It should explain what each skill does, what arguments it needs, and where it is available: globally, for a project, or for a specific model/backend.

| ID | Skills Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| SKL1 | Search skills | Dynamically search skills by name, purpose, provider, project, or keyword. | wired | Skills Registry filters already loaded FileMap/Models metadata on input by name, scope, backend/provider, description, provenance, setup, permission, and usage example; it does not call `/bridge/message`, `/bridge/call-result`, POST, or a fake skills backend while filtering. |
| SKL2 | Global skills | Shows skills available across all projects. | wired | Skills Registry renders FileMap capability rows as global/read-only metadata with relative-path provenance and no fake project-specific ownership. |
| SKL3 | Project skills | Shows skills available for the active project. | wired | Skills Registry renders an Active project skills section keyed to `activeProjectContext()`, showing that project’s UI-local pinned skills bucket plus loaded global/backend capabilities as fallback; project switching refreshes the section and uses the selected project’s pin bucket without calling a fake project-skills backend, mutating skills, sending prompts, or enabling Auto routing. |
| SKL4 | Model/backend skills | Shows which skills are available by Codex, Max/Claude, or other backend. | wired | Skills Registry renders `/bridge/models` rows with backend/provider labels and setup status; it does not enable Auto routing or send prompts. |
| SKL5 | Skill description | Explains what each skill does in user-readable language. | wired | Skills Registry descriptions come from FileMap entry purpose text or Models setup/readiness hints and remain display-only metadata. |
| SKL6 | Arguments schema | Shows required and optional arguments for each skill. | wired | Skills Registry rows render display-only argument schema text for FileMap metadata (`path`, `area`, `related_tests`) and Models metadata (`backend`, manually supplied prompt text, `auto=false`); schemas are searchable but do not execute skills, validate prompts, assemble model payloads, call providers, mutate files, or enable Auto routing. |
| SKL7 | Usage example | Shows a short example command or prompt pattern. | wired | Skills Registry rows include non-executing examples for FileMap/Atlas inspection or manual model selector use; examples are display text only and do not execute, call providers, mutate files, send prompts, install tools, sign in, or enable Auto routing. |
| SKL8 | Permission boundary | Shows whether the skill reads files, writes files, uses network, or affects accounts. | wired | Skills Registry rows include a permission boundary that keeps FileMap metadata read-only and Models rows free of install, login, account probing, Auto routing, or prompt-send authority. |
| SKL9 | Install/setup status | Shows missing dependencies or login/setup requirements. | wired | Skills Registry renders model/backend setup posture from `/bridge/models`; FileMap capabilities show related-test/setup metadata when available. |
| SKL10 | Run/request path | Provides a clear path to invoke or request the skill when supported. | wired | Skills Registry shows non-executing usage examples such as opening a relative path through FileMap/Atlas or selecting an already available backend in the manual model selector; the surface itself does not run skills. |
| SKL11 | Skill provenance | Shows whether skill is built-in, project-local, plugin-provided, or user-defined. | wired | Skills Registry marks rows with backend provenance such as `backend:filemap` or `backend:models`; it does not infer user-defined/plugin provenance without backend metadata. |
| SKL12 | Favorite/pin skill | Allows important skills to be pinned for the active project/user. | wired | Skills Registry pin controls persist row ids under `meridian.skills.pinned.v1` bucketed by active project context in the local user UI profile, sort pinned rows first, show a Pinned skills section, and do not mutate backend skills, routes, files, accounts, providers, or prompts. |

### Archive Surface Subitems

Archive preserves reloadable sessions. It differs from long-term knowledge because the user expects a session may be reopened and run again, while Echo/Atlas knowledge is extracted memory or retrieval context.

| ID | Archive Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| ARC0 | Close/archive proof snapshot | Shows current session-close/archive proof posture before any live archive controls exist. | wired | Spark Archive opens `/bridge/session-close-archive-proof` as display-only typed proof over GET only; no live close/archive/reload/run-again/delete control, POST route, message route, raw prompt, raw worker chat, raw worker session history, pasted transcript/log/detail body, replay, or deletion is authorized. Orchestrator may ingest compact typed session state only; raw detail is fetched on demand only. |
| ARC1 | Session archive list | Shows archived sessions that can be inspected later. | planned | Archive list is real or empty; no fake sessions. |
| ARC2 | Reload session | Restores an archived session into an active/reopened state where supported. | planned | Reloaded session preserves identity/source metadata. |
| ARC3 | Run again | Allows rerun/resume/restart from archived session context where backend supports it. | planned | Action names the actual steering mode used. |
| ARC4 | Archive metadata | Stores project, model/backend, role, timestamps, status, and source session id. | wired | Spark Archive renders a display-only Archive metadata frame from `/bridge/session-close-archive-proof`, showing target/source session ids plus session name, project, role, model provider/name, observed timestamp, and stopped status for the current archive preview without exposing transcript bodies, reload/run-again controls, or a real archive storage backend. |
| ARC5 | Context reference | Allows Prime/session to reference archived context intentionally. | planned | Reference creates explicit context link, not hidden prompt drag. |
| ARC6 | Search archived sessions | Searches archive by project, role, model, status, date, and text summary. | planned | Search results are scoped and fast. |
| ARC7 | Archive summary | Stores compact session summary for scanability. | wired | Spark Archive renders a compact display-only Archive summary from `/bridge/session-close-archive-proof`, showing the backend summary plus status, session, project, and proof-posture scan fields without loading full transcripts, searching archives, or claiming durable archive storage. |
| ARC8 | Transcript access | Allows full transcript access when available and authorized. | planned | Full transcript opens on demand only. |
| ARC9 | Archive to knowledge handoff | Allows extracting durable lessons/memory into Echo/Atlas separately. | planned | Extraction is explicit and does not replace archive. |
| ARC10 | Restore proof/artifacts | Links archived session to proof, files, or artifacts created. | wired | Spark Archive renders a display-only Restore proof/artifacts frame from `/bridge/session-close-archive-proof`, exposing compact archive proof/evidence refs as inspectable ids for the current preview while keeping raw artifact bodies, reload/run-again controls, and a real archive restoration backend unavailable. |
| ARC11 | Archive retention | Supports retention/archive policy once storage model exists. | planned | Retention state is visible and reversible where possible. |
| ARC12 | Safe deletion boundary | Deleting an archive is separate from closing or filtering and requires explicit intent. | planned | No archive deletion from one-click close. |

### Close Surface Subitems

Close is a targeted session-control action, not merely closing a panel. It should preserve the useful Polaris behavior: target a session, force write-through, update Obsidian where applicable, then close intentionally.

| ID | Close Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| CLS1 | Target selection | Lets user/Prime choose the session or surface to close. | planned | Target is explicit before action runs. |
| CLS2 | Write-through before close | Forces pending session state/transcript/metadata write before closing. | planned | Close records a final saved state event. |
| CLS3 | Obsidian capture | Writes or queues an Obsidian update before close when applicable. | planned | Obsidian result is visible as success/failure. |
| CLS4 | Close summary | Captures concise close summary with status, next action, blockers, and proof refs. | wired | Spark Archive renders a display-only Close summary from `/bridge/session-close-archive-proof`, joining command-preview posture with archive/close proof blockers and evidence refs to show status, next action, expected transition, and proof references for the current close/archive preview without closing a session, writing history, or claiming a durable archive backend. |
| CLS5 | Archive option | Offers archive-on-close for sessions worth reopening. | planned | Archived close appears in Archive list. |
| CLS6 | No silent data loss | Blocks close or warns when write-through fails. | planned | Failed write-through leaves session open or visibly recoverable. |
| CLS7 | Stop-before-close check | Detects running work before close and asks for stop/archive/leave-running path. | planned | Running session cannot be silently killed. |
| CLS8 | Close overlay mode | Closes transient UI overlays without affecting sessions. | wired | Spark Close returns the right panel to User mode without running session close/write-through. |
| CLS9 | Close status event | Emits structured event for session lifecycle/history. | planned | Event is visible to Beacon/Session Lifecycle. |
| CLS10 | Restore after close | Closed sessions can be found through recent/Archive where applicable. | planned | Recently closed item is recoverable. |
| CLS11 | Permission gate | Higher-risk close actions require explicit confirmation. | planned | Public/account/build-critical sessions do not close accidentally. |
| CLS12 | Orchestrator-led close | Prime can propose routine close but must expose reason and saved state. | planned | Proposed close includes reason and target. |

### Speech / Voice

| ID | Control / Feature | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| VO1 | Speech mode icon | Shows first-class spoken interaction state while capture/output backends remain unavailable. | wired | The top speech-mode icon reflects compact `/bridge/voice-io` states such as listening/thinking/speaking/blocked/unavailable, but remains disabled/`aria-disabled=true` and does not capture audio, speak responses, read aloud, or mutate mute state. |

### Speech / Voice Subitems

Speech/Voice is first-class planning now. The user should be able to speak with Prime and be spoken to through Spark, with clear listening/thinking/speaking states.

| ID | Voice Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| VOC1 | Push-to-talk | Lets user hold/click to speak to Prime. | planned | Speech capture starts/stops with visible state. |
| VOC2 | Wake/listening state | Shows when Spark is listening, idle, thinking, or speaking. | wired | Top speech icon and Voice I/O surface reflect backend-backed listening/thinking/speaking/blocked/unavailable states from compact typed status; executable capture/output remains unauthorized. |
| VOC3 | Speech-to-text | Converts spoken user input into prompt text before send. | planned | Transcribed text is visible/editable before or after send by mode. |
| VOC4 | Voice submit mode | Supports spoken prompt submission to Prime. | planned | Voice prompt follows same routing as typed Prime prompt. |
| VOC5 | Read-aloud response | Speaks Prime/model responses through Spark. | partial | Read-aloud status/control is visible from the Voice I/O surface, but it is aria-disabled and does not speak response bodies. |
| VOC6 | Mute output | Mutes spoken responses without disabling typed responses. | partial | Mute status/control is visible from the Voice I/O surface, but it is aria-disabled and does not mutate output state. |
| VOC7 | Interrupt speech | Allows user to stop current spoken response. | planned | Speech stops without losing transcript. |
| VOC8 | Voice selection | Chooses Spark voice once voice provider exists. | planned | Selected voice is visible and persistent. |
| VOC9 | Dictation correction | Allows correction of misheard text before/after sending. | planned | Correction updates prompt/transcript metadata. |
| VOC10 | Voice command intents | Recognizes command families such as reset, reload, open, close, filter, and crosscheck. | planned | Recognized command previews intended action before risky execution. |
| VOC11 | Privacy indicator | Makes microphone capture state obvious. | wired | Top speech icon carries `data-capture-state` and a capture title, and Voice I/O renders a backend-sourced Voice privacy indicator from `/bridge/voice-io` showing microphone capture active/inactive, whether capture can start, permission prompt state, and fail-closed posture; no permission request, microphone capture, speech synthesis, read-aloud, mute mutation, prompt send, or provider/settings mutation is exposed. |
| VOC12 | Public setup guidance | Explains microphone/browser permissions and speech provider setup in public builds. | wired | Voice I/O surfaces render a Public voice setup boundary from `/bridge/voice-io`; missing microphone or speech-provider authorization is setup guidance only, with no permission request, capture start, speech synthesis, secret read, provider settings mutation, or typed prompt/response disruption. |

### Harness Dock Buttons

Harness buttons switch the right panel into Harness mode. They are not merely labels or shortcuts. The right panel becomes a full-panel harness logic list, with previous User Session mode preserved for return.

| ID | Harness Button | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| HN1 | Prime | Opens/focuses Prime runtime logic surface. | wired | Click opens Prime Runtime Logic with backend-sourced decision, context, source refs, proof logic, and blockers. |
| HN2 | Bifrost | Opens/focuses UI/Bifrost surface. | wired | Click opens Bifrost Voice I/O from `/bridge/voice-io` with compact typed state only; no microphone capture, speech output, read-aloud, mute mutation, raw prompt/response, raw worker history, or worker chat is exposed. |
| HN3 | Relay | Opens/focuses model-routing surface. | wired | Click opens Relay Runtime Logic with bridge/access/model/dispatch/blocker logic; Auto remains disabled. |
| HN4 | Beacon | Opens/focuses heartbeat/liveness surface. | wired | Click opens Beacon Liveness with backend-sourced heartbeat/advisory/guardrail status from `/bridge/beacon-liveness`; no raw worker chat or local path leakage. |
| HN5 | Security | Reserved TBD harness identity; replaces generic TBD. | wired | Security is the planned reserved harness identity with `Security-Guardrails`, opens the generic display-only harness surface, and keeps unsupported actions/no-backend-state visible without any bridge-backed security snapshot, POST, `/bridge/message`, branch movement, or executable guardrail action. |
| HN6 | Aegis | Opens/focuses proof/cross-check surface. | wired | Click opens Aegis Runtime Logic from `/bridge/aegis-logic`; proof state is display-only and does not apply console responses or expose raw evidence bodies. |
| HN7 | Compass | Opens/focuses mission/project bearing surface. | wired | Click opens Compass Runtime Logic with backend-sourced project selector, Prime prompt context, and portfolio boundary sections. |
| HN8 | Vulcan / Session Lifecycle | Opens/focuses session lifecycle controls. | wired | Click opens Vulcan Runtime Logic with backend-sourced User Session independence, project-aware session grouping, stale target guard, and lifecycle boundary sections. |
| HN9 | Atlas | Opens/focuses knowledge/context retrieval surface. | wired | Click opens Atlas Retrieval from `/bridge/atlas-retrieval`; display uses safe retrieval metadata and must not expose raw record bodies. |
| HN10 | Charon / FileMap | Opens/focuses navigation/FileMap surface. | wired | Click opens FileMap Registry from `/bridge/filemap`; entries use relative repo paths only, with no absolute/local filesystem path leakage. |
| HN11 | Arbiter / Codex Reviews | Opens/focuses review queue surface. | wired | Click opens Review Console from `/bridge/review-console`; findings are display-safe and no raw prompt, raw response, or worker chat bodies are shown. |
| HN12 | Workflow | Opens/focuses workflow/sub-agent surface. | wired | Click opens Workflow Dispatch Status from `/bridge/workflow-dispatch-status`; status is display-only and does not execute sub-agent work. |
| HN13 | Federation | Opens/focuses federation/network surface. | wired | Click opens Federation Horizon with backend-sourced planning-only boundaries; no fake network state or remote execution controls. |
| HN14 | Echo | Opens/focuses memory surface. | wired | Click opens Echo Memory from `/bridge/echo-memory`; records are display-safe and memory mutation/recall bodies are not exposed. |
| HN15 | Ratchet / Tool | Opens/focuses tool execution surface. | wired | Click opens Ratchet-Tools through the generic display-only harness surface with a planned capability boundary; no fake tool execution, provider/tool call, POST, `/bridge/message`, or result-recovery path is exposed. |
| HN16 | Source / Git | Opens/focuses git/source-control surface. | wired | Click opens Source-Git through the generic display-only harness surface with a planned capability boundary; no branch movement, commit, push, reset, file mutation, POST, `/bridge/message`, or result-recovery path is exposed. |
| HN17 | Vision / Browser | Opens/focuses browser/vision surface. | wired | Click opens Vision-Browser through the generic display-only harness surface with a planned capability boundary; no fake browser state, page control, screenshot, remote navigation, POST, `/bridge/message`, or result-recovery path is exposed. |
| HN18 | Autonomy / Release | Opens/focuses display-only release/autonomy posture from Prime autonomy. | wired | `/bridge/prime-autonomy` renders a safe snapshot with release/deployment execution, credentials/account probing, raw prompts/responses/evidence bodies, raw worker chat, PIDs, and filesystem paths all blocked. |

### Compass And Vulcan Backend Readiness

Compass and Vulcan definitions are backend/V2 build requirements, not UI checklist items. Track project definition, project bounds, cross-project handoff logic, session lifecycle state, command plan proof, and harness relationships in `docs/v2-progress-tracker.md` before wiring deeper UI controls here.

| ID | Backend Dependency | UI Readiness Rule | Current Status | Verification |
|---|---|---|---|---|
| HBD0 | Prime runtime contract | Prime UI may render backend-sourced orchestration logic, but must not invent owner, proof, blocker, or executability state outside the Prime backend packet. | wired | Prime panel reads `/bridge/prime-logic`; review status lives in `docs/v2-progress-tracker.md`. |
| HBD1 | Compass backend checklist | Compass UI may render backend-sourced project logic, but must not invent project definitions or cross-project handoff controls before V2 backend rows are built. | wired | Compass panel reads `/bridge/compass-logic`; deeper backend rows live in `docs/v2-progress-tracker.md`. |
| HBD2 | Vulcan backend checklist | Vulcan UI may render backend-sourced session lifecycle logic, but must not execute session command plans before V2 backend rows are built. | wired | Vulcan panel reads `/bridge/vulcan-logic`; deeper backend rows live in `docs/v2-progress-tracker.md`. |
| HBD3 | Relay/Model backend ownership | UI may render model-call posture from existing backend snapshots, but must not create provider route tables, prompt payloads, fallback rules, transport gates, or provider-balance calculations in the UI or Prime layer. | wired | Models/Relay/Balance surfaces read `/bridge/models`, `/bridge/relay-logic`, `/bridge/relay-evidence`, and `/bridge/provider-balance` as display-safe backend-owned snapshots. |

### Echo Memory Subitems

Echo owns durable memory ranking and memory-result visibility. It may surface compact summaries, tags, ranking scores, and source refs, but it must not expose raw memory bodies or mutate recall/write state from the UI.

| ID | Echo Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| ECHO0 | Display-only memory ranking | Shows memory query boundary and ranked memory summaries from the backend. | wired | Echo Memory renders `/bridge/echo-memory` with project/tags/limit plus id, kind, summary, source, importance, pinned state, tags, score, reason, and created time; record bodies and memory mutation stay unavailable. |

### Atlas Retrieval Subitems

Atlas owns retrieval over allowlisted project knowledge and FileMap context. It may surface retrieval metadata and display-safe excerpts, but it must not dump raw records, hidden context, or provider outputs into Prime.

| ID | Atlas Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| ATL0 | Display-only retrieval metadata | Shows retrieval query, missing paths, truncation state, and display-safe hits. | wired | Atlas Retrieval renders `/bridge/atlas-retrieval` with terms, required paths, limit, truncated state, missing paths, hit path/title/source/score/reason, and allowlisted excerpt text only. |

### FileMap / Charon Subitems

Charon owns navigation through the FileMap registry. It may surface repo-relative path metadata and related tests, but it must not leak absolute local filesystem paths or move branches/worktrees.

| ID | FileMap Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| FM0 | Display-only relative-path registry | Shows FileMap area counts and focus entries from the backend registry. | wired | FileMap Registry renders `/bridge/filemap` with entry counts, test coverage counts, area counts, repo-relative paths, purpose, related tests, and notes; no absolute local paths or source-control actions are exposed. |

### Harness Mode Subitems

Harness mode is for reviewing and updating harness logic items. It may expose diagnostics and scoped controls, but model interaction goes through Prime and Relay; it should not pretend a harness can receive arbitrary direct commands until that harness target is defined.

| ID | Harness Mode Item | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| HMS1 | Enter harness mode | Clicking a harness button switches the right panel into Harness mode. | wired | Right panel title/target changes to selected harness. |
| HMS2 | Preserve User Session mode | Previous User Session target is preserved when entering Harness mode. | wired | Return to User Session restores the prior `meridian.user-session.target.v1` target or shows the stale-target warning if the session disappeared. |
| HMS3 | Harness logic list | Shows a full-panel list of logic items for the selected harness. | wired | Harness mode opens a full right-panel surface with Harness logic and Backend link sections, not a prompt window or blank chat; model-harness aspect buttons render their own display-only logic sections and backend binding source. |
| HMS4 | Prime review path | Prime reviews harness intent, risk, and proof needs before model interaction. | wired | Prime Runtime Logic renders a display-only `Prime review before dispatch` section from `/bridge/prime-logic`, naming intent, reviewed action, owner, risk, Prime status, Aegis proof needs, and blocking proof gates while leaving route/provider/payload decisions with Relay and Model Harness. |
| HMS5 | Relay-mediated model interaction | Model calls for harness logic go through Relay + Model Harness routing and payload construction. | wired | Model Harness backend-binding surfaces render a display-only Relay-mediated dispatch posture by joining `/bridge/relay-logic`, `/bridge/provider-balance`, and `/bridge/relay-evidence` fields for route source, selected provider, routing owner, policy state, exact lane plan, payload continuity refs, and intent/payload evidence refs; route/model/payload ownership stays with Relay + Model Harness and the UI does not call providers or mutate routing. |
| HMS6 | Harness-specific actions | Right-panel actions target selected harness logic item. | wired | Generic harness surfaces expose display-only action metadata naming the selected harness and `Harness logic` item, keep execution blocked until reviewed backend actions exist, and do not POST, call `/bridge/message`, call `/bridge/call-result`, retarget User Sessions, or route to another harness. |
| HMS7 | Unsupported action guard | If harness logic action is not supported yet, action is blocked with readable warning. | wired | Generic planned harness surfaces render an explicit Unsupported action guard naming the selected harness and showing that action status is blocked/display-only until a reviewed backend exists; no POST, `/bridge/message`, provider calls, branch movement, or live tool/browser/security actions are exposed. |
| HMS8 | Logic update framing | Harness mode language frames work as updating/adding harness logic. | wired | Generic planned harness surfaces render a Logic update framing section that frames work as reviewing/updating/adding harness logic items after backend review, while explicitly saying this is not arbitrary project/session control. |
| HMS9 | Harness state summary | Shows concise harness status once real state exists. | wired | Generic planned harness surfaces render a Harness state summary that names the selected harness, explicitly shows real backend state as unavailable, and avoids fake health, latency, uptime, or degraded/healthy claims. |
| HMS10 | Harness diagnostics | Shows harness diagnostic events when available. | wired | Model Harness backend-binding surfaces render a display-only Harness diagnostics section from existing `/bridge/relay-evidence` advisory fields plus `/bridge/workflow-dispatch-status` visibility policy, showing prompt-packet decision/severity/blockers, payload status and warning/blocker tags, provider validation/telemetry/warnings/blockers, and dispatch visibility posture; it does not claim per-harness event history, execute harness work, or expose raw artifacts. |
| HMS11 | Harness proof link | Links harness changes to proof/checks when applicable. | wired | Generic harness surfaces render a display-only proof/check link from `/bridge/filemap` for the selected harness; Atlas now shows the registered workflow adapter and related `tests/test_workflow_atlas.py` proof path without executing tests, workflow orders, providers, file writes, or branch movement. |
| HMS12 | Harness permission boundary | High-risk harness actions require explicit approval. | wired | Planned Tool/Git/Browser harness surfaces render a permission boundary saying explicit approval and reviewed backend wiring are required before execution, while Source/Git branch/file actions and Tool/Browser execution stay unavailable; Release uses `/bridge/prime-autonomy` display-safe posture with release execution unauthorized and controls hidden, so high-risk actions cannot run silently. |
| HMS13 | Harness mode close | Closing Harness mode returns to previous valid right-panel mode. | wired | Spark Close returns Harness mode to User mode without losing User Session state. |
| HMS14 | Harness edit preservation | Unsaved harness-mode item edits are preserved per harness where useful. | wired | Generic planned harness surfaces render a UI-local unsaved harness logic note stored under `meridian.harness.draft.v1.<harness>`; switching away/back restores the draft for that selected harness only, with no backend write, POST, `/bridge/message`, `/bridge/call-result`, harness execution, or cross-harness draft leakage. |
| HMS15 | No cross-harness leakage | Logic item edits/actions for one harness do not silently route to another harness. | wired | Generic planned harness surfaces render a Harness isolation boundary naming the active harness, scoping routing to the selected harness only, and blocking silent reroutes to another harness; no POST, `/bridge/message`, result-recovery path, or executable harness action is exposed. |

### Bridge / Backend Features

| ID | Feature | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| BR1 | Meridian model bridge | Receives UI prompts and routes to selected local CLI backend. | wired | `/bridge/health` returns ok plus bridge version/capabilities. |
| BR2 | Codex backend | Sends selected prompts to Codex CLI. | wired | Select Codex; prompt returns Codex CLI response or readable setup error. |
| BR3 | Max backend | Sends selected prompts to Claude CLI when available. | wired | Select Max; prompt returns Claude response or readable setup error. |
| BR4 | CLI setup detection | Detects missing CLI/auth and gives install/login guidance. | wired | `/bridge/models` and failed calls return setup guidance. |
| BR5 | Recent call diagnostics | Stores metadata only, never prompt text, and identifies the bridge generation. | wired | `/bridge/recent-calls` returns bridge version/capabilities plus request id/channel/backend/status/context counts. |
| BR6 | Bridge origin guard | Accepts local Meridian UI and command-line checks; blocks arbitrary web origins from prompt/restart endpoints. | wired | Self-test proves `127.0.0.1:5500` is allowed and `example.com` is blocked. |
| BR7 | Prime/Relay Auto routing | Future: Prime declares intent/constraints and Relay + Model Harness choose the governed model route. | planned | Auto remains disabled until this contract exists and exposes backend-owned dispatch evidence. |
| BR8 | Session close/archive proof snapshot | Exposes archive proof posture as a display-only typed snapshot. | wired | `GET /bridge/session-close-archive-proof` returns compact typed session lifecycle proof only; there is no POST route, no message route, no executable command handler, and no raw prompt/chat/session-history/transcript/log/detail body exposure. |

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
| MB2 | Auto remains unavailable until Relay + Model Harness own routing mechanics and Prime owns only intent/risk/proof inputs. | Served page contains disabled Auto option or equivalent unavailable state. |
| MB3 | Selecting Codex sends through the Meridian bridge, not Polaris. | Request goes to `http://127.0.0.1:8767/bridge/message`; no Polaris path or process is touched. |
| MB4 | Selecting Max sends through the Meridian bridge when the Claude CLI is available. | `/bridge/models` reports Max availability; bridge invokes Claude with print/json/no-session-persistence over stdin and parses the JSON result. |
| MB5 | Public setup errors are readable. | Missing CLI or auth failure returns install/login guidance instead of a silent hang. |
| MB6 | Request metadata is tracked without logging prompt text. | `/bridge/recent-calls` shows bridge version/capabilities plus request id, channel, backend, model label, duration, status, and visible-context counts only. |
| MB7 | Model/context label appears below or near the response area when known. | Manual: send a follow-up request and confirm displayed model/source plus visible context count. |
| MB8 | Visible session continuity | Follow-up prompts carry the visible panel transcript as bounded context, with no hidden backend memory. | Response metadata and `/bridge/recent-calls` record nonzero `sessionContextEntries` after a follow-up prompt. |
| MB9 | Bridge capability guard | UI blocks prompt sends when the running bridge does not advertise visible transcript context support. | Old bridge shows restart-required status instead of silently sending stateless follow-ups. |
| MB10 | Bridge restart endpoint | Local bridge exposes a same-port restart endpoint for Reset recovery. | `POST /bridge/restart` marks restart in progress before delayed process replacement, duplicate in-flight restart calls return idempotently, child processes are hidden on Windows, then `/bridge/health` and `/bridge/models` come back with visible-context capability. |
| MB11 | Bridge capability parity | `/bridge/health` and `/bridge/models` advertise the same bridge version and capability flags, and the UI readiness line shows the active bridge generation. | Both endpoints report `version=local-bridge-routes-v2`, `visibleTranscriptContext`, `recentCallContextDiagnostics`, and `samePortRestart`; stale generations show restart-required. |
| MB12 | Local-origin bridge access | Browser access to bridge endpoints is limited to the Meridian local UI origins. | Disallowed origins get `403`; command-line checks without an Origin header still work. |
| MB13 | Bridge readiness self-heal | UI rechecks bridge readiness when the page regains focus or visibility. | Restart bridge externally, return to the page, and model readiness plus User Session targets refresh without manual reload. |
| MB14 | Relay bridge visibility | Relay panel shows and refreshes live bridge access status from `/bridge/health`, not static copy. | Open Relay; Bridge route shows online/offline, version, visible-context state, and reset recovery state; focus/visibility refresh updates it. |
| MB15 | Lost response recovery | If the browser loses a completed model response, the UI retrieves the short-lived local result by request id and renders it in the visible transcript. | `/bridge/call-result` returns output for a completed request id; `/bridge/recent-calls` remains metadata-only. |
| MB16 | Relay logic snapshot | Relay panel renders model-routing logic from the backend/domain snapshot, not a duplicated static UI list. | `/bridge/relay-logic` returns `source=meridian_core.relay.route_from_tier`; Relay panel shows source, route precedence, tier logic, Tier 3 proof/blockers, and no Heartbeat text. |
| MB17 | Relay dispatch visibility | Relay panel renders dispatch lane/order/payload policy from the backend dispatch plan snapshot. | `/bridge/relay-logic` includes `dispatch.source=meridian_core.relay_dispatch.build_relay_dispatch_plan`; panel shows dispatch logic without prompt payload text. |
| MB18 | Relay audit depth | Relay panel renders fallback/rejection/proof/telemetry audit depth from the backend route audit. | `/bridge/relay-logic` includes `auditDepth`; panel shows silent fallback blocked, counts, primary blocker, and primary proof for Tier 3. |
| MB19 | Relay collapsible capability headers | Relay panel exposes the expert Relay capability breakdown in collapsible headers sourced from the backend snapshot. | `/bridge/relay-logic` includes `capabilitySections`; panel shows Relay Job, Risk Tier Routing, Model Lane Logic, Access Route Precedence, Session Lifecycle Logic, Context Latency Privacy, Prompt Budget Logic, Audit Logic, Dispatch Logic, and Current Limits. |
| MB20 | Relay prime directives | Relay panel opens with Prime Directives and Prime Directive Proofs before deeper capability sections. | `/bridge/relay-logic` includes `primeDirectives` and `primeDirectiveProofs`; panel shows the three principles and three proof questions at the top. |
| MB21 | User session targets | Bridge exposes routable User Session targets from real Meridian worktrees. | `/bridge/user-sessions` returns `userSessionTargets=true`, excludes shared main, and User prompts send the selected `sessionTargetId`. |

## Harness UI Rules

| # | Rule | Proof |
|---|------|-------|
| H1 | Harness buttons do not pretend to be complete before a harness surface exists. | Click behavior is either wired to a real panel or visibly inactive/coming soon by design. |
| H2 | User/session panels follow rules; orchestrator/Prime panels follow logic. | UI copy and behavior keep Prime logic separate from user/session rules. |
| H3 | Security is the reserved icon/identity for the TBD security harness. | Harness map lists Security for the TBD slot before wiring actions. |
| H4 | Prime/Relay model routing remains a future gate until harness ownership is defined. | No UI default to Auto and no hidden automatic routing without an explicit contract that keeps provider/payload/transport mechanics in Relay + Model Harness. |
| H5 | Any new harness surface exposes scoped logic-item actions only when that harness can receive them. | Manual/code review: harness/action target is explicit and does not leak into the wrong session channel. |

## Visual Regression Checks

| # | Check | Proof |
|---|-------|-------|
| V1 | Central spark image is present after refresh. | Visual check or served HTML references existing `bifrost/static/media` Spark assets, including `spark-center-final.png`; current UI has no missing `static/media` Spark URL. |
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
Invoke-RestMethod http://127.0.0.1:8767/bridge/health -TimeoutSec 3
Invoke-RestMethod http://127.0.0.1:8767/bridge/models -TimeoutSec 5
```

For VS Code Live Server checks:

```powershell
$r = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5500/index.html -TimeoutSec 5
@(
  'session-prompt-input',
  'session-response-output',
  'value="codex" selected',
  'value="auto" disabled',
  '/bridge/models',
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
| A prompt disappears without a response or setup error | Check bridge health, `/bridge/models`, browser console, and recent call diagnostics before changing layout. |
| Center image disappears while wiring behavior | Restore visual baseline before continuing behavior work. |
| Model selector defaults to Auto before Prime/Relay routing exists | Revert to Codex default and keep Auto disabled. |
| New button label conflicts with AI/session semantics | Rename or remove it before wiring. Example: do not use Clear for a visual wipe unless it really clears model/session memory. |

## Clearance Record

Append entries here as items are verified.

```text
YYYY-MM-DD HH:MM TZ - <item#> cleared; proof: <short note>; commit: <hash>
```

- 2026-06-01 20:02 -06:00 - Containment event: local main had implementation/UI commits touching `index.html`, `meridian_core/relay_logic_snapshot.py`, `scripts/meridian-model-bridge.js`, and `tests/test_relay_logic_snapshot.py`. Preserved first head as `codex/quarantine-main-impl-6c03da75-20260601-200013`; an external child Codex app-server re-cherry-picked equivalent commits (`1292503d`, `d06f6a0b`, `8ceb7f18`) onto main, preserved as `codex/quarantine-main-impl-8ceb7f18-20260601-200218`. Stopped three `codex.exe app-server --listen stdio://` child helpers, then reset `main` clean to `origin/main` at `24520c5d`. No worker branch movement or push performed.
- 2026-06-01 20:16 -06:00 - Containment event: local main had five implementation/UI commits ahead of `origin/main` (`bc49c722`, `f1d5ff4c`, `ba59a4f3`, `04818cc7`, `992caa8a`) touching `index.html`, `docs/ui-integration-checklist.md`, `meridian_core/relay_logic_snapshot.py`, `scripts/meridian-model-bridge.js`, and `tests/test_relay_logic_snapshot.py`. Preserved head as `codex/quarantine-main-impl-992caa8a-20260601-201629`, then reset `main` clean to `origin/main` at `adc332d1`. The same implementation set reappeared with new commit ids (`feada92c`, `76efcc8f`, `fd3bd14e`, `a98e2d2c`, `00e205ed`); preserved second head as `codex/quarantine-main-impl-00e205ed-20260601-201746` and reset `main` clean to `origin/main` again. A third recurrence appeared as commits (`a5bc3d34`, `ab213410`, `3c9aba11`, `ab857311`, `53f5f205`) plus dirty Relay docs; preserved head as `codex/quarantine-main-impl-53f5f205-20260601-201847`, preserved dirty patch as `local quarantine patch preserved; path redacted`, and reset `main` clean to `origin/main` at `a7e150c7`. No worker branch movement or implementation push performed.
- 2026-06-01 20:27 -06:00 - Containment event: local main had an uncommitted `index.html` Relay styling change. Preserved dirty patch as `local quarantine patch preserved; path redacted`, then reset `main` clean to `origin/main` at `05eb26d1`. No worker branch movement or implementation push performed.
