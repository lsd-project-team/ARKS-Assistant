import type { useUnsavedGuard } from '../hooks/useUnsavedGuard';
import { Button } from './ui';
import { ConfirmationNotice } from './ConfirmationNotice';

export function UnsavedNotice({ guard }: { guard: ReturnType<typeof useUnsavedGuard> }) {
  if (!guard.pending) return null;
  return (
    <ConfirmationNotice>
      <span>修改尚未保存。</span>
      <Button onClick={guard.cancel}>继续编辑</Button>
      <Button onClick={guard.discard}>放弃修改</Button>
    </ConfirmationNotice>
  );
}
