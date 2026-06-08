'use strict';

const { app, BrowserWindow, Tray, Menu, nativeImage, shell } = require('electron');
const path = require('path');
const store = require('./store');
const ipc = require('./ipc');

let mainWindow = null;
let tray = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1180,
    height: 820,
    minWidth: 880,
    minHeight: 640,
    backgroundColor: '#0E0E10',
    title: 'ARIA',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));
  mainWindow.once('ready-to-show', () => mainWindow.show());

  // External links open in the system browser, not inside the app.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function createTray() {
  // 1x1 transparent placeholder so the app runs before a real icon is added.
  const icon = nativeImage.createFromDataURL(
    'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
  );
  try {
    tray = new Tray(icon);
    tray.setToolTip('ARIA — desktop assistant');
    tray.setContextMenu(
      Menu.buildFromTemplate([
        { label: 'Show ARIA', click: () => (mainWindow ? mainWindow.show() : createWindow()) },
        { type: 'separator' },
        { label: 'Quit', click: () => app.quit() },
      ])
    );
    tray.on('click', () => (mainWindow ? mainWindow.show() : createWindow()));
  } catch {
    // Tray unavailable on some headless/Linux setups — non-fatal.
  }
}

app.whenReady().then(() => {
  store.init();
  ipc.register();
  createWindow();
  createTray();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  // Keep running in the tray on macOS; quit elsewhere.
  if (process.platform !== 'darwin') app.quit();
});
