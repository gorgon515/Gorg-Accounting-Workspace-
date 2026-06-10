'use strict';

const { app, BrowserWindow, Tray, Menu, nativeImage, shell, Notification, session } = require('electron');
const path = require('path');
const store = require('./store');
const ipc = require('./ipc');
const skills = require('./services/skills');

let stopAlertChecker = null;

let mainWindow = null;
let tray = null;

app.setName('ARIA');

function buildAppMenu() {
  const isMac = process.platform === 'darwin';
  const template = [
    ...(isMac ? [{ role: 'appMenu' }] : []),
    { label: 'File', submenu: [isMac ? { role: 'close' } : { role: 'quit' }] },
    { role: 'editMenu' },
    { role: 'viewMenu' },
    { role: 'windowMenu' },
    {
      role: 'help',
      submenu: [
        {
          label: 'ARIA on GitHub',
          click: () => shell.openExternal('https://github.com/gorgon515/Gorg-Accounting-Workspace-'),
        },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1180,
    height: 820,
    minWidth: 880,
    minHeight: 640,
    backgroundColor: '#0E0E10',
    title: 'ARIA',
    icon: path.join(__dirname, '..', '..', 'build', 'icon.png'),
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));
  mainWindow.once('ready-to-show', () => mainWindow.show());

  // Headless smoke test: ARIA_SCREENSHOT=<path> launches, captures the
  // rendered window after it settles, writes the PNG, and quits. Used in CI
  // and local sanity checks; a no-op in normal use.
  if (process.env.ARIA_SCREENSHOT) {
    mainWindow.webContents.once('did-finish-load', () => {
      setTimeout(async () => {
        try {
          const img = await mainWindow.webContents.capturePage();
          require('fs').writeFileSync(process.env.ARIA_SCREENSHOT, img.toPNG());
          console.log('[screenshot] wrote', process.env.ARIA_SCREENSHOT);
        } catch (err) {
          console.error('[screenshot] failed:', err.message);
        }
        app.quit();
      }, 2500);
    });
  }

  // External links open in the system browser, not inside the app.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function trayIcon() {
  // Use the generated app icon, downscaled for the tray. Falls back to a 1x1
  // transparent pixel if the file isn't present.
  try {
    const img = nativeImage.createFromPath(path.join(__dirname, '..', '..', 'build', 'icon.png'));
    if (!img.isEmpty()) return img.resize({ width: 18, height: 18 });
  } catch { /* fall through */ }
  return nativeImage.createFromDataURL(
    'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
  );
}

function createTray() {
  const icon = trayIcon();
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

function startAlertChecker() {
  const alerts = skills.getSkill('alerts').api;
  stopAlertChecker = alerts.startChecker({
    intervalMs: 60000,
    onTrigger: (a) => {
      const now = a.triggeredPrice != null ? ` (now ${a.triggeredPrice.toFixed(2)})` : '';
      const body = `${a.symbol} is ${a.direction} ${a.price}${now}`;
      try {
        if (Notification.isSupported()) new Notification({ title: 'ARIA price alert', body }).show();
      } catch { /* notifications unavailable */ }
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('alert:triggered', a);
      }
    },
  });
}

// Single-instance: focus the existing window instead of launching a second app.
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });

  app.whenReady().then(() => {
    store.init();
    // Allow microphone access for voice capture (getUserMedia).
    session.defaultSession.setPermissionRequestHandler((_wc, permission, cb) => {
      cb(permission === 'media' || permission === 'audioCapture');
    });
    buildAppMenu();
    ipc.register();
    createWindow();
    createTray();
    startAlertChecker();

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
  });

  app.on('window-all-closed', () => {
    // Keep running in the tray on macOS; quit elsewhere.
    if (process.platform !== 'darwin') app.quit();
  });
}
