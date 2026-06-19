// Tiny in-app pub/sub event bus + notification store for the HUD.
//
// An Electron renderer has no global event system of its own; this bus lets
// decoupled components communicate (navigation, alerts, notifications) without
// prop-drilling or a heavyweight state library.

export type HeliosEvent = 'alert' | 'navigate' | 'notification' | 'agent' | 'refresh';

type Handler = (payload?: any) => void;

class EventBus {
  private handlers = new Map<HeliosEvent, Set<Handler>>();

  /** Subscribe to an event. Returns an unsubscribe function. */
  on(event: HeliosEvent, handler: Handler): () => void {
    let set = this.handlers.get(event);
    if (!set) {
      set = new Set();
      this.handlers.set(event, set);
    }
    set.add(handler);
    return () => {
      this.handlers.get(event)?.delete(handler);
    };
  }

  /** Emit an event to all subscribers. */
  emit(event: HeliosEvent, payload?: any): void {
    this.handlers.get(event)?.forEach((h) => {
      try {
        h(payload);
      } catch (err) {
        // A bad subscriber must not break the emitter.
        console.error(`[eventBus] handler for "${event}" threw`, err);
      }
    });
  }
}

export const bus = new EventBus();

// ---- Notification store -----------------------------------------------------

export interface Notification {
  id: string;
  kind: 'alert' | 'info' | 'agent' | 'accounting';
  title: string;
  body?: string;
  ts: number;
}

const _notifications: Notification[] = [];

/** Add a notification and broadcast a 'notification' event. */
export function pushNotification(n: Omit<Notification, 'id' | 'ts'> & { ts?: number }): Notification {
  const full: Notification = {
    id: `ntf_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    ts: n.ts ?? Date.now(),
    kind: n.kind,
    title: n.title,
    body: n.body,
  };
  _notifications.unshift(full);
  if (_notifications.length > 100) _notifications.length = 100;
  bus.emit('notification', full);
  return full;
}

/** Snapshot of current notifications, newest first. */
export function getNotifications(): Notification[] {
  return [..._notifications];
}

/** Clear all notifications and broadcast the change. */
export function clearNotifications(): void {
  _notifications.length = 0;
  bus.emit('notification');
}
