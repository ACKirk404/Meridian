'use strict';

const http = require('node:http');
const { spawn } = require('node:child_process');

const HOST = process.env.MERIDIAN_MODEL_HOST || '127.0.0.1';
const PORT = Number(process.env.MERIDIAN_MODEL_PORT || 8767);
const DEFAULT_CWD = process.env.MERIDIAN_MODEL_CWD || process.cwd();
const RECENT_CALLS_LIMIT = Number(process.env.MERIDIAN_MODEL_RECENT_CALLS || 40);
const RECENT_RESULTS_LIMIT = Number(process.env.MERIDIAN_MODEL_RECENT_RESULTS || 20);
const RECENT_RESULT_TTL_MS = Number(process.env.MERIDIAN_MODEL_RESULT_TTL_MS || 300000);
const RECENT_RESULT_TEXT_LIMIT = Number(process.env.MERIDIAN_MODEL_RESULT_TEXT_LIMIT || 80000);
const SESSION_TRANSCRIPT_LIMIT = Number(process.env.MERIDIAN_SESSION_TRANSCRIPT_LIMIT || 12);
const SESSION_TRANSCRIPT_CHAR_LIMIT = Number(process.env.MERIDIAN_SESSION_TRANSCRIPT_CHAR_LIMIT || 12000);
const BRIDGE_VERSION = 'local-bridge-routes-v2';
const BRIDGE_CAPABILITIES = {
  visibleTranscriptContext: true,
  recentCallContextDiagnostics: true,
  samePortRestart: true,
  requestResultRecovery: true,
  relayLogicSnapshot: true,
  relayEvidenceSnapshot: true,
  primeRuntimeSnapshot: true,
  compassLogicSnapshot: true,
  vulcanLogicSnapshot: true,
  beaconLivenessSnapshot: true,
  reviewConsoleSnapshot: true,
  federationHorizonSnapshot: true,
  providerBalanceSnapshot: true,
  goalRuntimeSnapshot: true,
  workflowDispatchStatusSnapshot: true,
  echoMemorySnapshot: true,
  atlasRetrievalSnapshot: true,
  fileMapSnapshot: true,
  aegisLogicSnapshot: true,
  sessionCloseArchiveProofSnapshot: true,
  voiceIoSnapshot: true,
  primeAutonomyReleaseSnapshot: true,
  userSessionTargets: true,
};
const BRIDGE_ROUTES = Object.freeze({
  health: '/bridge/health',
  models: '/bridge/models',
  relayLogic: '/bridge/relay-logic',
  relayEvidence: '/bridge/relay-evidence',
  primeLogic: '/bridge/prime-logic',
  compassLogic: '/bridge/compass-logic',
  vulcanLogic: '/bridge/vulcan-logic',
  beaconLiveness: '/bridge/beacon-liveness',
  reviewConsole: '/bridge/review-console',
  federationHorizon: '/bridge/federation-horizon',
  providerBalance: '/bridge/provider-balance',
  goalRuntime: '/bridge/goal-runtime',
  workflowDispatchStatus: '/bridge/workflow-dispatch-status',
  echoMemory: '/bridge/echo-memory',
  atlasRetrieval: '/bridge/atlas-retrieval',
  fileMap: '/bridge/filemap',
  aegisLogic: '/bridge/aegis-logic',
  sessionCloseArchiveProof: '/bridge/session-close-archive-proof',
  voiceIo: '/bridge/voice-io',
  primeAutonomyRelease: '/bridge/prime-autonomy',
  userSessions: '/bridge/user-sessions',
  recentCalls: '/bridge/recent-calls',
  callResult: '/bridge/call-result',
  restart: '/bridge/restart',
  message: '/bridge/message',
});
const ALLOWED_ORIGINS = new Set((process.env.MERIDIAN_MODEL_ALLOWED_ORIGINS || 'http://127.0.0.1:5500,http://localhost:5500,null')
  .split(',')
  .map((origin) => origin.trim())
  .filter(Boolean));
const recentCalls = [];
const recentResults = [];
let restartInProgress = false;

function beginRestartRequest() {
  if (restartInProgress) return false;
  restartInProgress = true;
  return true;
}

if (process.argv.includes('--self-test')) {
  const samples = [
    classifySetupError('codex', 'codex is not recognized as an internal or external command'),
    classifySetupError('max', 'not authenticated, please login'),
  ];
  const setupFlags = [
    needsSetup('codex', 'codex is not recognized as an internal or external command'),
    needsSetup('max', 'not authenticated, please login'),
    needsSetup('codex', 'Process exited with code 1'),
  ];
  const contextPrompt = promptWithVisibleSession('What should I do next?', [
    { role: 'user', text: 'Remember this visible detail.' },
    { role: 'model', text: 'I can see the visible detail.' },
  ]);
  const emptyPrompt = promptWithVisibleSession('Fresh question', []);
  const contextOk = (
    contextPrompt.entries === 2 &&
    contextPrompt.chars > 0 &&
    contextPrompt.prompt.includes('USER: Remember this visible detail.') &&
    contextPrompt.prompt.includes('MODEL: I can see the visible detail.') &&
    contextPrompt.prompt.includes('CURRENT USER PROMPT: What should I do next?') &&
    emptyPrompt.entries === 0 &&
    emptyPrompt.prompt === 'Fresh question'
  );
  const maxJsonOk = normalizeModelText('max', JSON.stringify({ result: 'max clean ok' })) === 'max clean ok';
  rememberResult({ requestId: 'self-test-result', ok: true, text: 'recoverable text' });
  const resultRecoveryOk = resultForRequestId('self-test-result')?.text === 'recoverable text';
  const setupOk = samples.every(Boolean) && setupFlags[0] && setupFlags[1] && !setupFlags[2];
  const capabilitiesOk = BRIDGE_CAPABILITIES.visibleTranscriptContext && BRIDGE_CAPABILITIES.samePortRestart && BRIDGE_CAPABILITIES.requestResultRecovery && BRIDGE_CAPABILITIES.relayLogicSnapshot && BRIDGE_CAPABILITIES.relayEvidenceSnapshot && BRIDGE_CAPABILITIES.primeRuntimeSnapshot && BRIDGE_CAPABILITIES.compassLogicSnapshot && BRIDGE_CAPABILITIES.vulcanLogicSnapshot && BRIDGE_CAPABILITIES.beaconLivenessSnapshot && BRIDGE_CAPABILITIES.reviewConsoleSnapshot && BRIDGE_CAPABILITIES.federationHorizonSnapshot && BRIDGE_CAPABILITIES.providerBalanceSnapshot && BRIDGE_CAPABILITIES.goalRuntimeSnapshot && BRIDGE_CAPABILITIES.workflowDispatchStatusSnapshot && BRIDGE_CAPABILITIES.echoMemorySnapshot && BRIDGE_CAPABILITIES.atlasRetrievalSnapshot && BRIDGE_CAPABILITIES.fileMapSnapshot && BRIDGE_CAPABILITIES.aegisLogicSnapshot && BRIDGE_CAPABILITIES.sessionCloseArchiveProofSnapshot && BRIDGE_CAPABILITIES.voiceIoSnapshot && BRIDGE_CAPABILITIES.primeAutonomyReleaseSnapshot;
  const sampleSession = sessionTargetFromWorktree({
    path: 'C:\\Users\\scott\\Code\\Meridian-Worktrees\\build-5-bifrost',
    branch: 'refs/heads/worktree-build-5-bifrost',
    head: 'abc123',
  });
  const waitingSession = sessionTargetFromWorktree({
    path: 'C:\\Users\\scott\\Code\\Meridian-Worktrees\\build-5-test-waiting',
    branch: 'refs/heads/worktree-build-5-test-waiting',
    head: 'def456',
  });
  const hiddenSession = sessionTargetFromWorktree({
    path: 'C:\\Users\\scott\\Code\\Meridian-Worktrees\\codex-reviews-b',
    branch: 'refs/heads/codex-reviews-b',
    head: 'fed789',
  });
  const sharedMainSession = sessionTargetFromWorktree({
    path: 'C:\\Users\\scott\\Code\\Meridian',
    branch: 'refs/heads/main',
    head: 'abc789',
  });
  const sessionTargetsOk = (
    BRIDGE_CAPABILITIES.userSessionTargets &&
    sampleSession?.sessionId === 'build-5-bifrost' &&
    sampleSession.routable &&
    sampleSession.status === 'live' &&
    waitingSession?.status === 'waiting' &&
    hiddenSession?.status === 'hidden' &&
    sharedMainSession === null
  );
  const versionOk = BRIDGE_VERSION === 'local-bridge-routes-v2';
  const routeNamesOk = Object.values(BRIDGE_ROUTES).every((route) => route.startsWith('/bridge/') && !route.startsWith('/api/'));
  const originOk = isAllowedOrigin({ headers: { origin: 'http://127.0.0.1:5500' } }) && !isAllowedOrigin({ headers: { origin: 'https://example.com' } });
  const restartGuardOk = beginRestartRequest() && !beginRestartRequest();
  console.log(JSON.stringify({ ok: setupOk && contextOk && maxJsonOk && resultRecoveryOk && capabilitiesOk && sessionTargetsOk && versionOk && routeNamesOk && originOk && restartGuardOk, samples, setupFlags, contextOk, maxJsonOk, resultRecoveryOk, capabilitiesOk, sessionTargetsOk, versionOk, routeNamesOk, originOk, restartGuardOk }, null, 2));
  process.exit(0);
}

function isAllowedOrigin(req) {
  const origin = req?.headers?.origin;
  return !origin || ALLOWED_ORIGINS.has(origin);
}

function corsOrigin(req) {
  const origin = req?.headers?.origin;
  if (!origin) return '*';
  return isAllowedOrigin(req) ? origin : 'null';
}

function sendJson(res, status, body, req) {
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': corsOrigin(req),
    'Access-Control-Allow-Headers': 'content-type',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
  });
  res.end(JSON.stringify(body));
}

function blockDisallowedOrigin(req, res) {
  if (isAllowedOrigin(req)) return false;
  sendJson(res, 403, { ok: false, error: 'Origin is not allowed for the Meridian model bridge.' }, req);
  return true;
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let raw = '';
    req.setEncoding('utf8');
    req.on('data', (chunk) => {
      raw += chunk;
      if (raw.length > 200_000) {
        reject(new Error('Request body too large'));
        req.destroy();
      }
    });
    req.on('end', () => resolve(raw));
    req.on('error', reject);
  });
}

function commandForBackend(backend, prompt) {
  if (backend === 'auto') {
    return commandForBackend(process.env.MERIDIAN_AUTO_BACKEND || 'codex', prompt);
  }
  if (backend === 'max') {
    const bin = process.env.MERIDIAN_CLAUDE_BIN || 'claude';
    return {
      bin,
      args: ['-p', '--no-session-persistence', '--output-format', 'json', '--permission-mode', 'dontAsk'],
      stdin: prompt,
      model: process.env.MERIDIAN_CLAUDE_MODEL || 'Claude Max',
    };
  }
  if (backend === 'codex') {
    const bin = process.env.MERIDIAN_CODEX_BIN || 'codex';
    return {
      bin,
      args: ['exec', '--json', '-'],
      stdin: prompt,
      model: process.env.MERIDIAN_CODEX_MODEL || 'Codex CLI default',
    };
  }
  throw new Error(`Unknown backend: ${backend}`);
}

function normalizeTranscriptText(value, limit = 2000) {
  const text = String(value || '').replace(/\s+/g, ' ').trim();
  if (text.length <= limit) return text;
  return `${text.slice(0, limit - 12).trim()} [truncated]`;
}

function visibleTranscriptContext(transcript) {
  if (!Array.isArray(transcript)) return { text: '', entries: 0, chars: 0 };
  const lines = [];
  let chars = 0;
  for (const entry of transcript.slice(-SESSION_TRANSCRIPT_LIMIT)) {
    const body = normalizeTranscriptText(entry?.text);
    if (!body) continue;
    const role = String(entry?.role || 'model').toUpperCase();
    const model = entry?.model ? ` (${normalizeTranscriptText(entry.model, 120)})` : '';
    const line = `${role}${model}: ${body}`;
    if (chars + line.length > SESSION_TRANSCRIPT_CHAR_LIMIT) break;
    lines.push(line);
    chars += line.length;
  }
  return { text: lines.join('\n\n'), entries: lines.length, chars };
}

function promptWithVisibleSession(prompt, transcript) {
  const context = visibleTranscriptContext(transcript);
  if (!context.text) return { prompt, entries: 0, chars: 0 };
  return {
    prompt: [
      'Use this visible Meridian panel transcript as the conversation context. It is not hidden memory; it is the same visible session text in the UI.',
      context.text,
      `CURRENT USER PROMPT: ${prompt}`,
    ].join('\n\n'),
    entries: context.entries,
    chars: context.chars,
  };
}

function normalizeModelText(backend, stdout) {
  const text = stdout.trim();
  if (backend === 'max') {
    try {
      const item = JSON.parse(text);
      if (item?.result) return String(item.result).trim();
    } catch {
      // Fall through to raw text if Claude output is not JSON.
    }
    return text;
  }
  if (backend !== 'codex') return text;
  const lines = text.split(/\r?\n/).filter(Boolean);
  const messages = [];
  for (const line of lines) {
    try {
      const item = JSON.parse(line);
      if (item?.type === 'agent_message' && item.text) messages.push(item.text);
      if (item?.item?.type === 'agent_message' && item.item.text) messages.push(item.item.text);
    } catch {
      // Keep parsing later JSONL lines; Codex versions may emit non-JSON status text.
    }
  }
  return messages.length ? messages.join('\n') : text;
}

function backendName(backend) {
  if (backend === 'max') return 'Claude Max';
  if (backend === 'codex') return 'Codex';
  return backend || 'model';
}

function installHint(backend) {
  if (backend === 'max') return 'Install the Claude CLI, then run `claude login` with your Anthropic/Claude account.';
  if (backend === 'codex') return 'Install the Codex CLI, then run `codex login` with your OpenAI account.';
  return 'Install and sign in to the selected model CLI.';
}

function classifySetupError(backend, errorText) {
  const text = String(errorText || '').trim();
  const lower = text.toLowerCase();
  const name = backendName(backend);
  if (
    lower.includes('not recognized') ||
    lower.includes('command not found') ||
    lower.includes('enoent') ||
    lower.includes('could not be found')
  ) {
    return `${name} CLI is not installed or is not on PATH. ${installHint(backend)}`;
  }
  if (
    lower.includes('login') ||
    lower.includes('not authenticated') ||
    lower.includes('unauthorized') ||
    lower.includes('authentication') ||
    lower.includes('api key') ||
    lower.includes('sign in')
  ) {
    return `${name} CLI is installed, but it is not logged in for this machine. ${installHint(backend)}`;
  }
  return text || `${name} CLI failed before returning a response. ${installHint(backend)}`;
}

function rememberCall(entry) {
  recentCalls.push({
    at: new Date().toISOString(),
    ...entry,
  });
  while (recentCalls.length > RECENT_CALLS_LIMIT) recentCalls.shift();
}

function pruneRecentResults(now = Date.now()) {
  while (recentResults.length && recentResults[0].expiresAtMs <= now) recentResults.shift();
  while (recentResults.length > RECENT_RESULTS_LIMIT) recentResults.shift();
}

function rememberResult(entry) {
  if (!entry?.requestId) return;
  const now = Date.now();
  pruneRecentResults(now);
  recentResults.push({
    at: new Date(now).toISOString(),
    expiresAtMs: now + RECENT_RESULT_TTL_MS,
    requestId: entry.requestId,
    channel: entry.channel || '',
    requestedBackend: entry.requestedBackend || '',
    backend: entry.backend || '',
    model: entry.model || '',
    ok: Boolean(entry.ok),
    setupRequired: Boolean(entry.setupRequired),
    text: String(entry.text || '').slice(0, RECENT_RESULT_TEXT_LIMIT),
    error: entry.error || null,
    durationMs: entry.durationMs || 0,
    sessionContextEntries: entry.sessionContextEntries || 0,
    sessionContextChars: entry.sessionContextChars || 0,
  });
  pruneRecentResults(now);
}

function resultForRequestId(requestId) {
  pruneRecentResults();
  for (let index = recentResults.length - 1; index >= 0; index -= 1) {
    if (recentResults[index].requestId === requestId) {
      const { expiresAtMs, ...result } = recentResults[index];
      return result;
    }
  }
  return null;
}

function needsSetup(backend, errorText) {
  const text = String(errorText || '').toLowerCase();
  return (
    text.includes('not recognized') ||
    text.includes('command not found') ||
    text.includes('enoent') ||
    text.includes('could not be found') ||
    text.includes('login') ||
    text.includes('not authenticated') ||
    text.includes('unauthorized') ||
    text.includes('authentication') ||
    text.includes('api key') ||
    text.includes('sign in')
  );
}

function spawnModelProcess(command, cwd) {
  return spawn(command.bin, command.args, {
    cwd: cwd || DEFAULT_CWD,
    shell: process.platform === 'win32',
    windowsHide: true,
    env: {
      ...process.env,
      MERIDIAN_MODEL_BRIDGE: '1',
    },
  });
}

function restartBridge() {
  server.close(() => {
    const child = spawn(process.execPath, [__filename], {
      cwd: DEFAULT_CWD,
      detached: true,
      stdio: 'ignore',
      windowsHide: true,
      env: process.env,
    });
    child.unref();
    setTimeout(() => process.exit(0), 50);
  });
}

function checkCommandAvailable(bin) {
  return new Promise((resolve) => {
    const child = spawn(process.platform === 'win32' ? 'where' : 'command', process.platform === 'win32' ? [bin] : ['-v', bin], {
      shell: process.platform !== 'win32',
      windowsHide: true,
    });
    child.on('error', () => resolve(false));
    child.on('close', (code) => resolve(code === 0));
  });
}

async function modelStatus() {
  const codexBin = process.env.MERIDIAN_CODEX_BIN || 'codex';
  const claudeBin = process.env.MERIDIAN_CLAUDE_BIN || 'claude';
  const [codexInstalled, claudeInstalled] = await Promise.all([
    checkCommandAvailable(codexBin),
    checkCommandAvailable(claudeBin),
  ]);
  return {
    ok: true,
    service: 'meridian-model-bridge',
    version: BRIDGE_VERSION,
    capabilities: BRIDGE_CAPABILITIES,
    models: [
      {
        backend: 'codex',
        label: process.env.MERIDIAN_CODEX_MODEL || 'Codex CLI default',
        cli: codexBin,
        installed: codexInstalled,
        setupHint: installHint('codex'),
      },
      {
        backend: 'max',
        label: process.env.MERIDIAN_CLAUDE_MODEL || 'Claude Max',
        cli: claudeBin,
        installed: claudeInstalled,
        setupHint: installHint('max'),
      },
    ],
  };
}

function relayLogicSnapshot() {
  return new Promise((resolve) => {
    const pythonBin = process.env.MERIDIAN_PYTHON_BIN || 'python';
    const child = spawn(pythonBin, ['-m', 'meridian_core.relay_logic_snapshot'], {
      cwd: DEFAULT_CWD,
      shell: process.platform === 'win32',
      windowsHide: true,
      env: {
        ...process.env,
        PYTHONIOENCODING: 'utf-8',
      },
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => {
      stdout += chunk;
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk;
    });
    child.on('error', (error) => {
      resolve({ ok: false, error: error.message });
    });
    child.on('close', (code) => {
      if (code !== 0) {
        resolve({ ok: false, error: stderr.trim() || `Relay logic snapshot exited with code ${code}` });
        return;
      }
      try {
        resolve(JSON.parse(stdout));
      } catch (error) {
        resolve({ ok: false, error: `Relay logic snapshot returned invalid JSON: ${error.message}` });
      }
    });
  });
}

function relayEvidenceSnapshot() {
  return pythonJsonSnapshot('Relay evidence', String.raw`
import json
from meridian_core.aegis import (
    PromptPacketProofMetadata,
    PromptPayloadMeterInput,
    ProviderResultValidationInput,
    evaluate_prompt_packet_proof_policy,
    evaluate_prompt_payload_meter_advisory,
    evaluate_provider_result_validation_advisory,
    serialize_prompt_packet_policy_result,
    serialize_prompt_payload_meter_policy_result,
    serialize_provider_result_validation_policy_result,
)
from meridian_core.model_adapter import (
    bind_deepseek_transport_authority,
    bind_deepseek_validation_disposition,
    deepseek_candidate_metadata_preset,
)

deepseek_metadata = deepseek_candidate_metadata_preset("fast")
deepseek_disposition = bind_deepseek_validation_disposition(deepseek_metadata)
deepseek_transport_authority = bind_deepseek_transport_authority(deepseek_metadata)

prompt_packet_result = evaluate_prompt_packet_proof_policy(
    PromptPacketProofMetadata(
        packet_id="packet-relay-001",
        packet_hash_status="present",
        packet_hash="sha256:abc123",
        prompt_tokens=512,
        max_context_tokens=2048,
        budget_ref="budget:tier2:default",
        source_lineage={"direct_input": 512},
        allowed_sources=("direct_input", "atlas_retrieval"),
        aegis_evidence_ids=(
            "packet:packet-relay-001",
            "budget:budget-tier2-default",
            "source:direct-input",
        ),
        risk_tier=2,
        proof_requirement="artifact",
        selected_model_id="gpt-4o-2026-06-01",
        model_trust_state="trusted",
        snapshot_requirement="not_required",
        snapshot_status="not_required",
        human_gate_required=False,
        human_approval_present=False,
        dual_lane_required=False,
        dual_lane_proof_present=False,
        demotion_target_tier=None,
    )
)
payload_meter_result = evaluate_prompt_payload_meter_advisory(
    PromptPayloadMeterInput(
        label_bucket="under-1k",
        budget_percent=24.5,
        growth_delta_tokens=0,
        payload_status="ok",
        q_mode_prompt_drag_state="flat",
        route_continuity_refs=(
            "provider:deepseek",
            "model:deepseek-chat",
            "route:direct",
        ),
        blocker_tags=(),
        warning_tags=(),
        evidence_refs=(
            "payload:snapshot-001",
            "budget:prompt-meter-ok",
            "proof:route-continuity",
        ),
    )
)
provider_result = evaluate_provider_result_validation_advisory(
    ProviderResultValidationInput(
        validation_status="valid",
        warning_tags=(),
        blocker_tags=(),
        evidence_refs=(
            "result:relay-dispatch-001",
            "proof:direct-provider-route",
            "budget:prompt-drag-ok",
        ),
        telemetry_available=True,
        external_review_state="not_required",
    )
)
per_call_intent = {
    "requested_by": "Prime / Relay",
    "prime_intent_ref": "prime-intent:display-safe-demo",
    "project_ref": "project:Meridian",
    "action_type": "relay_evidence_advisory",
    "call_goal": "Display Relay prompt-packet, payload-meter, and provider-result advisory posture for the selected model harness aspect.",
    "expected_output_shape": "compact advisory snapshot with policy decisions, blockers, warnings, and evidence refs",
    "risk_tier": 2,
    "proof_requirement": "prompt packet proof metadata plus Relay/Aegis evidence refs",
    "disallowed_outputs": [
        "raw prompt text",
        "raw provider response bodies",
        "provider credential or account details",
        "branch movement or file mutation instructions",
    ],
    "payload_budget_ref": "budget:tier2:default",
    "evidence_refs": [
        "packet:packet-relay-001",
        "budget:budget-tier2-default",
        "payload:snapshot-001",
        "result:relay-dispatch-001",
    ],
    "authority_boundary": "display_only; no provider call, route mutation, prompt assembly, raw response recovery, or Auto routing",
}
print(json.dumps({
    "ok": True,
    "source": "meridian_core.aegis",
    "version": "v2-relay-evidence-advisory-2026-06-07",
    "harness": "Relay / Model Harness / Aegis",
    "summary": "Display-safe prompt packet, payload meter, and provider-result advisory state.",
    "display_only": True,
    "mutation_authorized": False,
    "raw_prompt_visible": False,
    "raw_provider_response_visible": False,
    "provider_call_authorized": False,
    "prompt_packet": serialize_prompt_packet_policy_result(prompt_packet_result),
    "prompt_payload_meter": serialize_prompt_payload_meter_policy_result(payload_meter_result),
    "provider_result": serialize_provider_result_validation_policy_result(provider_result),
    "per_call_intent": per_call_intent,
    "deepseek_validation_disposition": (
        None if deepseek_disposition is None else deepseek_disposition.to_dict()
    ),
    "deepseek_transport_authority": (
        None if deepseek_transport_authority is None else deepseek_transport_authority.to_dict()
    ),
}))
`);
}

function compassLogicSnapshot() {
  return new Promise((resolve) => {
    const child = spawn('python', ['-m', 'meridian_core.compass_logic_snapshot'], {
      cwd: DEFAULT_CWD,
      shell: process.platform === 'win32',
      windowsHide: true,
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
    child.stderr.on('data', (chunk) => { stderr += chunk.toString(); });
    child.on('error', (error) => {
      resolve({ ok: false, error: error.message });
    });
    child.on('close', (code) => {
      if (code !== 0) {
        resolve({ ok: false, error: stderr.trim() || `Compass logic snapshot exited with code ${code}` });
        return;
      }
      try {
        resolve({ ok: true, snapshot: JSON.parse(stdout) });
      } catch (error) {
        resolve({ ok: false, error: `Compass logic snapshot returned invalid JSON: ${error.message}` });
      }
    });
  });
}

function primeLogicSnapshot() {
  return new Promise((resolve) => {
    const pythonBin = process.env.MERIDIAN_PYTHON_BIN || 'python';
    const child = spawn(pythonBin, ['-m', 'meridian_core.prime_runtime'], {
      cwd: DEFAULT_CWD,
      shell: process.platform === 'win32',
      windowsHide: true,
      env: {
        ...process.env,
        PYTHONIOENCODING: 'utf-8',
      },
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
    child.stderr.on('data', (chunk) => { stderr += chunk.toString(); });
    child.on('error', (error) => {
      resolve({ ok: false, error: error.message });
    });
    child.on('close', (code) => {
      if (code !== 0) {
        resolve({ ok: false, error: stderr.trim() || `Prime logic snapshot exited with code ${code}` });
        return;
      }
      try {
        resolve(JSON.parse(stdout));
      } catch (error) {
        resolve({ ok: false, error: `Prime logic snapshot returned invalid JSON: ${error.message}` });
      }
    });
  });
}

function vulcanLogicSnapshot() {
  return new Promise((resolve) => {
    const child = spawn('python', ['-m', 'meridian_core.vulcan_logic_snapshot'], {
      cwd: DEFAULT_CWD,
      shell: process.platform === 'win32',
      windowsHide: true,
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
    child.stderr.on('data', (chunk) => { stderr += chunk.toString(); });
    child.on('error', (error) => {
      resolve({ ok: false, error: error.message });
    });
    child.on('close', (code) => {
      if (code !== 0) {
        resolve({ ok: false, error: stderr.trim() || `Vulcan logic snapshot exited with code ${code}` });
        return;
      }
      try {
        resolve({ ok: true, snapshot: JSON.parse(stdout) });
      } catch (error) {
        resolve({ ok: false, error: `Vulcan logic snapshot returned invalid JSON: ${error.message}` });
      }
    });
  });
}

function beaconLivenessSnapshot() {
  return new Promise((resolve) => {
    const child = spawn('python', ['-m', 'meridian_core.beacon_liveness_snapshot'], {
      cwd: DEFAULT_CWD,
      shell: process.platform === 'win32',
      windowsHide: true,
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
    child.stderr.on('data', (chunk) => { stderr += chunk.toString(); });
    child.on('error', (error) => {
      resolve({ ok: false, error: error.message });
    });
    child.on('close', (code) => {
      if (code !== 0) {
        resolve({ ok: false, error: stderr.trim() || `Beacon liveness snapshot exited with code ${code}` });
        return;
      }
      try {
        resolve({ ok: true, snapshot: JSON.parse(stdout) });
      } catch (error) {
        resolve({ ok: false, error: `Beacon liveness snapshot returned invalid JSON: ${error.message}` });
      }
    });
  });
}

function reviewConsoleSnapshot() {
  return new Promise((resolve) => {
    const child = spawn('python', ['-m', 'meridian_core.review_console_snapshot'], {
      cwd: DEFAULT_CWD,
      shell: process.platform === 'win32',
      windowsHide: true,
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
    child.stderr.on('data', (chunk) => { stderr += chunk.toString(); });
    child.on('error', (error) => {
      resolve({ ok: false, error: error.message });
    });
    child.on('close', (code) => {
      if (code !== 0) {
        resolve({ ok: false, error: stderr.trim() || `Review Console snapshot exited with code ${code}` });
        return;
      }
      try {
        resolve({ ok: true, snapshot: JSON.parse(stdout) });
      } catch (error) {
        resolve({ ok: false, error: `Review Console snapshot returned invalid JSON: ${error.message}` });
      }
    });
  });
}

function federationHorizonSnapshot() {
  return new Promise((resolve) => {
    const child = spawn('python', ['-m', 'meridian_core.federation_horizon_snapshot'], {
      cwd: DEFAULT_CWD,
      shell: process.platform === 'win32',
      windowsHide: true,
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
    child.stderr.on('data', (chunk) => { stderr += chunk.toString(); });
    child.on('error', (error) => {
      resolve({ ok: false, error: error.message });
    });
    child.on('close', (code) => {
      if (code !== 0) {
        resolve({ ok: false, error: stderr.trim() || `Federation horizon snapshot exited with code ${code}` });
        return;
      }
      try {
        resolve({ ok: true, snapshot: JSON.parse(stdout) });
      } catch (error) {
        resolve({ ok: false, error: `Federation horizon snapshot returned invalid JSON: ${error.message}` });
      }
    });
  });
}

function pythonJsonSnapshot(label, source) {
  return new Promise((resolve) => {
    const pythonBin = process.env.MERIDIAN_PYTHON_BIN || 'python';
    const child = spawn(pythonBin, ['-c', source], {
      cwd: DEFAULT_CWD,
      shell: false,
      windowsHide: true,
      env: {
        ...process.env,
        PYTHONIOENCODING: 'utf-8',
      },
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
    child.stderr.on('data', (chunk) => { stderr += chunk.toString(); });
    child.on('error', (error) => {
      resolve({ ok: false, error: error.message });
    });
    child.on('close', (code) => {
      if (code !== 0) {
        resolve({ ok: false, error: stderr.trim() || `${label} snapshot exited with code ${code}` });
        return;
      }
      try {
        resolve(JSON.parse(stdout));
      } catch (error) {
        resolve({ ok: false, error: `${label} snapshot returned invalid JSON: ${error.message}` });
      }
    });
  });
}

function providerBalanceSnapshot() {
  return pythonJsonSnapshot('Provider balance', String.raw`
import json
from meridian_core.provider_balance import (
    ProviderCostPressure,
    ProviderCreditStatus,
    ProviderHealth,
    ProviderPolicyState,
    ProviderQuotaState,
    ProviderRouteKind,
    ProviderRoutingOwner,
    ProviderTrustState,
    build_provider_balance_snapshot,
    build_provider_balance_summary,
)

snapshots = (
    build_provider_balance_snapshot(
        "claude",
        display_name="Claude",
        model_name="claude-sonnet-4-20250514",
        trust_state=ProviderTrustState.TRUSTED,
        health=ProviderHealth.OK,
        route_kind=ProviderRouteKind.DIRECT,
        context_budget_tokens=200000,
        prompt_budget_tokens=4000,
        current_prompt_tokens=920,
        prompt_budget_percent=23.0,
        prompt_delta_tokens=0,
        cost_pressure=ProviderCostPressure.LOW,
        quota_state=ProviderQuotaState.AVAILABLE,
        remaining_credit_label="credit available",
        credit_status=ProviderCreditStatus.AVAILABLE,
        estimated_spend_label="estimated spend low",
        notes="Primary provider ready",
        evidence_refs=("adapter:claude",),
    ),
)
summary = build_provider_balance_summary(
    snapshots,
    selected_provider="claude",
    routing_owner=ProviderRoutingOwner.RELAY,
    policy_state=ProviderPolicyState.WARNING,
    evidence_refs=("snapshot:relay-provider-balance-2026-06-07",),
)
print(json.dumps({
    "ok": True,
    "source": "meridian_core.provider_balance",
    "version": "v3-provider-balance-2026-06-07",
    "harness": "Relay / Model Harness",
    "summary": "Display-safe provider balance summary; no live account probing.",
    "display_only": True,
    "mutation_authorized": False,
    "provider_balance": summary.to_mapping(),
}))
`);
}

function goalRuntimeSnapshot() {
  return pythonJsonSnapshot('Goal runtime', String.raw`
import json
from datetime import datetime, timezone
from meridian_core.aegis import (
    V3GoalCheckpointDisciplineInput,
    evaluate_v3_goal_checkpoint_discipline_advisory,
    serialize_v3_goal_checkpoint_discipline_policy_result,
)
from meridian_core.goal_runtime import (
    BlockResumeKind,
    GoalContinuationPolicy,
    GoalObjectiveRef,
    GoalRecord,
    GoalStatus,
    HarnessWriter,
    UsageLimitResumeKind,
)

stamp = datetime(2026, 6, 7, 13, 18, tzinfo=timezone.utc)
record = GoalRecord(
    goal_id="goal-001",
    project="meridian",
    objective_text="ship the v3 goal runtime backend domain slice",
    owners=(HarnessWriter.PRIME, HarnessWriter.COMPASS),
    status=GoalStatus.ACTIVE,
    risk_tier=1,
    continuation_policy=GoalContinuationPolicy(
        max_active_attempts=3,
        cooldown_seconds=60,
        usage_limit_resume_kind=UsageLimitResumeKind.WAIT_FOR_SIGNAL,
        block_resume_kind=BlockResumeKind.MANUAL,
        proof_required_for_resume=True,
        human_gate_on_resume_kinds=(),
    ),
    created_at=stamp,
    updated_at=stamp,
    contract_version="v3-goal-runtime-2026-06-07",
    objective_ref=GoalObjectiveRef(
        id="backlog-42",
        label="ship v3 goal slice",
        source="backlog",
    ),
)
discipline_input = V3GoalCheckpointDisciplineInput(
    goal_objective_present=True,
    active_owner_lane="prime_compass",
    last_git_checkpoint_ref="git-checkpoint:goal-runtime-001",
    last_obsidian_checkpoint_ref="obsidian-checkpoint:goal-runtime-001",
    checkpoint_cadence_state="current",
    token_budget_status="within_budget",
    time_budget_status="within_budget",
    review_gate_refs=("review:goal-runtime-ready",),
    lease_gate_refs=("lease:goal-runtime-active",),
    blocker_policy_state="defined",
    proof_refs=(
        "proof:v3-parking-lot-goal-runtime",
        "proof:agentic-framework-long-term-goals",
    ),
)
discipline_result = evaluate_v3_goal_checkpoint_discipline_advisory(
    discipline_input
)
print(json.dumps({
    "ok": True,
    "source": "meridian_core.goal_runtime / meridian_core.aegis",
    "version": "v3-goal-runtime-2026-06-07",
    "harness": "Prime / Compass / Beacon / Echo / Aegis",
    "summary": "Display-safe active goal runtime record with checkpoint discipline advisory.",
    "display_only": True,
    "mutation_authorized": False,
    "goal": record.to_safe_dict(),
    "checkpoint_discipline": serialize_v3_goal_checkpoint_discipline_policy_result(
        discipline_result
    ),
}))
`);
}

function workflowDispatchStatusSnapshot() {
  return pythonJsonSnapshot('Workflow dispatch/status', String.raw`
import json
from dataclasses import fields, is_dataclass
from enum import Enum
from meridian_core.workflow_dispatch import (
    WorkflowErrorSummary,
    WorkflowFailureKind,
    WorkflowHarness,
    WorkflowResultSummary,
)

def safe(obj):
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj):
        return {field.name: safe(getattr(obj, field.name)) for field in fields(obj)}
    if isinstance(obj, tuple):
        return [safe(item) for item in obj]
    if isinstance(obj, list):
        return [safe(item) for item in obj]
    if isinstance(obj, dict):
        return {str(key): safe(value) for key, value in obj.items()}
    return obj

success = WorkflowResultSummary(
    work_order_id="wo-001",
    harness=WorkflowHarness.ATLAS,
    result_shape="AtlasResult",
    summary="one bounded result distilled",
    outputs=("hit-1",),
    proof_trail=("proof.atlas.candidates",),
    tokens_used=12,
    time_used_seconds=0.5,
)
failure = WorkflowErrorSummary(
    work_order_id="wo-002",
    harness=WorkflowHarness.ATLAS,
    failure_kind=WorkflowFailureKind.GATE_REQUIRED,
    summary="tier-three order missing gate context",
)
print(json.dumps({
    "ok": True,
    "source": "meridian_core.workflow_dispatch",
    "version": "v3-workflow-dispatch-2026-06-07",
    "harness": "Workflow Sub-agents",
    "summary": "Display-safe workflow dispatch/status summaries; heartbeat history and raw artifacts are excluded.",
    "display_only": True,
    "mutation_authorized": False,
    "workflow": {
        "success_summary": safe(success),
        "error_summary": safe(failure),
        "recent_runs": [
            {
                "run_ref": "workflow-run:atlas-success-001",
                "harness": WorkflowHarness.ATLAS.value,
                "status": "completed",
                "summary": success.summary,
                "proof_trail": list(success.proof_trail),
                "observed_at": "2026-06-07T18:58:00+00:00",
            },
            {
                "run_ref": "workflow-run:atlas-gate-002",
                "harness": WorkflowHarness.ATLAS.value,
                "status": "blocked",
                "summary": failure.summary,
                "proof_trail": list(failure.proof_trail),
                "observed_at": "2026-06-07T19:00:00+00:00",
            },
        ],
        "status_policy": {
            "dispatch_surface": "display_only",
            "heartbeat_history_visible": False,
            "raw_artifacts_visible": False,
            "tier_three_gate_required": True,
            "cadence_view": {
                "cadence_kind": "on_review_gate_clear",
                "trigger_type": "event_gate",
                "trigger_ref": "review_console_pass + gate_context",
                "next_expected_check_at": "2026-06-07T19:05:00+00:00",
                "heartbeat_policy": "history_hidden_status_only",
            },
        },
    },
}))
`);
}

function echoMemorySnapshot() {
  return pythonJsonSnapshot('Echo memory', String.raw`
import json
from datetime import datetime, timezone
from meridian_core.echo import (
    EchoRepository,
    MemoryKind,
    MemoryQuery,
    MemoryRecord,
    MemorySource,
)

repo = EchoRepository()
records = (
    MemoryRecord(
        record_id="memory-001",
        project="Meridian",
        kind=MemoryKind.DECISION,
        summary="Electron app is the Meridian UI",
        body="display body intentionally withheld",
        source=MemorySource.PRIME,
        created_at=datetime(2026, 6, 7, 12, 0, tzinfo=timezone.utc),
        importance=5,
        pinned=True,
        tags=("ui", "electron", "authority"),
    ),
    MemoryRecord(
        record_id="memory-002",
        project="Meridian",
        kind=MemoryKind.PLAN,
        summary="Backend capabilities surface as display-only panels first",
        body="display body intentionally withheld",
        source=MemorySource.REVIEW_CONSOLE,
        created_at=datetime(2026, 6, 7, 12, 30, tzinfo=timezone.utc),
        importance=4,
        pinned=False,
        tags=("ui", "backend", "proof"),
    ),
)
for record in records:
    repo.add(record)
hits = repo.query(MemoryQuery(project="Meridian", tags=("ui",), limit=5))
print(json.dumps({
    "ok": True,
    "source": "meridian_core.echo",
    "version": "v2-echo-runtime-2026-06-07",
    "harness": "Echo",
    "summary": "Display-safe Echo memory ranking sample; record bodies are withheld.",
    "display_only": True,
    "mutation_authorized": False,
    "query": {
        "project": "Meridian",
        "tags": ["ui"],
        "limit": 5,
        "include_superseded": False,
    },
    "hits": [
        {
            "record_id": hit.record.record_id,
            "kind": hit.record.kind.value,
            "summary": hit.record.summary,
            "source": hit.record.source.value,
            "importance": hit.record.importance,
            "pinned": hit.record.pinned,
            "tags": list(hit.record.tags),
            "score": hit.score,
            "reason": hit.reason,
            "created_at": hit.record.created_at.isoformat(),
        }
        for hit in hits
    ],
}))
`);
}

function atlasRetrievalSnapshot() {
  return pythonJsonSnapshot('Atlas retrieval', String.raw`
import json
from dataclasses import asdict
from meridian_core.atlas import AtlasQuery, query
from meridian_core.filemap import make_default_map

result = query(
    AtlasQuery(
        terms=("workflow", "echo", "atlas"),
        required_paths=("docs/workflow-subagent-harness-contract.md", "docs/echo-memory-contract.md"),
        limit=6,
    ),
    filemap_entries=tuple(make_default_map().all_entries()),
)
print(json.dumps({
    "ok": True,
    "source": "meridian_core.atlas",
    "version": "v2-atlas-runtime-2026-06-07",
    "harness": "Atlas",
    "summary": "Display-safe Atlas retrieval sample over FileMap and allowlisted docs.",
    "display_only": True,
    "mutation_authorized": False,
    "query": {
        "terms": ["workflow", "echo", "atlas"],
        "required_paths": ["docs/workflow-subagent-harness-contract.md", "docs/echo-memory-contract.md"],
        "limit": 6,
    },
    "hits": [
        {
            "path": hit.path,
            "title": hit.title,
            "reason": hit.reason,
            "excerpt": hit.excerpt or "",
            "source": hit.source.value,
            "score": hit.score,
        }
        for hit in result.hits
    ],
    "missing_paths": list(result.missing_paths),
    "truncated": result.truncated,
}))
`);
}

function fileMapSnapshot() {
  return pythonJsonSnapshot('FileMap', String.raw`
import json
from collections import Counter
from meridian_core.filemap import FileArea, make_default_map

fm = make_default_map()
entries = fm.all_entries()
areas = Counter(entry.area for entry in entries)
focus_areas = (
    FileArea.FILE_MAP,
    FileArea.WORKFLOW_ATLAS,
    "Architecture memory",
    "Echo memory",
    "Atlas retrieval",
    FileArea.WORKFLOW_DISPATCH,
    FileArea.GOAL_RUNTIME,
    FileArea.PROVIDER_BALANCE,
)
workflow_focus_entries = [
    entry for entry in entries
    if entry.area == FileArea.WORKFLOW_ATLAS
]
workflow_focus_paths = {entry.path for entry in workflow_focus_entries}
general_focus_entries = [
    entry for entry in entries
    if entry.path not in workflow_focus_paths
    and (entry.area in focus_areas or "echo" in entry.path.lower() or "atlas" in entry.path.lower())
]
focus_entries = (workflow_focus_entries + general_focus_entries)[:12]
print(json.dumps({
    "ok": True,
    "source": "meridian_core.filemap",
    "version": "v2-filemap-runtime-2026-06-07",
    "harness": "FileMap / Charon",
    "summary": "Display-safe FileMap registry sample using relative repository paths only.",
    "display_only": True,
    "mutation_authorized": False,
    "entry_count": len(entries),
    "with_tests_count": len(fm.with_tests()),
    "injection_summary": fm.injection_summary(),
    "area_counts": [
        {"area": area, "count": count}
        for area, count in sorted(areas.items())
    ],
    "focus_entries": [
        {
            "path": entry.path,
            "area": entry.area,
            "purpose": entry.purpose,
            "related_tests": list(entry.related_tests),
            "notes": entry.notes,
        }
        for entry in focus_entries
    ],
}))
`);
}

function aegisLogicSnapshot() {
  return pythonJsonSnapshot('Aegis logic', String.raw`
import json
from meridian_core.aegis import (
    EvidenceSeverity,
    ProofTrail,
    evidence_from_cross_check,
)
from meridian_core.cognition_policy import (
    CognitionActionType,
    evaluate_cognition_policy,
)

trail = ProofTrail()
trail.add(evidence_from_cross_check(
    "aegis-ui-001",
    "relay_dispatch",
    "prompt_packet",
    "PromptPacket proof metadata present",
    EvidenceSeverity.INFO,
))
trail.add(evidence_from_cross_check(
    "aegis-ui-002",
    "review_console",
    "human_gate",
    "Tier-three review gate requires explicit approval",
    EvidenceSeverity.ERROR,
))
result = evaluate_cognition_policy(
    3,
    CognitionActionType.BUILD,
    proof_trail=trail,
    human_gate_approved=False,
)
policy = result.policy
print(json.dumps({
    "ok": True,
    "source": "meridian_core.aegis / meridian_core.cognition_policy",
    "version": "v2-aegis-runtime-2026-06-07",
    "harness": "Aegis",
    "summary": "Display-safe Aegis proof and cognition-policy gate sample.",
    "display_only": True,
    "mutation_authorized": False,
    "raw_evidence_body_visible": False,
    "proof_trail": {
        "is_clean": trail.is_clean(),
        "evidence_count": len(trail.evidence),
        "blocking_count": len(trail.blocking()),
        "open_count": len(trail.open_findings()),
        "evidence": [
            {
                "id": evidence.id,
                "type": evidence.evidence_type.value,
                "severity": evidence.severity.value,
                "status": evidence.status.value,
                "source": evidence.source,
                "target": evidence.target,
                "summary": evidence.summary,
                "proof_blocking": evidence.is_proof_blocking(),
            }
            for evidence in trail.evidence
        ],
    },
    "cognition_policy": {
        "action_type": policy.action_type.value,
        "risk_tier": policy.risk_tier,
        "lanes": [lane.value for lane in policy.lanes],
        "requires_proof": policy.requires_proof,
        "requires_review": policy.requires_review,
        "requires_human_gate": policy.requires_human_gate,
        "reason": policy.reason,
        "decision": result.decision.value,
        "can_dispatch": result.can_dispatch,
        "blocking_reasons": list(result.blocking_reasons),
        "relay_route": {
            "risk_tier": result.relay_route.risk_tier,
            "mode": result.relay_route.mode.value,
            "reason": result.relay_route.reason,
            "requires_independence": result.relay_route.requires_independence,
            "requires_human_gate": result.relay_route.requires_human_gate,
        },
    },
}))
`);
}

function sessionCloseArchiveProofSnapshot() {
  return pythonJsonSnapshot('Session close/archive proof', String.raw`
import json
from datetime import datetime, timedelta, timezone
from meridian_core.session_lifecycle import (
    CloseArchiveWriteThroughAction,
    CommandIntent,
    GoalRuntimeCheckpointCadence,
    GoalRuntimeCheckpointSurface,
    GoalRuntimeContinuationState,
    HarnessRole,
    HealthState,
    OperationScope,
    PermissionContext,
    PermissionState,
    ProofState,
    ReviewCadenceState,
    SessionCommandPlan,
    SessionLifecycleState,
    SessionStatus,
    build_v3_goal_runtime_checkpoint_proof_packet,
    build_close_archive_write_through_proof,
    build_v2_command_plan_preview_proof,
    gather_prime_autonomy_input,
)

observed_at = datetime(2026, 6, 7, 18, 0, tzinfo=timezone.utc)
permission_context = PermissionContext(
    approved_by="prime",
    approval_scope=frozenset([OperationScope.ARCHIVE]),
    escalation_gate=False,
    escalation_reason=None,
    branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
    approved_by_secondary=None,
    unlock_expiry=observed_at + timedelta(minutes=45),
    task_scope="close-archive-write-through",
    last_permission_change=observed_at,
)
running_session = SessionLifecycleState(
    session_id="session-close-archive-proof",
    session_name="Build 2 Close Archive Proof",
    project_name="Meridian",
    project_path="project-ref:meridian",
    harness_role=HarnessRole.BUILD,
    assigned_queue_file="queue-ref:live-build-2",
    model_provider="anthropic",
    model_name="claude-opus-4-7",
    status=SessionStatus.RUNNING,
    worktree_path="worktree-ref:build-2-close-archive",
    branch_name="codex/build-2-close-archive-proof",
    current_task_id="close-archive-write-through",
    last_queue_read_at=observed_at,
    last_queue_write_at=observed_at,
    last_prompt_sent_at=observed_at,
    last_prompt_payload_size=9000,
    review_cadence_state=ReviewCadenceState.CLEARED,
    proof_state=ProofState.COMMAND_STAGED,
    health_state=HealthState.HEALTHY,
    blocker_summary=None,
    permission_context=permission_context,
)
stopped_session = SessionLifecycleState(
    **{**running_session.__dict__, "status": SessionStatus.STOPPED}
)
archive_command_plan = SessionCommandPlan(
    session_id=stopped_session.session_id,
    session_name=stopped_session.session_name,
    command_intent=CommandIntent.ARCHIVE,
    reason="Archive after durable write-through proof and review gate.",
    expected_state_transition=(SessionStatus.STOPPED, SessionStatus.ARCHIVED),
    current_state_evidence="session-close-archive-proof:stopped",
    queue_file_evidence=stopped_session.assigned_queue_file,
    worktree_evidence=stopped_session.worktree_path,
    review_gate_evidence="session-lifecycle.review-gate.pending",
    proof_requirement=ProofState.COMMAND_STAGED,
    queue_file_affected=stopped_session.assigned_queue_file,
    worktree_path_affected=stopped_session.worktree_path,
    branch_affected=stopped_session.branch_name,
    aegis_gate_result="pending",
    cadence_gate_required=True,
    cadence_gate_status=ReviewCadenceState.REVIEW_GATED,
    is_executable_now=False,
    human_approval_required=True,
    approval_context="Archive preview requires human review.",
    rollback_or_recovery_note="Preserve queue, proof, and handoff refs.",
    permission_state=stopped_session.permission_context.branch_permission_state,
    permission_operation=OperationScope.ARCHIVE,
    permission_operation_allowed=True,
)

archive_proof = build_close_archive_write_through_proof(
    stopped_session,
    CloseArchiveWriteThroughAction.ARCHIVE,
    write_through_completed=True,
    human_gate_approved=True,
    timestamp=observed_at,
)
close_proof = build_close_archive_write_through_proof(
    running_session,
    CloseArchiveWriteThroughAction.CLOSE,
    write_through_completed=True,
    human_gate_approved=False,
    timestamp=observed_at,
)
write_through_probe = build_close_archive_write_through_proof(
    running_session,
    CloseArchiveWriteThroughAction.WRITE_THROUGH,
    write_through_completed=False,
    human_gate_approved=False,
    timestamp=observed_at,
)
command_preview = build_v2_command_plan_preview_proof(
    stopped_session,
    archive_command_plan,
    timestamp=observed_at,
)
obsidian_capture = build_v3_goal_runtime_checkpoint_proof_packet(
    checkpoint_id="checkpoint-close-archive-001",
    goal_id="goal-close-archive-proof",
    goal_title="close archive durability review",
    owning_lane="spark_archive",
    owning_session_label=stopped_session.session_name,
    update_surface=GoalRuntimeCheckpointSurface.OBSIDIAN,
    checkpoint_cadence=GoalRuntimeCheckpointCadence.BEFORE_BLOCKER_HANDOFF,
    token_budget_summary="not_applicable",
    time_budget_summary="within_window",
    latest_git_ref="git-checkpoint:close-archive-proof-001",
    latest_obsidian_ref="obsidian-checkpoint:close-archive-proof-001",
    reviewer_gate_refs=("review:close-archive-proof",),
    lease_gate_refs=("lease:close-archive-proof",),
    blocker_tags=("close_archive.awaiting_human_review",),
    continuation_state=GoalRuntimeContinuationState.READY_FOR_HANDOFF,
    evidence_refs=(
        "proof:close-archive-write-through",
        "proof:obsidian-checkpoint-close-archive",
    ),
    timestamp=observed_at,
)
archive_history = gather_prime_autonomy_input(
    sessions=(stopped_session,),
    queues_by_harness={stopped_session.harness_role.value: (stopped_session.assigned_queue_file,)},
    recent_completions=("session-close-archive-proof:archived", "session-close-archive-proof:closed"),
    timestamp=observed_at,
)
print(json.dumps({
    "ok": True,
    "source": "meridian_core.session_lifecycle",
    "version": "v2-session-close-archive-proof-2026-06-07",
    "harness": "Session Lifecycle",
    "summary": "Display-safe close/archive write-through and command-plan preview proof.",
    "display_only": True,
    "mutation_authorized": False,
    "live_control_authorized": False,
    "raw_prompt_visible": False,
    "raw_worker_chat_visible": False,
    "raw_worker_session_history_visible": False,
    "pasted_transcript_body_visible": False,
    "pasted_log_body_visible": False,
    "raw_detail_body_visible": False,
    "orchestrator_intake": "compact_typed_session_state_only",
    "raw_detail_access": "fetched_on_demand_only",
    "archive_metadata": {
        "target_session_id": stopped_session.session_id,
        "session_name": stopped_session.session_name,
        "project_name": stopped_session.project_name,
        "harness_role": stopped_session.harness_role.value,
        "model_provider": stopped_session.model_provider,
        "model_name": stopped_session.model_name,
        "status": stopped_session.status.value,
        "source_session_id": running_session.session_id,
        "observed_at": observed_at.isoformat(),
    },
    "archive_sessions": [
        {
            "session_ref": session_ref,
            "status": "archived" if session_ref.endswith(":archived") else "closed",
        }
        for session_ref in archive_history.recent_completions
    ],
    "recent_close_refs": list(archive_history.recent_completions),
    "obsidian_capture": obsidian_capture.to_dict(),
    "proofs": {
        "archive": archive_proof.to_dict(),
        "close": close_proof.to_dict(),
        "write_through": write_through_probe.to_dict(),
    },
    "command_plan_preview": command_preview.to_dict(),
}))
`);
}

function voiceIoSnapshot() {
  return pythonJsonSnapshot('Voice I/O', String.raw`
import json
from bifrost.cockpit import sample_cockpit_view_model

voice = sample_cockpit_view_model().voice
print(json.dumps({
    "ok": True,
    "source": "bifrost.cockpit.VoiceIOState",
    "version": "bifrost-voice-io-display-2026-06-07",
    "harness": "Bifrost / Spark",
    "summary": "Display-safe Voice I/O state from the reviewed Bifrost view model.",
    "display_only": True,
    "mutation_authorized": False,
    "microphone_authorized": False,
    "speech_output_authorized": False,
    "read_aloud_authorized": False,
    "controls_disabled": True,
    "voice": {
        "listening": voice.listening,
        "dictating": voice.dictating,
        "thinking": voice.thinking,
        "speaking": voice.speaking,
        "muted": voice.muted,
        "blocked": voice.blocked,
        "boot_status": voice.boot_status,
        "input_mode": voice.input_mode,
        "output_mode": voice.output_mode,
        "permission_state": voice.permission_state,
        "status_call": voice.status_call,
        "last_intent_ref": voice.last_intent_ref,
    },
    "controls": [
        {"id": "input-status", "label": "Mic", "aria_disabled": True},
        {"id": "read-aloud-status", "label": "Read", "aria_disabled": True},
        {"id": "mute-status", "label": "Mute", "aria_disabled": True},
    ],
}))
`);
}

function primeAutonomyReleaseSnapshot() {
  return new Promise((resolve) => {
    const child = spawn('python', ['-m', 'meridian_core.release_autonomy_snapshot'], {
      cwd: DEFAULT_CWD,
      shell: process.platform === 'win32',
      windowsHide: true,
      env: {
        ...process.env,
        PYTHONIOENCODING: 'utf-8',
      },
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
    child.stderr.on('data', (chunk) => { stderr += chunk.toString(); });
    child.on('error', (error) => {
      resolve({ ok: false, error: error.message });
    });
    child.on('close', (code) => {
      if (code !== 0) {
        resolve({ ok: false, error: stderr.trim() || `Prime Autonomy Release snapshot exited with code ${code}` });
        return;
      }
      try {
        resolve({ ok: true, snapshot: JSON.parse(stdout) });
      } catch (error) {
        resolve({ ok: false, error: `Prime Autonomy Release snapshot returned invalid JSON: ${error.message}` });
      }
    });
  });
}

function parseGitWorktrees(stdout) {
  const records = [];
  let current = null;
  for (const line of String(stdout || '').split(/\r?\n/)) {
    if (line.startsWith('worktree ')) {
      if (current) records.push(current);
      current = { path: line.slice('worktree '.length), branch: '', head: '' };
      continue;
    }
    if (!current) continue;
    if (line.startsWith('HEAD ')) current.head = line.slice('HEAD '.length);
    if (line.startsWith('branch ')) current.branch = line.slice('branch '.length);
  }
  if (current) records.push(current);
  return records;
}

function sessionTargetFromWorktree(record) {
  const worktreePath = String(record?.path || '');
  const normalized = worktreePath.replaceAll('\\', '/');
  if (!/\/Meridian-Worktrees\//i.test(normalized)) return null;
  const sessionId = normalized.split('/').filter(Boolean).pop();
  if (!sessionId) return null;
  const branch = String(record?.branch || '').replace(/^refs\/heads\//, '');
  const sessionText = `${sessionId} ${branch}`;
  const state = /review|codex-reviews/i.test(sessionText)
    ? 'hidden'
    : (/(test[-_ ]?waiting|waiting[-_ ]?for[-_ ]?test|\bwaiting\b)/i.test(sessionText) ? 'waiting' : 'live');
  return {
    sessionId,
    sessionName: sessionId.replace(/[-_]+/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase()),
    projectName: 'Meridian',
    status: state,
    routable: true,
    cwd: worktreePath,
    branch,
    head: String(record?.head || ''),
  };
}

function userSessionTargets() {
  return new Promise((resolve) => {
    const child = spawn('git', ['worktree', 'list', '--porcelain'], {
      cwd: DEFAULT_CWD,
      shell: process.platform === 'win32',
      windowsHide: true,
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
    child.stderr.on('data', (chunk) => { stderr += chunk.toString(); });
    child.on('error', (error) => {
      resolve({ ok: false, error: error.message, sessions: [] });
    });
    child.on('close', (code) => {
      if (code !== 0) {
        resolve({ ok: false, error: stderr.trim() || `git worktree exited with code ${code}`, sessions: [] });
        return;
      }
      const sessions = parseGitWorktrees(stdout)
        .map(sessionTargetFromWorktree)
        .filter(Boolean)
        .sort((left, right) => left.projectName.localeCompare(right.projectName) || left.sessionName.localeCompare(right.sessionName));
      resolve({
        ok: true,
        service: 'meridian-model-bridge',
        version: BRIDGE_VERSION,
        capabilities: BRIDGE_CAPABILITIES,
        sessions,
      });
    });
  });
}

async function sessionTargetById(sessionId) {
  const snapshot = await userSessionTargets();
  if (!snapshot.ok) return null;
  return snapshot.sessions.find((session) => session.sessionId === sessionId && session.routable) || null;
}

function runModel({ backend, prompt, cwd, transcript }) {
  return new Promise((resolve) => {
    let command;
    const sessionPrompt = promptWithVisibleSession(prompt, transcript);
    try {
      command = commandForBackend(backend, sessionPrompt.prompt);
    } catch (error) {
      resolve({ ok: false, text: '', error: error.message });
      return;
    }

    const child = spawnModelProcess(command, cwd);

    let stdout = '';
    let stderr = '';
    let settled = false;
    let timeout = null;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      if (timeout) clearTimeout(timeout);
      resolve(result);
    };
    child.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
    child.stderr.on('data', (chunk) => { stderr += chunk.toString(); });
    if (command.stdin !== null && command.stdin !== undefined) {
      child.stdin.end(command.stdin);
    }
    child.on('error', (error) => {
      finish({
        ok: false,
        text: stdout.trim(),
        error: classifySetupError(backend, error.message),
        model: command.model,
        setupRequired: true,
        sessionContextEntries: sessionPrompt.entries,
        sessionContextChars: sessionPrompt.chars,
      });
    });
    timeout = setTimeout(() => {
      child.kill();
      finish({
        ok: false,
        text: stdout.trim(),
        error: 'Model call timed out',
        model: command.model,
        setupRequired: false,
        sessionContextEntries: sessionPrompt.entries,
        sessionContextChars: sessionPrompt.chars,
      });
    }, Number(process.env.MERIDIAN_MODEL_TIMEOUT_MS || 60000));

    child.on('close', (code) => {
      const rawError = stderr.trim() || `Process exited with code ${code}`;
      finish({
        ok: code === 0,
        text: normalizeModelText(backend, stdout),
        error: code === 0 ? null : classifySetupError(backend, rawError),
        model: command.model,
        setupRequired: code === 0 ? false : needsSetup(backend, rawError),
        sessionContextEntries: sessionPrompt.entries,
        sessionContextChars: sessionPrompt.chars,
      });
    });
  });
}

const server = http.createServer(async (req, res) => {
  if (req.method === 'OPTIONS') {
    if (blockDisallowedOrigin(req, res)) return;
    sendJson(res, 204, {}, req);
    return;
  }

  if (blockDisallowedOrigin(req, res)) return;

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.health) {
    sendJson(res, 200, {
      ok: true,
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.models) {
    sendJson(res, 200, await modelStatus(), req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.relayLogic) {
    const snapshot = await relayLogicSnapshot();
    sendJson(res, snapshot.ok ? 200 : 500, {
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      ...snapshot,
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.relayEvidence) {
    const snapshot = await relayEvidenceSnapshot();
    sendJson(res, snapshot.ok ? 200 : 500, {
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      ...snapshot,
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.primeLogic) {
    const snapshot = await primeLogicSnapshot();
    sendJson(res, snapshot.ok ? 200 : 500, {
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      ...snapshot,
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.compassLogic) {
    const result = await compassLogicSnapshot();
    sendJson(res, result.ok ? 200 : 500, {
      ok: result.ok,
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      ...(result.ok ? { ...result.snapshot } : { error: result.error }),
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.vulcanLogic) {
    const result = await vulcanLogicSnapshot();
    sendJson(res, result.ok ? 200 : 500, {
      ok: result.ok,
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      ...(result.ok ? { ...result.snapshot } : { error: result.error }),
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.beaconLiveness) {
    const result = await beaconLivenessSnapshot();
    sendJson(res, result.ok ? 200 : 500, {
      ok: result.ok,
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      ...(result.ok ? { ...result.snapshot } : { error: result.error }),
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.reviewConsole) {
    const result = await reviewConsoleSnapshot();
    sendJson(res, result.ok ? 200 : 500, {
      ok: result.ok,
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      ...(result.ok ? { ...result.snapshot } : { error: result.error }),
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.federationHorizon) {
    const result = await federationHorizonSnapshot();
    sendJson(res, result.ok ? 200 : 500, {
      ok: result.ok,
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      ...(result.ok ? { ...result.snapshot } : { error: result.error }),
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.providerBalance) {
    const snapshot = await providerBalanceSnapshot();
    sendJson(res, snapshot.ok ? 200 : 500, {
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      ...snapshot,
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.goalRuntime) {
    const snapshot = await goalRuntimeSnapshot();
    sendJson(res, snapshot.ok ? 200 : 500, {
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      ...snapshot,
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.workflowDispatchStatus) {
    const snapshot = await workflowDispatchStatusSnapshot();
    sendJson(res, snapshot.ok ? 200 : 500, {
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      ...snapshot,
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.echoMemory) {
    const snapshot = await echoMemorySnapshot();
    sendJson(res, snapshot.ok ? 200 : 500, {
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      ...snapshot,
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.atlasRetrieval) {
    const snapshot = await atlasRetrievalSnapshot();
    sendJson(res, snapshot.ok ? 200 : 500, {
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      ...snapshot,
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.fileMap) {
    const snapshot = await fileMapSnapshot();
    sendJson(res, snapshot.ok ? 200 : 500, {
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      ...snapshot,
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.aegisLogic) {
    const snapshot = await aegisLogicSnapshot();
    sendJson(res, snapshot.ok ? 200 : 500, {
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      ...snapshot,
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.sessionCloseArchiveProof) {
    const snapshot = await sessionCloseArchiveProofSnapshot();
    sendJson(res, snapshot.ok ? 200 : 500, {
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      ...snapshot,
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.voiceIo) {
    const snapshot = await voiceIoSnapshot();
    sendJson(res, snapshot.ok ? 200 : 500, {
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      ...snapshot,
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.primeAutonomyRelease) {
    const result = await primeAutonomyReleaseSnapshot();
    sendJson(res, result.ok ? 200 : 500, {
      ok: result.ok,
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      ...(result.ok ? { ...result.snapshot } : { error: result.error }),
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.userSessions) {
    const snapshot = await userSessionTargets();
    sendJson(res, snapshot.ok ? 200 : 500, snapshot, req);
    return;
  }

  if (req.method === 'GET' && req.url === BRIDGE_ROUTES.recentCalls) {
    sendJson(res, 200, {
      ok: true,
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      calls: recentCalls.slice().reverse(),
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url.startsWith(BRIDGE_ROUTES.callResult)) {
    const requestUrl = new URL(req.url, `http://${HOST}:${PORT}`);
    const requestId = String(requestUrl.searchParams.get('requestId') || '');
    const result = resultForRequestId(requestId);
    if (!result) {
      sendJson(res, 404, { ok: false, error: 'Result not found' }, req);
      return;
    }
    sendJson(res, 200, {
      ok: true,
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      requestId,
      result,
    }, req);
    return;
  }

  if (req.method === 'POST' && req.url === BRIDGE_ROUTES.restart) {
    if (!beginRestartRequest()) {
      sendJson(res, 202, { ok: true, restarting: true, alreadyRestarting: true }, req);
      return;
    }
    sendJson(res, 202, { ok: true, restarting: true }, req);
    setTimeout(restartBridge, 25);
    return;
  }

  if (req.method === 'POST' && req.url === BRIDGE_ROUTES.message) {
    try {
      const body = JSON.parse(await readBody(req));
      const backend = String(body.backend || '').toLowerCase();
      const requestedBackend = String(body.requestedBackend || backend || '').toLowerCase();
      const channel = String(body.channel || 'prime').toLowerCase();
      const projectContext = String(body.projectContext || 'Meridian').trim() || 'Meridian';
      const requestId = String(body.requestId || '');
      const prompt = String(body.prompt || '').trim();
      const transcript = Array.isArray(body.transcript) ? body.transcript : [];
      const sessionTargetId = String(body.sessionTargetId || '');
      let sessionTarget = null;
      let cwd = body.cwd ? String(body.cwd) : DEFAULT_CWD;
      if (!prompt) {
        sendJson(res, 400, { ok: false, error: 'Missing prompt' }, req);
        return;
      }
      if (channel === 'user') {
        sessionTarget = sessionTargetId ? await sessionTargetById(sessionTargetId) : null;
        if (!sessionTarget) {
          sendJson(res, 409, { ok: false, text: '', error: 'Select a live User Session target before sending.', setupRequired: false }, req);
          return;
        }
        cwd = sessionTarget.cwd;
      }
      const started = Date.now();
      const result = await runModel({ backend, prompt, cwd, transcript });
      result.requestedBackend = requestedBackend;
      result.backend = backend;
      result.channel = channel;
      result.projectContext = projectContext;
      result.requestId = requestId;
      result.durationMs = Date.now() - started;
      result.sessionTarget = sessionTarget ? {
        sessionId: sessionTarget.sessionId,
        sessionName: sessionTarget.sessionName,
        cwd: sessionTarget.cwd,
      } : null;
      rememberCall({
        requestId,
        channel,
        requestedBackend,
        backend,
        model: result.model,
        ok: result.ok,
        setupRequired: Boolean(result.setupRequired),
        durationMs: result.durationMs,
        sessionContextEntries: result.sessionContextEntries || 0,
        sessionContextChars: result.sessionContextChars || 0,
        sessionTargetId: sessionTarget?.sessionId || '',
        projectContext,
      });
      rememberResult({
        requestId,
        channel,
        requestedBackend,
        backend,
        model: result.model,
        ok: result.ok,
        setupRequired: Boolean(result.setupRequired),
        text: result.text || '',
        error: result.error || null,
        durationMs: result.durationMs,
        sessionContextEntries: result.sessionContextEntries || 0,
        sessionContextChars: result.sessionContextChars || 0,
        sessionTargetId: sessionTarget?.sessionId || '',
        projectContext,
      });
      sendJson(res, result.ok ? 200 : 500, result, req);
    } catch (error) {
      sendJson(res, 500, { ok: false, text: '', error: error.message }, req);
    }
    return;
  }

  sendJson(res, 404, { ok: false, error: 'Not found' }, req);
});

server.listen(PORT, HOST, () => {
  console.log(`[meridian-model-bridge] http://${HOST}:${PORT}`);
});
