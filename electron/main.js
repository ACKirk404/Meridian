'use strict';

// Meridian cockpit Electron app shell.
//
// Owns the local app runtime: starts the Meridian model bridge when needed,
// opens a desktop window for the cockpit UI, and shuts down only bridge
// processes that this app launched.
//
// Secure defaults:
//   - loadFile() of a local path only (no remote URL load).
//   - contextIsolation: true and nodeIntegration: false in the renderer.
//   - sandbox: true and webSecurity: true.
//   - will-navigate is blocked except to the local UI file.
//   - window.open / target=_blank is denied (V1 cockpit is observation-only).

const { app, BrowserWindow } = require('electron');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { pathToFileURL } = require('node:url');

const UI_FILE = path.resolve(__dirname, '..', 'index.html');
const UI_URL = pathToFileURL(UI_FILE).toString();
const BRIDGE_HOST = process.env.MERIDIAN_MODEL_HOST || '127.0.0.1';
const BRIDGE_PORT = Number(process.env.MERIDIAN_MODEL_PORT || 8767);
const BRIDGE_PROTOCOL = 'http';
const BRIDGE_HEALTH_URL = `${BRIDGE_PROTOCOL}://${BRIDGE_HOST}:${BRIDGE_PORT}/bridge/health`;
const BRIDGE_SCRIPT = path.resolve(__dirname, '..', 'scripts', 'meridian-model-bridge.js');

let ownedBridgeProcess = null;

function createCockpitWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 640,
    title: 'Meridian Cockpit',
    backgroundColor: '#0f111a',
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
    },
  });

  win.webContents.on('will-navigate', (event, navUrl) => {
    if (navUrl !== UI_URL) {
      event.preventDefault();
    }
  });

  win.webContents.setWindowOpenHandler(() => {
    return { action: 'deny' };
  });

  win.loadFile(UI_FILE);
  return win;
}

function getBridgeLogPaths(electronApp = app) {
  const logDir = path.join(electronApp.getPath('userData'), 'logs');
  return {
    logDir,
    stdoutPath: path.join(logDir, 'meridian-model-bridge.stdout.log'),
    stderrPath: path.join(logDir, 'meridian-model-bridge.stderr.log'),
  };
}

function bridgeHealthCheck({ request = http.get, timeoutMs = 700 } = {}) {
  return new Promise((resolve) => {
    const req = request(BRIDGE_HEALTH_URL, (res) => {
      let body = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => {
        body += chunk;
      });
      res.on('end', () => {
        if (res.statusCode !== 200) {
          resolve(false);
          return;
        }
        try {
          const parsed = JSON.parse(body);
          resolve(Boolean(parsed.ok));
        } catch {
          resolve(false);
        }
      });
    });
    req.on('error', () => resolve(false));
    req.setTimeout(timeoutMs, () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitForBridgeReady({ attempts = 30, intervalMs = 200, healthCheck = bridgeHealthCheck } = {}) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    if (await healthCheck()) return true;
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  return false;
}

async function ensureModelBridge({
  electronApp = app,
  healthCheck = bridgeHealthCheck,
  spawnProcess = spawn,
  bridgeScript = BRIDGE_SCRIPT,
  nodeRuntime = process.execPath,
} = {}) {
  if (await healthCheck()) {
    return { started: false, alreadyRunning: true, process: null };
  }

  const { logDir, stdoutPath, stderrPath } = getBridgeLogPaths(electronApp);
  fs.mkdirSync(logDir, { recursive: true });
  const stdout = fs.openSync(stdoutPath, 'a');
  const stderr = fs.openSync(stderrPath, 'a');
  const child = spawnProcess(nodeRuntime, [bridgeScript], {
    cwd: path.resolve(__dirname, '..'),
    detached: false,
    env: {
      ...process.env,
      ELECTRON_RUN_AS_NODE: '1',
      MERIDIAN_MODEL_HOST: BRIDGE_HOST,
      MERIDIAN_MODEL_PORT: String(BRIDGE_PORT),
    },
    stdio: ['ignore', stdout, stderr],
    windowsHide: true,
  });

  ownedBridgeProcess = child;
  child.once('exit', () => {
    if (ownedBridgeProcess === child) ownedBridgeProcess = null;
  });

  const ready = await waitForBridgeReady({ healthCheck });
  return { started: true, alreadyRunning: false, ready, process: child, stdoutPath, stderrPath };
}

function stopOwnedBridge() {
  if (!ownedBridgeProcess || ownedBridgeProcess.killed) return false;
  const child = ownedBridgeProcess;
  ownedBridgeProcess = null;
  child.kill();
  return true;
}

async function startMeridianApp() {
  await ensureModelBridge();
  createCockpitWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createCockpitWindow();
    }
  });
}

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  stopOwnedBridge();
});

if (require.main === module) {
  app.whenReady().then(startMeridianApp);
}

module.exports = {
  BRIDGE_HEALTH_URL,
  BRIDGE_SCRIPT,
  createCockpitWindow,
  ensureModelBridge,
  getBridgeLogPaths,
  startMeridianApp,
  stopOwnedBridge,
  UI_FILE,
  UI_URL,
  waitForBridgeReady,
};
