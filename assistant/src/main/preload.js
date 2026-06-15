'use strict';

// Secure bridge: exposes a minimal, typed API to the renderer. The renderer
// never gets Node or ipcRenderer directly (contextIsolation stays on).
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('aria', {
  config: () => ipcRenderer.invoke('aria:config'),
  ask: (text, history) => ipcRenderer.invoke('aria:ask', { text, history }),
  // Streaming brain events (delta / tool_result / done / error). Register once.
  onBrainEvent: (cb) => ipcRenderer.on('brain:event', (_e, evt) => cb(evt)),
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
    candles: (symbol, range) => ipcRenderer.invoke('stocks:candles', { symbol, range }),
    marketNews: () => ipcRenderer.invoke('stocks:marketNews'),
    calendar: (symbols) => ipcRenderer.invoke('stocks:calendar', symbols),
  },
  realtime: {
    subscribe: (symbols) => ipcRenderer.invoke('realtime:subscribe', symbols),
    unsubscribe: () => ipcRenderer.invoke('realtime:unsubscribe'),
    status: () => ipcRenderer.invoke('realtime:status'),
    // main -> renderer push per price tick { symbol, price, time }
    onTick: (cb) => ipcRenderer.on('quote:tick', (_e, t) => cb(t)),
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
    addEvent: (payload) => ipcRenderer.invoke('google:event:add', payload),
  },
  broker: {
    status: () => ipcRenderer.invoke('broker:status'),
    connect: (creds) => ipcRenderer.invoke('broker:connect', creds),
    disconnect: () => ipcRenderer.invoke('broker:disconnect'),
    encryptionAvailable: () => ipcRenderer.invoke('broker:encryptionAvailable'),
  },
  accounting: {
    summary: (range) => ipcRenderer.invoke('acct:summary', range),
    txns: (filter) => ipcRenderer.invoke('acct:txns', filter),
    addTxn: (t) => ipcRenderer.invoke('acct:txn:add', t),
    deleteTxn: (id) => ipcRenderer.invoke('acct:txn:delete', id),
    categories: () => ipcRenderer.invoke('acct:categories'),
    invoices: (filter) => ipcRenderer.invoke('acct:invoices', filter),
    addInvoice: (inv) => ipcRenderer.invoke('acct:invoice:add', inv),
    markPaid: (id) => ipcRenderer.invoke('acct:invoice:paid', id),
    deleteInvoice: (id) => ipcRenderer.invoke('acct:invoice:delete', id),
  },
  study: {
    stats: () => ipcRenderer.invoke('study:stats'),
    due: (filter) => ipcRenderer.invoke('study:due', filter),
    review: (id, grade) => ipcRenderer.invoke('study:review', { id, grade }),
    addCard: (c) => ipcRenderer.invoke('study:card:add', c),
    addVocab: (v) => ipcRenderer.invoke('study:vocab:add', v),
    deleteCard: (id) => ipcRenderer.invoke('study:card:delete', id),
    notes: (filter) => ipcRenderer.invoke('study:notes', filter),
    addNote: (n) => ipcRenderer.invoke('study:note:add', n),
    deleteNote: (id) => ipcRenderer.invoke('study:note:delete', id),
    log: (s) => ipcRenderer.invoke('study:log', s),
    cpa: () => ipcRenderer.invoke('study:cpa'),
    setCpa: (p) => ipcRenderer.invoke('study:cpa:set', p),
  },
  russian: {
    progress: () => ipcRenderer.invoke('russian:progress'),
    curriculum: () => ipcRenderer.invoke('russian:curriculum'),
    lesson: (id) => ipcRenderer.invoke('russian:lesson', id),
    alphabet: () => ipcRenderer.invoke('russian:alphabet'),
    start: (id) => ipcRenderer.invoke('russian:start', id),
    complete: (p) => ipcRenderer.invoke('russian:complete', p),
    setLevel: (l) => ipcRenderer.invoke('russian:setLevel', l),
    seedVocab: (theme) => ipcRenderer.invoke('russian:seedVocab', { theme }),
    logPractice: (p) => ipcRenderer.invoke('russian:logPractice', p),
    settings: (s) => ipcRenderer.invoke('russian:settings', s),
    review: () => ipcRenderer.invoke('russian:review'),
  },
  strategy: {
    idea: (symbol) => ipcRenderer.invoke('strategy:idea', symbol),
    scan: () => ipcRenderer.invoke('strategy:scan'),
    tranche: (symbol, opts) => ipcRenderer.invoke('strategy:tranche', { symbol, ...(opts || {}) }),
    actionPlan: (symbols) => ipcRenderer.invoke('strategy:actionPlan', { symbols }),
  },
  imessage: {
    status: () => ipcRenderer.invoke('imessage:status'),
  },
  telegram: {
    status: () => ipcRenderer.invoke('telegram:status'),
  },
});
