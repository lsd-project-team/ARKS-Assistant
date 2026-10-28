import { useState } from 'react';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { useAuth } from '../../auth/AuthContext';
import type { Client } from '../shared/client';
import { useHandoverDraft } from '../shared/drafts';
import { HandoverModal } from '../shared/HandoverModal';
import { EmptyState } from '../shared/Presentation';
import type { Definitions, HandoverRecord } from '../shared/types';
import { ids, text } from '../shared/types';
import { packageDescription } from './packageContents';

export function PackageBuilder({
  scopeId,
  client,
  records,
  definitions,
  onSaved,
  onClose,
}: {
  scopeId: string;
  client: Client;
  records: HandoverRecord[];
  definitions: Definitions;
  onSaved: (row: HandoverRecord) => void;
  onClose: () => void;
}) {
  const user = useAuth().session?.user;
  const actor = user?.display_name || user?.username || '';
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
  const description = packageDescription(draft.payload);
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  return (
    <HandoverModal
      title="生成交接包"
      description="保存所选记录的当前版本，后续修改不影响此包。"
      className="package-builder"
      onClose={onClose}
      onSubmit={(event) => {
        event.preventDefault();
        setBusy(true);
        void client
          .send<HandoverRecord>('/packages', {
            ...draft.payload,
            scope: description,
            gaps: '',
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
            {busy ? '正在生成…' : '生成交接包'}
          </Button>
        </>
      }
    >
      <ErrorText error={error || warning} reveal />
      <fieldset disabled={busy}>
        <div className="handover-fields">
          <label className="handover-field-wide">
            <span>名称</span>
            <input
              required
              maxLength={200}
              value={draft.title}
              onChange={(event) => setDraft({ ...draft, title: event.target.value })}
            />
          </label>
        </div>
        <h3>选择交接内容</h3>
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
                  {definitions.kinds[row.kind]}
                  {row.kind !== 'debug_issue' &&
                    ` · v${row.version} · ${definitions.states[row.state]}`}
                </small>
              </span>
            </label>
          ))}
        </div>
        {!eligible.length && (
          <EmptyState title="暂无可打包的记录">先补充交接内容，再生成固定版本的交接包。</EmptyState>
        )}
        <details className="handover-form-section">
          <summary>补充信息（选填）</summary>
          <div className="handover-fields">
            <label className="handover-field-wide">
              <span>接收对象</span>
              <input
                maxLength={2000}
                value={text(draft.payload.recipient)}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    payload: { ...draft.payload, recipient: event.target.value },
                  })
                }
              />
            </label>
            <label className="handover-field-wide">
              <span>交接说明</span>
              <textarea
                rows={3}
                maxLength={100000}
                placeholder="可补充交接背景、缺项或尚未确认的条件"
                value={description}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    payload: { ...draft.payload, scope: event.target.value, gaps: '' },
                  })
                }
              />
            </label>
          </div>
        </details>
      </fieldset>
    </HandoverModal>
  );
}
