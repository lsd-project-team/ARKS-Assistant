import { useEffect, useState } from 'react';

export function useUnsavedGuard(dirty: boolean, busy = false, additionalDirty = false) {
  const [pending, setPending] = useState<() => void>();
  useEffect(() => {
    if (!dirty && !additionalDirty) return;
    const protect = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', protect);
    return () => window.removeEventListener('beforeunload', protect);
  }, [dirty, additionalDirty]);
  return {
    pending: !!pending,
    request: (action: () => void) => {
      if (busy) return;
      if (dirty) setPending(() => action);
      else action();
    },
    cancel: () => setPending(undefined),
    discard: () => {
      setPending(undefined);
      pending?.();
    },
  };
}
