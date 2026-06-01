'use strict';

const http = require('node:http');
const { spawn } = require('node:child_process');

const HOST = process.env.MERIDIAN_MODEL_HOST || '127.0.0.1';
const PORT = Number(process.env.MERIDIAN_MODEL_PORT || 8767);
const DEFAULT_CWD = process.env.MERIDIAN_MODEL_CWD || process.cwd();

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
  console.log(JSON.stringify({ ok: samples.every(Boolean) && setupFlags[0] && setupFlags[1] && !setupFlags[2], samples, setupFlags }, null, 2));
  process.exit(0);
}

function sendJson(res, status, body) {
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'content-type',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
  });
  res.end(JSON.stringify(body));
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

function runModel({ backend, prompt, cwd }) {
  return new Promise((resolve) => {
    let command;
    try {
      command = commandForBackend(backend, prompt);
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
      finish({ ok: false, text: stdout.trim(), error: classifySetupError(backend, error.message), model: command.model, setupRequired: true });
    });
    timeout = setTimeout(() => {
      child.kill();
      finish({ ok: false, text: stdout.trim(), error: 'Model call timed out', model: command.model, setupRequired: false });
    }, Number(process.env.MERIDIAN_MODEL_TIMEOUT_MS || 60000));

    child.on('close', (code) => {
      const rawError = stderr.trim() || `Process exited with code ${code}`;
      finish({
        ok: code === 0,
        text: normalizeModelText(backend, stdout),
        error: code === 0 ? null : classifySetupError(backend, rawError),
        model: command.model,
        setupRequired: code === 0 ? false : needsSetup(backend, rawError),
      });
    });
  });
}

const server = http.createServer(async (req, res) => {
  if (req.method === 'OPTIONS') {
    sendJson(res, 204, {});
    return;
  }

  if (req.method === 'GET' && req.url === '/health') {
    sendJson(res, 200, { ok: true, service: 'meridian-model-bridge' });
    return;
  }

  if (req.method === 'GET' && req.url === '/api/models') {
    sendJson(res, 200, await modelStatus());
    return;
  }

  if (req.method === 'POST' && req.url === '/api/message') {
    try {
      const body = JSON.parse(await readBody(req));
      const backend = String(body.backend || '').toLowerCase();
      const requestedBackend = String(body.requestedBackend || backend || '').toLowerCase();
      const prompt = String(body.prompt || '').trim();
      const cwd = body.cwd ? String(body.cwd) : DEFAULT_CWD;
      if (!prompt) {
        sendJson(res, 400, { ok: false, error: 'Missing prompt' });
        return;
      }
      const result = await runModel({ backend, prompt, cwd });
      result.requestedBackend = requestedBackend;
      sendJson(res, result.ok ? 200 : 500, result);
    } catch (error) {
      sendJson(res, 500, { ok: false, text: '', error: error.message });
    }
    return;
  }

  sendJson(res, 404, { ok: false, error: 'Not found' });
});

server.listen(PORT, HOST, () => {
  console.log(`[meridian-model-bridge] http://${HOST}:${PORT}`);
});
