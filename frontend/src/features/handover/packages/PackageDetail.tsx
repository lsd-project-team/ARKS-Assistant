import { useState, type ReactNode } from 'react';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { HandoverModal } from '../shared/HandoverModal';
import type { Client } from '../shared/client';
import type { Definitions, HandoverRecord } from '../shared/types';
import { refs, text } from '../shared/types';
import { localTime } from '../shared/format';
import { packageGroups, packageNotes } from './packageContents';
import { PackageContentsList } from './PackageContentsList';
import { packageStatus } from './packageStatus';
import './package-detail.css';

export function PackageDetail({
  row,
  version,
  records,
  client,
  readError,
  history,
  onClose,
  onOpen,
  onConfirm,
}: {
  row: HandoverRecord;
  version?: number;
  records: HandoverRecord[];
  definitions: Definitions;
  client: Client;
  readError?: unknown;
  history: ReactNode;
  onClose: () => void;
  onOpen: (id: string, version?: number) => void;
  onConfirm?: () => Promise<void>;
}) {
  const [downloading, setDownloading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<unknown>();
  const groups = packageGroups(row.payload, records);
  const count = groups.reduce((total, group) => total + group.items.length, 0);
  const confirmed = row.state === 'confirmed';
  const current = records.find((record) => record.id === row.id);
  const downloadable = confirmed && (!current || current.state === 'confirmed');
  async function confirm() {
    if (!onConfirm || confirming) return;
    setConfirming(true);
    setError(undefined);
    try {
      await onConfirm();
    } catch (error) {
      setError(error);
    } finally {
      setConfirming(false);
    }
  }
  async function download() {
    if (!downloadable || downloading || confirming) return;
    setDownloading(true);
    setError(undefined);
    try {
      await client.download(
        `/packages/${row.id}/export?format=zip&version=${row.version}`,
        `${row.title}.zip`,
      );
    } catch (error) {
      setError(error);
    } finally {
      setDownloading(false);
    }
  }
  return (
    <HandoverModal
      title={row.title}
      description={version ? '正在查看历史交接包' : undefined}
      className="package-detail"
      onClose={onClose}
      footer={
        <>
          {version && <Button onClick={() => onOpen(row.id)}>返回当前交接包</Button>}
          {!version && row.state !== 'archived' && !confirmed && onConfirm && (
            <Button disabled={confirming} onClick={() => void confirm()}>
              {confirming ? '正在确认…' : '确认交接包'}
            </Button>
          )}
          <Button
            className="primary"
            disabled={!downloadable || downloading || confirming}
            title={downloadable ? undefined : '确认后可下载'}
            onClick={() => void download()}
          >
            {downloading ? '正在下载…' : '下载完整包'}
          </Button>
          <Button onClick={onClose}>关闭</Button>
        </>
      }
    >
      <ErrorText error={error || readError} reveal />
      <div className="package-detail-state">
        <span className={`handover-status handover-status-${confirmed ? 'confirmed' : 'draft'}`}>
          {packageStatus(row.state)}
        </span>
        {!downloadable && <span className="handover-muted">确认后可下载</span>}
      </div>
      <dl className="package-detail-summary">
        {text(row.payload.recipient).trim() && (
          <div>
            <dt>接收对象</dt>
            <dd>{text(row.payload.recipient)}</dd>
          </div>
        )}
        <div>
          <dt>生成时间</dt>
          <dd>
            <time dateTime={row.created_at}>{localTime(row.created_at)}</time>
          </dd>
        </div>
        <div>
          <dt>包内内容</dt>
          <dd>{count} 条</dd>
        </div>
      </dl>
      {packageNotes(row.payload).map((item) => (
        <section className="package-detail-note" key={item.id}>
          <h3>{item.label}</h3>
          <p>{item.content}</p>
        </section>
      ))}
      <section className="package-detail-contents" aria-label="交接内容">
        <PackageContentsList groups={groups} client={client} onOpen={onOpen} />
        {!count && <p className="handover-muted">这个交接包暂无包内内容。</p>}
      </section>
      {!!refs(row.payload.evidence).length && (
        <section className="package-detail-note">
          <h3>关联来源</h3>
          {refs(row.payload.evidence).map((item, index) => (
            <div className="handover-evidence" key={index}>
              <Button onClick={() => onOpen(item.record_id, item.version)}>
                {records.find((record) => record.id === item.record_id)?.title || '关联记录'}
              </Button>
              {item.locator && <span>{item.locator}</span>}
              {item.quote && <blockquote>{item.quote}</blockquote>}
            </div>
          ))}
        </section>
      )}
      {row.confirmation?.actor && (
        <p className="handover-notice">
          {row.confirmation.decision === 'reject' ? '拒绝审核人' : '确认人'}：
          {row.confirmation.actor} · {row.confirmation.role} · {localTime(row.confirmation.time)}
          <br />
          {row.confirmation.opinion}
        </p>
      )}
      {history}
    </HandoverModal>
  );
}
