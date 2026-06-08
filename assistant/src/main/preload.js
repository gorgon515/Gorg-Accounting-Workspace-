'use strict';

// Secure bridge: exposes a minimal, typed API to the renderer. The renderer
// never gets Node or ipcRenderer directly (contextIsolation stays on).
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('aria', {
  config: () => ipcRenderer.invoke('aria:config'),
  ask: (text, history) => ipcRenderer.invoke('aria:ask', { text, history }),
  stocks: {
    quote: (symbol) => ipcRenderer.invoke('stocks:quote', symbol),
    quotes: (symbols) => ipcRenderer.invoke('stocks:quotes', symbols),
    search: (query) => ipcRenderer.invoke('stocks:search', query),
    history: (symbol, range) => ipcRenderer.invoke('stocks:history', { symbol, range }),
    watchlist: () => ipcRenderer.invoke('stocks:watchlist'),
    watchlistQuotes: () => ipcRenderer.invoke('stocks:watchlist:quotes'),
    addToWatchlist: (symbol) => ipcRenderer.invoke('stocks:watchlist:add', symbol),
    removeFromWatchlist: (symbol) => ipcRenderer.invoke('stocks:watchlist:remove', symbol),
  },
});
