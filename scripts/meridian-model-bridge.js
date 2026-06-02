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
const BRIDGE_VERSION = 'visible-transcript-v1';
const BRIDGE_CAPABILITIES = {
  visibleTranscriptContext: true,
  recentCallContextDiagnostics: true,
  samePortRestart: true,
  requestResultRecovery: true,
  relayLogicSnapshot: true,
  userSessionTargets: true,
};
const ALLOWED_ORIGINS = new Set((process.env.MERIDIAN_MODEL_ALLOWED_ORIGINS || 'http://127.0.0.1:5500,http://localhost:5500,null')
  .split(',')
  .map((origin) => origin.trim())
  .filter(Boolean));
const recentCalls = [];
const recentResults = [];

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
  const capabilitiesOk = BRIDGE_CAPABILITIES.visibleTranscriptContext && BRIDGE_CAPABILITIES.samePortRestart && BRIDGE_CAPABILITIES.requestResultRecovery && BRIDGE_CAPABILITIES.relayLogicSnapshot;
  const sampleSession = sessionTargetFromWorktree({
    path: 'C:\\Users\\scott\\Code\\Meridian-Worktrees\\build-5-bifrost',
    branch: 'refs/heads/worktree-build-5-bifrost',
    head: 'abc123',
  });
  const sessionTargetsOk = BRIDGE_CAPABILITIES.userSessionTargets && sampleSession?.sessionId === 'build-5-bifrost' && sampleSession.routable;
  const originOk = isAllowedOrigin({ headers: { origin: 'http://127.0.0.1:5500' } }) && !isAllowedOrigin({ headers: { origin: 'https://example.com' } });
  console.log(JSON.stringify({ ok: setupOk && contextOk && maxJsonOk && resultRecoveryOk && capabilitiesOk && sessionTargetsOk && originOk, samples, setupFlags, contextOk, maxJsonOk, resultRecoveryOk, capabilitiesOk, sessionTargetsOk, originOk }, null, 2));
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
  const state = /review|codex-reviews/i.test(sessionId) ? 'hidden' : 'live';
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

  if (req.method === 'GET' && req.url === '/health') {
    sendJson(res, 200, {
      ok: true,
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === '/api/models') {
    sendJson(res, 200, await modelStatus(), req);
    return;
  }

  if (req.method === 'GET' && req.url === '/api/relay-logic') {
    const snapshot = await relayLogicSnapshot();
    sendJson(res, snapshot.ok ? 200 : 500, {
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      ...snapshot,
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url === '/api/user-sessions') {
    const snapshot = await userSessionTargets();
    sendJson(res, snapshot.ok ? 200 : 500, snapshot, req);
    return;
  }

  if (req.method === 'GET' && req.url === '/api/recent-calls') {
    sendJson(res, 200, {
      ok: true,
      service: 'meridian-model-bridge',
      version: BRIDGE_VERSION,
      capabilities: BRIDGE_CAPABILITIES,
      calls: recentCalls.slice().reverse(),
    }, req);
    return;
  }

  if (req.method === 'GET' && req.url.startsWith('/api/call-result')) {
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

  if (req.method === 'POST' && req.url === '/api/restart') {
    sendJson(res, 202, { ok: true, restarting: true }, req);
    setTimeout(restartBridge, 25);
    return;
  }

  if (req.method === 'POST' && req.url === '/api/message') {
    try {
      const body = JSON.parse(await readBody(req));
      const backend = String(body.backend || '').toLowerCase();
      const requestedBackend = String(body.requestedBackend || backend || '').toLowerCase();
      const channel = String(body.channel || 'prime').toLowerCase();
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
      result.channel = channel;
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
