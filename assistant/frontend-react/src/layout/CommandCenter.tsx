import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { RightPanel } from './RightPanel';
import { useNav } from '../router';
import { ROUTE_BY_ID, ROUTES } from '../routes';

// Three-column command center: navigation · workspace · live intelligence.
export function CommandCenter() {
  const { active } = useNav();
  const route = ROUTE_BY_ID[active] ?? ROUTES[0];
  const View = route.component;

  return (
    <div className="h-screen w-screen flex bg-obsidian text-ivory">
      <Sidebar />
      <div className="flex-1 min-w-0 flex flex-col">
        <Topbar />
        <main className="flex-1 min-h-0 p-4 overflow-hidden">
          <View />
        </main>
      </div>
      <RightPanel />
    </div>
  );
}
