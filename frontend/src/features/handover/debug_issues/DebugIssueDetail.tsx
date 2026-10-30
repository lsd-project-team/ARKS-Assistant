import { useState } from 'react';
import { useAuth } from '../../auth/AuthContext';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { HandoverModal } from '../shared/HandoverModal';
import {
  debugMetadataFields,
  debugKnowledgeFields,
  debugKnowledgePayload,
  debugRecordType,
  debugStatus,
  debugVisiblePayload,
} from './debugIssues';
import { ids, text, type HandoverRecord } from '../shared/types';
import type { Client } from '../shared/client';
import { DebugIssueImages } from './DebugIssueImages';
import { DebugIssueImageUpload } from './DebugIssueImageUpload';

export function DebugIssueDetail({
  row,
  version,
  client,
  onEdit,
  onChanged,
  onOpen,
  onClose,
}: {
  row: HandoverRecord;
  version?: number;
  client: Client;
  onEdit: (row: HandoverRecord) => void;
  onChanged: () => void;
  onOpen: (id: string, version?: number) => void;
  onClose: () => void;
}) {
  const { session } = useAuth();
  const payload = debugVisiblePayload(row.payload);
  const knowledge = debugKnowledgePayload(payload);
  const auxiliaryFields = debugMetadataFields;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  async function archive() {
    setBusy(true);
    setError(undefined);
    const action = row.state === 'archived' ? 'restore' : 'archive';
    try {
      await client.send(`/records/${row.id}/${action}`, {
        version: row.version,
        actor: session?.user.display_name || session?.user.username,
        opinion: action === 'archive' ? '归档问题与经验记录' : '恢复问题与经验记录',
      });
      onChanged();
      onClose();
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }
  return (
    <HandoverModal
      title={row.title}
      description={version ? '查看本次引用的问答内容' : '查看问题、答案和关键词'}
      onClose={onClose}
      className="handover-detail debug-issue-detail"
    >
      <ErrorText error={error} reveal />
      <div className="handover-actions handover-detail-toolbar">
        <span>{debugRecordType(row.payload).label}</span>
        <span
          className={`debug-status ${payload.resolution_status === 'recorded' ? 'recorded' : payload.resolution_status === 'resolved' ? 'resolved' : ''}`}
        >
          {debugStatus(row.payload)}
        </span>
        {!version && row.state !== 'archived' && <Button onClick={() => onEdit(row)}>编辑</Button>}
        {version && <Button onClick={() => onOpen(row.id)}>查看最新记录</Button>}
        {!version && (
          <Button disabled={busy} onClick={() => void archive()}>
            {row.state === 'archived' ? '恢复记录' : '归档'}
          </Button>
        )}
      </div>
      <dl className="debug-issue-detail-fields">
        {debugKnowledgeFields.map(({ key, label }) => (
          <div key={key}>
            <dt>{label}</dt>
            <dd>{text(knowledge[key]) || '—'}</dd>
          </div>
        ))}
        <div>
          <dt>关键词</dt>
          <dd>{ids(payload.keywords).join('、') || '—'}</dd>
        </div>
      </dl>
      <details className="debug-issue-additional">
        <summary>记录信息</summary>
        <dl className="debug-issue-detail-fields">
          <div>
            <dt>录入人</dt>
            <dd>{text(payload.reported_by) || '—'}</dd>
          </div>
          <div>
            <dt>录入时间</dt>
            <dd>{row.created_at}</dd>
          </div>
          {auxiliaryFields
            .filter(({ key }) => text(payload[key]))
            .map(({ key, label }) => (
              <div key={key}>
                <dt>{label}</dt>
                <dd>{text(payload[key])}</dd>
              </div>
            ))}
        </dl>
      </details>
      {!version && row.state !== 'archived' && (
        <DebugIssueImageUpload row={row} client={client} onChanged={onChanged} />
      )}
      <DebugIssueImages row={row} />
      {text(payload.original_text) && (
        <details className="debug-issue-original">
          <summary>查看录入原文</summary>
          <pre>{text(payload.original_text)}</pre>
        </details>
      )}
    </HandoverModal>
  );
}
