import { useState } from 'react';
import { ApiError } from '../../../app/api/client';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { defaults, EvidenceFields, Fields, PlanSteps } from '../shared/Fields';
import { HandoverModal } from '../shared/HandoverModal';
import type { Client } from '../shared/client';
import { useHandoverDraft } from '../shared/drafts';
import type { Definitions, HandoverRecord, Kind, Payload } from '../shared/types';
import { text } from '../shared/types';

export function RecordEditor({
  scopeId,
  client,
  definitions,
  records,
  kind,
  row,
  initial = {},
  actor,
  onActor,
  onSaved,
  onClose,
}: {
  scopeId: string;
  client: Client;
  definitions: Definitions;
  records: HandoverRecord[];
  kind: Kind;
  row?: HandoverRecord;
  initial?: Payload;
  actor: string;
  onActor: (value: string) => void;
  onSaved: (row: HandoverRecord) => void;
  onClose: () => void;
}) {
  const payload = row?.payload;
  const draftState = useHandoverDraft(scopeId, row?.id || `new:${kind}:${text(initial.task_id)}`, {
    title: row?.title || '',
    payload: { ...defaults(definitions, kind), ...payload, ...initial },
    version: row?.version,
  });
  const { draft, setDraft } = draftState;
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const [incoming, setIncoming] = useState<HandoverRecord>();
  const [opinion, setOpinion] = useState('');
  const setPayload = (payload: Payload) => setDraft({ ...draft, payload });
  async function save() {
    setBusy(true);
    setError(undefined);
    try {
      const result = await client.send<HandoverRecord>(
        row ? `/records/${row.id}` : '/records',
        {
          kind,
          title: draft.title,
          payload: draft.payload,
          actor,
          version: draft.version,
          reason: opinion,
        },
        row ? 'PATCH' : 'POST',
      );
      draftState.clear();
      onSaved(result);
    } catch (error) {
      setError(error);
    } finally {
      setBusy(false);
    }
  }
  return (
    <HandoverModal
      title={`${row ? '编辑' : '新增'}${definitions.kinds[kind]}`}
      onClose={onClose}
      description="整理内容并保存为草稿。关闭时保留本机草稿。"
      onSubmit={(event) => {
        event.preventDefault();
        void save();
      }}
      footer={
        <>
          <span className="handover-muted">保存后到“复核与追溯”审核</span>
          <Button type="button" disabled={busy} onClick={onClose}>
            关闭并保留草稿
          </Button>
          <Button className="primary" disabled={busy || !actor.trim()} type="submit">
            {busy ? '正在保存…' : '保存草稿'}
          </Button>
        </>
      }
    >
      {draftState.restored && (
        <p className="handover-notice">已恢复交接工作台的本机草稿，请检查内容与版本后保存。</p>
      )}
      <ErrorText error={error || draftState.warning} reveal />
      {error instanceof ApiError && error.status === 409 && row && (
        <Button
          type="button"
          onClick={() =>
            void client.get<HandoverRecord>(`/records/${row.id}`).then(setIncoming).catch(setError)
          }
        >
          查看服务器当前版本
        </Button>
      )}
      {incoming && (
        <section className="handover-conflict">
          <h3>服务器当前版本 v{incoming.version}</h3>
          <p>逐项比较后，可将服务器的内容复制到草稿中，再使用当前版本号提交。</p>
          <dl>
            {Object.entries(incoming.payload)
              .filter(([key, value]) => definitions.fields[key] && typeof value === 'string')
              .map(([key, value]) => (
                <div key={key}>
                  <dt>{definitions.fields[key]}</dt>
                  <dd>
                    {String(value) || '未填写'}
                    <Button
                      type="button"
                      onClick={() => setPayload({ ...draft.payload, [key]: value })}
                    >
                      采用此项
                    </Button>
                  </dd>
                </div>
              ))}
          </dl>
          <Button
            type="button"
            onClick={() => {
              setDraft({
                ...draft,
                version: incoming.version,
                // 访谈表单不再编辑引用，冲突重试保留服务器最新的关联，避免隐藏字段覆盖。
                payload:
                  kind === 'interview'
                    ? { ...draft.payload, evidence: incoming.payload.evidence }
                    : draft.payload,
              });
              setIncoming(undefined);
              setError(undefined);
            }}
          >
            已完成比较，使用 v{incoming.version} 继续保存
          </Button>
        </section>
      )}
      <fieldset disabled={busy}>
        <section className="handover-editor-section">
          <h3>记录信息</h3>
          <div className="handover-fields">
            <label className="handover-field-wide">
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
            <label>
              <span>修改说明</span>
              <input
                maxLength={2000}
                value={opinion}
                onChange={(event) => setOpinion(event.target.value)}
              />
            </label>
          </div>
        </section>
        <Fields
          kind={kind}
          value={draft.payload}
          onChange={setPayload}
          definitions={definitions}
          records={records.filter((item) => item.id !== row?.id)}
        />
        {kind === 'plan' && (
          <PlanSteps
            value={draft.payload.steps}
            onChange={(steps) => setPayload({ ...draft.payload, steps })}
          />
        )}
        {/* 访谈原文自身就是来源；隐藏手工证据输入，保存时仍保留已有引用。 */}
        {kind !== 'interview' && (
          <EvidenceFields
            value={draft.payload.evidence}
            onChange={(evidence) => setPayload({ ...draft.payload, evidence })}
            records={records.filter((item) => item.id !== row?.id)}
          />
        )}
      </fieldset>
    </HandoverModal>
  );
}
