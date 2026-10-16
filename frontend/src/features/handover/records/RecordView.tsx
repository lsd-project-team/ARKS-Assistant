import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { DebugIssueDetail } from '../debug_issues/DebugIssueDetail';
import { SourceDetailFooter } from '../materials/SourceContent';
import { SourceImport } from '../materials/SourceImport';
import { PackageDetail } from '../packages/PackageDetail';
import { RecordHistory, type RecordRevision } from '../reviews/RecordHistory';
import { RecordReview } from '../reviews/RecordReview';
import { HandoverSelect } from '../shared/Controls';
import { HandoverModal } from '../shared/HandoverModal';
import { Status } from '../shared/RecordCard';
import type { Client } from '../shared/client';
import type { Definitions, HandoverRecord, Kind, Payload } from '../shared/types';
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
  reviewOnly = false,
  canReview = false,
  actor,
  onActor,
  onClose,
  onOpen,
  onEdit,
  onChanged,
  onDiscuss,
  onCurrentSource,
}: {
  scopeId: string;
  identifier: string;
  version?: number;
  client: Client;
  definitions: Definitions;
  records: HandoverRecord[];
  reviewOnly?: boolean;
  canReview?: boolean;
  actor: string;
  onActor: (value: string) => void;
  onClose: () => void;
  onOpen: (id: string, version?: number) => void;
  onEdit: (row: HandoverRecord) => void;
  onChanged: () => void;
  onDiscuss?: (row: HandoverRecord) => void;
  onCurrentSource?: (row: HandoverRecord) => Promise<void>;
}) {
  const readOnly = version !== undefined;

  const query = useQuery({
    queryKey: ['handover-record', scopeId, identifier, version],
    queryFn: () =>
      client.get<HandoverRecord>(`/records/${identifier}${version ? `?version=${version}` : ''}`),
  });
  const history = useQuery({
    queryKey: ['handover-history', scopeId, identifier],
    queryFn: () => client.get<RecordRevision[]>(`/records/${identifier}/history`),
    enabled: canReview,
  });
  const [action, setAction] = useState<'' | 'archive' | 'restore'>('');
  const [opinion, setOpinion] = useState('');
  const [role, setRole] = useState('');
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const [snapshot, setSnapshot] = useState<{ path: string; content: string; sha256: string }>();
  const [comparison, setComparison] = useState<{ changed: boolean }>();
  const [updatingSource, setUpdatingSource] = useState(false);
  const row = query.data;
  const historyContent = canReview ? (
    <RecordHistory
      identifier={identifier}
      history={history.data}
      error={history.error}
      loading={history.isPending}
      definitions={definitions}
      onOpen={onOpen}
      onRetry={() => void history.refetch()}
    />
  ) : null;
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
      if (canReview) void history.refetch();
    } catch (error) {
      setError(error);
    } finally {
      setBusy(false);
    }
  }
  if (row && reviewOnly && canReview) {
    return (
      <RecordReview
        key={`${row.id}:${version || 'current'}`}
        scopeId={scopeId}
        row={row}
        version={version}
        readOnly={readOnly}
        client={client}
        definitions={definitions}
        actor={actor}
        onActor={onActor}
        onClose={onClose}
        onOpen={onOpen}
        history={history.data}
        historyError={history.error}
        onReload={async () => {
          onChanged();
          const [recordResult, historyResult] = await Promise.all([
            query.refetch(),
            history.refetch(),
          ]);
          if (recordResult.error) throw recordResult.error;
          if (historyResult.error) throw historyResult.error;
          if (!recordResult.data) throw new Error('未能读取记录，请重试。');
          return recordResult.data;
        }}
        renderContent={(displayed) => (
          <RecordContent
            row={
              displayed.kind === 'candidate'
                ? {
                    ...displayed,
                    kind: text(displayed.payload.target_kind) as Kind,
                    payload: displayed.payload.proposed as Payload,
                  }
                : displayed
            }
            records={records}
            definitions={definitions}
            onOpen={onOpen}
            showConfirmation={false}
          />
        )}
      />
    );
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
        history={history.data}
        historyError={history.error}
        showHistory={canReview}
        onClose={onClose}
        onEdit={onEdit}
        onOpen={onOpen}
        onChanged={() => {
          onChanged();
          void query.refetch();
          if (canReview) void history.refetch();
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
        onChanged={onChanged}
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
        history={historyContent}
        onClose={onClose}
        onOpen={onOpen}
      />
    );
  }
  if (
    updatingSource &&
    row?.kind === 'source' &&
    !readOnly &&
    !version &&
    row.state !== 'archived'
  ) {
    return (
      <SourceImport
        key={row.id}
        scopeId={scopeId}
        replacing={row}
        client={client}
        actor={actor}
        onActor={onActor}
        onClose={() => setUpdatingSource(false)}
        onSaved={(updated) => {
          setUpdatingSource(false);
          onChanged();
          onOpen(updated.id);
        }}
      />
    );
  }
  return (
    <HandoverModal
      title={row?.title || '交接记录'}
      description={
        version
          ? '正在查看固定历史版本'
          : row?.kind === 'source'
            ? '查看资料内容'
            : '复核内容、关联证据和接续条件'
      }
      onClose={onClose}
      className={row?.kind === 'source' ? 'source-detail' : 'handover-detail'}
      footer={
        row?.kind === 'source' && (
          <SourceDetailFooter
            row={row}
            version={version}
            readOnly={readOnly}
            onUpdate={() => setUpdatingSource(true)}
            onDownload={() =>
              void client
                .download(
                  `/sources/${row.id}/original`,
                  text(row.payload.filename).split(/[\\/]/).pop() || '原始资料',
                )
                .catch(setError)
            }
            onClose={onClose}
            onOpen={onOpen}
          />
        )
      }
    >
      {query.isPending && <p role="status">正在读取记录…</p>}
      <ErrorText error={query.error || error} reveal />
      {query.error && <Button onClick={() => void query.refetch()}>重试</Button>}
      {row && (
        <>
          {row.kind !== 'source' && (
            <div className="handover-actions handover-detail-toolbar">
              <Status row={row} definitions={definitions} />
              <span>
                v{row.version} · {definitions.values[text(row.payload.origin)] || '人工整理'}
              </span>
              {!version &&
                !readOnly &&
                (row.kind !== 'candidate' || canReview) &&
                !['source', 'package', 'job'].includes(row.kind) &&
                !(row.kind === 'candidate' && text(row.payload.promoted_id)) &&
                row.state !== 'archived' && (
                  <Button onClick={() => onEdit(row)}>
                    {row.kind === 'candidate' ? '审核并合并' : '编辑'}
                  </Button>
                )}
              {onDiscuss && <Button onClick={() => onDiscuss(row)}>在对话中讨论</Button>}
            </div>
          )}
          {row.kind === 'candidate' ? (
            <>
              <p className="handover-notice">
                AI 候选 · {definitions.kinds[text(row.payload.target_kind) as Kind]}
                <br />
                {text(row.payload.reason)}
              </p>
              <RecordContent
                row={{
                  ...row,
                  kind: text(row.payload.target_kind) as Kind,
                  payload: row.payload.proposed as Payload,
                }}
                records={records}
                definitions={definitions}
                onOpen={onOpen}
              />
            </>
          ) : (
            <RecordContent row={row} records={records} definitions={definitions} onOpen={onOpen} />
          )}
          {row.kind === 'source' &&
            (text(row.payload.path) ||
              (Array.isArray(row.payload.files) && row.payload.files.length > 0)) && (
              <section className="handover-form-section">
                <div className="handover-actions">
                  {text(row.payload.path) && (
                    <>
                      <Button
                        onClick={() =>
                          void client
                            .get<{ changed: boolean }>(`/sources/${row.id}/compare`)
                            .then(setComparison)
                            .catch(setError)
                        }
                      >
                        比对当前版本
                      </Button>
                      {onCurrentSource && (
                        <Button onClick={() => void onCurrentSource(row).catch(setError)}>
                          在源码阅读器打开
                        </Button>
                      )}
                    </>
                  )}
                </div>
                {comparison && (
                  <p className="handover-notice" role="status">
                    {comparison.changed
                      ? '当前源码已经变化，交接记录仍保留原快照。'
                      : '比对完成：当前源码与固定快照一致。'}
                  </p>
                )}
                {Array.isArray(row.payload.files) && row.payload.files.length > 0 && (
                  <label className="handover-file-select">
                    <span>查看快照文件</span>
                    <HandoverSelect
                      label="查看快照文件"
                      value={snapshot?.path || ''}
                      onValueChange={(path) => {
                        if (!path) {
                          setSnapshot(undefined);
                          return;
                        }
                        void client
                          .get<{ path: string; content: string; sha256: string }>(
                            `/sources/${row.id}/file?path=${encodeURIComponent(path)}`,
                          )
                          .then(setSnapshot)
                          .catch(setError);
                      }}
                      options={[
                        { value: '', label: '选择文件' },
                        ...(row.payload.files as { path: string }[]).map((file) => ({
                          value: file.path,
                          label: file.path,
                        })),
                      ]}
                    />
                  </label>
                )}
                {snapshot && (
                  <>
                    <p>
                      {snapshot.path} · SHA256 {snapshot.sha256}
                    </p>
                    <pre className="handover-source">{snapshot.content}</pre>
                  </>
                )}
              </section>
            )}
          {!readOnly && !version && row.kind !== 'job' && (
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
              <p>请填写操作人和说明，操作会保留到历史记录。</p>
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
          {historyContent}
        </>
      )}
    </HandoverModal>
  );
}
