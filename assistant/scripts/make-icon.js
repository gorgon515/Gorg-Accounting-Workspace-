'use strict';

// Generates build/icon.png (1024×1024) by rendering an SVG mark with Electron
// and capturing it — no image toolchain needed. electron-builder derives the
// platform icons (.icns / .ico / linux sizes) from this PNG.
//
// Run: xvfb-run -a npx electron scripts/make-icon.js   (or just `npm run icon`)

const { app, BrowserWindow } = require('electron');
const fs = require('fs');
const path = require('path');

app.disableHardwareAcceleration();

const SIZE = 1024;
const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="${SIZE}" height="${SIZE}" viewBox="0 0 1024 1024">
  <rect width="1024" height="1024" rx="200" fill="#0E0E10"/>
  <rect x="6" y="6" width="1012" height="1012" rx="194" fill="none" stroke="#242428" stroke-width="10"/>
  <g stroke="#B8976A" stroke-width="80" stroke-linecap="round" fill="none">
    <line x1="512" y1="266" x2="298" y2="792"/>
    <line x1="512" y1="266" x2="726" y2="792"/>
    <line x1="392" y1="616" x2="632" y2="616"/>
  </g>
</svg>`;

app.whenReady().then(async () => {
  const win = new BrowserWindow({ width: SIZE, height: SIZE, show: false, frame: false });
  const html = `<body style="margin:0;width:${SIZE}px;height:${SIZE}px;background:#0E0E10">${svg}</body>`;
  await win.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(html));
  await new Promise((r) => setTimeout(r, 400));
  const img = await win.webContents.capturePage();
  const out = path.join(__dirname, '..', 'build', 'icon.png');
  fs.writeFileSync(out, img.toPNG());
  const { width, height } = img.getSize();
  console.log(`wrote ${out} (${width}x${height})`);
  app.quit();
});
