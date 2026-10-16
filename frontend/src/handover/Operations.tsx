import { HandoverModal } from './HandoverModal';
import { useState } from 'react';
import { Button, ErrorText } from '../components/ui';
import type { Client } from './client';
import { useHandoverDraft } from './drafts';
import type { Definitions, HandoverRecord } from './types';
import { ids, text } from './types';
import { EmptyState } from './Presentation';

export { SourceImport } from './SourceImport';

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

export function PackageBuilder({
  scopeId,
  client,
  records,
  definitions,
  actor,
  onActor,
  onSaved,
  onClose,
}: {
  scopeId: string;
  client: Client;
  records: HandoverRecord[];
  definitions: Definitions;
  actor: string;
  onActor: (value: string) => void;
  onSaved: (row: HandoverRecord) => void;
  onClose: () => void;
}) {
  const eligible = records.filter(
    (row) =>
      !['package', 'receipt', 'candidate', 'job'].includes(row.kind) && row.state !== 'archived',
  );
  const { draft, setDraft, clear, warning } = useHandoverDraft(scopeId, 'package', {
    title: '设备软件交接包',
    payload: { recipient: '', scope: '', gaps: '', record_ids: eligible.map((row) => row.id) },
  });
  // 旧草稿可能仍选中已移除的接收记录；提交和计数只使用当前可打包内容。
  const eligibleIds = new Set(eligible.map((row) => row.id));
  const selected = ids(draft.payload.record_ids).filter((id) => eligibleIds.has(id));
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  return (
    <HandoverModal
      title="生成固定版本交接包"
      description="固定所选记录的当前版本，未确认内容会标注。设备操作仍需按接续条件复核。"
      onClose={onClose}
      onSubmit={(event) => {
        event.preventDefault();
        setBusy(true);
        void client
          .send<HandoverRecord>('/packages', {
            ...draft.payload,
            record_ids: selected,
            title: draft.title,
            actor,
          })
          .then((row) => {
            clear();
            onSaved(row);
          })
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
            {busy ? '正在生成…' : '保存交接包快照'}
          </Button>
        </>
      }
    >
      <ErrorText error={error || warning} reveal />
      <fieldset disabled={busy}>
        <div className="handover-fields">
          <label>
            <span>标题</span>
            <input
              required
              maxLength={200}
              value={draft.title}
              onChange={(event) => setDraft({ ...draft, title: event.target.value })}
            />
          </label>
          <label>
            <span>整理人</span>
            <input
              required
              maxLength={120}
              value={actor}
              onChange={(event) => onActor(event.target.value)}
            />
          </label>
          {Object.entries({
            recipient: '接收对象',
            scope: '交接范围',
            gaps: '缺项与尚未确认的条件',
          }).map(([key, label]) => (
            <label key={key}>
              <span>{label}</span>
              <textarea
                aria-label={label}
                rows={3}
                value={text(draft.payload[key])}
                onChange={(event) =>
                  setDraft({ ...draft, payload: { ...draft.payload, [key]: event.target.value } })
                }
              />
            </label>
          ))}
        </div>
        <h3>包内记录</h3>
        <div className="handover-selection-list">
          {eligible.map((row) => (
            <label key={row.id}>
              <input
                type="checkbox"
                checked={selected.includes(row.id)}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    payload: {
                      ...draft.payload,
                      record_ids: event.target.checked
                        ? [...selected, row.id]
                        : selected.filter((id) => id !== row.id),
                    },
                  })
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
          <EmptyState title="暂无可打包的记录">先补充交接内容，再生成固定版本的交接包。</EmptyState>
        )}
      </fieldset>
    </HandoverModal>
  );
}
