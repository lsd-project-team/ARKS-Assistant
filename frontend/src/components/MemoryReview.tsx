import type { MemoryReview as Review, MemoryRevision } from '../types';
import { ConfirmationNotice } from './ConfirmationNotice';
import { Button } from './ui';

const labels = { duplicate: '已有相同内容', conflict: '潜在事实冲突', similar: '内容相关，需复核' };

export function MemoryReview({
  rows,
  restoring,
  busy,
  onOpen,
  onConfirm,
  onCancel,
}: {
  rows: Review[];
  restoring?: MemoryRevision;
  busy: boolean;
  onOpen: (row: Review) => void;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!rows.length && !restoring) return null;
  const duplicate = rows.some((row) => row.kind === 'duplicate');
  return (
    <ConfirmationNotice busy={busy}>
      <div className="memory-review">
        <strong>{restoring ? '确认恢复历史版本' : '保存前核对相关记忆'}</strong>
        <p className="muted">
          检查包含词面、同名字段和自然语言复核。AI 提示的潜在矛盾仍需核对主体、时间与条件。
        </p>
        {restoring && <pre>{restoring.content}</pre>}
        {rows.map((row) => (
          <details key={`${row.scope}/${row.name}`}>
            <summary>
              {labels[row.kind]} · {row.name}
            </summary>
            <p>{row.reason}</p>
            <pre>{row.content}</pre>
            <Button disabled={busy} onClick={() => onOpen(row)}>
              打开已有记忆
            </Button>
          </details>
        ))}
        {restoring && (
          <p className="muted">将覆盖当前记忆，覆盖前的版本继续保留。其他记忆不会自动改动。</p>
        )}
        <div className="button-row">
          <Button disabled={busy} onClick={onCancel}>
            取消
          </Button>
          {!duplicate && (
            <Button disabled={busy} onClick={onConfirm}>
              {restoring ? '确认恢复此版本' : '核对后仍保存'}
            </Button>
          )}
        </div>
      </div>
    </ConfirmationNotice>
  );
}
