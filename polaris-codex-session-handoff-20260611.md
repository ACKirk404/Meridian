# Polaris + Codex Session Handoff

Purpose: teach a new session how to control Polaris for implementation work and
use Codex for review/coordination work.

This file is based on observed working behavior in the local Meridian setup on
2026-06-11.

## Ground Rules

- Use Polaris Claude Max chat sessions for implementation.
- Use Floor for Haiku-class work and Power for Opus-class work.
- Use Codex sessions for review, proof verification, git hygiene, promotion
  coordination, and cross-lane orchestration.
- Keep UI-owned files and backend-owned files separated by scope.
- Do not assume Polaris has a first-class tool here; connect through the local
  Polaris server protocol.

## Known Local Polaris Endpoint

Observed local Polaris server:

- HTTP app: `http://127.0.0.1:40010`
- WebSocket: `ws://127.0.0.1:40010/?clientId=<your-client-id>`

Observed repo-local hint:

- `.mcp.json` contains a Polaris MCP URL, but the practical control path used
  here was the Polaris app WebSocket, not a working direct MCP tool.

## Session Control Model

Polaris acts like a local app server with:

- an HTTP UI
- a WebSocket session/event channel
- JSON messages for launch, resume, stop, and session state

The minimal message flow is:

1. Connect WebSocket.
2. Send `ui-client-hello`.
3. Send `launch-chat` to open a Claude Max session.
4. Watch for `session-created`.
5. Poll or reconnect and inspect `init`, `line`, and `session-status`.
6. Send `resume` to steer an existing session.
7. Send `stop` if a session drifts.

## Why Use `launch-chat`

For this setup, `launch-chat` is the correct Claude Max path.

Observed behavior:

- `launch-chat` uses Claude Max via local CLI / Max plan.
- `tier: "floor"` maps to Haiku-class work.
- `tier: "power"` maps to Opus-class work.
- This is the safest path when the instruction is "use Claude Max chat only."

Do not use OpenRouter model ids when the requirement is Claude Max chat.

## Required Project Binding

Always bind Polaris work to the `Meridian` project and supply the intended
workdir.

Important nuance:

- Polaris may mirror the session into a temp worktree under
  `C:\Users\scott\AppData\Local\Temp\polaris-wt\...`
- That is normal.
- Still pass:
  - `projectName: "Meridian"`
  - `workDir: "<target worktree path>"`

After launch, verify the session still reports:

- `projectName: "Meridian"`
- the expected temp worktree or mirrored workdir

If project binding drifts, send a `resume` turn that explicitly rebinds
`projectName: "Meridian"` and restates scope.

## Minimal WebSocket Protocol

### 1. Connect

WebSocket URL:

```text
ws://127.0.0.1:40010/?clientId=codex-some-unique-id
```

### 2. Hello

Send:

```json
{
  "type": "ui-client-hello",
  "clientId": "codex-some-unique-id",
  "tabId": "codex-some-unique-tab"
}
```

### 3. Launch a Claude Max session

Use `launch-chat`:

```json
{
  "type": "launch-chat",
  "prompt": "Full implementation prompt goes here.",
  "displayPrompt": "Short visible label",
  "workDir": "C:/Users/scott/.codex/worktrees/some-worktree",
  "projectName": "Meridian",
  "tier": "floor"
}
```

Notes:

- Put the full instructions in `prompt`.
- Keep `displayPrompt` short; it is mostly the visible label.
- For Opus-class work, change `tier` to `"power"`.

### 4. Watch for session creation

Look for:

```json
{
  "type": "session-created",
  "sessionId": "chat_...",
  "projectName": "Meridian",
  "isChat": true
}
```

Persist:

- `sessionId`
- `resumeId` from later session state

### 5. Poll session state

When you reconnect and receive the `init` payload, find the session by id and
read:

- `status`
- `projectName`
- `workDir`
- `resumeId`
- recent `lines`

Observed useful event types:

- `init`
- `line`
- `session-created`
- `session-status`
- `context-usage`

### 6. Resume / steer an existing session

Send:

```json
{
  "type": "resume",
  "sessionId": "chat_1781166316307",
  "prompt": "Tighten scope to tests/test_bifrost_cockpit.py only.",
  "displayPrompt": "Tighten scope",
  "resumeId": "04d4e494-fedc-40f0-a096-8c0c4aef46ce",
  "model": null,
  "projectName": "Meridian"
}
```

Use `resume` when:

- the session asks for clarification
- the session drifts out of scope
- you need to reassert project binding
- you want to convert a fuzzy task into a mechanical patch

### 7. Stop a drifting session

Send:

```json
{
  "type": "stop",
  "sessionId": "chat_1781166116620"
}
```

Stop immediately if the session:

- edits out-of-scope files
- switches from test repair to backend surgery without authorization
- leaves the intended project/scope

## Recommended Control Loop

Use short control loops, not one long silent run.

Recommended pattern:

1. Launch session.
2. Capture `sessionId`.
3. Wait 10-30 seconds.
4. Poll `init` and inspect recent lines.
5. If on track, wait again.
6. If drifting, send a narrow `resume`.
7. When done, inspect git state yourself.

This is much more reliable than waiting several minutes without visibility.

## How To Use Floor and Power

### Floor = Haiku-class work

Use for:

- narrow test repairs
- one-file patches
- mechanical string/assertion changes
- scoped documentation updates

Launch:

```json
{
  "type": "launch-chat",
  "prompt": "...",
  "displayPrompt": "Haiku narrow patch",
  "workDir": "C:/.../worktree",
  "projectName": "Meridian",
  "tier": "floor"
}
```

### Power = Opus-class work

Use for:

- multi-file implementation slices
- harder reasoning
- riskier refactors
- synthesis across several modules/tests

Launch:

```json
{
  "type": "launch-chat",
  "prompt": "...",
  "displayPrompt": "Opus implementation slice",
  "workDir": "C:/.../worktree",
  "projectName": "Meridian",
  "tier": "power"
}
```

## Opening Numerous Polaris Sessions

Polaris supports parallel sessions. The safe way to fan out:

1. Give each session a unique, disjoint file scope.
2. Use a distinct worktree when overlap risk is nontrivial.
3. Keep each prompt explicit about:
   - allowed files
   - forbidden files
   - required proof commands
   - commit message if successful
4. Track each session id separately.
5. Poll each session in short bursts.

Good parallel split example:

- Session A: backend module + matching tests
- Session B: another backend module + matching tests
- Session C: docs-only proof/update work
- Session D: narrow repair on a single failing test file

Bad split example:

- two sessions editing the same module
- one session editing backend and another session editing shared package exports
  without coordination

## Prompting Pattern That Works Better

Broad prompts drift. Mechanical prompts behave better.

Prefer:

```text
Work only in:
- tests/test_bifrost_cockpit.py

Make only these changes:
1. Delete line X
2. Change assertion Y from 5 to 4
3. Change assertion Z from 4 to 3

Do not edit any other file.
If backend edits are needed, stop and reply BLOCKED.

Then run:
- python -m pytest ...
- node --check ...
- node ... --self-test
- git diff --check

If green, commit with message: ...
```

## How To Review Polaris Work With Codex

Use Polaris for authorship and Codex for review.

Codex review loop:

1. Inspect the actual diff:
   - `git diff`
   - `git show --stat`
   - `git show --unified=...`
2. Re-run proof commands locally on the authoritative branch/worktree.
3. Confirm file scope stayed within the prompt.
4. Confirm the right project/worktree/branch was used.
5. Only then package into branch/PR/promotion flow.

Codex should be the lane that:

- verifies exact hash
- validates proof
- checks tree equality when needed
- updates coordination docs
- updates Obsidian logs
- manages PR and merge flow

## Opening Codex Review Sessions Here

If Codex thread/session tools are available, use them to create separate review
lanes rather than mixing implementation and review in one thread.

Typical patterns:

- Create a new Codex thread for exact-hash review of one PR
- Fork the current thread into a worktree-backed review lane
- Send follow-up prompts to a dedicated review thread with:
  - exact commit hash
  - exact file scope
  - exact proof commands/results
  - requested output: PASS / findings / narrower scope

What to ask a Codex review session for:

```text
Review exact commit <hash>.

Scope:
- file1
- file2

Run/confirm:
- pytest subset ...
- node --check ...
- self-test ...
- git diff --check

Return:
- PASS or findings only
- cite exact file/line when applicable
```

## Promotion Hygiene

Before promoting Polaris-authored work:

1. Push the clean branch.
2. Open a PR.
3. Put exact hash, file scope, proof, and requested ACK on the PR.
4. Record the same in coordination docs if the repo uses them.
5. Merge only through the approved coordination path.

## Things Learned The Hard Way

- If Polaris appears idle, poll session state instead of assuming failure.
- If a session asks for clarification, answer with exact file/line/scope.
- If the launch prompt seems ignored, send the full instructions again with
  `resume`.
- If the session edits forbidden files, stop it immediately.
- If a temp Polaris worktree and the real branch disagree, verify where the
  actual edit landed before claiming progress.
- If you proved a candidate branch, and later merged it, confirm the merged
  `main` tree matches the proven tip.

## Minimal Node Example

```js
const ws = new WebSocket('ws://127.0.0.1:40010/?clientId=codex-demo');

ws.addEventListener('open', () => {
  ws.send(JSON.stringify({
    type: 'ui-client-hello',
    clientId: 'codex-demo',
    tabId: 'codex-demo-tab',
  }));

  setTimeout(() => {
    ws.send(JSON.stringify({
      type: 'launch-chat',
      prompt: 'Work only in tests/test_bifrost_cockpit.py ...',
      displayPrompt: 'Haiku narrow patch',
      workDir: 'C:/Users/scott/.codex/worktrees/some-worktree',
      projectName: 'Meridian',
      tier: 'floor',
    }));
  }, 500);
});

ws.addEventListener('message', (event) => {
  const msg = JSON.parse(String(event.data));
  console.log(msg);
});
```

## Practical Bottom Line

Use Polaris chat sessions as implementation workers.
Use Floor for Haiku-class narrow work and Power for Opus-class deeper work.
Use short steering loops.
Use Codex as the reviewer, verifier, and promoter.
Keep every step explicit, scoped, and auditable.
