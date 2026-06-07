# Bifrost V2 Cockpit Extensions

**Owner:** Bifrost Harness
**Status:** Active V2 contract
**Source note:** `docs/jarvis-ui-source-assessment.md`

## Direction

Bifrost V2 should become a JARVIS-style command center for Prime. It should not continue as a generic dashboard or a loose collection of cards.

The visual base should combine:

- **Open.Jarvis** for reusable Windows/local assistant posture and MIT-friendly source patterns.
- **ethanplusai/jarvis** for orb/presence inspiration only, because the local license is personal/non-commercial without a commercial license.
- **Scott's parsed video reference** for the target feel: dark real-time command center, cyan glow, active agents, workflow map, and task tracker.

## Current Cockpit Contract

The active cockpit direction is Prime-first inside the Meridian Electron app.
The permanent UI should be quiet enough that Scott's attention lands on the
Prime command surface, not on worker dashboards.

The V2 cockpit should have these regions:

- **Prime command bay:** the dominant central prompt where Scott talks to Prime by text or voice.
- **Prime presence core:** a quiet `PRIMED` orb/pulse only. No provider balance, queue, proof, build-lane labels, payload labels, or worker abbreviations belong inside this center HUD.
- **Voice command layer:** always-visible voice input/output state. Meridian must support typed prompt input, microphone input, spoken Prime responses, mute, and spoken NASA-style boot/status calls.
- **Project rail:** project names first. Sessions are revealed only after Scott clicks into a project.
- **Harness consoles:** harnesses open on demand. Each focused harness panel includes a scoped prompt for that subsystem.
- **Mission feed:** a low-noise progress/proof surface for selected state changes. It must not become a worker log or review-queue cockpit.
- **Bottom instrumentation:** compact Beacon/Relay/Aegis/Compass/queue state and clock. No tier or version badges.

## Meridian Mapping

| JARVIS/HUD Concept | Meridian Concept |
|---|---|
| Orb / assistant core | Prime presence and wake state |
| Agent cards | Project drilldowns and session rows |
| Online/offline workers | Session Lifecycle state |
| Workflow map | Prime delegation map |
| Task feed | Queue runway and proof feed |
| System stats | Beacon and harness health |
| Token/model info | Relay prompt payload and Model Harness balance |
| Authority gates | Aegis policy and mission-feed gates |
| Voice interface | Prime microphone input, wake sequence audio, and spoken output |

## Implementation Rules

- Bifrost must display state; Prime owns decisions.
- No UI component should decide whether work is safe, executable, or approved.
- Worker/session detail is inspectable through project drilldowns, not permanently visible as a card wall.
- The cockpit must not reserve permanent top-nav space for Settings, Projects, Reset, Close, Cross Check, Backlog, Skills, Harness, or Balance. Prime can summon panels verbally or through focused controls.
- The cockpit must be fully voice-enabled: voice input, voice output, wake/boot audio, mute controls, and visible listening/thinking/speaking state.
- The Meridian UI is the Electron app. Root `index.html` is the active renderer
  source inside that app, so edits to it are edits to the Electron app's visible
  UI. It is part of the app today, not obsolete, detached, historical-only,
  independent, or a separate browser demo target. Deterministic Bifrost preview
  HTML exists only for backend/view-model proof tests.
- Code reuse must preserve license/copyright notices. Do not import non-commercial Ethan Jarvis code unless licensing is resolved.

## Current Implementation Slice

The current Bifrost runtime slice updates `bifrost/cockpit.py`, `bifrost/static/cockpit.css`, and `tests/test_bifrost_cockpit.py` around:

- a large central Prime command bay,
- a quiet `PRIMED` pulse core,
- a project-first rail with session drilldowns,
- on-demand harness consoles with scoped prompts,
- a visible Voice I/O indicator,
- tests proving old top navigation, review tabs, lane strip, and noisy HUD labels stay out of the rendered cockpit.

This slice is static/sample-data only, but its structure should let live Prime, Beacon, Relay, Aegis, Echo, Atlas, Session Lifecycle, Workflow/Sub-agent, and future Federation data plug in later.
