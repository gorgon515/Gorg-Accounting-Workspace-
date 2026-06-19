'use strict';

// HELIOS desktop mode.
//
// The standalone HELIOS app is the same Electron shell as ARIA, packaged with
// two extra resources: the React Command Center (resources/frontend) and a
// Python-free backend binary (resources/helios-backend). Detecting that bundle
// flips the shell into "HELIOS mode" — React UI + bundled backend — by setting
// the env knobs the rest of the app already understands (see config.js /
// services/sidecar.js). The ARIA build ships neither resource, so it is
// completely unaffected and continues to launch the classic renderer.
//
// This module must be required BEFORE ./config, which snapshots env at load.

const path = require('path');
const fs = require('fs');
const { app } = require('electron');

function detect() {
  try {
    if (!app.isPackaged) return null;
    const dir = path.join(process.resourcesPath, 'helios-backend');
    const binName = process.platform === 'win32' ? 'helios-backend.exe' : 'helios-backend';
    const bin = path.join(dir, binName);
    const frontend = path.join(process.resourcesPath, 'frontend', 'index.html');
    if (fs.existsSync(bin)) {
      return { bin, frontend };
    }
  } catch {
    /* ignore — fall back to ARIA behaviour */
  }
  return null;
}

const helios = detect();

if (helios) {
  app.setName('HELIOS');
  process.env.HELIOS_DESKTOP = '1';
  process.env.HELIOS_UI = 'react';
  process.env.HELIOS_SIDECAR_BIN = helios.bin;
  if (fs.existsSync(helios.frontend)) {
    process.env.HELIOS_FRONTEND_INDEX = helios.frontend;
  }
}

module.exports = { helios, isHelios: Boolean(helios) };
