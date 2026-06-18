'use strict';

// Wires renderer <-> main IPC. Two kinds of channels:
//   1. Direct stock data (UI panels) — work with no API key.
//   2. The AI brain (chat / voice) — needs ANTHROPIC_API_KEY.
const { ipcMain } = require('electron');
const config = require('./config');
const brain = require('./brain');
const skills = require('./services/skills');
const broker = require('./services/broker');
const stt = require('./services/stt');
const imessage = require('./services/imessage');
const telegram = require('./services/telegram');
const store = require('./store');

function register() {
  const stocks = skills.getSkill('stocks').api;
  const trading = skills.getSkill('trading').api;
  const productivity = skills.getSkill('productivity').api;
  const alerts = skills.getSkill('alerts').api;
  const google = skills.getSkill('google').api;
  const accounting = skills.getSkill('accounting').api;
  const study = skills.getSkill('study').api;
  const strategy = skills.getSkill('strategy').api;
  const language = skills.getSkill('language').api;
  const agents = skills.getSkill('agents').api;
  const sidecar = skills.getSkill('sidecar').api;
  const memory = skills.getSkill('memory').api;

  ipcMain.handle('aria:config', async () => {
    const b = await brain.status();
    return {
      hasBrain: b.ready,
      brain: b, // { engine, model, ready, local, reason }
      model: b.model,
      wakeWord: config.wakeWord,
      stt: stt.info(),
    };
  });

  // Speech-to-text
  ipcMain.handle('stt:available', () => stt.available());
  ipcMain.handle('stt:info', () => stt.info());
  ipcMain.handle('stt:transcribe', (_e, payload) => stt.transcribe(payload));

  // Brain (natural language / voice)
  ipcMain.handle('aria:ask', async (_e, { text, history }) => brain.ask(text, history || []));

  // Direct stock data for panels
  ipcMain.handle('stocks:quote', (_e, symbol) => stocks.getQuote(symbol));
  ipcMain.handle('stocks:quotes', (_e, symbols) => stocks.getQuotes(symbols));
  ipcMain.handle('stocks:search', (_e, query) => stocks.searchSymbol(query));
  ipcMain.handle('stocks:news', (_e, query) => stocks.getNews(query));
  ipcMain.handle('stocks:history', (_e, { symbol, range }) => stocks.getHistory(symbol, range));
  ipcMain.handle('stocks:watchlist', () => stocks.getWatchlist());
  ipcMain.handle('stocks:watchlist:quotes', () => stocks.getQuotes(stocks.getWatchlist()));
  ipcMain.handle('stocks:watchlist:add', (_e, symbol) => stocks.addToWatchlist(symbol));
  ipcMain.handle('stocks:watchlist:remove', (_e, symbol) => stocks.removeFromWatchlist(symbol));

  // Trading (paper). propose stages an order; only approve fills it.
  ipcMain.handle('trading:portfolio', () => trading.getPortfolio());
  ipcMain.handle('trading:pending', () => trading.listPending());
  ipcMain.handle('trading:propose', (_e, order) => trading.proposeTrade(order));
  ipcMain.handle('trading:approve', (_e, id) => trading.approve(id));
  ipcMain.handle('trading:reject', (_e, id) => trading.reject(id));
  ipcMain.handle('trading:orders', () => trading.getOrders());
  ipcMain.handle('trading:reset', () => trading.resetAccount());

  // Productivity
  ipcMain.handle('prod:tasks', (_e, filter) => productivity.listTasks({ filter }));
  ipcMain.handle('prod:task:add', (_e, t) => productivity.addTask(t));
  ipcMain.handle('prod:task:complete', (_e, id) => productivity.completeTask({ id }));
  ipcMain.handle('prod:task:delete', (_e, id) => productivity.deleteTask({ id }));
  ipcMain.handle('prod:briefing', () => productivity.briefing());

  // Alerts
  ipcMain.handle('alerts:list', () => alerts.listAlerts());
  ipcMain.handle('alerts:add', (_e, a) => alerts.addAlert(a));
  ipcMain.handle('alerts:remove', (_e, id) => alerts.removeAlert({ id }));

  // Google (Gmail + Calendar)
  ipcMain.handle('google:status', () => google.status());
  ipcMain.handle('google:connect', () => google.startAuth());
  ipcMain.handle('google:disconnect', () => google.disconnect());
  ipcMain.handle('google:agenda', () => google.listEvents());
  ipcMain.handle('google:inbox', () => google.listUnread());

  // Broker (trading account). The secret never crosses back to the renderer.
  ipcMain.handle('broker:status', () => broker.status());
  ipcMain.handle('broker:connect', (_e, creds) => broker.connect(creds));
  ipcMain.handle('broker:disconnect', () => broker.disconnect());
  ipcMain.handle('broker:encryptionAvailable', () => store.encryptionAvailable());

  // Accounting
  ipcMain.handle('acct:summary', (_e, range) => accounting.summary(range || {}));
  ipcMain.handle('acct:txns', (_e, filter) => accounting.listTransactions(filter || {}));
  ipcMain.handle('acct:txn:add', (_e, t) => accounting.addTransaction(t));
  ipcMain.handle('acct:txn:delete', (_e, id) => accounting.deleteTransaction({ id }));
  ipcMain.handle('acct:categories', () => accounting.categories());
  ipcMain.handle('acct:invoices', (_e, filter) => accounting.listInvoices(filter || {}));
  ipcMain.handle('acct:invoice:add', (_e, inv) => accounting.addInvoice(inv));
  ipcMain.handle('acct:invoice:paid', (_e, id) => accounting.markInvoicePaid({ id }));
  ipcMain.handle('acct:invoice:delete', (_e, id) => accounting.deleteInvoice({ id }));

  // Study
  ipcMain.handle('study:stats', () => study.studyStats());
  ipcMain.handle('study:due', (_e, filter) => study.dueFlashcards(filter || {}));
  ipcMain.handle('study:review', (_e, p) => study.reviewFlashcard(p));
  ipcMain.handle('study:card:add', (_e, c) => study.addFlashcard(c));
  ipcMain.handle('study:vocab:add', (_e, v) => study.addVocab(v));
  ipcMain.handle('study:card:delete', (_e, id) => study.deleteFlashcard({ id }));
  ipcMain.handle('study:notes', (_e, filter) => study.listNotes(filter || {}));
  ipcMain.handle('study:note:add', (_e, n) => study.addNote(n));
  ipcMain.handle('study:note:delete', (_e, id) => study.deleteNote({ id }));
  ipcMain.handle('study:log', (_e, s) => study.logStudy(s));
  ipcMain.handle('study:cpa', () => study.cpaStatus());
  ipcMain.handle('study:cpa:set', (_e, p) => study.setCpaProgress(p));

  // Trade ideas
  ipcMain.handle('strategy:idea', (_e, symbol) => strategy.tradeIdea(symbol));
  ipcMain.handle('strategy:scan', () => strategy.scanIdeas());

  // Language Immersion Center
  ipcMain.handle('lang:languages', () => language.LANGUAGES);
  ipcMain.handle('lang:curriculum', () => language.CURRICULUM);
  ipcMain.handle('lang:profile', () => language.getProfile());
  ipcMain.handle('lang:setLanguage', (_e, p) => language.setTargetLanguage(p || {}));
  ipcMain.handle('lang:progress', (_e, lang) => language.progress({ language: lang }));
  ipcMain.handle('lang:missions', (_e, lang) => language.dailyMissions({ language: lang }));
  ipcMain.handle('lang:mission:complete', (_e, p) => language.completeMission(p || {}));
  ipcMain.handle('lang:vocab:add', (_e, v) => language.addVocab(v || {}));
  ipcMain.handle('lang:due', (_e, lang) => language.dueReview({ language: lang }));

  // Agent orchestration (Agent Activity panel)
  ipcMain.handle('agents:roster', () => agents.roster(skills.skills));
  ipcMain.handle('agents:route', (_e, text) => agents.route(text));
  ipcMain.handle('agents:activity', () => agents.recentActivity());

  // Intelligence Sidecar (Quant Research + Accounting Intelligence)
  ipcMain.handle('sidecar:status', () => sidecar.status());
  ipcMain.handle('sidecar:analyze', (_e, p) => sidecar.analyze(p || {}));
  ipcMain.handle('sidecar:factors', (_e, p) => sidecar.factors(p || {}));
  ipcMain.handle('sidecar:risk', (_e, p) => sidecar.risk(p || {}));
  ipcMain.handle('sidecar:portfolio', (_e, p) => sidecar.portfolio(p || {}));
  ipcMain.handle('sidecar:ascTopics', () => sidecar.ascTopics());
  ipcMain.handle('sidecar:explainAsc', (_e, topic) => sidecar.explainAsc(topic));
  ipcMain.handle('sidecar:memo', (_e, p) => sidecar.memo(p || {}));
  // Phase 4 — intelligence engines
  ipcMain.handle('sidecar:acctBriefing', (_e, refresh) => sidecar.accountingBriefing(refresh));
  ipcMain.handle('sidecar:acctIntel', (_e, source) => sidecar.accountingIntel(source));
  ipcMain.handle('sidecar:acctIntelRefresh', () => sidecar.accountingIntelRefresh());
  ipcMain.handle('sidecar:acctGraph', (_e, asc) => sidecar.accountingGraph(asc));
  ipcMain.handle('sidecar:checklist', (_e, topic) => sidecar.checklist(topic));
  ipcMain.handle('sidecar:memoFull', (_e, p) => sidecar.memoFull(p || {}));
  ipcMain.handle('sidecar:fundamentals', (_e, p) => sidecar.fundamentals(p || {}));
  ipcMain.handle('sidecar:signal', (_e, p) => sidecar.signal(p || {}));
  ipcMain.handle('sidecar:marketBriefing', (_e, p) => sidecar.marketBriefing(p || {}));
  ipcMain.handle('sidecar:n8nStatus', () => sidecar.n8nStatus());
  ipcMain.handle('sidecar:n8nWorkflows', () => sidecar.n8nWorkflows());
  ipcMain.handle('sidecar:n8nGenerate', (_e, p) => sidecar.n8nGenerate(p || {}));
  // Phase 5 — personal chief of staff
  ipcMain.handle('sidecar:createTask', (_e, p) => sidecar.createTask(p));
  ipcMain.handle('sidecar:listTasks', (_e, status) => sidecar.listTasks(status));
  ipcMain.handle('sidecar:completeTask', (_e, tid) => sidecar.completeTask(tid));
  ipcMain.handle('sidecar:deleteTask', (_e, tid) => sidecar.deleteTask(tid));
  ipcMain.handle('sidecar:recommendTasks', () => sidecar.recommendTasks());
  ipcMain.handle('sidecar:createGoal', (_e, p) => sidecar.createGoal(p));
  ipcMain.handle('sidecar:goalsDashboard', () => sidecar.goalsDashboard());
  ipcMain.handle('sidecar:goalProgress', (_e, p) => sidecar.goalProgress(p));
  ipcMain.handle('sidecar:deleteGoal', (_e, gid) => sidecar.deleteGoal(gid));
  ipcMain.handle('sidecar:schedulerJobs', () => sidecar.schedulerJobs());
  ipcMain.handle('sidecar:schedulerSeed', () => sidecar.schedulerSeed());
  ipcMain.handle('sidecar:schedulerTick', () => sidecar.schedulerTick());
  ipcMain.handle('sidecar:cosBriefingAuto', () => sidecar.cosBriefingAuto());
  ipcMain.handle('sidecar:cosPlanAuto', () => sidecar.cosPlanAuto());
  ipcMain.handle('sidecar:cosDailyBriefing', (_e, ctx) => sidecar.cosDailyBriefing(ctx));
  ipcMain.handle('sidecar:cosEveningReview', (_e, ctx) => sidecar.cosEveningReview(ctx));
  ipcMain.handle('sidecar:emailBriefing', (_e, emails) => sidecar.emailBriefing(emails));
  ipcMain.handle('sidecar:calendarPlan', (_e, p) => sidecar.calendarPlan(p));
  // Phase 6 — accounting platform
  ipcMain.handle('sidecar:acctSeed', (_e, template) => sidecar.acctSeed(template));
  ipcMain.handle('sidecar:acctChart', () => sidecar.acctChart());
  ipcMain.handle('sidecar:acctJournal', (_e, p) => sidecar.acctJournal(p));
  ipcMain.handle('sidecar:acctEntries', (_e, q) => sidecar.acctEntries(q));
  ipcMain.handle('sidecar:acctTrialBalance', (_e, asOf) => sidecar.acctTrialBalance(asOf));
  ipcMain.handle('sidecar:acctBalanceSheet', (_e, asOf) => sidecar.acctBalanceSheet(asOf));
  ipcMain.handle('sidecar:acctIncome', (_e, p) => sidecar.acctIncome(p.start, p.end));
  ipcMain.handle('sidecar:acctCashFlow', (_e, p) => sidecar.acctCashFlow(p.start, p.end));
  ipcMain.handle('sidecar:acctApAging', () => sidecar.acctApAging());
  ipcMain.handle('sidecar:acctArAging', () => sidecar.acctArAging());
  ipcMain.handle('sidecar:acctAddVendor', (_e, p) => sidecar.acctAddVendor(p));
  ipcMain.handle('sidecar:acctAddBill', (_e, p) => sidecar.acctAddBill(p));
  ipcMain.handle('sidecar:acctAddCustomer', (_e, p) => sidecar.acctAddCustomer(p));
  ipcMain.handle('sidecar:acctAddInvoice', (_e, p) => sidecar.acctAddInvoice(p));
  ipcMain.handle('sidecar:acctAssets', () => sidecar.acctAssets());
  ipcMain.handle('sidecar:acctAddAsset', (_e, p) => sidecar.acctAddAsset(p));
  ipcMain.handle('sidecar:acctAssetSchedule', (_e, id) => sidecar.acctAssetSchedule(id));
  ipcMain.handle('sidecar:acctClients', () => sidecar.acctClients());
  ipcMain.handle('sidecar:acctImportJournal', (_e, csv) => sidecar.acctImportJournal(csv));
  ipcMain.handle('sidecar:acctAudit', () => sidecar.acctAudit());
  ipcMain.handle('sidecar:acctDashboard', (_e, asOf) => sidecar.acctDashboard(asOf));
  // Phase 7 — tax & advisory workbench
  ipcMain.handle('sidecar:ocrStatus', () => sidecar.ocrStatus());
  ipcMain.handle('sidecar:docProcess', (_e, p) => sidecar.docProcess(p));
  ipcMain.handle('sidecar:docSearch', (_e, q) => sidecar.docSearch(q));
  ipcMain.handle('sidecar:taxTopics', () => sidecar.taxTopics());
  ipcMain.handle('sidecar:taxResearch', (_e, query) => sidecar.taxResearch(query));
  ipcMain.handle('sidecar:taxMemo', (_e, p) => sidecar.taxMemo(p));
  ipcMain.handle('sidecar:orgClient', (_e, p) => sidecar.orgClient(p));
  ipcMain.handle('sidecar:orgDashboard', () => sidecar.orgDashboard());
  ipcMain.handle('sidecar:wpTrialBalance', (_e, asOf) => sidecar.wpTrialBalance(asOf));
  ipcMain.handle('sidecar:wpLead', (_e, p) => sidecar.wpLead(p.type, p.asOf));
  ipcMain.handle('sidecar:advisoryAnalysis', (_e, asOf) => sidecar.advisoryAnalysis(asOf));
  ipcMain.handle('sidecar:advisoryDD', (_e, year) => sidecar.advisoryDD(year));
  ipcMain.handle('sidecar:globalSearch', (_e, q) => sidecar.globalSearch(q));
  // Phase 8 — execution / automation
  ipcMain.handle('sidecar:execQueue', () => sidecar.execQueue());
  ipcMain.handle('sidecar:execActions', (_e, status) => sidecar.execActions(status));
  ipcMain.handle('sidecar:execApprove', (_e, p) => sidecar.execApprove(p.id, p));
  ipcMain.handle('sidecar:execReject', (_e, p) => sidecar.execReject(p.id, p));
  ipcMain.handle('sidecar:execExecute', (_e, id) => sidecar.execExecute(id));
  ipcMain.handle('sidecar:execRollback', (_e, id) => sidecar.execRollback(id));
  ipcMain.handle('sidecar:execAutomateDoc', (_e, p) => sidecar.execAutomateDoc(p));
  ipcMain.handle('sidecar:closeStart', (_e, period) => sidecar.closeStart(period));
  ipcMain.handle('sidecar:closeUpdate', (_e, p) => sidecar.closeUpdate(p));
  ipcMain.handle('sidecar:closeDashboard', () => sidecar.closeDashboard());
  ipcMain.handle('sidecar:outcomesMetrics', () => sidecar.outcomesMetrics());
  ipcMain.handle('sidecar:opsFirm', () => sidecar.opsFirm());
  ipcMain.handle('sidecar:opsPortfolio', () => sidecar.opsPortfolio());
  ipcMain.handle('sidecar:workflowBuild', (_e, p) => sidecar.workflowBuild(p));
  // Phase 9 — security, vault, backup, recovery & sync
  ipcMain.handle('sidecar:securityStatus', () => sidecar.securityStatus());
  ipcMain.handle('sidecar:securityHealth', () => sidecar.securityHealth());
  ipcMain.handle('sidecar:vaultInitialize', (_e, pw) => sidecar.vaultInitialize(pw));
  ipcMain.handle('sidecar:vaultUnlock', (_e, pw) => sidecar.vaultUnlock(pw));
  ipcMain.handle('sidecar:vaultLock', () => sidecar.vaultLock());
  ipcMain.handle('sidecar:vaultSecrets', () => sidecar.vaultSecrets());
  ipcMain.handle('sidecar:vaultSetSecret', (_e, p) => sidecar.vaultSetSecret(p));
  ipcMain.handle('sidecar:vaultGetSecret', (_e, ref) => sidecar.vaultGetSecret(ref));
  ipcMain.handle('sidecar:vaultRotateSecret', (_e, p) => sidecar.vaultRotateSecret(p.ref, p.value));
  ipcMain.handle('sidecar:vaultDeleteSecret', (_e, ref) => sidecar.vaultDeleteSecret(ref));
  ipcMain.handle('sidecar:vaultRotateMaster', (_e, p) => sidecar.vaultRotateMaster(p));
  ipcMain.handle('sidecar:vaultAccessLog', (_e, limit) => sidecar.vaultAccessLog(limit));
  ipcMain.handle('sidecar:secMemoryPut', (_e, p) => sidecar.secMemoryPut(p));
  ipcMain.handle('sidecar:secMemoryGet', (_e, key) => sidecar.secMemoryGet(key));
  ipcMain.handle('sidecar:secDocumentPut', (_e, p) => sidecar.secDocumentPut(p));
  ipcMain.handle('sidecar:secDocumentGet', (_e, id) => sidecar.secDocumentGet(id));
  ipcMain.handle('sidecar:complianceEvents', (_e, q) => sidecar.complianceEvents(q));
  ipcMain.handle('sidecar:complianceRecord', (_e, p) => sidecar.complianceRecord(p));
  ipcMain.handle('sidecar:complianceVerify', () => sidecar.complianceVerify());
  ipcMain.handle('sidecar:complianceStats', () => sidecar.complianceStats());
  ipcMain.handle('sidecar:permissionMatrix', () => sidecar.permissionMatrix());
  ipcMain.handle('sidecar:permissionForAgent', (_e, agent) => sidecar.permissionForAgent(agent));
  ipcMain.handle('sidecar:integrityLedger', () => sidecar.integrityLedger());
  ipcMain.handle('sidecar:integrityAudit', () => sidecar.integrityAudit());
  ipcMain.handle('sidecar:backupCreate', (_e, p) => sidecar.backupCreate(p));
  ipcMain.handle('sidecar:backupList', (_e, limit) => sidecar.backupList(limit));
  ipcMain.handle('sidecar:backupStats', () => sidecar.backupStats());
  ipcMain.handle('sidecar:backupVerify', (_e, id) => sidecar.backupVerify(id));
  ipcMain.handle('sidecar:backupRetention', (_e, keep) => sidecar.backupRetention(keep));
  ipcMain.handle('sidecar:restoreValidate', (_e, p) => sidecar.restoreValidate(p));
  ipcMain.handle('sidecar:restoreInspect', (_e, p) => sidecar.restoreInspect(p));
  ipcMain.handle('sidecar:restoreRun', (_e, p) => sidecar.restoreRun(p));
  ipcMain.handle('sidecar:recoveryPoints', () => sidecar.recoveryPoints());
  ipcMain.handle('sidecar:recoveryPlan', () => sidecar.recoveryPlan());
  ipcMain.handle('sidecar:recoverySimulate', (_e, pw) => sidecar.recoverySimulate(pw));
  ipcMain.handle('sidecar:recoveryReport', (_e, pw) => sidecar.recoveryReport(pw));
  ipcMain.handle('sidecar:syncRegisterDevice', (_e, name) => sidecar.syncRegisterDevice(name));
  ipcMain.handle('sidecar:syncDevices', () => sidecar.syncDevices());
  ipcMain.handle('sidecar:syncPush', (_e, p) => sidecar.syncPush(p));
  ipcMain.handle('sidecar:syncPull', (_e, p) => sidecar.syncPull(p));
  ipcMain.handle('sidecar:syncConflicts', () => sidecar.syncConflicts());
  ipcMain.handle('sidecar:syncAudit', () => sidecar.syncAudit());
  ipcMain.handle('sidecar:syncStatus', () => sidecar.syncStatus());

  // Memory (Memory Center)
  ipcMain.handle('memory:list', (_e, query) => memory.recall(query ? { query } : {}));
  ipcMain.handle('memory:remember', (_e, m) => memory.remember(m || {}));
  ipcMain.handle('memory:forget', (_e, p) => memory.forget(p || {}));

  // iMessage bridge status (macOS)
  ipcMain.handle('imessage:status', () => imessage.available());

  // Telegram bridge status (cross-platform)
  ipcMain.handle('telegram:status', () => telegram.status());
}

module.exports = { register };
