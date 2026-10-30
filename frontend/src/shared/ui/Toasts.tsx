import { useEffect, useState } from 'react';
import { Check, CircleAlert, X } from 'lucide-react';
import { useToasts, toast, type ToastItem } from '../utils/toasts';

function Toast({ item }: { item: ToastItem }) {
  const dismiss = useToasts((state) => state.dismiss);
  const [busy, setBusy] = useState(false);
  const [paused, setPaused] = useState(false);
  useEffect(() => {
    if (paused || busy) return;
    const timeout = setTimeout(
      () => dismiss(item.id),
      item.durationMs ?? (item.action ? 10_000 : 5000),
    );
    return () => clearTimeout(timeout);
  }, [item.id, item.action, item.durationMs, paused, busy, dismiss]);
  return (
    <div
      className={`toast ${item.tone}`}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      {!item.plain && (item.tone === 'error' ? <CircleAlert size={15} /> : <Check size={15} />)}
      <span>{item.message}</span>
      {item.action && (
        <button
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await item.action!.run();
              dismiss(item.id);
            } catch (error) {
              toast(
                error instanceof Error ? error.message : '操作失败，请重试',
                undefined,
                'error',
              );
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? '处理中…' : item.action.label}
        </button>
      )}
      {!item.plain && (
        <button aria-label="关闭提示" onClick={() => dismiss(item.id)}>
          <X size={13} />
        </button>
      )}
    </div>
  );
}

export function Toasts() {
  const items = useToasts((state) => state.items);
  return (
    <div className="toast-stack" role="log" aria-live="polite" aria-relevant="additions">
      {items.map((item) => (
        <Toast key={item.id} item={item} />
      ))}
    </div>
  );
}
