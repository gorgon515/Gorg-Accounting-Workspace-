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
