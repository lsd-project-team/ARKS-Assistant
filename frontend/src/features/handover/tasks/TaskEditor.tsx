import { useState } from 'react';
import { ApiError } from '../../../app/api/client';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { HandoverModal } from '../shared/HandoverModal';
import { HandoverSelect } from '../shared/Controls';
import { useHandoverDraft } from '../shared/drafts';
import type { Client } from '../shared/client';
import { text, type HandoverRecord, type Payload } from '../shared/types';
import {
  taskActor,
  taskEditablePayload,
  taskStage,
  taskStageLabel,
  taskStages,
} from './taskProgress';
import './task-progress.css';

export function TaskEditor({
  scopeId,
  client,
  row,
  initial = {},
  actor,
  onSaved,
  onClose,
}: {
  scopeId: string;
  client: Client;
  row?: HandoverRecord;
  initial?: Payload;
  actor: string;
  onSaved: (row: HandoverRecord) => void;
  onClose: () => void;
}) {
  const state = useHandoverDraft(scopeId, row?.id || 'new:task:', {
    title: row?.title || '',
    payload: { owner: '', work_status: 'todo', goal: '', notes: '', ...row?.payload, ...initial },
    version: row?.version,
  });
  const { draft, setDraft } = state;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [incoming, setIncoming] = useState<HandoverRecord>();
  const update = (key: string, value: string) =>
    setDraft({ ...draft, payload: { ...draft.payload, [key]: value } });
  async function save() {
    setBusy(true);
    setError(undefined);
    try {
      const result = await client.send<HandoverRecord>(
        row ? `/records/${row.id}` : '/records',
        {
          kind: 'task',
          title: draft.title.trim(),
          payload: draft.payload,
          actor: taskActor(actor),
          version: draft.version,
          reason: row ? '更新工作项与进度备注' : '',
        },
        row ? 'PATCH' : 'POST',
      );
      state.clear();
      onSaved(result);
    } catch (error) {
      setError(error);
    } finally {
      setBusy(false);
    }
  }
  async function readLatest() {
    if (!row) return;
    setBusy(true);
    try {
      setIncoming(await client.get<HandoverRecord>(`/records/${row.id}`));
    } catch (error) {
      setError(error);
    } finally {
      setBusy(false);
    }
  }
  return (
    <HandoverModal
      title={row ? '编辑工作' : '新增工作'}
      description="记录工作内容，直接更新状态和进度备注。"
      className="task-editor"
      onClose={onClose}
      onSubmit={(event) => {
        event.preventDefault();
        void save();
      }}
      footer={
        <>
          <Button type="button" disabled={busy} onClick={onClose}>
            关闭并保留填写
          </Button>
          <Button className="primary" type="submit" disabled={busy || !draft.title.trim()}>
            {busy ? '正在保存…' : '保存工作'}
          </Button>
        </>
      }
    >
      {state.restored && <p className="handover-notice">已恢复上次填写，请检查后保存。</p>}
      <ErrorText error={error || state.warning} reveal />
      {error instanceof ApiError && error.status === 409 && row && (
        <Button type="button" disabled={busy} onClick={() => void readLatest()}>
          查看最新内容
        </Button>
      )}
      {incoming && (
        <section className="handover-conflict">
          <h3>最新内容 · v{incoming.version}</h3>
          <dl className="handover-record-fields">
            <div>
              <dt>工作名称</dt>
              <dd>{incoming.title}</dd>
            </div>
            <div>
              <dt>负责人</dt>
              <dd>{text(incoming.payload.owner) || '未指定'}</dd>
            </div>
            <div>
              <dt>状态</dt>
              <dd>{taskStageLabel(incoming.payload)}</dd>
            </div>
            <div>
              <dt>工作说明</dt>
              <dd>{text(incoming.payload.goal) || '未填写'}</dd>
            </div>
            <div>
              <dt>进度备注</dt>
              <dd>{text(incoming.payload.notes) || '未填写'}</dd>
            </div>
          </dl>
          <p>请比较最新内容与下方填写，再选择如何继续。</p>
          <div className="handover-actions">
            <Button
              type="button"
              onClick={() => {
                setDraft({
                  title: incoming.title,
                  payload: incoming.payload,
                  version: incoming.version,
                });
                setIncoming(undefined);
                setError(undefined);
              }}
            >
              采用最新内容
            </Button>
            <Button
              type="button"
              onClick={() => {
                setDraft({
                  ...draft,
                  payload: taskEditablePayload(incoming.payload, draft.payload),
                  version: incoming.version,
                });
                setIncoming(undefined);
                setError(undefined);
              }}
            >
              保留我的填写，合并后继续
            </Button>
          </div>
        </section>
      )}
      <fieldset disabled={busy} className="task-editor-fields">
        <label>
          <span>
            工作名称 <small>必填</small>
          </span>
          <input
            required
            maxLength={200}
            value={draft.title}
            placeholder="例如：核对点胶配方保存问题"
            onChange={(event) => setDraft({ ...draft, title: event.target.value })}
          />
        </label>
        <div className="task-editor-row">
          <label>
            <span>负责人</span>
            <input
              maxLength={2000}
              value={text(draft.payload.owner)}
              placeholder="可稍后指定"
              onChange={(event) => update('owner', event.target.value)}
            />
          </label>
          <label>
            <span>状态</span>
            <HandoverSelect
              label="工作状态"
              value={taskStage(draft.payload)}
              options={[...taskStages]}
              onValueChange={(value) => update('work_status', value)}
              disabled={busy}
            />
          </label>
        </div>
        <label>
          <span>工作说明</span>
          <textarea
            rows={3}
            maxLength={100000}
            value={text(draft.payload.goal)}
            placeholder="简单描述这项工作"
            onChange={(event) => update('goal', event.target.value)}
          />
        </label>
        <label>
          <span>进度备注</span>
          <textarea
            rows={3}
            maxLength={100000}
            value={text(draft.payload.notes)}
            placeholder="记录最新进展或遇到的问题"
            onChange={(event) => update('notes', event.target.value)}
          />
        </label>
      </fieldset>
    </HandoverModal>
  );
}
