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

## Layout Requirements

The V2 cockpit should have these regions:

- **Prime presence core:** a central or left-dominant orb/status core showing Prime state: online, thinking, executing, waiting, blocked, degraded.
- **Prime command lane:** the main orchestrator conversation/input area where Scott talks to Prime.
- **Voice command layer:** always-visible voice input/output state. Meridian must support typed prompt input, microphone input, spoken Prime responses, and spoken NASA-style boot/status calls.
- **Review/proof lane:** the non-orchestrator gate surface for Codex reviews, Aegis findings, proof status, and human-gate requests.
- **Agent runway:** visible Build/Review worker cards with queue state, current task, next task, worktree, model/provider, and last heartbeat.
- **Delegation map:** node/workflow view showing Prime -> harness -> worker/session relationships.
- **Task tracker/feed:** per-agent task feed and completion log, with enough detail to prove work is moving without requiring Scott to open every worker.
- **Harness strip:** Bifrost, Relay, Aegis, Beacon, Echo, Atlas, Model Harness, and Session Lifecycle health.
- **Provider/balance surface:** Claude, OpenAI, DeepSeek, and aggregator status with usage/cost pressure.
- **Prompt payload surface:** per-dispatch prompt size label, budget percent, and growth/flat status.

## Meridian Mapping

| JARVIS/HUD Concept | Meridian Concept |
|---|---|
| Orb / assistant core | Prime presence and wake state |
| Agent cards | Build and review lane cards |
| Online/offline workers | Session Lifecycle state |
| Workflow map | Prime delegation map |
| Task feed | Queue runway and proof feed |
| System stats | Beacon and harness health |
| Token/model info | Relay prompt payload and Model Harness balance |
| Authority gates | Aegis policy and Review Console gates |
| Voice interface | Prime microphone input, wake sequence audio, and spoken output |

## Implementation Rules

- Bifrost must display state; Prime owns decisions.
- No UI component should decide whether work is safe, executable, or approved.
- Every agent card must show enough proof to answer: what is it doing, where is it working, when did it last move, and what blocks it?
- The cockpit must retain Polaris's best navigation affordances: Settings, Projects, Reset, Close, Cross Check, Backlog, Skills, Harness, and Balance.
- The cockpit must be fully voice-enabled: voice input, voice output, wake/boot audio, mute controls, and visible listening/thinking/speaking state.
- The interface should be browser-first HTML/CSS and render deterministically as static preview HTML for tests. Electron is optional packaging, not the center of gravity, unless Meridian later needs desktop-only capabilities.
- Code reuse must preserve license/copyright notices. Do not import non-commercial Ethan Jarvis code unless licensing is resolved.

## First Implementation Slice

The next Bifrost runtime slice should update `bifrost/cockpit.py`, `bifrost/static/cockpit.css`, and `tests/test_bifrost_cockpit.py` to add:

- a Prime presence/orb panel,
- a worker runway with active/next task labels,
- a delegation map placeholder,
- a prompt payload/provider balance strip,
- a visible Voice I/O indicator,
- tests proving the new labels render and are escaped.

This first slice may be static/sample-data only, but it must visibly move the cockpit toward the parsed JARVIS command-center reference.
