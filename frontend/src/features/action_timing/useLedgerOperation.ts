import { useEffect, useRef, useState } from 'react';

export function useLedgerOperation() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  async function run(task: (signal: AbortSignal) => Promise<unknown>) {
    if (pending.current) return false;
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true);
    setError(undefined);
    try {
      await task(controller.signal);
      return !controller.signal.aborted;
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure);
      return false;
    } finally {
      pending.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return { busy, error, run, clearError: () => setError(undefined) };
}
