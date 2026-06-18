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

export type RouteGroup = 'Core' | 'Finance' | 'Learning' | 'System';

export interface RouteDef {
  id: string;
  label: string;
  icon: string;
  group: RouteGroup;
  component: ComponentType;
}

// Order matches the HELIOS left-sidebar navigation spec.
export const ROUTES: RouteDef[] = [
  { id: 'assistant', label: 'Assistant', icon: '◈', group: 'Core', component: Assistant },
  { id: 'cos', label: 'Chief of Staff', icon: '★', group: 'Core', component: ChiefOfStaff },
  { id: 'dashboard', label: 'Dashboard', icon: '⬡', group: 'Core', component: Dashboard },
  { id: 'markets', label: 'Markets', icon: '▤', group: 'Finance', component: Markets },
  { id: 'portfolio', label: 'Portfolio', icon: '◴', group: 'Finance', component: Portfolio },
  { id: 'accounting', label: 'Accounting', icon: '§', group: 'Finance', component: Accounting },
  { id: 'ledger', label: 'Ledger / Books', icon: '⊞', group: 'Finance', component: Ledger },
  { id: 'workbench', label: 'Tax & Advisory', icon: '⊟', group: 'Finance', component: Workbench },
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
  { id: 'settings', label: 'Settings', icon: '⚙', group: 'System', component: Settings },
];

export const ROUTE_BY_ID: Record<string, RouteDef> = Object.fromEntries(ROUTES.map((r) => [r.id, r]));
