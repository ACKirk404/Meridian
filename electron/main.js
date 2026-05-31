'use strict';

// Meridian — V1 Bifrost cockpit Electron app shell.
//
// Opens a desktop window that loads the locally generated Bifrost cockpit HTML
// preview file. The preview HTML is produced by `python bifrost/preview.py`
// (see the npm `preview` script). This shell does not embed any business
// logic; it is strictly a viewer for the static Bifrost cockpit document.
//
// Secure defaults:
//   - loadFile() of a local path only (no remote URL load).
//   - contextIsolation: true and nodeIntegration: false in the renderer.
//   - sandbox: true and webSecurity: true.
//   - will-navigate is blocked except to the local preview file.
//   - window.open / target=_blank is denied (V1 cockpit is observation-only).

const { app, BrowserWindow } = require('electron');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const PREVIEW_FILE = path.resolve(__dirname, '..', 'bifrost', 'preview.html');
const PREVIEW_URL = pathToFileURL(PREVIEW_FILE).toString();

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
    if (navUrl !== PREVIEW_URL) {
      event.preventDefault();
    }
  });

  win.webContents.setWindowOpenHandler(() => {
    return { action: 'deny' };
  });

  win.loadFile(PREVIEW_FILE);
  return win;
}

app.whenReady().then(() => {
  createCockpitWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createCockpitWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

module.exports = {
  createCockpitWindow,
  PREVIEW_FILE,
  PREVIEW_URL,
};
