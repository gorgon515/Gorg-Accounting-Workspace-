import { useEffect } from 'react';
import { NavProvider } from './router';
import { CommandCenter } from './layout/CommandCenter';
import { helios } from './ipc/client';
import { bus, pushNotification } from './lib/eventBus';

export default function App() {
  // Wire the Electron main → renderer push channels into the event bus once.
  useEffect(() => {
    helios.onAlert((a: any) => {
      const now = a?.triggeredPrice != null ? ` (now ${a.triggeredPrice})` : '';
      pushNotification({ kind: 'alert', title: `${a.symbol} ${a.direction} ${a.price}`, body: `Price alert${now}` });
      bus.emit('alert', a);
    });
  }, []);

  return (
    <NavProvider>
      <CommandCenter />
    </NavProvider>
  );
}
