# JARVIS UI Source Assessment

**Owner:** Bifrost Harness
**Status:** V2 cockpit source direction

## Decision

Meridian should not continue designing the cockpit from scratch. Bifrost V2 should start from existing JARVIS/HUD interface patterns and adapt them to Prime's command-center model.

## Candidate Sources

### Primary Candidate: Open.Jarvis

- Repository: https://github.com/dmrr35/Open.Jarvis
- Fit: Windows-first, local-first desktop assistant with a cyber-style UI.
- Useful patterns: local degraded mode, runtime states, diagnostics, provider safety, desktop posture, cyber dashboard language.
- License note: README reports MIT.
- Meridian use: strongest source for Windows/local desktop assistant feel and status/state vocabulary.

### Visual Candidate: ethanplusai/jarvis

- Repository: https://github.com/ethanplusai/jarvis
- Fit: voice-first assistant with an audio-reactive Three.js particle orb.
- Useful patterns: voice/orb presence, cinematic assistant feel, "online assistant" atmosphere.
- Risk: macOS-heavy app integrations and license must be verified before reuse.
- Meridian use: visual reference for Prime presence, wake sequence, and live-state animation.

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

## Bifrost Adaptation Rules

- Use existing HUD/JARVIS structure as a starting point, not a generic dashboard.
- Preserve Meridian-specific information architecture: Prime command center first, then queues, review gates, harness state, prompt payload, provider balance, and proofs.
- Do not adopt vendor/account automation from any source without passing Meridian's account/public-consumption policy.
- Do not copy source code unless license and attribution are verified.
- Prefer adapting layout, interaction patterns, animation concepts, and component structure before importing implementation.
- Keep Bifrost view-only for decisions: Prime owns logic; Bifrost displays state, gates, and user controls.

## First Build Slice

Build 5 should produce a Bifrost V2 visual adoption contract that:

- selects the repo/patterns to use as the visual base,
- maps source concepts to Meridian concepts,
- identifies code that can be reused versus only referenced,
- defines attribution/license requirements,
- specifies the first cockpit implementation slice after the contract.

