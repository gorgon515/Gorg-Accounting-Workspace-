// Shared types for IPC payloads. Kept intentionally tolerant (optional fields)
// because the data originates from the Node services at runtime.

export interface BrainStatus {
  engine?: string;
  model?: string;
  ready?: boolean;
  local?: boolean;
  reason?: string;
}
export interface AppConfig {
  hasBrain?: boolean;
  brain?: BrainStatus;
  model?: string;
  wakeWord?: string;
  stt?: { engine?: string; model?: string; ready?: boolean };
}

export interface AgentRosterItem {
  key: string;
  name: string;
  role: string;
  persona?: string;
  skills: string[];
  permissions?: { memory?: string; canPropose?: boolean };
  tools: number;
  status: 'online' | 'idle' | 'planned';
  planned?: string | null;
}
export interface AgentActivity {
  agent: string;
  name: string;
  tool: string | null;
  ok: boolean;
  confidence?: string | null;
  ts: number;
}
export interface RouteResult {
  agent: string;
  name: string;
  score: number;
  confidence: 'low' | 'medium' | 'high';
  alternates: string[];
}

export interface SidecarStatus {
  ready: boolean;
  url: string;
  managed?: boolean;
  autostart?: boolean;
  reason?: string | null;
}
export interface AnalyzeResult {
  symbol?: string;
  price: number;
  points: number;
  trend?: string;
  rsi14?: number;
  macd?: { macd: number; signal: number; histogram: number };
  bollinger?: { middle: number; upper: number; lower: number; percent_b: number };
  momentum_20?: number;
  volatility_annualized?: number;
  max_drawdown?: number;
  signals: string[];
}
export interface FactorResult {
  symbol: string;
  composite: number | null;
  rating: string;
  factors: Record<string, { score: number | null; metrics_used: number; rating: string }>;
  coverage: { factors_scored: number; metrics_used: number };
}
export interface MemoResult {
  issue: string;
  facts: string;
  guidance: { citation: string; title: string; summary: string; framework: string[] };
  analysis: string;
  conclusion: string;
  disclosure_impact: string[];
  cpa_exam_impact: string;
  citations: string[];
}
export interface AscTopic {
  asc: string;
  title: string;
}

export interface LanguageMeta {
  code: string;
  name: string;
  native: string;
  flag: string;
}
export interface LanguageProgress {
  language: string;
  name: string;
  native: string;
  flag: string;
  selfLevel: string;
  estimatedLevel: string;
  words: number;
  dueNow: number;
  streakDays: number;
  missionsToday: number;
  missionsDoneToday: number;
}
export interface Mission {
  id: string;
  kind: string;
  text: string;
  done: boolean;
}
export interface CurriculumLevel {
  level: string;
  label: string;
  goals: string[];
}

export interface AcctSummary {
  income?: number;
  expenses?: number;
  net?: number;
  cash?: number;
  receivable?: number;
  byCategory?: Record<string, number>;
}
export interface CpaSection {
  section: string;
  progress: number;
  status: string;
  examDate: string | null;
}
export interface CpaStatus {
  provider: string;
  sections: CpaSection[];
  overallProgress: number;
  link: string;
}

export interface Quote {
  symbol: string;
  name?: string;
  price?: number;
  change?: number;
  changePercent?: number;
  currency?: string;
  error?: string;
}
export interface MemoryItem {
  id: string;
  fact: string;
  category: string;
  createdAt: string;
}
export interface Task {
  id: string;
  title?: string;
  text?: string;
  due?: string;
  done?: boolean;
}
