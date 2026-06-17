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
  { id: 'dashboard', label: 'Dashboard', icon: '⬡', group: 'Core', component: Dashboard },
  { id: 'markets', label: 'Markets', icon: '▤', group: 'Finance', component: Markets },
  { id: 'portfolio', label: 'Portfolio', icon: '◴', group: 'Finance', component: Portfolio },
  { id: 'accounting', label: 'Accounting', icon: '§', group: 'Finance', component: Accounting },
  { id: 'cpa', label: 'CPA Center', icon: '✓', group: 'Learning', component: CPACenter },
  { id: 'language', label: 'Language', icon: '⌘', group: 'Learning', component: Language },
  { id: 'calendar', label: 'Calendar', icon: '◷', group: 'Core', component: Calendar },
  { id: 'email', label: 'Email', icon: '✉', group: 'Core', component: Email },
  { id: 'memory', label: 'Memory', icon: '◉', group: 'System', component: Memory },
  { id: 'agents', label: 'Agents', icon: '⊹', group: 'System', component: AgentActivity },
  { id: 'automations', label: 'Automations', icon: '⚙', group: 'System', component: Automations },
  { id: 'settings', label: 'Settings', icon: '⚙', group: 'System', component: Settings },
];

export const ROUTE_BY_ID: Record<string, RouteDef> = Object.fromEntries(ROUTES.map((r) => [r.id, r]));
