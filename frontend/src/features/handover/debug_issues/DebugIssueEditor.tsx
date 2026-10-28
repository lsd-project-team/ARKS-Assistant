import { useState } from 'react';
import { ApiError } from '../../../app/api/client';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { HandoverModal } from '../shared/HandoverModal';
import { HandoverSelect } from '../shared/Controls';
import { useHandoverDraft } from '../shared/drafts';
import { debugEditablePayload, debugIssueFields, debugRecordTypes } from './debugIssues';
import { ids, text, type HandoverRecord } from '../shared/types';
import type { Client } from '../shared/client';

export function DebugIssueEditor({
  client,
  row,
  onSaved,
  onClose,
}: {
  client: Client;
  row?: HandoverRecord;
  onSaved: (row: HandoverRecord) => void;
  onClose: () => void;
}) {
  const state = useHandoverDraft('global', row?.id || 'new:debug_issue', {
    title: row?.title || '',
    version: row?.version,
    payload: {
      ...debugEditablePayload(row?.payload || {}),
      keywords_text: ids(debugEditablePayload(row?.payload || {}).keywords).join('，'),
    },
  });
  const { draft, setDraft } = state;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [latest, setLatest] = useState<HandoverRecord>();
  function update(key: string, value: string) {
    setDraft({ ...draft, payload: { ...draft.payload, [key]: value } });
  }
  async function save() {
    setBusy(true);
    setError(undefined);
    try {
      const payload = {
        ...debugEditablePayload(draft.payload),
        keywords: text(draft.payload.keywords_text)
          .split(/[，,；;\n]+/)
          .map((value) => value.trim())
          .filter(Boolean),
      };
      const result = await client.send<HandoverRecord>(
        row ? `/debug-issues/${row.id}` : '/debug-issues',
        { title: draft.title.trim(), payload, version: draft.version },
        row ? 'PATCH' : 'POST',
      );
      state.clear();
      onSaved(result);
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }
  return (
    <HandoverModal
      title={row ? '编辑记录' : '添加记录'}
      description="保存问题、经验和工作进展，按原文填写记录人及时间。"
      onClose={onClose}
      onSubmit={(event) => {
        event.preventDefault();
        void save();
      }}
      className="debug-issue-editor"
      footer={
        <>
          <span className="handover-muted">保存后可在后续问答中检索</span>
          <Button type="button" disabled={busy} onClick={onClose}>
            关闭并保留草稿
          </Button>
          <Button className="primary" type="submit" disabled={busy}>
            {busy ? '正在保存…' : '保存记录'}
          </Button>
        </>
      }
    >
      {state.restored && <p className="handover-notice">已恢复未保存的记录，请检查后继续。</p>}
      <ErrorText error={error || state.warning} reveal />
      {error instanceof ApiError && error.status === 409 && row && (
        <div className="handover-conflict">
          <p>内容可能已被其他人更新，你的输入仍保留。</p>
          <Button
            type="button"
            onClick={() =>
              void client.get<HandoverRecord>(`/records/${row.id}`).then(setLatest).catch(setError)
            }
          >
            读取最新版本
          </Button>
          {latest && (
            <>
              <pre>{JSON.stringify(debugEditablePayload(latest.payload), null, 2)}</pre>
              <Button
                type="button"
                onClick={() => {
                  setDraft({ ...draft, version: latest.version });
                  setLatest(undefined);
                  setError(undefined);
                }}
              >
                已核对，使用最新版本号保存当前内容
              </Button>
            </>
          )}
        </div>
      )}
      <label className="debug-issue-field">
        <span>
          记录标题 <b>*</b>
        </span>
        <input
          required
          maxLength={200}
          value={draft.title}
          onChange={(event) => setDraft({ ...draft, title: event.target.value })}
          placeholder="用一句话描述事项"
        />
      </label>
      <label className="debug-issue-field">
        <span>记录类型</span>
        <HandoverSelect
          value={text(draft.payload.record_type)}
          onValueChange={(record_type) =>
            setDraft({
              ...draft,
              payload: {
                ...draft.payload,
                ...debugEditablePayload({ ...draft.payload, record_type }),
              },
            })
          }
          label="记录类型"
          options={[...debugRecordTypes]}
        />
      </label>
      {draft.payload.record_type === 'problem' && (
        <label className="debug-issue-field">
          <span>处理状态</span>
          <HandoverSelect
            value={text(draft.payload.resolution_status)}
            onValueChange={(value) => update('resolution_status', value)}
            label="处理状态"
            options={[
              { value: 'open', label: '未解决' },
              { value: 'resolved', label: '已解决' },
            ]}
          />
        </label>
      )}
      <div className="debug-issue-editor-fields">
        {debugIssueFields.map((field) => (
          <label key={field.key} className={`debug-issue-field ${'short' in field ? 'short' : ''}`}>
            <span>
              {field.label}
              {'required' in field && <b> *</b>}
            </span>
            {'short' in field ? (
              <input
                maxLength={2000}
                value={text(draft.payload[field.key])}
                onChange={(event) => update(field.key, event.target.value)}
              />
            ) : (
              <textarea
                required={
                  'required' in field ||
                  (field.key === 'solution' && draft.payload.resolution_status === 'resolved')
                }
                maxLength={30000}
                rows={3}
                value={text(draft.payload[field.key])}
                placeholder={'placeholder' in field ? field.placeholder : '可选'}
                onChange={(event) => update(field.key, event.target.value)}
              />
            )}
          </label>
        ))}
      </div>
      <label className="debug-issue-field">
        <span>关键词</span>
        <input
          value={text(draft.payload.keywords_text)}
          onChange={(event) => update('keywords_text', event.target.value)}
          placeholder="用逗号分隔，如：取片、真空、报警码"
        />
      </label>
    </HandoverModal>
  );
}
