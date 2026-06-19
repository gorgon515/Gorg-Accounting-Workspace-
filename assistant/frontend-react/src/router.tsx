import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { bus } from './lib/eventBus';

interface Nav {
  active: string;
  navigate: (id: string) => void;
}

const NavContext = createContext<Nav>({ active: 'dashboard', navigate: () => {} });

// Lightweight in-app router. An Electron desktop app has no URL to route, so a
// context-held active view id gives instant, dependency-free navigation. Other
// components can also navigate by emitting a 'navigate' bus event.
export function NavProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState('executive');
  useEffect(() => bus.on('navigate', (id?: any) => typeof id === 'string' && setActive(id)), []);
  return <NavContext.Provider value={{ active, navigate: setActive }}>{children}</NavContext.Provider>;
}

export const useNav = () => useContext(NavContext);
