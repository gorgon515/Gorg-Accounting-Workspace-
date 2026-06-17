# HELIOS Command Center — React HUD

The Phase-3 front end: a **React + TypeScript + TailwindCSS + Framer Motion**
command-center UI for the HELIOS desktop app. It is built **additively** — the
existing vanilla renderer (`../src/renderer`) remains the default; this React HUD
is opt-in until visually validated, so the app never regresses.

## Run

```bash
cd assistant/frontend-react
npm install
npm run build        # tsc --noEmit && vite build  → dist/   (the acceptance test)
npm run dev          # browser dev server (UI preview; IPC is mocked-absent)
```

Launch the desktop app with the React HUD:

```bash
cd assistant
HELIOS_UI=react npm start      # loads frontend-react/dist if built, else classic
```

`main.js` loads `frontend-react/dist/index.html` when `HELIOS_UI=react` **and**
the build exists; otherwise it falls back to the classic renderer (and warns).
Both UIs share the same preload, so `window.aria` (the IPC bridge) is identical.

## Why it builds and runs anywhere

The same bundle must run inside Electron (where `window.aria` exists) and in a
plain browser (where it does not). Every IPC call goes through
`src/ipc/client.ts`, which rejects clearly when the bridge is absent; the
`useAsync` hook turns that into a graceful "lives in the desktop app" state
instead of a crash. So `npm run dev` renders the full HUD with empty/offline
panels, and inside Electron the same panels fill with live data.

## Architecture

```
src/
  main.tsx / App.tsx        entry; wires Electron push channels → event bus
  router.tsx                lightweight context router (instant nav, no deps)
  routes.tsx                route registry → left-sidebar navigation
  ipc/
    client.ts               typed, safe wrapper over window.aria
    types.ts                shared payload types
  lib/
    eventBus.ts             pub/sub + notification log (real-time, no reloads)
    format.ts               money/percent/time-ago/classname helpers
  hooks/
    useAsync.ts             data fetch with loading/error/reload + polling
    useEventBus.ts          subscribe a component to bus events
  components/               the design system (see below)
  layout/
    CommandCenter.tsx        three-column shell
    Sidebar.tsx Topbar.tsx RightPanel.tsx
  views/                    one per nav destination
    Dashboard Assistant Markets Portfolio Accounting CPACenter
    Language Calendar Email Memory Automations Settings AgentActivity
```

### Design system (`src/components`)

`Button, Card, Panel, Drawer, Modal, StatusBadge, AgentCard, MetricCard,
ActivityFeed, Table, Chart, Timeline, VoiceVisualizer, NotificationPanel`
(+ `EmptyState/Loading/ErrorState`). Dark-mode-first, glassmorphism, gold accent,
JetBrains Mono for figures — mirroring the original design tokens in
`tailwind.config.js`. `Chart` is a dependency-free SVG renderer (smaller, safer
build than a charting lib).

### Real-time event bus

`lib/eventBus.ts` is a tiny pub/sub. `App.tsx` subscribes to the Electron
`alert:triggered` push channel and republishes it as a notification + `alert`
event; panels poll their IPC sources on intervals (agent activity every 4s,
markets every 60s) and the right rail updates without reloads.

## Layout

Three columns: **left** navigation (Assistant, Dashboard, Markets, Portfolio,
Accounting, CPA, Language, Calendar, Email, Memory, Agents, Automations,
Settings), **center** workspace (the active view), **right** live-intelligence
rail (agent activity, notifications, system status). Topbar shows the brain/
sidecar status and the clock.

## Status

The build is the verified acceptance criterion (`npm run build` passes;
typecheck clean). Visual validation inside Electron and the final cut-over to make
React the default renderer are the remaining step — kept opt-in deliberately so
the working classic UI is never at risk.
