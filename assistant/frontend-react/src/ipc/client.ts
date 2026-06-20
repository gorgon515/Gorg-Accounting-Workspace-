// Typed, safe wrapper over the Electron preload bridge (window.aria).
//
// The same React bundle must (a) run inside Electron where window.aria exists,
// and (b) build/run in a plain browser where it does not. Every call therefore
// goes through `call()`, which rejects clearly when the bridge is absent so the
// useAsync hook can render an "offline" state instead of crashing.

import type {
  AgentActivity, AgentRosterItem, AnalyzeResult, AppConfig, AscTopic, CpaStatus,
  CurriculumLevel, FactorResult, LanguageMeta, LanguageProgress, MemoResult,
  MemoryItem, Mission, Quote, RouteResult, SidecarStatus, Task,
} from './types';

type Bridge = any;

function bridge(): Bridge | undefined {
  return (globalThis as any).aria;
}

export function hasBridge(): boolean {
  return typeof bridge() !== 'undefined';
}

async function call<T>(fn: (b: Bridge) => Promise<T> | T): Promise<T> {
  const b = bridge();
  if (!b) throw new Error('HELIOS bridge unavailable — open inside the desktop app.');
  return await fn(b);
}

// Build a `?a=1&b=2` query string from defined params (Phase 13 REST helpers).
function qs(params?: Record<string, any>): string {
  if (!params) return '';
  const pairs = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  return pairs.length ? `?${pairs.join('&')}` : '';
}

export const helios = {
  hasBridge,
  config: (): Promise<AppConfig> => call((b) => b.config()),
  ask: (text: string, history: any[] = []): Promise<any> => call((b) => b.ask(text, history)),

  agents: {
    roster: (): Promise<AgentRosterItem[]> => call((b) => b.agents.roster()),
    route: (text: string): Promise<RouteResult> => call((b) => b.agents.route(text)),
    activity: (): Promise<AgentActivity[]> => call((b) => b.agents.activity()),
  },

  sidecar: {
    status: (): Promise<SidecarStatus> => call((b) => b.sidecar.status()),
    analyze: (p: any): Promise<AnalyzeResult> => call((b) => b.sidecar.analyze(p)),
    factors: (p: any): Promise<FactorResult> => call((b) => b.sidecar.factors(p)),
    risk: (p: any): Promise<any> => call((b) => b.sidecar.risk(p)),
    portfolio: (p: any): Promise<any> => call((b) => b.sidecar.portfolio(p)),
    ascTopics: (): Promise<{ topics: AscTopic[] }> => call((b) => b.sidecar.ascTopics()),
    explainAsc: (topic: string): Promise<any> => call((b) => b.sidecar.explainAsc(topic)),
    memo: (p: any): Promise<MemoResult> => call((b) => b.sidecar.memo(p)),
    // Phase 4 — intelligence engines
    acctBriefing: (refresh?: boolean): Promise<any> => call((b) => b.sidecar.acctBriefing(refresh)),
    acctIntel: (source?: string): Promise<any> => call((b) => b.sidecar.acctIntel(source)),
    acctIntelRefresh: (): Promise<any> => call((b) => b.sidecar.acctIntelRefresh()),
    acctGraph: (asc?: string): Promise<any> => call((b) => b.sidecar.acctGraph(asc)),
    checklist: (topic: string): Promise<any> => call((b) => b.sidecar.checklist(topic)),
    memoFull: (p: any): Promise<any> => call((b) => b.sidecar.memoFull(p)),
    fundamentals: (p: any): Promise<any> => call((b) => b.sidecar.fundamentals(p)),
    signal: (p: any): Promise<any> => call((b) => b.sidecar.signal(p)),
    marketBriefing: (p: any): Promise<any> => call((b) => b.sidecar.marketBriefing(p)),
    n8nStatus: (): Promise<any> => call((b) => b.sidecar.n8nStatus()),
    n8nWorkflows: (): Promise<any> => call((b) => b.sidecar.n8nWorkflows()),
    n8nGenerate: (p: any): Promise<any> => call((b) => b.sidecar.n8nGenerate(p)),
    // Phase 5 — personal chief of staff
    createTask: (p: any): Promise<any> => call((b) => b.sidecar.createTask(p)),
    listTasks: (status?: string): Promise<any> => call((b) => b.sidecar.listTasks(status)),
    completeTask: (tid: string): Promise<any> => call((b) => b.sidecar.completeTask(tid)),
    deleteTask: (tid: string): Promise<any> => call((b) => b.sidecar.deleteTask(tid)),
    recommendTasks: (): Promise<any> => call((b) => b.sidecar.recommendTasks()),
    createGoal: (p: any): Promise<any> => call((b) => b.sidecar.createGoal(p)),
    goalsDashboard: (): Promise<any> => call((b) => b.sidecar.goalsDashboard()),
    goalProgress: (p: any): Promise<any> => call((b) => b.sidecar.goalProgress(p)),
    deleteGoal: (gid: string): Promise<any> => call((b) => b.sidecar.deleteGoal(gid)),
    schedulerJobs: (): Promise<any> => call((b) => b.sidecar.schedulerJobs()),
    schedulerSeed: (): Promise<any> => call((b) => b.sidecar.schedulerSeed()),
    schedulerTick: (): Promise<any> => call((b) => b.sidecar.schedulerTick()),
    cosBriefingAuto: (): Promise<any> => call((b) => b.sidecar.cosBriefingAuto()),
    cosPlanAuto: (): Promise<any> => call((b) => b.sidecar.cosPlanAuto()),
    cosDailyBriefing: (ctx: any): Promise<any> => call((b) => b.sidecar.cosDailyBriefing(ctx)),
    cosEveningReview: (ctx: any): Promise<any> => call((b) => b.sidecar.cosEveningReview(ctx)),
    emailBriefing: (emails: any): Promise<any> => call((b) => b.sidecar.emailBriefing(emails)),
    calendarPlan: (p: any): Promise<any> => call((b) => b.sidecar.calendarPlan(p)),
    // Phase 6 — accounting platform
    acctSeed: (t?: string): Promise<any> => call((b) => b.sidecar.acctSeed(t)),
    acctChart: (): Promise<any> => call((b) => b.sidecar.acctChart()),
    acctJournal: (p: any): Promise<any> => call((b) => b.sidecar.acctJournal(p)),
    acctEntries: (q?: string): Promise<any> => call((b) => b.sidecar.acctEntries(q)),
    acctTrialBalance: (asOf?: string): Promise<any> => call((b) => b.sidecar.acctTrialBalance(asOf)),
    acctBalanceSheet: (asOf?: string): Promise<any> => call((b) => b.sidecar.acctBalanceSheet(asOf)),
    acctIncome: (start: string, end: string): Promise<any> => call((b) => b.sidecar.acctIncome(start, end)),
    acctApAging: (): Promise<any> => call((b) => b.sidecar.acctApAging()),
    acctArAging: (): Promise<any> => call((b) => b.sidecar.acctArAging()),
    acctAddCustomer: (p: any): Promise<any> => call((b) => b.sidecar.acctAddCustomer(p)),
    acctAddInvoice: (p: any): Promise<any> => call((b) => b.sidecar.acctAddInvoice(p)),
    acctAssets: (): Promise<any> => call((b) => b.sidecar.acctAssets()),
    acctAudit: (): Promise<any> => call((b) => b.sidecar.acctAudit()),
    acctDashboard: (asOf?: string): Promise<any> => call((b) => b.sidecar.acctDashboard(asOf)),
    // Phase 7 — workbench
    ocrStatus: (): Promise<any> => call((b) => b.sidecar.ocrStatus()),
    docProcess: (p: any): Promise<any> => call((b) => b.sidecar.docProcess(p)),
    docSearch: (q?: string): Promise<any> => call((b) => b.sidecar.docSearch(q)),
    taxResearch: (query: string): Promise<any> => call((b) => b.sidecar.taxResearch(query)),
    taxMemo: (p: any): Promise<any> => call((b) => b.sidecar.taxMemo(p)),
    orgDashboard: (): Promise<any> => call((b) => b.sidecar.orgDashboard()),
    orgClient: (p: any): Promise<any> => call((b) => b.sidecar.orgClient(p)),
    wpTrialBalance: (asOf?: string): Promise<any> => call((b) => b.sidecar.wpTrialBalance(asOf)),
    advisoryAnalysis: (asOf: string): Promise<any> => call((b) => b.sidecar.advisoryAnalysis(asOf)),
    advisoryDD: (year: number): Promise<any> => call((b) => b.sidecar.advisoryDD(year)),
    globalSearch: (q: string): Promise<any> => call((b) => b.sidecar.globalSearch(q)),
    // Phase 8 — execution
    execQueue: (): Promise<any> => call((b) => b.sidecar.execQueue()),
    execActions: (status?: string): Promise<any> => call((b) => b.sidecar.execActions(status)),
    execApprove: (p: any): Promise<any> => call((b) => b.sidecar.execApprove(p)),
    execReject: (p: any): Promise<any> => call((b) => b.sidecar.execReject(p)),
    execExecute: (id: number): Promise<any> => call((b) => b.sidecar.execExecute(id)),
    execRollback: (id: number): Promise<any> => call((b) => b.sidecar.execRollback(id)),
    closeStart: (period: string): Promise<any> => call((b) => b.sidecar.closeStart(period)),
    closeUpdate: (p: any): Promise<any> => call((b) => b.sidecar.closeUpdate(p)),
    closeDashboard: (): Promise<any> => call((b) => b.sidecar.closeDashboard()),
    outcomesMetrics: (): Promise<any> => call((b) => b.sidecar.outcomesMetrics()),
    opsFirm: (): Promise<any> => call((b) => b.sidecar.opsFirm()),
  },

  language: {
    languages: (): Promise<LanguageMeta[]> => call((b) => b.language.languages()),
    curriculum: (): Promise<CurriculumLevel[]> => call((b) => b.language.curriculum()),
    profile: (): Promise<any> => call((b) => b.language.profile()),
    setLanguage: (p: any): Promise<any> => call((b) => b.language.setLanguage(p)),
    progress: (lang?: string): Promise<LanguageProgress> => call((b) => b.language.progress(lang)),
    missions: (lang?: string): Promise<{ missions: Mission[] }> => call((b) => b.language.missions(lang)),
    completeMission: (p: any): Promise<any> => call((b) => b.language.completeMission(p)),
    addVocab: (v: any): Promise<any> => call((b) => b.language.addVocab(v)),
  },

  accounting: {
    summary: (range?: any): Promise<any> => call((b) => b.accounting.summary(range)),
    invoices: (filter?: any): Promise<any[]> => call((b) => b.accounting.invoices(filter)),
  },

  study: {
    cpa: (): Promise<CpaStatus> => call((b) => b.study.cpa()),
    stats: (): Promise<any> => call((b) => b.study.stats()),
  },

  stocks: {
    watchlistQuotes: (): Promise<Quote[]> => call((b) => b.stocks.watchlistQuotes()),
    quote: (s: string): Promise<Quote> => call((b) => b.stocks.quote(s)),
    history: (symbol: string, range: string): Promise<any> => call((b) => b.stocks.history(symbol, range)),
    news: (q: string): Promise<any[]> => call((b) => b.stocks.news(q)),
  },

  trading: {
    portfolio: (): Promise<any> => call((b) => b.trading.portfolio()),
    orders: (): Promise<any[]> => call((b) => b.trading.orders()),
  },

  productivity: {
    tasks: (filter?: string): Promise<Task[]> => call((b) => b.productivity.tasks(filter)),
    briefing: (): Promise<any> => call((b) => b.productivity.briefing()),
  },

  google: {
    status: (): Promise<any> => call((b) => b.google.status()),
    agenda: (): Promise<any> => call((b) => b.google.agenda()),
    inbox: (): Promise<any> => call((b) => b.google.inbox()),
  },

  memory: {
    list: (query?: string): Promise<MemoryItem[]> => call((b) => b.memory.list(query)),
    forget: (p: any): Promise<any> => call((b) => b.memory.forget(p)),
  },

  // Phase 9 — security, backup, sync, health
  security: {
    status: (): Promise<any> => call((b) => b.sidecar.securityStatus()),
    vaultStatus: (): Promise<any> => call((b) => b.sidecar.vaultStatus()),
    vaultInit: (p: any): Promise<any> => call((b) => b.sidecar.vaultInit(p)),
    vaultUnlock: (p: any): Promise<any> => call((b) => b.sidecar.vaultUnlock(p)),
    vaultLock: (): Promise<any> => call((b) => b.sidecar.vaultLock()),
    listSecrets: (): Promise<any> => call((b) => b.sidecar.listSecrets()),
    storeSecret: (p: any): Promise<any> => call((b) => b.sidecar.storeSecret(p)),
    retrieveSecret: (name: string): Promise<any> => call((b) => b.sidecar.retrieveSecret(name)),
    deleteSecret: (name: string): Promise<any> => call((b) => b.sidecar.deleteSecret(name)),
    rotateSecret: (name: string, p: any): Promise<any> => call((b) => b.sidecar.rotateSecret(name, p)),
    secretHistory: (name: string): Promise<any> => call((b) => b.sidecar.secretHistory(name)),
    vaultAudit: (): Promise<any> => call((b) => b.sidecar.vaultAudit()),
    complianceLog: (p?: any): Promise<any> => call((b) => b.sidecar.complianceLog(p)),
    verifyEntry: (id: number | string): Promise<any> => call((b) => b.sidecar.verifyEntry(id)),
    verifyChain: (): Promise<any> => call((b) => b.sidecar.verifyChain()),
    listAgents: (): Promise<any> => call((b) => b.sidecar.listAgents()),
    checkPermission: (p: any): Promise<any> => call((b) => b.sidecar.checkPermission(p)),
  },

  backup: {
    status: (): Promise<any> => call((b) => b.sidecar.backupStatus()),
    createFull: (p: any): Promise<any> => call((b) => b.sidecar.backupFull(p)),
    createIncremental: (p: any): Promise<any> => call((b) => b.sidecar.backupIncremental(p)),
    createSelective: (p: any): Promise<any> => call((b) => b.sidecar.backupSelective(p)),
    list: (): Promise<any> => call((b) => b.sidecar.backupList()),
    verify: (id: string): Promise<any> => call((b) => b.sidecar.backupVerify(id)),
    restorePoints: (): Promise<any> => call((b) => b.sidecar.restorePoints()),
    restoreFull: (p: any): Promise<any> => call((b) => b.sidecar.restoreFull(p)),
    restoreSelective: (p: any): Promise<any> => call((b) => b.sidecar.restoreSelective(p)),
    restorePit: (p: any): Promise<any> => call((b) => b.sidecar.restorePit(p)),
    drStatus: (): Promise<any> => call((b) => b.sidecar.drStatus()),
    drIntegrity: (): Promise<any> => call((b) => b.sidecar.drIntegrity()),
    drSimulate: (id: string): Promise<any> => call((b) => b.sidecar.drSimulate(id)),
    drPlan: (): Promise<any> => call((b) => b.sidecar.drPlan()),
    drReport: (): Promise<any> => call((b) => b.sidecar.drReport()),
  },

  sync: {
    status: (): Promise<any> => call((b) => b.sidecar.syncStatus()),
    registerDevice: (p: any): Promise<any> => call((b) => b.sidecar.syncRegisterDevice(p)),
    listDevices: (): Promise<any> => call((b) => b.sidecar.syncListDevices()),
    heartbeat: (id: string): Promise<any> => call((b) => b.sidecar.syncHeartbeat(id)),
    deregisterDevice: (id: string): Promise<any> => call((b) => b.sidecar.syncDeregisterDevice(id)),
    startSession: (p: any): Promise<any> => call((b) => b.sidecar.syncStartSession(p)),
    completeSession: (id: string, p: any): Promise<any> => call((b) => b.sidecar.syncCompleteSession(id, p)),
    getDelta: (p: any): Promise<any> => call((b) => b.sidecar.syncDelta(p)),
    push: (p: any): Promise<any> => call((b) => b.sidecar.syncPush(p)),
    listConflicts: (): Promise<any> => call((b) => b.sidecar.syncConflicts()),
    resolveConflict: (id: number | string, p: any): Promise<any> => call((b) => b.sidecar.syncResolveConflict(id, p)),
    auditLog: (p?: any): Promise<any> => call((b) => b.sidecar.syncAudit(p)),
  },

  healthMonitor: {
    status: (): Promise<any> => call((b) => b.sidecar.healthStatus()),
    database: (): Promise<any> => call((b) => b.sidecar.healthDatabase()),
    security: (): Promise<any> => call((b) => b.sidecar.healthSecurity()),
    backup: (): Promise<any> => call((b) => b.sidecar.healthBackup()),
    sync: (): Promise<any> => call((b) => b.sidecar.healthSync()),
    dailyReport: (): Promise<any> => call((b) => b.sidecar.healthDailyReport()),
    weeklyReport: (): Promise<any> => call((b) => b.sidecar.healthWeeklyReport()),
    history: (): Promise<any> => call((b) => b.sidecar.healthHistory()),
  },

  // Phase 10 — workspaces, plugins, public API, licensing, monitoring, updates
  workspaces: {
    listOrgs: (): Promise<any> => call((b) => b.sidecar.workspacesListOrgs()),
    createOrg: (p: any): Promise<any> => call((b) => b.sidecar.workspacesCreateOrg(p)),
    getOrg: (id: string): Promise<any> => call((b) => b.sidecar.workspacesGetOrg(id)),
    updateOrg: (id: string, p: any): Promise<any> => call((b) => b.sidecar.workspacesUpdateOrg(id, p)),
    deleteOrg: (id: string): Promise<any> => call((b) => b.sidecar.workspacesDeleteOrg(id)),
    orgStats: (id: string): Promise<any> => call((b) => b.sidecar.workspacesOrgStats(id)),
    listUsers: (orgId: string): Promise<any> => call((b) => b.sidecar.workspacesListUsers(orgId)),
    inviteUser: (p: any): Promise<any> => call((b) => b.sidecar.workspacesInviteUser(p)),
    updateUserRole: (userId: string, role: string): Promise<any> => call((b) => b.sidecar.workspacesUpdateRole(userId, role)),
    removeUser: (userId: string): Promise<any> => call((b) => b.sidecar.workspacesRemoveUser(userId)),
    getRoles: (): Promise<any> => call((b) => b.sidecar.workspacesGetRoles()),
  },

  plugins: {
    list: (status?: string): Promise<any> => call((b) => b.sidecar.pluginsList(status)),
    install: (manifest: any): Promise<any> => call((b) => b.sidecar.pluginsInstall(manifest)),
    enable: (id: string): Promise<any> => call((b) => b.sidecar.pluginsEnable(id)),
    disable: (id: string): Promise<any> => call((b) => b.sidecar.pluginsDisable(id)),
    uninstall: (id: string): Promise<any> => call((b) => b.sidecar.pluginsUninstall(id)),
    getInfo: (id: string): Promise<any> => call((b) => b.sidecar.pluginsGetInfo(id)),
    sandboxAudit: (): Promise<any> => call((b) => b.sidecar.pluginsSandboxAudit()),
  },

  publicApi: {
    listKeys: (ownerId?: string): Promise<any> => call((b) => b.sidecar.apiKeysList(ownerId)),
    createKey: (p: any): Promise<any> => call((b) => b.sidecar.apiKeysCreate(p)),
    getKey: (id: string): Promise<any> => call((b) => b.sidecar.apiKeysGet(id)),
    revokeKey: (id: string): Promise<any> => call((b) => b.sidecar.apiKeysRevoke(id)),
    verifyKey: (key: string): Promise<any> => call((b) => b.sidecar.apiKeysVerify(key)),
    keyStats: (): Promise<any> => call((b) => b.sidecar.apiKeysStats()),
    rateLimitCheck: (p: any): Promise<any> => call((b) => b.sidecar.rateLimitCheck(p)),
    rateLimitStats: (keyId: string): Promise<any> => call((b) => b.sidecar.rateLimitStats(keyId)),
    rateLimitReset: (keyId: string): Promise<any> => call((b) => b.sidecar.rateLimitReset(keyId)),
    listWebhooks: (ownerId?: string): Promise<any> => call((b) => b.sidecar.webhooksList(ownerId)),
    createWebhook: (p: any): Promise<any> => call((b) => b.sidecar.webhooksCreate(p)),
    updateWebhook: (id: string, p: any): Promise<any> => call((b) => b.sidecar.webhooksUpdate(id, p)),
    deleteWebhook: (id: string): Promise<any> => call((b) => b.sidecar.webhooksDelete(id)),
    deliverWebhook: (id: string, p: any): Promise<any> => call((b) => b.sidecar.webhooksDeliver(id, p)),
    webhookDeliveries: (id: string): Promise<any> => call((b) => b.sidecar.webhooksDeliveries(id)),
    webhookStats: (id: string): Promise<any> => call((b) => b.sidecar.webhooksStats(id)),
  },

  licensing: {
    listEditions: (): Promise<any> => call((b) => b.sidecar.licensingEditions()),
    generate: (p: any): Promise<any> => call((b) => b.sidecar.licensingGenerate(p)),
    verify: (key: string): Promise<any> => call((b) => b.sidecar.licensingVerify(key)),
    activate: (p: any): Promise<any> => call((b) => b.sidecar.licensingActivate(p)),
    getActive: (): Promise<any> => call((b) => b.sidecar.licensingGetActive()),
    listActivations: (): Promise<any> => call((b) => b.sidecar.licensingActivations()),
    revoke: (id: string): Promise<any> => call((b) => b.sidecar.licensingRevoke(id)),
  },

  monitoring: {
    recordError: (p: any): Promise<any> => call((b) => b.sidecar.monitoringRecordError(p)),
    listErrors: (p?: any): Promise<any> => call((b) => b.sidecar.monitoringListErrors(p)),
    resolveError: (id: string, p?: any): Promise<any> => call((b) => b.sidecar.monitoringResolveError(id, p)),
    errorStats: (): Promise<any> => call((b) => b.sidecar.monitoringErrorStats()),
    recordSample: (p: any): Promise<any> => call((b) => b.sidecar.monitoringRecordSample(p)),
    performanceMetric: (name: string, p?: any): Promise<any> => call((b) => b.sidecar.monitoringPerformanceMetric(name, p)),
    performanceDashboard: (): Promise<any> => call((b) => b.sidecar.monitoringPerformanceDashboard()),
    createIncident: (p: any): Promise<any> => call((b) => b.sidecar.monitoringCreateIncident(p)),
    listIncidents: (p?: any): Promise<any> => call((b) => b.sidecar.monitoringListIncidents(p)),
    updateIncident: (id: string, p: any): Promise<any> => call((b) => b.sidecar.monitoringUpdateIncident(id, p)),
    addTimeline: (id: string, p: any): Promise<any> => call((b) => b.sidecar.monitoringAddTimeline(id, p)),
    resolveIncident: (id: string, p: any): Promise<any> => call((b) => b.sidecar.monitoringResolveIncident(id, p)),
    mttrStats: (): Promise<any> => call((b) => b.sidecar.monitoringMttrStats()),
  },

  updates: {
    checkForUpdates: (channel?: string): Promise<any> => call((b) => b.sidecar.updatesCheck(channel)),
    download: (p: any): Promise<any> => call((b) => b.sidecar.updatesDownload(p)),
    install: (p: any): Promise<any> => call((b) => b.sidecar.updatesInstall(p)),
    rollback: (p?: any): Promise<any> => call((b) => b.sidecar.updatesRollback(p)),
    listChannels: (): Promise<any> => call((b) => b.sidecar.updatesChannels()),
    getSettings: (): Promise<any> => call((b) => b.sidecar.updatesSettings()),
    updateSettings: (p: any): Promise<any> => call((b) => b.sidecar.updatesUpdateSettings(p)),
    history: (): Promise<any> => call((b) => b.sidecar.updatesHistory()),
    validateInstall: (): Promise<any> => call((b) => b.sidecar.updatesValidateInstall()),
    setupDataDir: (): Promise<any> => call((b) => b.sidecar.updatesSetupDataDir()),
  },

  // Phase 11 — strategic reasoning & autonomous intelligence
  reasoning: {
    recommend: (): Promise<any> => call((b) => b.sidecar.reasoningRecommend()),
    decompose: (p: any): Promise<any> => call((b) => b.sidecar.reasoningDecompose(p)),
    prioritize: (p: any): Promise<any> => call((b) => b.sidecar.reasoningPrioritize(p)),
    tradeoffs: (p: any): Promise<any> => call((b) => b.sidecar.reasoningTradeoffs(p)),
    constraints: (p: any): Promise<any> => call((b) => b.sidecar.reasoningConstraints(p)),
    runProposals: (): Promise<any> => call((b) => b.sidecar.reasoningRunProposals()),
    listProposals: (status?: string): Promise<any> => call((b) => b.sidecar.reasoningListProposals(status)),
    proposalStats: (): Promise<any> => call((b) => b.sidecar.reasoningProposalStats()),
    decideProposal: (id: string, decision: string): Promise<any> => call((b) => b.sidecar.reasoningDecide(id, decision)),
    learningAccuracy: (kind?: string): Promise<any> => call((b) => b.sidecar.reasoningLearningAccuracy(kind)),
  },

  intelligence: {
    buildGraph: (): Promise<any> => call((b) => b.sidecar.intelBuildGraph()),
    graph: (domain?: string): Promise<any> => call((b) => b.sidecar.intelGraph(domain)),
    insights: (): Promise<any> => call((b) => b.sidecar.intelInsights()),
    graphStats: (): Promise<any> => call((b) => b.sidecar.intelGraphStats()),
    scanOpportunities: (): Promise<any> => call((b) => b.sidecar.intelScanOpps()),
    listOpportunities: (p?: any): Promise<any> => call((b) => b.sidecar.intelListOpps(p)),
    setOpportunityStatus: (id: string, status: string): Promise<any> => call((b) => b.sidecar.intelOppStatus(id, status)),
    scanRisks: (): Promise<any> => call((b) => b.sidecar.intelScanRisks()),
    listRisks: (p?: any): Promise<any> => call((b) => b.sidecar.intelListRisks(p)),
    riskSummary: (): Promise<any> => call((b) => b.sidecar.intelRiskSummary()),
    setRiskStatus: (id: string, status: string): Promise<any> => call((b) => b.sidecar.intelRiskStatus(id, status)),
  },

  forecasting: {
    metric: (metric: string, months?: number): Promise<any> => call((b) => b.sidecar.forecastMetric(metric, months)),
    all: (months?: number): Promise<any> => call((b) => b.sidecar.forecastAll(months)),
    retirement: (p: any): Promise<any> => call((b) => b.sidecar.forecastRetirement(p)),
    scenario: (p: any): Promise<any> => call((b) => b.sidecar.forecastScenario(p)),
    sensitivity: (p: any): Promise<any> => call((b) => b.sidecar.forecastSensitivity(p)),
    levers: (): Promise<any> => call((b) => b.sidecar.forecastLevers()),
  },

  advisory: {
    personalDashboard: (): Promise<any> => call((b) => b.sidecar.advisoryPersonalDashboard()),
    personalRecommendations: (horizon?: string): Promise<any> => call((b) => b.sidecar.advisoryPersonalRecs(horizon)),
    businessAnalysis: (): Promise<any> => call((b) => b.sidecar.advisoryBusinessAnalysis()),
    executiveReport: (): Promise<any> => call((b) => b.sidecar.advisoryExecReport()),
    capacity: (p: any): Promise<any> => call((b) => b.sidecar.advisoryCapacity(p)),
  },

  executive: {
    commandCenter: (): Promise<any> => call((b) => b.sidecar.execCommandCenter()),
    morningBriefing: (): Promise<any> => call((b) => b.sidecar.execMorningBriefing()),
  },

  // Phase 12 — knowledge engine, RAG, institutional memory & self-improving intelligence
  knowledge: {
    ingest: (p: any): Promise<any> => call((b) => b.sidecar.knowledgeIngest(p)),
    list: (p?: any): Promise<any> => call((b) => b.sidecar.knowledgeList(p)),
    get: (id: string): Promise<any> => call((b) => b.sidecar.knowledgeGet(id)),
    update: (id: string, fields: any): Promise<any> => call((b) => b.sidecar.knowledgeUpdate(id, fields)),
    link: (p: any): Promise<any> => call((b) => b.sidecar.knowledgeLink(p)),
    links: (id: string): Promise<any> => call((b) => b.sidecar.knowledgeLinks(id)),
    conflicts: (resolved?: boolean): Promise<any> => call((b) => b.sidecar.knowledgeConflicts(resolved)),
    resolveConflict: (id: number, resolution: string): Promise<any> => call((b) => b.sidecar.knowledgeResolveConflict(id, resolution)),
    gaps: (status?: string): Promise<any> => call((b) => b.sidecar.knowledgeGaps(status)),
    addGap: (p: any): Promise<any> => call((b) => b.sidecar.knowledgeAddGap(p)),
    health: (): Promise<any> => call((b) => b.sidecar.knowledgeHealth()),
    stats: (): Promise<any> => call((b) => b.sidecar.knowledgeStats()),
  },

  institutionalMemory: {
    record: (p: any): Promise<any> => call((b) => b.sidecar.memoryRecord(p)),
    list: (p?: any): Promise<any> => call((b) => b.sidecar.memoryList(p)),
    get: (id: string): Promise<any> => call((b) => b.sidecar.memoryGet(id)),
    updateOutcome: (id: string, outcome: string, confidence: number): Promise<any> =>
      call((b) => b.sidecar.memoryUpdateOutcome(id, outcome, confidence)),
    search: (q: string): Promise<any> => call((b) => b.sidecar.memorySearch(q)),
    stats: (): Promise<any> => call((b) => b.sidecar.memoryStats()),
  },

  rag: {
    query: (p: any): Promise<any> => call((b) => b.sidecar.ragQuery(p)),
    search: (p: any): Promise<any> => call((b) => b.sidecar.ragSearch(p)),
    embed: (text: string, model?: string): Promise<any> => call((b) => b.sidecar.ragEmbed(text, model)),
    models: (): Promise<any> => call((b) => b.sidecar.ragModels()),
    benchmark: (model: string, n?: number): Promise<any> => call((b) => b.sidecar.ragBenchmark(model, n)),
    modelStats: (model: string): Promise<any> => call((b) => b.sidecar.ragModelStats(model)),
    collections: (): Promise<any> => call((b) => b.sidecar.ragCollections()),
    metrics: (): Promise<any> => call((b) => b.sidecar.ragMetrics()),
  },

  synthesis: {
    synthesize: (p: any): Promise<any> => call((b) => b.sidecar.synthesisSynthesize(p)),
    reports: (domain?: string): Promise<any> => call((b) => b.sidecar.synthesisReports(domain)),
    getReport: (id: string): Promise<any> => call((b) => b.sidecar.synthesisGetReport(id)),
    stats: (): Promise<any> => call((b) => b.sidecar.synthesisStats()),
  },

  selfImprovement: {
    record: (p: any): Promise<any> => call((b) => b.sidecar.siRecord(p)),
    accuracy: (window?: number): Promise<any> => call((b) => b.sidecar.siAccuracy(window)),
    trend: (kind: string): Promise<any> => call((b) => b.sidecar.siTrend(kind)),
    history: (kind?: string): Promise<any> => call((b) => b.sidecar.siHistory(kind)),
    generateOpportunities: (): Promise<any> => call((b) => b.sidecar.siGenerateOpportunities()),
    opportunities: (status?: string): Promise<any> => call((b) => b.sidecar.siOpportunities(status)),
    addPriority: (p: any): Promise<any> => call((b) => b.sidecar.siAddPriority(p)),
    priorities: (): Promise<any> => call((b) => b.sidecar.siPriorities()),
    runCycle: (): Promise<any> => call((b) => b.sidecar.siRunCycle()),
    dashboard: (): Promise<any> => call((b) => b.sidecar.siDashboard()),
  },

  // Phase 13 — live connectors, intelligence, research, financial hub, ops, agents.
  // All routed through a single generic REST passthrough on the sidecar bridge.
  connectors: {
    list: (p?: { category?: string; kind?: string }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/connectors${qs(p)}`)),
    get: (id: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/connectors/${id}`)),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/connectors/stats')),
    enable: (id: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/connectors/${id}/enable`)),
    disable: (id: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/connectors/${id}/disable`)),
    updateConfig: (id: string, config: any): Promise<any> =>
      call((b) => b.sidecar.request('PUT', `/api/connectors/${id}/config`, { config })),
    storeCredential: (id: string, p: any): Promise<any> =>
      call((b) => b.sidecar.request('POST', `/api/connectors/${id}/credential`, p)),
    health: (id: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/connectors/${id}/health`)),
    fetch: (id: string, p?: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/connectors/${id}/fetch`, p || {})),
    logs: (id: string, limit?: number): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/connectors/${id}/logs${qs({ limit })}`)),
  },

  liveIntel: {
    items: (p?: { domain?: string; source?: string; limit?: number }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/live-intel/items${qs(p)}`)),
    alerts: (status?: string): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/live-intel/alerts${qs({ status })}`)),
    acknowledgeAlert: (id: string): Promise<any> =>
      call((b) => b.sidecar.request('POST', `/api/live-intel/alerts/${id}/acknowledge`)),
    signals: (p?: { domain?: string; limit?: number }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/live-intel/signals${qs(p)}`)),
    poll: (connectorId: string, domain?: string): Promise<any> =>
      call((b) => b.sidecar.request('POST', `/api/live-intel/poll/${connectorId}${qs({ domain })}`)),
    sources: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/live-intel/sources')),
    monitors: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/live-intel/monitors')),
    addMonitor: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/live-intel/monitors', p)),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/live-intel/stats')),
  },

  researchMissions: {
    list: (p?: { status?: string; team?: string }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/research/missions${qs(p)}`)),
    create: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/research/missions', p)),
    get: (id: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/research/missions/${id}`)),
    run: (id: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/research/missions/${id}/run`)),
    pause: (id: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/research/missions/${id}/pause`)),
    reports: (p?: { mission_id?: string; team?: string; limit?: number }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/research/reports${qs(p)}`)),
    teams: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/research/teams')),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/research/stats')),
  },

  financialHub: {
    prices: (symbol: string, limit?: number): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/financial-hub/prices/${symbol}${qs({ limit })}`)),
    economic: (seriesId: string, limit?: number): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/financial-hub/economic/${seriesId}${qs({ limit })}`)),
    filings: (p?: { form?: string; limit?: number }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/financial-hub/filings${qs(p)}`)),
    watchlist: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/financial-hub/watchlist')),
    addWatchlist: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/financial-hub/watchlist', p)),
    removeWatchlist: (symbol: string): Promise<any> =>
      call((b) => b.sidecar.request('DELETE', `/api/financial-hub/watchlist/${symbol}`)),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/financial-hub/stats')),
  },

  cpaOps: {
    updates: (p?: { category?: string; priority?: string; limit?: number }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/cpa-ops/updates${qs(p)}`)),
    ingest: (): Promise<any> => call((b) => b.sidecar.request('POST', '/api/cpa-ops/ingest')),
    digest: (): Promise<any> => call((b) => b.sidecar.request('POST', '/api/cpa-ops/digest')),
    advisories: (p?: { status?: string; advisory_type?: string }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/cpa-ops/advisories${qs(p)}`)),
    createAdvisory: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/cpa-ops/advisories', p)),
    compliance: (p?: { category?: string; status?: string }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/cpa-ops/compliance${qs(p)}`)),
    addCompliance: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/cpa-ops/compliance', p)),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/cpa-ops/stats')),
  },

  marketIntel: {
    generateBrief: (): Promise<any> => call((b) => b.sidecar.request('POST', '/api/market-intel/brief/generate')),
    latestBrief: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/market-intel/brief/latest')),
    briefs: (limit?: number): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/market-intel/briefs${qs({ limit })}`)),
    signals: (p?: { signal_type?: string; symbol?: string; status?: string }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/market-intel/signals${qs(p)}`)),
    detectSignals: (): Promise<any> => call((b) => b.sidecar.request('POST', '/api/market-intel/signals/detect')),
    dismissSignal: (id: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/market-intel/signals/${id}/dismiss`)),
    watchlistAlerts: (p?: { symbol?: string }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/market-intel/watchlist-alerts${qs(p)}`)),
    macro: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/market-intel/macro/latest')),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/market-intel/stats')),
  },

  fusion: {
    run: (): Promise<any> => call((b) => b.sidecar.request('POST', '/api/fusion/run')),
    events: (p?: { status?: string; severity?: string; limit?: number }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/fusion/events${qs(p)}`)),
    acknowledgeEvent: (id: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/fusion/events/${id}/acknowledge`)),
    rules: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/fusion/rules')),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/fusion/stats')),
  },

  eventMonitor: {
    scan: (): Promise<any> => call((b) => b.sidecar.request('POST', '/api/event-monitor/scan')),
    checkDeadlines: (): Promise<any> => call((b) => b.sidecar.request('POST', '/api/event-monitor/check-deadlines')),
    events: (p?: { category?: string; severity?: string; status?: string }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/event-monitor/events${qs(p)}`)),
    acknowledgeEvent: (id: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/event-monitor/events/${id}/acknowledge`)),
    resolveEvent: (id: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/event-monitor/events/${id}/resolve`)),
    deadlines: (p?: { category?: string; status?: string }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/event-monitor/deadlines${qs(p)}`)),
    addDeadline: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/event-monitor/deadlines', p)),
    rules: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/event-monitor/rules')),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/event-monitor/stats')),
  },

  workforceAgents: {
    list: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/agents')),
    run: (id: string, p?: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/agents/${id}/run`, p || { trigger: 'manual', inputs: {} })),
    runs: (id: string, limit?: number): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/agents/${id}/runs${qs({ limit })}`)),
    actions: (id: string, status?: string): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/agents/${id}/actions${qs({ status })}`)),
    pendingApprovals: (limit?: number): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/agents/approvals/pending${qs({ limit })}`)),
    approve: (actionId: string, approvedBy?: string): Promise<any> =>
      call((b) => b.sidecar.request('POST', `/api/agents/actions/${actionId}/approve`, { approved_by: approvedBy || 'user' })),
    reject: (actionId: string): Promise<any> =>
      call((b) => b.sidecar.request('POST', `/api/agents/actions/${actionId}/reject`)),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/agents/stats/all')),
  },

  // Phase 14 — quant lab, backtesting, portfolio, risk, factors, alt-data,
  // thesis, earnings, macro, investment agents & portfolio command center.
  quantLab: {
    strategies: (p?: { status?: string; category?: string }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/quant-lab/strategies${qs(p)}`)),
    createStrategy: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/quant-lab/strategies', p)),
    getStrategy: (id: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/quant-lab/strategies/${id}`)),
    updateStrategy: (id: string, p: any): Promise<any> => call((b) => b.sidecar.request('PUT', `/api/quant-lab/strategies/${id}`, p)),
    versions: (id: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/quant-lab/strategies/${id}/versions`)),
    runExperiment: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/quant-lab/experiments', p)),
    experiments: (p?: { strategy_id?: string }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/quant-lab/experiments${qs(p)}`)),
    hypotheses: (status?: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/quant-lab/hypotheses${qs({ status })}`)),
    createHypothesis: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/quant-lab/hypotheses', p)),
    notebooks: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/quant-lab/notebooks')),
    createNotebook: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/quant-lab/notebooks', p)),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/quant-lab/stats')),
  },

  backtesting: {
    run: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/backtesting/run', p)),
    walkForward: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/backtesting/walk-forward', p)),
    monteCarlo: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/backtesting/monte-carlo', p)),
    sensitivity: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/backtesting/sensitivity', p)),
    runs: (p?: { strategy_id?: string }): Promise<any> => call((b) => b.sidecar.request('GET', `/api/backtesting/runs${qs(p)}`)),
    getRun: (id: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/backtesting/runs/${id}`)),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/backtesting/stats')),
  },

  portfolioLab: {
    methods: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/portfolio-lab/methods')),
    list: (status?: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/portfolio-lab/portfolios${qs({ status })}`)),
    construct: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/portfolio-lab/portfolios', p)),
    get: (id: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/portfolio-lab/portfolios/${id}`)),
    rebalance: (id: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/portfolio-lab/portfolios/${id}/rebalance`)),
    rebalances: (p?: { portfolio_id?: string; status?: string }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/portfolio-lab/rebalances${qs(p)}`)),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/portfolio-lab/stats')),
  },

  riskAnalytics: {
    analyze: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/risk-analytics/analyze', p)),
    stressTest: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/risk-analytics/stress-test', p)),
    scenario: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/risk-analytics/scenario', p)),
    factorExposure: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/risk-analytics/factor-exposure', p)),
    scenarios: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/risk-analytics/scenarios')),
    reports: (p?: { portfolio_id?: string }): Promise<any> => call((b) => b.sidecar.request('GET', `/api/risk-analytics/reports${qs(p)}`)),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/risk-analytics/stats')),
  },

  factors: {
    library: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/factors/library')),
    score: (symbol: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/factors/score/${symbol}`)),
    rank: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/factors/rank', p)),
    combine: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/factors/combine', p)),
    snapshot: (symbols: string[]): Promise<any> => call((b) => b.sidecar.request('POST', '/api/factors/snapshot', { symbols })),
    custom: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/factors/custom')),
    createCustom: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/factors/custom', p)),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/factors/stats')),
  },

  altdata: {
    datasets: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/altdata/datasets')),
    ingest: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/altdata/ingest', p)),
    observations: (dataset: string, symbol?: string): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/altdata/observations/${dataset}${qs({ symbol })}`)),
    generateSignals: (dataset: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/altdata/signals/${dataset}`)),
    signals: (dataset?: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/altdata/signals${qs({ dataset })}`)),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/altdata/stats')),
  },

  thesis: {
    list: (p?: { status?: string; symbol?: string }): Promise<any> => call((b) => b.sidecar.request('GET', `/api/thesis/theses${qs(p)}`)),
    create: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/thesis/theses', p)),
    get: (id: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/thesis/theses/${id}`)),
    update: (id: string, fields: any): Promise<any> => call((b) => b.sidecar.request('PUT', `/api/thesis/theses/${id}`, { fields })),
    addReview: (id: string, p: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/thesis/theses/${id}/review`, p)),
    reviews: (id: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/thesis/theses/${id}/reviews`)),
    close: (id: string, p: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/thesis/theses/${id}/close`, p)),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/thesis/stats')),
  },

  earnings: {
    events: (p?: { symbol?: string; status?: string }): Promise<any> => call((b) => b.sidecar.request('GET', `/api/earnings/events${qs(p)}`)),
    addEvent: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/earnings/events', p)),
    surprise: (eid: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/earnings/events/${eid}/surprise`)),
    scorecard: (eid: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/earnings/events/${eid}/scorecard`)),
    scorecards: (p?: { symbol?: string }): Promise<any> => call((b) => b.sidecar.request('GET', `/api/earnings/scorecards${qs(p)}`)),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/earnings/stats')),
  },

  macro: {
    indicators: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/macro/indicators')),
    yieldCurve: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/macro/yield-curve')),
    classifyRegime: (): Promise<any> => call((b) => b.sidecar.request('POST', '/api/macro/regime')),
    regimeHistory: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/macro/regime/history')),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/macro/stats')),
  },

  quantAgents: {
    list: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/quant-agents')),
    run: (key: string, p?: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/quant-agents/${key}/run`, p || { trigger: 'manual', inputs: {} })),
    runs: (key: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/quant-agents/${key}/runs`)),
    actions: (key: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/quant-agents/${key}/actions`)),
  },

  portfolioCommand: {
    overview: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/portfolio-command/overview')),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/portfolio-command/stats')),
  },

  // Phase 15 — Voice OS, Conversation, Notifications, Presence, Ambient, LLM Runtime, Desktop
  voice: {
    status: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/voice/status')),
    setMode: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/voice/mode', p)),
    capabilities: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/voice/capabilities')),
    profiles: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/voice/profiles')),
    createProfile: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/voice/profiles', p)),
    getProfile: (pid: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/voice/profiles/${pid}`)),
    updateProfile: (pid: string, p: any): Promise<any> => call((b) => b.sidecar.request('PUT', `/api/voice/profiles/${pid}`, p)),
    activateProfile: (pid: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/voice/profiles/${pid}/activate`, {})),
    setSttEngine: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/voice/stt-engine', p)),
    setTtsEngine: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/voice/tts-engine', p)),
    synthesize: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/voice/synthesize', p)),
    transcribe: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/voice/transcribe', p)),
    wake: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/voice/wake', p)),
    wakeHistory: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/voice/wake/history')),
    startSession: (p?: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/voice/sessions', p || {})),
    sessions: (limit?: number): Promise<any> => call((b) => b.sidecar.request('GET', `/api/voice/sessions${qs({ limit })}`)),
    getSession: (sid: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/voice/sessions/${sid}`)),
    endSession: (sid: string, p?: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/voice/sessions/${sid}/end`, p || {})),
    addTurn: (sid: string, p: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/voice/sessions/${sid}/turns`, p)),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/voice/stats')),
  },

  conversation: {
    createThread: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/conversation/threads', p)),
    threads: (p?: any): Promise<any> => call((b) => b.sidecar.request('GET', `/api/conversation/threads${qs(p)}`)),
    getThread: (tid: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/conversation/threads/${tid}`)),
    sendMessage: (tid: string, p: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/conversation/threads/${tid}/messages`, p)),
    getContext: (tid: string, maxTurns?: number): Promise<any> => call((b) => b.sidecar.request('GET', `/api/conversation/threads/${tid}/context${qs({ max_turns: maxTurns })}`)),
    closeThread: (tid: string, p?: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/conversation/threads/${tid}/close`, p || {})),
    summarize: (tid: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/conversation/threads/${tid}/summarize`, {})),
    search: (q: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/conversation/search${qs({ q })}`)),
    analytics: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/conversation/analytics')),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/conversation/stats')),
  },

  notifications: {
    send: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/notifications/send', p)),
    list: (p?: any): Promise<any> => call((b) => b.sidecar.request('GET', `/api/notifications/${qs(p)}`)),
    markRead: (nid: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/notifications/${nid}/read`, {})),
    markAllRead: (): Promise<any> => call((b) => b.sidecar.request('POST', '/api/notifications/read-all', {})),
    dismiss: (nid: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/notifications/${nid}/dismiss`, {})),
    escalate: (nid: string, p: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/notifications/${nid}/escalate`, p)),
    quietHours: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/notifications/quiet-hours')),
    setQuietHours: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/notifications/quiet-hours', p)),
    focusMode: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/notifications/focus-mode')),
    setFocusMode: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/notifications/focus-mode', p)),
    batch: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/notifications/batch')),
    channels: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/notifications/channels')),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/notifications/stats')),
  },

  presence: {
    state: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/presence/state')),
    setMode: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/presence/mode', p)),
    getMode: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/presence/mode')),
    updateContext: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/presence/context', p)),
    getContext: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/presence/context')),
    setCalendar: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/presence/calendar', p)),
    getCalendar: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/presence/calendar')),
    setFocus: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/presence/focus', p)),
    getFocus: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/presence/focus')),
    history: (limit?: number): Promise<any> => call((b) => b.sidecar.request('GET', `/api/presence/history${qs({ limit })}`)),
    adaptive: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/presence/adaptive')),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/presence/stats')),
  },

  ambient: {
    generateBriefing: (p?: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/ambient/briefing', p || {})),
    latestBriefing: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/ambient/briefing')),
    briefingHistory: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/ambient/briefing/history')),
    addReminder: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/ambient/reminders', p)),
    reminders: (activeOnly?: boolean): Promise<any> => call((b) => b.sidecar.request('GET', `/api/ambient/reminders${qs({ active_only: activeOnly })}`)),
    dismissReminder: (rid: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/ambient/reminders/${rid}/dismiss`, {})),
    checkTriggers: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/ambient/triggers')),
    recordAlert: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/ambient/alerts', p)),
    alerts: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/ambient/alerts')),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/ambient/stats')),
  },

  llmRuntime: {
    models: (p?: any): Promise<any> => call((b) => b.sidecar.request('GET', `/api/llm-runtime/models${qs(p)}`)),
    registerModel: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/llm-runtime/models', p)),
    getModel: (name: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/llm-runtime/models/${name}`)),
    route: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/llm-runtime/route', p)),
    budgetContext: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/llm-runtime/budget-context', p)),
    optimizePrompt: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/llm-runtime/optimize-prompt', p)),
    cacheResponse: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/llm-runtime/cache', p)),
    recordInference: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/llm-runtime/inference', p)),
    metrics: (model?: string, hours?: number): Promise<any> => call((b) => b.sidecar.request('GET', `/api/llm-runtime/metrics${qs({ model, hours })}`)),
    gpu: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/llm-runtime/gpu')),
    benchmark: (name: string, p?: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/llm-runtime/benchmark/${name}`, p || {})),
    performance: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/llm-runtime/performance')),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/llm-runtime/stats')),
  },

  desktop: {
    launch: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/desktop/launch', p)),
    apps: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/desktop/apps')),
    focus: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/desktop/focus', p)),
    readClipboard: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/desktop/clipboard')),
    writeClipboard: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/desktop/clipboard', p)),
    openFile: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/desktop/open-file', p)),
    listDirectory: (path?: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/desktop/directory${qs({ path })}`)),
    searchFiles: (p?: any): Promise<any> => call((b) => b.sidecar.request('GET', `/api/desktop/search-files${qs(p)}`)),
    systemInfo: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/desktop/system-info')),
    resources: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/desktop/resources')),
    createAutomation: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/desktop/automations', p)),
    automations: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/desktop/automations')),
    runAutomation: (aid: string, p?: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/desktop/automations/${aid}/run`, p || {})),
    approvals: (status?: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/desktop/approvals${qs({ status })}`)),
    approve: (aid: string, p?: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/desktop/approvals/${aid}/approve`, p || {})),
    reject: (aid: string, p?: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/desktop/approvals/${aid}/reject`, p || {})),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/desktop/stats')),
  },

  voiceAgents: {
    list: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/voice-agents')),
    run: (key: string, p?: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/voice-agents/${key}/run`, p || { trigger: 'manual', inputs: {} })),
    runs: (key: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/voice-agents/${key}/runs`)),
    actions: (key: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/voice-agents/${key}/actions`)),
  },

  // ── Phase 15.5 — Live Operations, Stability & Continuous Evolution ──────────
  runtime: {
    mode: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/runtime/mode')),
    setMode: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/runtime/mode', p)),
    diagnostics: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/runtime/diagnostics')),
    dependencyCheck: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/runtime/dependency-check')),
    dbIntegrity: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/runtime/db-integrity')),
    healthValidation: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/runtime/health-validation')),
    safeStartup: (): Promise<any> => call((b) => b.sidecar.request('POST', '/api/runtime/safe-startup', {})),
    dailyDriver: (): Promise<any> => call((b) => b.sidecar.request('POST', '/api/runtime/daily-driver', {})),
    recordCrash: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/runtime/crash', p)),
    recoverCrash: (id: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/runtime/crash/${id}/recover`, {})),
    crashes: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/runtime/crashes')),
    modeHistory: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/runtime/mode/history')),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/runtime/stats')),
  },

  featureFlags: {
    create: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/feature-flags/', p)),
    list: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/feature-flags/')),
    get: (key: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/feature-flags/${key}`)),
    enable: (key: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/feature-flags/${key}/enable`, {})),
    disable: (key: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/feature-flags/${key}/disable`, {})),
    setRollout: (key: string, p: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/feature-flags/${key}/rollout`, p)),
    setRoles: (key: string, p: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/feature-flags/${key}/roles`, p)),
    setWorkspaces: (key: string, p: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/feature-flags/${key}/workspaces`, p)),
    kill: (key: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/feature-flags/${key}/kill`, {})),
    revive: (key: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/feature-flags/${key}/revive`, {})),
    evaluate: (key: string, p: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/feature-flags/${key}/evaluate`, p)),
    analytics: (key: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/feature-flags/${key}/analytics`)),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/feature-flags/stats')),
  },

  releaseChannels: {
    channels: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/release-channels/')),
    assignments: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/release-channels/assignments')),
    assign: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/release-channels/assign', p)),
    assigned: (p: any): Promise<any> => call((b) => b.sidecar.request('GET', `/api/release-channels/assigned${qs(p)}`)),
    pin: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/release-channels/pin', p)),
    getPin: (p: any): Promise<any> => call((b) => b.sidecar.request('GET', `/api/release-channels/pin${qs(p)}`)),
    rollback: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/release-channels/rollback', p)),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/release-channels/stats')),
  },

  migrations: {
    register: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/migrations/', p)),
    list: (status?: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/migrations/${qs({ status })}`)),
    pending: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/migrations/pending')),
    applied: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/migrations/applied')),
    apply: (id: string, p?: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/migrations/${id}/apply`, p || {})),
    rollback: (id: string, p?: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/migrations/${id}/rollback`, p || {})),
    validate: (id: string): Promise<any> => call((b) => b.sidecar.request('POST', `/api/migrations/${id}/validate`, {})),
    currentVersion: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/migrations/current-version')),
    history: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/migrations/history')),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/migrations/stats')),
  },

  pluginUpgrades: {
    register: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/plugin-upgrades/register', p)),
    versions: (pluginId?: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/plugin-upgrades/versions${qs({ plugin_id: pluginId })}`)),
    installed: (pluginId: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/plugin-upgrades/installed${qs({ plugin_id: pluginId })}`)),
    compatibility: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/plugin-upgrades/compatibility', p)),
    resolve: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/plugin-upgrades/resolve', p)),
    plan: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/plugin-upgrades/plan', p)),
    sandboxVerify: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/plugin-upgrades/sandbox-verify', p)),
    apply: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/plugin-upgrades/apply', p)),
    rollback: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/plugin-upgrades/rollback', p)),
    history: (pluginId?: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/plugin-upgrades/history${qs({ plugin_id: pluginId })}`)),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/plugin-upgrades/stats')),
  },

  feedback: {
    capture: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/feedback/', p)),
    list: (p?: any): Promise<any> => call((b) => b.sidecar.request('GET', `/api/feedback/${qs(p)}`)),
    get: (id: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/feedback/${id}`)),
    setStatus: (id: string, p: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/feedback/${id}/status`, p)),
    resolve: (id: string, p?: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/feedback/${id}/resolve`, p || {})),
    topFriction: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/feedback/top/friction')),
    topFailures: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/feedback/top/failures')),
    summary: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/feedback/summary')),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/feedback/stats')),
  },

  evolution: {
    add: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/evolution/', p)),
    list: (p?: any): Promise<any> => call((b) => b.sidecar.request('GET', `/api/evolution/${qs(p)}`)),
    get: (id: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/evolution/${id}`)),
    update: (id: string, p: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/evolution/${id}`, p)),
    setStatus: (id: string, p: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/evolution/${id}/status`, p)),
    assign: (id: string, p: any): Promise<any> => call((b) => b.sidecar.request('POST', `/api/evolution/${id}/assign`, p)),
    prioritized: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/evolution/prioritized')),
    roadmap: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/evolution/roadmap')),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/evolution/stats')),
  },

  stability: {
    recordCrash: (p: any): Promise<any> => call((b) => b.sidecar.request('POST', '/api/stability/crash', p)),
    crashes: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/stability/crashes')),
    crashAnalysis: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/stability/crash-analysis')),
    clusters: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/stability/clusters')),
    slowWorkflows: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/stability/slow-workflows')),
    longTasks: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/stability/long-tasks')),
    memoryLeak: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/stability/memory-leak')),
    reliability: (kind?: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/stability/reliability${qs({ kind })}`)),
    agentReliability: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/stability/reliability/agents')),
    connectorReliability: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/stability/reliability/connectors')),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/stability/stats')),
  },

  opsDashboard: {
    overview: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/ops-dashboard/overview')),
    systemHealth: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/ops-dashboard/system-health')),
    agentHealth: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/ops-dashboard/agent-health')),
    connectorHealth: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/ops-dashboard/connector-health')),
    voiceHealth: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/ops-dashboard/voice-health')),
    storage: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/ops-dashboard/storage')),
    memoryGrowth: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/ops-dashboard/memory-growth')),
    knowledgeGrowth: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/ops-dashboard/knowledge-growth')),
    mostUsed: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/ops-dashboard/most-used')),
    recentFailures: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/ops-dashboard/recent-failures')),
    pendingApprovals: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/ops-dashboard/pending-approvals')),
    snapshot: (): Promise<any> => call((b) => b.sidecar.request('POST', '/api/ops-dashboard/snapshot', {})),
    snapshots: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/ops-dashboard/snapshots')),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/ops-dashboard/stats')),
  },

  // ── Phase 15.75 — Investment Discovery Engine ──────────────────────────────
  discovery: {
    universeStats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/discovery/universe/stats')),
    universe: (p?: { sector?: string; cap_tier?: string; exchange?: string; limit?: number }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/discovery/universe${qs(p)}`)),
    security: (symbol: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/discovery/universe/${symbol}`)),
    seed: (): Promise<any> => call((b) => b.sidecar.request('POST', '/api/discovery/universe/seed', {})),
    ingest: (securities: any[]): Promise<any> => call((b) => b.sidecar.request('POST', '/api/discovery/universe/ingest', { securities })),
    strategies: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/discovery/scan/strategies')),
    scan: (strategy: string, limit?: number): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/discovery/scan${qs({ strategy, limit })}`)),
    rank: (p?: { limit?: number; exclude_mega_cap?: boolean; penalize_coverage?: boolean; portfolio_overlap?: string[] }): Promise<any> =>
      call((b) => b.sidecar.request('POST', '/api/discovery/rank', p || {})),
    ideas: (tier?: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/discovery/ideas${qs({ tier })}`)),
    memo: (symbol: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/discovery/memo/${symbol}`)),
    portfolios: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/discovery/portfolios')),
    buildPortfolio: (p: { style: string; size?: number }): Promise<any> =>
      call((b) => b.sidecar.request('POST', '/api/discovery/portfolios/build', p)),
    daily: (): Promise<any> => call((b) => b.sidecar.request('POST', '/api/discovery/daily', {})),
    dailyLatest: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/discovery/daily/latest')),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/discovery/stats')),
  },

  // ── Phase 15.75 — Language Academy ─────────────────────────────────────────
  languageAcademy: {
    languages: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/language-academy/languages')),
    curriculum: (language: string, level?: string): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/language-academy/curriculum${qs({ language, level })}`)),
    lessons: (p?: { language?: string; level?: string; topic?: string; limit?: number }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/language-academy/lessons${qs(p)}`)),
    lesson: (lessonId: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/language-academy/lessons/${lessonId}`)),
    generateLesson: (p: { language: string; level: string; topic: string }): Promise<any> =>
      call((b) => b.sidecar.request('POST', '/api/language-academy/lessons/generate', p)),
    vocabulary: (p: { language: string; topic?: string; level?: string; limit?: number }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/language-academy/vocabulary${qs(p)}`)),
    vocabTopics: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/language-academy/vocabulary/topics')),
    review: (p: { language: string; limit?: number }): Promise<any> =>
      call((b) => b.sidecar.request('POST', '/api/language-academy/vocabulary/review', p)),
    grade: (p: { card_id: string; grade: number }): Promise<any> =>
      call((b) => b.sidecar.request('POST', '/api/language-academy/vocabulary/grade', p)),
    grammar: (language: string, level?: string): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/language-academy/grammar${qs({ language, level })}`)),
    grammarRule: (ruleId: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/language-academy/grammar/${ruleId}`)),
    grammarCheck: (p: { language: string; text: string; rule_id?: string }): Promise<any> =>
      call((b) => b.sidecar.request('POST', '/api/language-academy/grammar/check', p)),
    scenarios: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/language-academy/conversation/scenarios')),
    startConversation: (p: { language: string; scenario: string; level?: string }): Promise<any> =>
      call((b) => b.sidecar.request('POST', '/api/language-academy/conversation/start', p)),
    respond: (p: { session_id: string; text: string }): Promise<any> =>
      call((b) => b.sidecar.request('POST', '/api/language-academy/conversation/respond', p)),
    listening: (p?: { language?: string; level?: string }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/language-academy/listening${qs(p)}`)),
    listeningExercise: (exId: string): Promise<any> => call((b) => b.sidecar.request('GET', `/api/language-academy/listening/${exId}`)),
    gradeListening: (p: { ex_id: string; answers: any }): Promise<any> =>
      call((b) => b.sidecar.request('POST', '/api/language-academy/listening/grade', p)),
    pronunciation: (p: { language: string; target: string; attempt: string }): Promise<any> =>
      call((b) => b.sidecar.request('POST', '/api/language-academy/pronunciation/score', p)),
    placement: (p: { language: string; answers?: any }): Promise<any> =>
      call((b) => b.sidecar.request('POST', '/api/language-academy/assessment/placement', p)),
    tests: (p?: { language?: string; level?: string; kind?: string }): Promise<any> =>
      call((b) => b.sidecar.request('GET', `/api/language-academy/assessment/tests${qs(p)}`)),
    submitTest: (p: { test_id: string; answers: any }): Promise<any> =>
      call((b) => b.sidecar.request('POST', '/api/language-academy/assessment/submit', p)),
    coachToday: (language: string): Promise<any> =>
      call((b) => b.sidecar.request('POST', '/api/language-academy/coach/today', { language })),
    stats: (): Promise<any> => call((b) => b.sidecar.request('GET', '/api/language-academy/stats')),
  },

  // main → renderer push (price alerts). No-op outside Electron.
  onAlert(cb: (a: any) => void): void {
    const b = bridge();
    if (b && b.alerts && typeof b.alerts.onTriggered === 'function') b.alerts.onTriggered(cb);
  },
};
