import { useState } from 'react';
import { Button, ErrorText } from '../../../shared/ui/ui';
import type { Client } from '../shared/client';
import { HandoverModal } from '../shared/HandoverModal';
import { EmptyState } from '../shared/Presentation';
import type { Definitions, HandoverRecord } from '../shared/types';

export function AIOperation({
  client,
  records,
  definitions,
  action,
  actor,
  onActor,
  onSaved,
  onClose,
}: {
  client: Client;
  records: HandoverRecord[];
  definitions: Definitions;
  action: string;
  actor: string;
  onActor: (value: string) => void;
  onSaved: (row: HandoverRecord) => void;
  onClose: () => void;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const eligible = records.filter(
    (row) => !['job', 'candidate', 'package'].includes(row.kind) && row.state !== 'archived',
  );
  const labels: Record<string, string> = {
    extract: '提取交接候选',
    plan: '生成接续计划候选',
    framework: '整理软件框架候选',
    training: '整理培训候选',
  };
  return (
    <HandoverModal
      title={labels[action]}
      description="分析所选记录的固定版本，结果需在候选区审核后合并。"
      className="handover-chooser"
      onClose={onClose}
      onSubmit={(event) => {
        event.preventDefault();
        setBusy(true);
        void client
          .send<HandoverRecord>('/ai', { action, record_ids: selected, actor })
          .then(onSaved)
          .catch(setError)
          .finally(() => setBusy(false));
      }}
      footer={
        <>
          <span>已选 {selected.length} 条</span>
          <Button
            type="submit"
            className="primary"
            disabled={busy || !selected.length || !actor.trim()}
          >
            {busy ? '正在提交…' : '开始分析'}
          </Button>
        </>
      }
    >
      <ErrorText error={error} reveal />
      <label className="handover-file-select">
        <span>发起人</span>
        <input
          required
          maxLength={120}
          value={actor}
          onChange={(event) => onActor(event.target.value)}
        />
      </label>
      <p className="handover-muted">
        选择 1–20 条资料。生成接续计划时选一个工作项，并附上对应的基线、资料与约束。
      </p>
      <div className="handover-selection-list">
        {eligible.map((row) => (
          <label key={row.id}>
            <input
              type="checkbox"
              checked={selected.includes(row.id)}
              disabled={busy || (!selected.includes(row.id) && selected.length >= 20)}
              onChange={(event) =>
                setSelected(
                  event.target.checked
                    ? [...selected, row.id]
                    : selected.filter((id) => id !== row.id),
                )
              }
            />
            <span>
              {row.title}
              <small>
                {definitions.kinds[row.kind]} · v{row.version} · {definitions.states[row.state]}
              </small>
            </span>
          </label>
        ))}
      </div>
      {!eligible.length && (
        <EmptyState title="暂无可分析的记录">先添加资料或工作项，再选择分析范围。</EmptyState>
      )}
    </HandoverModal>
  );
}
