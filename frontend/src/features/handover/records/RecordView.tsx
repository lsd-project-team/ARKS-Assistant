import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { DebugIssueDetail } from '../debug_issues/DebugIssueDetail';
import { OriginalMaterialViewer } from '../materials/OriginalMaterialViewer';
import { PackageDetail } from '../packages/PackageDetail';
import { HandoverModal } from '../shared/HandoverModal';
import { Status } from '../shared/RecordCard';
import type { Client } from '../shared/client';
import type { Definitions, HandoverRecord } from '../shared/types';
import { text } from '../shared/types';
import { TaskDetail } from '../tasks/TaskDetail';
import { taskLegacyPayload } from '../tasks/taskProgress';
import { RecordContent } from './RecordContent';

export function RecordView({
  scopeId,
  identifier,
  version,
  client,
  definitions,
  records,
  actor,
  onActor,
  onClose,
  onOpen,
  onEdit,
  onChanged,
  onDiscuss,
}: {
  scopeId: string;
  identifier: string;
  version?: number;
  client: Client;
  definitions: Definitions;
  records: HandoverRecord[];
  actor: string;
  onActor: (value: string) => void;
  onClose: () => void;
  onOpen: (id: string, version?: number) => void;
  onEdit: (row: HandoverRecord) => void;
  onChanged: () => void;
  onDiscuss?: (row: HandoverRecord) => void;
}) {
  const readOnly = version !== undefined;

  const query = useQuery({
    queryKey: ['handover-record', scopeId, identifier, version],
    queryFn: () =>
      client.get<HandoverRecord>(`/records/${identifier}${version ? `?version=${version}` : ''}`),
  });
  const [action, setAction] = useState<'' | 'archive' | 'restore'>('');
  const [opinion, setOpinion] = useState('');
  const [role, setRole] = useState('');
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const row = query.data;
  async function act() {
    if (!row || !action) return;
    setBusy(true);
    setError(undefined);
    try {
      await client.send(`/records/${identifier}/${action}`, {
        version: row.version,
        actor,
        opinion,
        role,
      });
      setAction('');
      onChanged();
      void query.refetch();
    } catch (error) {
      setError(error);
    } finally {
      setBusy(false);
    }
  }
  if (row?.kind === 'source') {
    return <OriginalMaterialViewer row={row} client={client} onClose={onClose} />;
  }
  if (row?.kind === 'task') {
    const legacy = taskLegacyPayload(row.payload);
    return (
      <TaskDetail
        row={row}
        version={version}
        client={client}
        actor={actor}
        readOnly={readOnly}
        onClose={onClose}
        onEdit={onEdit}
        onOpen={onOpen}
        onChanged={() => {
          onChanged();
          void query.refetch();
        }}
        legacy={
          version && (Object.keys(legacy).length || row.confirmation?.actor) ? (
            <RecordContent
              row={{ ...row, payload: legacy }}
              records={records}
              definitions={definitions}
              onOpen={onOpen}
            />
          ) : undefined
        }
      />
    );
  }
  if (row?.kind === 'debug_issue') {
    return (
      <DebugIssueDetail
        row={row}
        version={version}
        client={client}
        onEdit={onEdit}
        onChanged={() => {
          onChanged();
          void query.refetch();
        }}
        onOpen={onOpen}
        onClose={onClose}
      />
    );
  }
  if (row?.kind === 'package') {
    return (
      <PackageDetail
        row={row}
        version={version}
        records={records}
        definitions={definitions}
        client={client}
        readError={query.error}
        onClose={onClose}
        onOpen={onOpen}
      />
    );
  }
  return (
    <HandoverModal
      title={row?.title || '交接记录'}
      description={version ? '正在查看固定历史版本' : '查看内容、关联证据和接续条件'}
      onClose={onClose}
      className="handover-detail"
    >
      {query.isPending && <p role="status">正在读取记录…</p>}
      <ErrorText error={query.error || error} reveal />
      {query.error && <Button onClick={() => void query.refetch()}>重试</Button>}
      {row && (
        <>
          <div className="handover-actions handover-detail-toolbar">
            <Status row={row} definitions={definitions} />
            <span>
              v{row.version} · {definitions.values[text(row.payload.origin)] || '人工整理'}
            </span>
            {!version &&
              !readOnly &&
              !['source', 'package'].includes(row.kind) &&
              row.state !== 'archived' && <Button onClick={() => onEdit(row)}>编辑</Button>}
            {onDiscuss && <Button onClick={() => onDiscuss(row)}>在对话中讨论</Button>}
          </div>
          <RecordContent
            row={row}
            records={records}
            definitions={definitions}
            onOpen={onOpen}
            showConfirmation={false}
          />
          {!readOnly && !version && (
            <div className="handover-actions handover-form-section">
              <Button
                disabled={busy}
                onClick={() => setAction(row.state === 'archived' ? 'restore' : 'archive')}
              >
                {row.state === 'archived' ? '恢复记录' : '归档记录'}
              </Button>
            </div>
          )}
          {action && (
            <form
              className="handover-confirm"
              onSubmit={(event) => {
                event.preventDefault();
                void act();
              }}
            >
              <h3>{action === 'archive' ? '归档记录' : '恢复记录'}</h3>
              <p>请填写操作人和说明。</p>
              <div className="handover-fields">
                <label>
                  <span>操作人</span>
                  <input
                    required
                    maxLength={120}
                    value={actor}
                    onChange={(event) => onActor(event.target.value)}
                  />
                </label>
                <label>
                  <span>职责</span>
                  <input
                    maxLength={120}
                    value={role}
                    onChange={(event) => setRole(event.target.value)}
                  />
                </label>
                <label className="handover-field-wide">
                  <span>操作说明</span>
                  <textarea
                    required
                    maxLength={2000}
                    rows={3}
                    value={opinion}
                    onChange={(event) => setOpinion(event.target.value)}
                  />
                </label>
              </div>
              <div className="handover-confirm-actions">
                <Button type="button" disabled={busy} onClick={() => setAction('')}>
                  取消
                </Button>
                <Button className="primary" disabled={busy} type="submit">
                  {busy ? '正在处理…' : '提交'}
                </Button>
              </div>
            </form>
          )}
        </>
      )}
    </HandoverModal>
  );
}
