import { useState, type ReactNode } from 'react';
import { Button, ErrorText } from '../components/ui';
import { HandoverModal } from './HandoverModal';
import { TaskStatus } from './TaskStatus';
import { localTime } from './format';
import { text, type HandoverRecord } from './types';
import { taskActor } from './taskProgress';
import type { Client } from './client';
import './task-progress.css';

export function TaskDetail({
  row,
  version,
  client,
  actor,
  readOnly,
  history,
  historyError,
  showHistory = false,
  legacy,
  onClose,
  onEdit,
  onOpen,
  onChanged,
}: {
  row: HandoverRecord;
  version?: number;
  client: Client;
  actor: string;
  readOnly: boolean;
  history?: { version: number; created_at: string }[];
  historyError?: unknown;
  showHistory?: boolean;
  legacy?: ReactNode;
  onClose: () => void;
  onEdit: (row: HandoverRecord) => void;
  onOpen: (id: string, version?: number) => void;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  async function archive() {
    setBusy(true);
    setError(undefined);
    try {
      const archived = row.state === 'archived';
      await client.send(`/records/${row.id}/${archived ? 'restore' : 'archive'}`, {
        version: row.version,
        actor: taskActor(actor),
        opinion: archived ? '恢复工作项' : '归档工作项',
      });
      onChanged();
      onClose();
    } catch (error) {
      setError(error);
    } finally {
      setBusy(false);
    }
  }
  return (
    <HandoverModal
      title={row.title}
      description={version ? `正在查看历史内容 · v${version}` : '查看工作内容和最新进展。'}
      className="task-detail"
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>关闭</Button>
          {version ? (
            <Button onClick={() => onOpen(row.id)}>返回当前工作</Button>
          ) : (
            !readOnly &&
            row.state !== 'archived' && (
              <Button className="primary" onClick={() => onEdit(row)}>
                编辑工作
              </Button>
            )
          )}
        </>
      }
    >
      <ErrorText error={error} reveal />
      <dl className="task-detail-summary">
        <div>
          <dt>负责人</dt>
          <dd>{text(row.payload.owner) || '未指定'}</dd>
        </div>
        <div>
          <dt>状态</dt>
          <dd>
            <TaskStatus row={row} />
            {row.state === 'archived' && <small>已归档</small>}
          </dd>
        </div>
        <div>
          <dt>更新时间</dt>
          <dd>
            <time dateTime={row.updated_at}>{localTime(row.updated_at)}</time>
          </dd>
        </div>
      </dl>
      <section className="task-detail-text">
        <h3>工作说明</h3>
        <p>{text(row.payload.goal) || '暂无说明'}</p>
      </section>
      <section className="task-detail-text">
        <h3>进度备注</h3>
        <p>{text(row.payload.notes) || '暂无备注'}</p>
      </section>
      {version && legacy && (
        <details className="handover-form-section">
          <summary>历史补充信息</summary>
          {legacy}
        </details>
      )}
      {showHistory && (
        <details className="handover-form-section">
          <summary>修改记录</summary>
          <ErrorText error={historyError} reveal />
          {history?.map((item) => (
            <div className="handover-history" key={item.version}>
              <Button onClick={() => onOpen(row.id, item.version)}>v{item.version}</Button>
              <time dateTime={item.created_at}>{localTime(item.created_at)}</time>
            </div>
          ))}
        </details>
      )}
      {!version && !readOnly && (
        <div className="task-archive-action">
          <Button disabled={busy} onClick={() => void archive()}>
            {busy ? '正在处理…' : row.state === 'archived' ? '恢复工作' : '归档工作'}
          </Button>
        </div>
      )}
    </HandoverModal>
  );
}
