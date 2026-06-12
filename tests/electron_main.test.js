'use strict';

const assert = require('node:assert/strict');
const EventEmitter = require('node:events');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const mainPath = path.resolve(__dirname, '..', 'electron', 'main.js');
const originalLoad = Module._load;

function loadMainWithElectronMock() {
  const electronMock = {
    app: {
      getPath(name) {
        assert.equal(name, 'userData');
        return fs.mkdtempSync(path.join(os.tmpdir(), 'meridian-electron-test-'));
      },
      on() {},
      quit() {},
      whenReady() {
        return Promise.resolve();
      },
    },
    BrowserWindow: class BrowserWindow {
      constructor(options) {
        this.options = options;
        this.webContents = {
          on() {},
          setWindowOpenHandler() {},
        };
      }

      loadFile(file) {
        this.loadedFile = file;
      }

      static getAllWindows() {
        return [];
      }
    },
  };

  delete require.cache[mainPath];
  Module._load = function loadWithElectronMock(request, parent, isMain) {
    if (request === 'electron') return electronMock;
    return originalLoad.call(this, request, parent, isMain);
  };
  try {
    return require(mainPath);
  } finally {
    Module._load = originalLoad;
  }
}

function fakeChildProcess() {
  const child = new EventEmitter();
  child.killed = false;
  child.kill = () => {
    child.killed = true;
    child.emit('exit', 0);
    return true;
  };
  return child;
}

test('runtime exports stable local UI and bridge paths', () => {
  const main = loadMainWithElectronMock();

  assert.equal(main.BRIDGE_HEALTH_URL, 'http://127.0.0.1:8767/bridge/health');
  assert.equal(path.basename(main.UI_FILE), 'index.html');
  assert.equal(path.basename(main.BRIDGE_SCRIPT), 'meridian-model-bridge.js');
  assert.match(main.UI_URL, /^file:\/\//);
});

test('ensureModelBridge reuses an already running bridge', async () => {
  const main = loadMainWithElectronMock();
  let spawnCount = 0;

  const result = await main.ensureModelBridge({
    healthCheck: async () => true,
    spawnProcess: () => {
      spawnCount += 1;
      return fakeChildProcess();
    },
  });

  assert.deepEqual(result, { started: false, alreadyRunning: true, process: null });
  assert.equal(spawnCount, 0);
});

test('ensureModelBridge starts the bridge with Electron-as-Node and log files', async () => {
  const main = loadMainWithElectronMock();
  const tempUserData = fs.mkdtempSync(path.join(os.tmpdir(), 'meridian-runtime-'));
  const electronApp = {
    getPath(name) {
      assert.equal(name, 'userData');
      return tempUserData;
    },
  };
  const child = fakeChildProcess();
  const calls = [];
  let healthChecks = 0;

  const result = await main.ensureModelBridge({
    electronApp,
    bridgeScript: 'C:\\Meridian\\scripts\\meridian-model-bridge.js',
    nodeRuntime: 'C:\\Meridian\\Meridian.exe',
    healthCheck: async () => {
      healthChecks += 1;
      return healthChecks > 1;
    },
    spawnProcess: (bin, args, options) => {
      calls.push({ bin, args, options });
      return child;
    },
  });

  assert.equal(result.started, true);
  assert.equal(result.alreadyRunning, false);
  assert.equal(result.ready, true);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].bin, 'C:\\Meridian\\Meridian.exe');
  assert.deepEqual(calls[0].args, ['C:\\Meridian\\scripts\\meridian-model-bridge.js']);
  const pathKey = Object.keys(calls[0].options.env).find((key) => key.toLowerCase() === 'path');
  const childPath = calls[0].options.env[pathKey].toLowerCase();

  assert.equal(calls[0].options.env.ELECTRON_RUN_AS_NODE, '1');
  assert.equal(calls[0].options.env.MERIDIAN_MODEL_HOST, '127.0.0.1');
  assert.equal(calls[0].options.env.MERIDIAN_MODEL_PORT, '8767');
  assert.equal(path.basename(calls[0].options.env.MERIDIAN_MODEL_CWD), 'Meridian');
  assert.match(childPath, /appdata\\roaming\\npm/);
  assert.match(childPath, /microsoft\\windowsapps/);
  assert.equal(calls[0].options.windowsHide, true);
  assert.equal(fs.existsSync(path.join(tempUserData, 'logs')), true);

  assert.equal(main.stopOwnedBridge(), true);
  assert.equal(child.killed, true);
  assert.equal(main.stopOwnedBridge(), false);
});

test('bridgeRuntimePath preserves existing PATH entries and appends Windows CLI locations', () => {
  const main = loadMainWithElectronMock();
  const result = main.bridgeRuntimePath({
    Path: 'C:\\Existing',
    APPDATA: 'C:\\Users\\scott\\AppData\\Roaming',
    LOCALAPPDATA: 'C:\\Users\\scott\\AppData\\Local',
  });

  assert.equal(result.pathKey, 'Path');
  assert.equal(result.value.split(path.delimiter)[0], 'C:\\Existing');
  assert.match(result.value, /AppData\\Roaming\\npm/);
  assert.match(result.value, /Microsoft\\WindowsApps/);
});

test('resolveModelCwd maps a portable dist launch back to the repo root', () => {
  const main = loadMainWithElectronMock();
  const repoRoot = path.resolve(__dirname, '..');
  const distDir = path.join(repoRoot, 'dist');
  const resolved = main.resolveModelCwd({ PORTABLE_EXECUTABLE_DIR: distDir }, 'C:\\Temp\\extracted\\resources\\app');

  assert.equal(resolved, repoRoot);
});

test('createCockpitWindow keeps the renderer sandboxed', () => {
  const main = loadMainWithElectronMock();
  const win = main.createCockpitWindow();

  assert.equal(win.options.title, 'Meridian Cockpit');
  assert.equal(win.options.webPreferences.contextIsolation, true);
  assert.equal(win.options.webPreferences.nodeIntegration, false);
  assert.equal(win.options.webPreferences.sandbox, true);
  assert.equal(win.loadedFile, main.UI_FILE);
});
