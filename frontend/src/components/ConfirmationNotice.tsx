import { useEffect, useRef, type ReactNode } from 'react';

export function ConfirmationNotice({
  children,
  busy = false,
}: {
  children: ReactNode;
  busy?: boolean;
}) {
  const notice = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (busy) return;
    // 长表单的确认区域可能在屏幕下方，出现时必须让用户看见并能直接操作。
    notice.current?.scrollIntoView({ block: 'nearest' });
    const buttons = notice.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)');
    Array.from(buttons || [])
      .find(
        (button) => !button.closest('details:not([open])') && button.getClientRects().length > 0,
      )
      ?.focus({ preventScroll: true });
  }, [busy]);
  return (
    <div ref={notice} className="unsaved-notice" role="alert">
      {children}
    </div>
  );
}
