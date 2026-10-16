import { useState } from 'react';
import { useAuth } from '../../auth/AuthContext';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { HandoverModal } from '../shared/HandoverModal';
import { debugIssueFields, debugRecordType, debugStatus } from './debugIssues';
import { ids, text, type HandoverRecord } from '../shared/types';
import type { Client } from '../shared/client';

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
      description={version ? `固定历史版本 v${row.version}` : '回看事项原文、处理经过与结果'}
      onClose={onClose}
      className="handover-detail debug-issue-detail"
    >
      <ErrorText error={error} reveal />
      <div className="handover-actions handover-detail-toolbar">
        <span>{debugRecordType(row.payload).label}</span>
        <span
          className={`debug-status ${row.payload.resolution_status === 'recorded' ? 'recorded' : row.payload.resolution_status === 'resolved' ? 'resolved' : ''}`}
        >
          {debugStatus(row.payload)}
        </span>
        <span className="handover-muted">
          v{row.version} · {row.payload.origin === 'ai' ? 'AI 整理' : '手动录入'} · 录入人：
          {text(row.payload.reported_by) || '未记录姓名'}
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
        {debugIssueFields
          .filter(({ key }) => text(row.payload[key]))
          .map(({ key, label }) => (
            <div key={key}>
              <dt>{label}</dt>
              <dd>{text(row.payload[key])}</dd>
            </div>
          ))}
        {!!ids(row.payload.keywords).length && (
          <div>
            <dt>关键词</dt>
            <dd>{ids(row.payload.keywords).join('、')}</dd>
          </div>
        )}
      </dl>
      {text(row.payload.original_text) && (
        <details className="debug-issue-original">
          <summary>查看录入原文</summary>
          <pre>{text(row.payload.original_text)}</pre>
        </details>
      )}
    </HandoverModal>
  );
}
