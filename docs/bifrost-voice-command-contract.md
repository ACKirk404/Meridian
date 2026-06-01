# Bifrost Voice Command Contract

**Owner:** Bifrost Harness
**Status:** V2 UI/product contract
**Purpose:** Define how Meridian becomes voice-enabled for input and output without putting orchestration logic inside the UI.

## Principle

Bifrost is Prime's voice surface, not Prime's decision engine. Voice commands create typed user intents, focus changes, dictation events, and read-aloud requests. Prime, Session Lifecycle, Relay, Aegis, Echo, and Atlas decide what those intents mean and whether they are executable.

## Required Voice States

Bifrost must expose these states in the cockpit view model:

- `muted`: microphone disabled and no wake/listen action is allowed.
- `idle`: voice controls available but not listening.
- `listening`: microphone is actively capturing user input.
- `dictating`: captured speech is being inserted into the prompt surface.
- `thinking`: Prime is processing the spoken intent.
- `speaking`: Prime output is being read aloud.
- `blocked`: voice action is unavailable due to permission, provider, browser, or Aegis policy.

The visual surface must make the active state obvious without adding top-navigation noise. The central `PRIMED` core may pulse while listening, thinking, or speaking.

## Command Families

### Harness Panel Commands

Voice commands may open, close, or focus harness panels:

- "Open Echo"
- "Show Atlas"
- "Focus Aegis"
- "Open Relay"
- "Show Session Lifecycle"
- "Open Review Console"
- "Show Bifrost"
- "Close this panel"

Expected result: Bifrost emits a panel-focus intent. Prime decides whether the panel exists, whether it needs context, and whether a human gate is required.

### Project And Lane Commands

Voice commands may switch project context or inspect session groups:

- "Open Meridian"
- "Switch to Polaris"
- "Show build lanes"
- "Show review lanes"
- "Open Build 1"
- "Show Codex Reviews B"
- "What is blocked?"
- "What is next?"

Expected result: Bifrost emits a project/lane focus intent. Session Lifecycle owns queue/session status. Bifrost displays the result but does not poll queues directly unless routed through approved state.

### Prompt Focus And Dictation Commands

Voice commands may control prompt entry:

- "Focus prompt"
- "Start dictation"
- "Stop dictation"
- "Clear dictation"
- "Append this to the prompt"
- "Send to Prime"
- "Cancel"

Expected result: Bifrost updates the local prompt surface or emits a submit intent. Relay still owns prompt payload accounting and Aegis still gates risky dispatch.

### Read-Aloud Commands

Voice commands may control spoken output:

- "Read Prime's answer"
- "Read the summary"
- "Read blockers"
- "Pause voice"
- "Resume voice"
- "Stop reading"
- "Mute"
- "Unmute"

Expected result: Bifrost emits a speech-output control intent. Prime output is read from structured response/progress surfaces, not scraped from arbitrary DOM text.

### Safety And Proof Commands

Voice commands may request proof status:

- "Show proof"
- "Read proof"
- "Why is this blocked?"
- "What needs review?"
- "What changed?"
- "Show the latest commit"

Expected result: Bifrost emits a proof-summary intent. Aegis and Codex Reviews remain the proof authorities.

## Typed Intent Shape

Voice capture should normalize into a small structured intent before it reaches Prime:

```text
VoiceCommandIntent
- phrase: original recognized phrase
- command_family: harness_panel | project_lane | dictation | speech_output | proof | unknown
- action: open | close | focus | start | stop | submit | read | pause | resume | mute | unmute | ask
- target: optional harness/project/lane/panel
- confidence: 0.0-1.0
- requires_confirmation: true/false
- evidence_refs: speech provider metadata, timestamp, current focused surface
```

Low-confidence or high-risk commands must be confirmation-gated before execution. Destructive commands are out of scope for this contract.

## Output Rules

- Spoken Prime output must be concise by default.
- Prime may summarize long review/proof data before speech output.
- Bifrost must provide mute and stop-reading controls.
- Speech output must not read secrets, API keys, private paths, or raw prompts unless Scott explicitly requests it and Aegis permits it.

## Out Of Scope

- No native speech recognition implementation in this contract.
- No provider selection for ASR/TTS.
- No autonomous session mutation from voice alone.
- No destructive queue, branch, worktree, filesystem, or account actions.
- No hidden always-on microphone behavior.

## Acceptance Criteria

- Voice state is represented in Bifrost state without UI-owned decision logic.
- Voice commands map to typed intents rather than free-form UI automation.
- Harness panel, project/lane, dictation, read-aloud, and proof command families are defined.
- Risky or low-confidence intents require confirmation.
- Bifrost remains browser-first; Electron may package the surface later but is not required for this contract.
