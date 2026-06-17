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

  // main → renderer push (price alerts). No-op outside Electron.
  onAlert(cb: (a: any) => void): void {
    const b = bridge();
    if (b && b.alerts && typeof b.alerts.onTriggered === 'function') b.alerts.onTriggered(cb);
  },
};
