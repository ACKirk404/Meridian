'use strict';

const http = require('node:http');
const { spawn } = require('node:child_process');

const HOST = process.env.MERIDIAN_MODEL_HOST || '127.0.0.1';
const PORT = Number(process.env.MERIDIAN_MODEL_PORT || 8767);
const DEFAULT_CWD = process.env.MERIDIAN_MODEL_CWD || process.cwd();
const RECENT_CALLS_LIMIT = Number(process.env.MERIDIAN_MODEL_RECENT_CALLS || 40);
const SESSION_TRANSCRIPT_LIMIT = Number(process.env.MERIDIAN_SESSION_TRANSCRIPT_LIMIT || 12);
const SESSION_TRANSCRIPT_CHAR_LIMIT = Number(process.env.MERIDIAN_SESSION_TRANSCRIPT_CHAR_LIMIT || 12000);
const BRIDGE_VERSION = 'visible-transcript-v1';
const BRIDGE_CAPABILITIES = {
  visibleTranscriptContext: true,
  recentCallContextDiagnostics: true,
  samePortRestart: true,
};
const ALLOWED_ORIGINS = new Set((process.env.MERIDIAN_MODEL_ALLOWED_ORIGINS || 'http://127.0.0.1:5500,http://localhost:5500,null')
  .split(',')
  .map((origin) => origin.trim())
  .filter(Boolean));
const recentCalls = [];

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
  const setupOk = samples.every(Boolean) && setupFlags[0] && setupFlags[1] && !setupFlags[2];
  const capabilitiesOk = BRIDGE_CAPABILITIES.visibleTranscriptContext && BRIDGE_CAPABILITIES.samePortRestart;
  const originOk = isAllowedOrigin({ headers: { origin: 'http://127.0.0.1:5500' } }) && !isAllowedOrigin({ headers: { origin: 'https://example.com' } });
  console.log(JSON.stringify({ ok: setupOk && contextOk && capabilitiesOk && originOk, samples, setupFlags, contextOk, capabilitiesOk, originOk }, null, 2));
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
      args: ['-p', prompt],
      stdin: null,
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

  if (req.method === 'GET' && req.url === '/api/recent-calls') {
    sendJson(res, 200, { ok: true, calls: recentCalls.slice().reverse() }, req);
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
      const cwd = body.cwd ? String(body.cwd) : DEFAULT_CWD;
      if (!prompt) {
        sendJson(res, 400, { ok: false, error: 'Missing prompt' }, req);
        return;
      }
      const started = Date.now();
      const result = await runModel({ backend, prompt, cwd, transcript });
      result.requestedBackend = requestedBackend;
      result.channel = channel;
      result.requestId = requestId;
      result.durationMs = Date.now() - started;
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
