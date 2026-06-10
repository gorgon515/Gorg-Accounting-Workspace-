'use strict';

// Secure bridge: exposes a minimal, typed API to the renderer. The renderer
// never gets Node or ipcRenderer directly (contextIsolation stays on).
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('aria', {
  config: () => ipcRenderer.invoke('aria:config'),
  ask: (text, history) => ipcRenderer.invoke('aria:ask', { text, history }),
  stt: {
    available: () => ipcRenderer.invoke('stt:available'),
    info: () => ipcRenderer.invoke('stt:info'),
    // payload is either { base64, sampleRate } for local PCM, or { base64, mime }
    // for the cloud audio-file path.
    transcribe: (payload) => ipcRenderer.invoke('stt:transcribe', payload),
  },
  stocks: {
    quote: (symbol) => ipcRenderer.invoke('stocks:quote', symbol),
    quotes: (symbols) => ipcRenderer.invoke('stocks:quotes', symbols),
    search: (query) => ipcRenderer.invoke('stocks:search', query),
    news: (query) => ipcRenderer.invoke('stocks:news', query),
    history: (symbol, range) => ipcRenderer.invoke('stocks:history', { symbol, range }),
    watchlist: () => ipcRenderer.invoke('stocks:watchlist'),
    watchlistQuotes: () => ipcRenderer.invoke('stocks:watchlist:quotes'),
    addToWatchlist: (symbol) => ipcRenderer.invoke('stocks:watchlist:add', symbol),
    removeFromWatchlist: (symbol) => ipcRenderer.invoke('stocks:watchlist:remove', symbol),
  },
  trading: {
    portfolio: () => ipcRenderer.invoke('trading:portfolio'),
    pending: () => ipcRenderer.invoke('trading:pending'),
    propose: (order) => ipcRenderer.invoke('trading:propose', order),
    approve: (id) => ipcRenderer.invoke('trading:approve', id),
    reject: (id) => ipcRenderer.invoke('trading:reject', id),
    orders: () => ipcRenderer.invoke('trading:orders'),
    reset: () => ipcRenderer.invoke('trading:reset'),
  },
  productivity: {
    tasks: (filter) => ipcRenderer.invoke('prod:tasks', filter),
    addTask: (t) => ipcRenderer.invoke('prod:task:add', t),
    completeTask: (id) => ipcRenderer.invoke('prod:task:complete', id),
    deleteTask: (id) => ipcRenderer.invoke('prod:task:delete', id),
    briefing: () => ipcRenderer.invoke('prod:briefing'),
  },
  alerts: {
    list: () => ipcRenderer.invoke('alerts:list'),
    add: (a) => ipcRenderer.invoke('alerts:add', a),
    remove: (id) => ipcRenderer.invoke('alerts:remove', id),
    // main -> renderer push when an alert fires
    onTriggered: (cb) => ipcRenderer.on('alert:triggered', (_e, data) => cb(data)),
  },
  google: {
    status: () => ipcRenderer.invoke('google:status'),
    connect: () => ipcRenderer.invoke('google:connect'),
    disconnect: () => ipcRenderer.invoke('google:disconnect'),
    agenda: () => ipcRenderer.invoke('google:agenda'),
    inbox: () => ipcRenderer.invoke('google:inbox'),
  },
  broker: {
    status: () => ipcRenderer.invoke('broker:status'),
    connect: (creds) => ipcRenderer.invoke('broker:connect', creds),
    disconnect: () => ipcRenderer.invoke('broker:disconnect'),
    encryptionAvailable: () => ipcRenderer.invoke('broker:encryptionAvailable'),
  },
});
