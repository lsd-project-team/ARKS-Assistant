import { useState, type ReactNode } from 'react';
import { Check, X } from 'lucide-react';
import { Button, ErrorText, Modal } from '../components/ui';
import { ApiError } from '../lib/api';
import type { Client } from './client';
import { useHandoverDraft } from './drafts';
import { localTime } from './format';
import { canReviewRecord } from './reviewPolicy';
import { text, type Definitions, type HandoverRecord } from './types';
import './record-review.css';

export interface ReviewRevision {
  version: number;
  state: string;
  created_at: string;
  confirmation: HandoverRecord['confirmation'];
}

export function RecordReview({
  scopeId,
  row,
  version,
  readOnly = false,
  client,
  definitions,
  actor,
  onActor,
  onClose,
  onOpen,
  onReload,
  history,
  historyError,
  renderContent,
}: {
  scopeId: string;
  row: HandoverRecord;
  version?: number;
  readOnly?: boolean;
  client: Client;
  definitions: Definitions;
  actor: string;
  onActor: (actor: string) => void;
  onClose: () => void;
  onOpen: (id: string, version?: number) => void;
  onReload: () => Promise<HandoverRecord>;
  history?: ReviewRevision[];
  historyError?: unknown;
  renderContent: (record: HandoverRecord) => ReactNode;
}) {
  const { draft, setDraft, clear, warning } = useHandoverDraft(scopeId, `review:${row.id}`, {
    title: '',
    payload: { opinion: '' },
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [reviewed, setReviewed] = useState<HandoverRecord>();
  // 冻结正在阅读的正文；查询发现新版本时，必须由审核人主动重新读取。
  const [displayed, setDisplayed] = useState(row);
  const current = reviewed || displayed;
  const opinion = text(draft.payload.opinion);
  const newerVersion = !reviewed && row.version !== displayed.version;
  const apiConflict =
    error instanceof ApiError && error.status === 409 && error.message.includes('记录已被更新');
  const stale = newerVersion || apiConflict;
  const available = canReviewRecord(current, readOnly || !!version);
  const ready = available && !busy && !stale && !!actor.trim() && !!opinion.trim();

  async function review(decision: 'confirm' | 'reject') {
    if (!ready) return;
    setBusy(true);
    setError(undefined);
    try {
      const result = await client.send<HandoverRecord>(`/records/${row.id}/${decision}`, {
        version: displayed.version,
        actor: actor.trim(),
        opinion: opinion.trim(),
      });
      // 先采用服务器返回的版本锁住按钮，避免刷新等待期间再次提交旧版本。
      setReviewed(result);
      clear();
      setDisplayed(await onReload());
      setReviewed(undefined);
    } catch (error) {
      setError(error);
    } finally {
      setBusy(false);
    }
  }

  async function reload() {
    setBusy(true);
    try {
      setDisplayed(await onReload());
      setError(undefined);
      setReviewed(undefined);
    } catch (error) {
      setError(error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open
      title={current.title}
      description="审核记录 · 查看内容与来源，确认或拒绝当前版本"
      onClose={onClose}
      className="handover-modal handover-review-modal"
    >
      <div className="record-review-layout">
        <section className="record-review-content" aria-label="审核内容">
          <div className="record-review-meta">
            <span>{definitions.kinds[row.kind]}</span>
            <span>v{current.version}</span>
            <span>{version ? '固定历史版本' : '当前版本'}</span>
          </div>
          {renderContent(current)}
          <details className="record-review-history">
            <summary>审核与修改历史</summary>
            <ErrorText error={historyError} />
            {history?.map((item) => (
              <article key={item.version}>
                <Button onClick={() => onOpen(row.id, item.version)}>
                  v{item.version} · {definitions.states[item.state] || item.state}
                </Button>
                <small>
                  {item.confirmation?.actor || '内容保存'} · {localTime(item.created_at)}
                </small>
                {item.confirmation?.opinion && <p>{item.confirmation.opinion}</p>}
              </article>
            ))}
          </details>
        </section>
        <aside className="record-review-sidebar" aria-label="审核操作">
          <div className="record-review-sidebar-heading">
            <h3>审核处理</h3>
            <span className={`handover-status handover-status-${current.state}`}>
              {definitions.states[current.state] || current.state}
            </span>
          </div>
          <p className="record-review-version">
            {definitions.kinds[row.kind]} · v{current.version}
          </p>
          <ErrorText
            error={
              apiConflict
                ? '审核期间内容已更新，请重新读取后核对。审核意见已保留。'
                : error || warning
            }
            reveal
          />
          {newerVersion && (
            <p role="status">内容已有新版本，请重新读取后再审核。审核意见已保留。</p>
          )}
          {stale && (
            <Button disabled={busy} onClick={() => void reload()}>
              重新读取最新版本
            </Button>
          )}
          {available ? (
            <form onSubmit={(event) => event.preventDefault()} className="record-review-form">
              <fieldset disabled={busy}>
                <label>
                  <span>审核人</span>
                  <input
                    required
                    maxLength={120}
                    value={actor}
                    onChange={(event) => onActor(event.target.value)}
                  />
                </label>
                <label>
                  <span>审核意见</span>
                  <textarea
                    required
                    rows={6}
                    maxLength={2000}
                    value={opinion}
                    placeholder="填写核对结果；拒绝时请说明原因。"
                    onChange={(event) =>
                      setDraft({ ...draft, payload: { opinion: event.target.value } })
                    }
                  />
                </label>
                <small>填写审核人和意见后提交，结果会记录到历史。</small>
              </fieldset>
              <div className="record-review-decisions">
                <Button
                  className="primary"
                  type="button"
                  disabled={!ready}
                  onClick={() => void review('confirm')}
                >
                  <Check size={16} />
                  确认
                </Button>
                <Button
                  className="record-review-reject"
                  type="button"
                  disabled={!ready}
                  onClick={() => void review('reject')}
                >
                  <X size={16} />
                  拒绝
                </Button>
              </div>
            </form>
          ) : (
            <div className="record-review-result" role="status">
              <strong>
                {version
                  ? '历史版本只供查看'
                  : `本版本${definitions.states[current.state] || '不支持审核'}`}
              </strong>
              <p>
                {current.state === 'rejected'
                  ? '拒绝原因和原内容已保留，补充后可重新提交审核。'
                  : '审核结果与原内容保留在版本历史中。'}
              </p>
              {version && <Button onClick={() => onOpen(row.id)}>查看当前版本</Button>}
            </div>
          )}
          {current.confirmation?.actor && (
            <dl className="record-review-outcome">
              <dt>审核人</dt>
              <dd>{current.confirmation.actor}</dd>
              <dt>审核时间</dt>
              <dd>{localTime(current.confirmation.time || current.updated_at)}</dd>
              <dt>{current.confirmation.decision === 'reject' ? '拒绝原因' : '审核意见'}</dt>
              <dd>{current.confirmation.opinion}</dd>
            </dl>
          )}
        </aside>
      </div>
    </Modal>
  );
}
