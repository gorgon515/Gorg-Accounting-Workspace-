import { useEffect } from 'react';
import { bus, type HeliosEvent } from '../lib/eventBus';

// Subscribe a component to a bus event for its lifetime.
export function useEventBus(event: HeliosEvent, handler: (payload?: any) => void): void {
  useEffect(() => bus.on(event, handler), [event, handler]);
}
