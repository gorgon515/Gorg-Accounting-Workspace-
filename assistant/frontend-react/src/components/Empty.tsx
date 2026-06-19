import type { ReactNode } from 'react';

// Shared loading / error / empty / offline states so every panel handles the
// absence of the IPC bridge (or data) consistently.
export function EmptyState({ message }: { message: ReactNode }) {
  return <p className="text-[12px] text-warmgray py-6 text-center">{message}</p>;
}

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-6 text-warmgray text-[12px]">
      <span className="w-3 h-3 rounded-full border border-gold/60 border-t-transparent animate-spin" />
      {label}
    </div>
  );
}

export function ErrorState({ error }: { error: string }) {
  const offline = /bridge unavailable/i.test(error);
  return (
    <p className="text-[12px] text-warmgray py-6 text-center">
      {offline ? 'Live data appears when running inside the HELIOS desktop app.' : `Error: ${error}`}
    </p>
  );
}

// Convenience wrapper: render children only when data is present.
export function AsyncView<T>({
  state, children,
}: {
  state: { data: T | null; loading: boolean; error: string | null };
  children: (data: T) => ReactNode;
}) {
  if (state.loading && !state.data) return <Loading />;
  if (state.error && !state.data) return <ErrorState error={state.error} />;
  if (!state.data) return <EmptyState message="No data." />;
  return <>{children(state.data)}</>;
}
