# JARVIS UI Source Assessment

**Owner:** Bifrost Harness
**Status:** V2 cockpit source direction

## Decision

Meridian should not continue designing the cockpit from scratch. Bifrost V2 should start from existing JARVIS/HUD interface patterns and adapt them to Prime's command-center model.

## Candidate Sources

### Primary Candidate: Open.Jarvis

- Repository: https://github.com/dmrr35/Open.Jarvis
- Local reference clone: `.tmp/jarvis-sources/Open.Jarvis`
- Fit: Windows-first, local-first desktop assistant with a cyber-style UI.
- Useful patterns: local degraded mode, runtime states, diagnostics, provider safety, desktop posture, cyber dashboard language.
- License note: verified local `LICENSE`; MIT. Code reuse is allowed with copyright/license notice preservation.
- Meridian use: strongest source for Windows/local desktop assistant feel and status/state vocabulary.
- Reuse posture: safe candidate for direct adaptation after attribution is added.

### Visual Candidate: ethanplusai/jarvis

- Repository: https://github.com/ethanplusai/jarvis
- Local reference clone: `.tmp/jarvis-sources/ethanplusai-jarvis`
- Fit: voice-first assistant with an audio-reactive Three.js particle orb.
- Useful patterns: voice/orb presence, cinematic assistant feel, "online assistant" atmosphere.
- License note: verified local `LICENSE`; personal/non-commercial use only without a separate commercial license.
- Risk: macOS-heavy app integrations and restricted license. Do not copy code into Meridian unless Scott obtains/accepts a compatible license path.
- Meridian use: visual reference for Prime presence, wake sequence, and live-state animation.
- Reuse posture: reference only for visual/interaction direction unless licensed.

### Architecture Candidate: vierisid/jarvis

- Repository: https://github.com/vierisid/jarvis
- Fit: always-on daemon, dashboard, sidecars, multi-agent delegation, workflow automation, authority gating.
- Useful patterns: daemon/sidecar split, dashboard rooms, visual workflow builder, autonomy controls.
- Risk: much broader than Meridian V2; avoid importing architecture wholesale.
- Meridian use: reference for command-center organization and long-running orchestrator posture.

### HUD Candidate: OpenClaw `jarvis-ui`

- Source: https://clawskills.sh/skills/jincocodev-jarvis-ui
- Claimed repository path: https://github.com/openclaw/skills/tree/main/skills/jincocodev/jarvis-ui
- Fit: web-based JARVIS-style HUD with Three.js orb, chat, token usage, model info, and system stats.
- Risk: direct repository access needs verification; treat as reference until source can be fetched and license confirmed.
- Meridian use: most directly aligned HUD concept if the code and license are available.
- Reuse posture: reference only until repository and license are verified.

## Parsed Video Reference

Scott provided a YouTube Shorts reference and Codex extracted a local contact sheet:

- Video URL: https://www.youtube.com/shorts/jKXIV5dEyXI
- Local temporary contact sheet: `.tmp/visual-reference/jarvis-short-full-contact-sheet.jpg`

Visible design requirements from the parsed video:

- Dark, high-contrast command-center surface.
- Cyan/teal glow as the primary signal color.
- Central JARVIS/Prime presence orb or status core.
- Agent cards visible as active workers with online/offline/task state.
- Node/workflow map showing delegation relationships.
- Separate task feed/tracker surface for individual agent work.
- Real-time operations feel: workers coming online, 24/7 monitoring, delegation, task ownership.
- The interface should feel like a command dashboard for an operating agent system, not a static admin page.

## Bifrost Adaptation Rules

- Use existing HUD/JARVIS structure as a starting point, not a generic dashboard.
- Preserve Meridian-specific information architecture: Prime command center first, then queues, review gates, harness state, prompt payload, provider balance, and proofs.
- Do not adopt vendor/account automation from any source without passing Meridian's account/public-consumption policy.
- Do not copy source code unless license and attribution are verified.
- Prefer adapting layout, interaction patterns, animation concepts, and component structure before importing implementation.
- Keep Bifrost view-only for decisions: Prime owns logic; Bifrost displays state, gates, and user controls.
- Prefer Open.Jarvis for reusable source posture, Ethan's Jarvis for orb/presence reference, and the parsed video for overall layout/energy.

## First Build Slice

Build 5 should produce a Bifrost V2 visual adoption contract that:

- selects the repo/patterns to use as the visual base,
- maps source concepts to Meridian concepts,
- identifies code that can be reused versus only referenced,
- defines attribution/license requirements,
- specifies the first cockpit implementation slice after the contract.
