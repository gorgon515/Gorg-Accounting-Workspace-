import type { ComponentType } from 'react';
import { Dashboard } from './views/Dashboard';
import { Assistant } from './views/Assistant';
import { Markets } from './views/Markets';
import { Portfolio } from './views/Portfolio';
import { Accounting } from './views/Accounting';
import { CPACenter } from './views/CPACenter';
import { Language } from './views/Language';
import { Calendar } from './views/Calendar';
import { Email } from './views/Email';
import { Memory } from './views/Memory';
import { Automations } from './views/Automations';
import { Settings } from './views/Settings';
import { AgentActivity } from './views/AgentActivity';
import { ChiefOfStaff } from './views/ChiefOfStaff';
import { Ledger } from './views/Ledger';
import { Workbench } from './views/Workbench';
import { Operations } from './views/Operations';
import { SecurityCenter } from './views/SecurityCenter';
import { BackupView } from './views/BackupView';
import { SyncView } from './views/SyncView';
import { HealthMonitor } from './views/HealthMonitor';
import { AuditCenter } from './views/AuditCenter';
import { WorkspaceCenter } from './views/WorkspaceCenter';
import { PluginManager } from './views/PluginManager';
import { APICenter } from './views/APICenter';
import { LicenseCenter } from './views/LicenseCenter';
import { PerformanceMonitor } from './views/PerformanceMonitor';
import { DeploymentCenter } from './views/DeploymentCenter';
import { ExecutiveCommandCenter } from './views/ExecutiveCommandCenter';
import { ForecastCenter } from './views/ForecastCenter';
import { ScenarioLab } from './views/ScenarioLab';
import { OpportunityCenter } from './views/OpportunityCenter';
import { RiskCenter } from './views/RiskCenter';
import { StrategicPlanningCenter } from './views/StrategicPlanningCenter';
import { KnowledgeCenter } from './views/KnowledgeCenter';
import { RAGCenter } from './views/RAGCenter';
import { ResearchCenter } from './views/ResearchCenter';
import { LearningCenter } from './views/LearningCenter';
import { ConnectorCenter } from './views/ConnectorCenter';
import { IntelligenceCenter } from './views/IntelligenceCenter';
import { ResearchMissions } from './views/ResearchMissions';
import { MarketOperations } from './views/MarketOperations';
import { CPAOperations } from './views/CPAOperations';
import { EventMonitor } from './views/EventMonitor';
import { SignalsDashboard } from './views/SignalsDashboard';
import { PortfolioCommandCenter } from './views/PortfolioCommandCenter';
import { QuantLab } from './views/QuantLab';
import { BacktestingCenter } from './views/BacktestingCenter';
import { PortfolioLab } from './views/PortfolioLab';
import { PortfolioRiskCenter } from './views/PortfolioRiskCenter';
import { FactorCenter } from './views/FactorCenter';
import { MacroCenter } from './views/MacroCenter';
import { ThesisCenter } from './views/ThesisCenter';
import { VoiceCenter } from './views/VoiceCenter';
import { ConversationCenter } from './views/ConversationCenter';
import { ExecutiveHUD } from './views/ExecutiveHUD';
import { NotificationCenter } from './views/NotificationCenter';
import { DesktopCenter } from './views/DesktopCenter';
import { PresenceCenter } from './views/PresenceCenter';
import { OperationsDashboard } from './views/OperationsDashboard';
import { DevelopmentCenter } from './views/DevelopmentCenter';
import { EvolutionCenter } from './views/EvolutionCenter';

export type RouteGroup = 'Core' | 'Strategy' | 'Finance' | 'Investing' | 'Knowledge' | 'Operations' | 'Learning' | 'System' | 'Experience' | 'Platform';

export interface RouteDef {
  id: string;
  label: string;
  icon: string;
  group: RouteGroup;
  component: ComponentType;
}

// Order matches the HELIOS left-sidebar navigation spec.
export const ROUTES: RouteDef[] = [
  { id: 'executive', label: 'Command Center', icon: '✦', group: 'Core', component: ExecutiveCommandCenter },
  { id: 'assistant', label: 'Assistant', icon: '◈', group: 'Core', component: Assistant },
  { id: 'cos', label: 'Chief of Staff', icon: '★', group: 'Core', component: ChiefOfStaff },
  { id: 'dashboard', label: 'Dashboard', icon: '⬡', group: 'Core', component: Dashboard },
  { id: 'forecast', label: 'Forecast Center', icon: '◇', group: 'Strategy', component: ForecastCenter },
  { id: 'scenario', label: 'Scenario Lab', icon: '⟿', group: 'Strategy', component: ScenarioLab },
  { id: 'opportunities', label: 'Opportunities', icon: '↗', group: 'Strategy', component: OpportunityCenter },
  { id: 'risks', label: 'Risk Center', icon: '⚠', group: 'Strategy', component: RiskCenter },
  { id: 'strategy', label: 'Strategic Planning', icon: '⊛', group: 'Strategy', component: StrategicPlanningCenter },
  { id: 'knowledge', label: 'Knowledge Center', icon: '◈', group: 'Knowledge', component: KnowledgeCenter },
  { id: 'rag', label: 'Semantic Search', icon: '⊗', group: 'Knowledge', component: RAGCenter },
  { id: 'research', label: 'Research', icon: '⊕', group: 'Knowledge', component: ResearchCenter },
  { id: 'learning', label: 'Learning Center', icon: '∞', group: 'Knowledge', component: LearningCenter },
  { id: 'intelligence', label: 'Intelligence Center', icon: '◎', group: 'Operations', component: IntelligenceCenter },
  { id: 'missions', label: 'Research Missions', icon: '⊕', group: 'Operations', component: ResearchMissions },
  { id: 'marketops', label: 'Market Operations', icon: '▥', group: 'Operations', component: MarketOperations },
  { id: 'cpaops', label: 'CPA Operations', icon: '⊡', group: 'Operations', component: CPAOperations },
  { id: 'events', label: 'Event Monitor', icon: '◔', group: 'Operations', component: EventMonitor },
  { id: 'signals', label: 'Signals Dashboard', icon: '⚹', group: 'Operations', component: SignalsDashboard },
  { id: 'connectors', label: 'Connector Center', icon: '⇆', group: 'Operations', component: ConnectorCenter },
  { id: 'markets', label: 'Markets', icon: '▤', group: 'Finance', component: Markets },
  { id: 'portfolio', label: 'Portfolio', icon: '◴', group: 'Finance', component: Portfolio },
  { id: 'accounting', label: 'Accounting', icon: '§', group: 'Finance', component: Accounting },
  { id: 'ledger', label: 'Ledger / Books', icon: '⊞', group: 'Finance', component: Ledger },
  { id: 'workbench', label: 'Tax & Advisory', icon: '⊟', group: 'Finance', component: Workbench },
  { id: 'pcc', label: 'Portfolio Command', icon: '◉', group: 'Investing', component: PortfolioCommandCenter },
  { id: 'quantlab', label: 'Quant Lab', icon: 'ƒ', group: 'Investing', component: QuantLab },
  { id: 'backtesting', label: 'Backtesting', icon: '⟲', group: 'Investing', component: BacktestingCenter },
  { id: 'portfoliolab', label: 'Portfolio Lab', icon: '◫', group: 'Investing', component: PortfolioLab },
  { id: 'portfoliorisk', label: 'Risk Center', icon: '⚠', group: 'Investing', component: PortfolioRiskCenter },
  { id: 'factors', label: 'Factor Center', icon: '⊞', group: 'Investing', component: FactorCenter },
  { id: 'macro', label: 'Macro Center', icon: '◍', group: 'Investing', component: MacroCenter },
  { id: 'theses', label: 'Thesis Center', icon: '✎', group: 'Investing', component: ThesisCenter },
  { id: 'cpa', label: 'CPA Center', icon: '✓', group: 'Learning', component: CPACenter },
  { id: 'language', label: 'Language', icon: '⌘', group: 'Learning', component: Language },
  { id: 'calendar', label: 'Calendar', icon: '◷', group: 'Core', component: Calendar },
  { id: 'email', label: 'Email', icon: '✉', group: 'Core', component: Email },
  { id: 'memory', label: 'Memory', icon: '◉', group: 'System', component: Memory },
  { id: 'operations', label: 'Operations', icon: '▶', group: 'System', component: Operations },
  { id: 'agents', label: 'Agents', icon: '⊹', group: 'System', component: AgentActivity },
  { id: 'automations', label: 'Automations', icon: '⚙', group: 'System', component: Automations },
  { id: 'security', label: 'Security Center', icon: '⚿', group: 'System', component: SecurityCenter },
  { id: 'backup', label: 'Backup & Recovery', icon: '⊙', group: 'System', component: BackupView },
  { id: 'sync', label: 'Sync', icon: '⇄', group: 'System', component: SyncView },
  { id: 'health', label: 'Health Monitor', icon: '♥', group: 'System', component: HealthMonitor },
  { id: 'audit', label: 'Audit Center', icon: '⊘', group: 'System', component: AuditCenter },
  { id: 'workspaces', label: 'Workspaces', icon: '⧉', group: 'System', component: WorkspaceCenter },
  { id: 'plugins', label: 'Plugins', icon: '⟐', group: 'System', component: PluginManager },
  { id: 'api', label: 'API Center', icon: '❯', group: 'System', component: APICenter },
  { id: 'license', label: 'License', icon: '◆', group: 'System', component: LicenseCenter },
  { id: 'performance', label: 'Performance', icon: '⚡', group: 'System', component: PerformanceMonitor },
  { id: 'deployment', label: 'Deployment', icon: '⬢', group: 'System', component: DeploymentCenter },
  { id: 'settings', label: 'Settings', icon: '⚙', group: 'System', component: Settings },
  { id: 'hud', label: 'Executive HUD', icon: '✦', group: 'Experience', component: ExecutiveHUD },
  { id: 'voice', label: 'Voice Center', icon: '◈', group: 'Experience', component: VoiceCenter },
  { id: 'conversation', label: 'Conversation', icon: '◎', group: 'Experience', component: ConversationCenter },
  { id: 'notifications', label: 'Notifications', icon: '◔', group: 'Experience', component: NotificationCenter },
  { id: 'desktop', label: 'Desktop Center', icon: '⬡', group: 'Experience', component: DesktopCenter },
  { id: 'presence', label: 'Presence', icon: '⊛', group: 'Experience', component: PresenceCenter },
  { id: 'opsdashboard', label: 'Operations', icon: '◉', group: 'Platform', component: OperationsDashboard },
  { id: 'devcenter', label: 'Development Center', icon: '⬡', group: 'Platform', component: DevelopmentCenter },
  { id: 'evolution', label: 'Evolution', icon: '∞', group: 'Platform', component: EvolutionCenter },
];

export const ROUTE_BY_ID: Record<string, RouteDef> = Object.fromEntries(ROUTES.map((r) => [r.id, r]));
