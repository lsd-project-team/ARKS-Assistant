import { HandoverModal } from './HandoverModal';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Button, ErrorText } from '../components/ui';
import type { Client } from './client';
import type { Definitions, HandoverRecord, Kind, Payload } from './types';
import { ids, refs, text } from './types';
import { localTime } from './format';
import { workStatusLabel } from './workStatus';
import { HandoverSelect } from './Controls';

export function Status({ row, definitions }: { row: HandoverRecord; definitions: Definitions }) {
  return (
    <span className={`handover-status handover-status-${row.state}`}>
      {definitions.states[row.state]}
    </span>
  );
}
export function RecordCard({
  row,
  definitions,
  onOpen,
}: {
  row: HandoverRecord;
  definitions: Definitions;
  onOpen: (id: string) => void;
}) {
  return (
    <button className="handover-record-card" onClick={() => onOpen(row.id)}>
      <div>
        <span className="handover-eyebrow">
          {definitions.kinds[row.kind]} · v{row.version}
        </span>
        <Status row={row} definitions={definitions} />
      </div>
      <strong>{row.title}</strong>
      <p>
        {text(
          row.payload.goal ||
            row.payload.question ||
            row.payload.intent ||
            row.payload.condition ||
            row.payload.scope ||
            row.payload.topic ||
            row.payload.parse_notes ||
            row.payload.prerequisites ||
            row.payload.operation ||
            row.payload.understanding,
        ) || '打开查看内容与来源'}
      </p>
      <small>
        {text(
          row.payload.owner || row.payload.author || row.payload.receiver || row.payload.provider,
        ) || '未指定负责人'}{' '}
        · {row.updated_at.slice(0, 10)}
      </small>
    </button>
  );
}

export function RecordContent({
  row,
  records,
  definitions,
  onOpen,
}: {
  row: HandoverRecord;
  records: HandoverRecord[];
  definitions: Definitions;
  onOpen: (id: string, version?: number) => void;
}) {
  function valueText(value: unknown, field?: string) {
    if (typeof value === 'number') return String(value);
    if (Array.isArray(value))
      return ids(value)
        .map((id) => records.find((item) => item.id === id)?.title || id)
        .join('、');
    const valueString = text(value);
    if (field === 'format')
      return (
        (
          { source: '源码文本', zip: '固定源码 ZIP', docx: 'Word 文档', pdf: 'PDF 文档' } as Record<
            string,
            string
          >
        )[valueString] || valueString
      );
    return (
      records.find((item) => item.id === valueString)?.title ||
      definitions.values[valueString] ||
      valueString
    );
  }
  return (
    <>
      <dl className="handover-record-fields">
        {Object.entries(row.payload)
          .filter(([key]) => definitions.fields[key] && !['origin'].includes(key))
          .map(([key, value]) => (
            <div key={key}>
              <dt>{definitions.fields[key]}</dt>
              <dd>
                {key === 'work_status'
                  ? workStatusLabel(row, definitions.values)
                  : valueText(value, key) || '未填写'}
              </dd>
            </div>
          ))}
      </dl>
      {Array.isArray(row.payload.steps) && (
        <section>
          <h3>接续步骤</h3>
          {(row.payload.steps as Payload[]).map((step, index) => (
            <article className="handover-step" key={index}>
              <h4>
                {index + 1}. {text(step.action)}
              </h4>
              {Object.entries({
                prerequisite: '前提',
                output: '输出',
                verification: '验证',
                stop: '停止条件',
                rollback: '回退',
                owner: '负责人',
              }).map(([key, label]) => (
                <p key={key}>
                  <strong>{label}：</strong>
                  {text(step[key]) || '未填写'}
                </p>
              ))}
            </article>
          ))}
        </section>
      )}
      <section className="handover-form-section">
        {row.kind === 'package' && (
          <>
            <h3>包内固定版本</h3>
            <div className="handover-actions">
              {refs(row.payload.records).map((item) => (
                <Button key={item.record_id} onClick={() => onOpen(item.record_id, item.version)}>
                  {records.find((record) => record.id === item.record_id)?.title || item.record_id}{' '}
                  · v{item.version}
                </Button>
              ))}
            </div>
          </>
        )}
        <h3>来源与固定版本</h3>
        {!refs(row.payload.evidence).length && <p className="handover-muted">尚未关联来源证据。</p>}
        {refs(row.payload.evidence).map((item, index) => (
          <div className="handover-evidence" key={index}>
            <Button onClick={() => onOpen(item.record_id, item.version)}>
              {records.find((row) => row.id === item.record_id)?.title || item.record_id} · v
              {item.version}
            </Button>
            <span>{item.locator || '未填写定位'}</span>
            {item.quote && <blockquote>{item.quote}</blockquote>}
          </div>
        ))}
      </section>
      {row.confirmation && (
        <p className="handover-notice">
          确认人：{row.confirmation.actor} · {row.confirmation.role} ·{' '}
          {localTime(row.confirmation.time)}
          <br />
          {row.confirmation.opinion}
        </p>
      )}
    </>
  );
}

export function RecordView({
  projectId,
  identifier,
  version,
  client,
  definitions,
  records,
  blocks,
  readOnly,
  actor,
  onActor,
  onClose,
  onOpen,
  onEdit,
  onNew,
  onChanged,
  onDiscuss,
  onCurrentSource,
}: {
  projectId: string;
  identifier: string;
  version?: number;
  client: Client;
  definitions: Definitions;
  records: HandoverRecord[];
  blocks: string[];
  readOnly: boolean;
  actor: string;
  onActor: (value: string) => void;
  onClose: () => void;
  onOpen: (id: string, version?: number) => void;
  onEdit: (row: HandoverRecord) => void;
  onNew: (kind: Kind, initial: Payload) => void;
  onChanged: () => void;
  onDiscuss: (row: HandoverRecord) => void;
  onCurrentSource: (row: HandoverRecord) => Promise<void>;
}) {
  const query = useQuery({
    queryKey: ['handover-record', projectId, identifier, version],
    queryFn: () =>
      client.get<HandoverRecord>(`/records/${identifier}${version ? `?version=${version}` : ''}`),
  });
  const history = useQuery({
    queryKey: ['handover-history', projectId, identifier],
    queryFn: () =>
      client.get<
        {
          version: number;
          state: string;
          created_at: string;
          confirmation: HandoverRecord['confirmation'];
        }[]
      >(`/records/${identifier}/history`),
  });
  const [section, setSection] = useState('summary');
  const [action, setAction] = useState('');
  const [opinion, setOpinion] = useState('');
  const [role, setRole] = useState('');
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const [snapshot, setSnapshot] = useState<{ path: string; content: string; sha256: string }>();
  const [comparison, setComparison] = useState<{ changed: boolean }>();
  const row = query.data;
  async function act() {
    if (!row) return;
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
      void history.refetch();
    } catch (error) {
      setError(error);
    } finally {
      setBusy(false);
    }
  }
  const relatedKinds: Record<string, Kind[]> = {
    evidence: ['verification'],
    issues: ['issue', 'decision', 'constraint'],
    plan: ['plan'],
  };
  const related = records.filter(
    (item) =>
      item.state !== 'archived' &&
      (text(item.payload.task_id) === identifier ||
        ids(item.payload.task_ids).includes(identifier) ||
        ids(row?.payload.constraints).includes(item.id)) &&
      relatedKinds[section]?.includes(item.kind),
  );
  return (
    <HandoverModal
      title={row?.title || '交接记录'}
      description={version ? '正在查看固定历史版本' : '复核内容、关联证据和接续条件'}
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
              !['source', 'package', 'job'].includes(row.kind) &&
              !(row.kind === 'candidate' && text(row.payload.promoted_id)) &&
              row.state !== 'archived' && (
                <Button onClick={() => onEdit(row)}>
                  {row.kind === 'candidate' ? '审核并合并' : '编辑'}
                </Button>
              )}
            <Button onClick={() => onDiscuss(row)}>在对话中讨论</Button>
          </div>
          {row.kind === 'task' && (
            <>
              <nav className="handover-detail-tabs" aria-label="工作项详情">
                {[
                  ['summary', '目标与现状'],
                  ['evidence', '证据与验证'],
                  ['issues', '问题与依赖'],
                  ['plan', '接续计划'],
                ].map(([id, label]) => (
                  <Button
                    key={id}
                    className={section === id ? 'active' : ''}
                    aria-pressed={section === id}
                    onClick={() => setSection(id)}
                  >
                    {label}
                  </Button>
                ))}
              </nav>
              {blocks.length > 0 && (
                <div className="handover-notice handover-risk">
                  <strong>接续前需要处理</strong>
                  <ul>
                    {blocks.map((block) => (
                      <li key={block}>{block}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
          {row.kind === 'candidate' ? (
            <>
              <p className="handover-notice">
                AI 候选 · {definitions.kinds[text(row.payload.target_kind) as Kind]}
                <br />
                {text(row.payload.reason)}
              </p>
              <RecordContent
                row={{ ...row, payload: row.payload.proposed as Payload }}
                records={records}
                definitions={definitions}
                onOpen={onOpen}
              />
            </>
          ) : section === 'summary' || row.kind !== 'task' ? (
            <RecordContent row={row} records={records} definitions={definitions} onOpen={onOpen} />
          ) : (
            <>
              <div className="handover-actions">
                {!readOnly &&
                  relatedKinds[section]?.map((kind) => (
                    <Button
                      key={kind}
                      onClick={() =>
                        onNew(kind, {
                          ...(kind === 'constraint' ? {} : { task_id: identifier }),
                          ...(kind === 'plan' || kind === 'verification'
                            ? { baseline_id: text(row.payload.baseline_id) }
                            : {}),
                          ...(kind === 'constraint' ? { task_ids: [identifier] } : {}),
                        })
                      }
                    >
                      新增{definitions.kinds[kind]}
                    </Button>
                  ))}
              </div>
              {section === 'issues' && (
                <p>
                  依赖工作：
                  {ids(row.payload.dependencies).map((id) => (
                    <Button key={id} onClick={() => onOpen(id)}>
                      {records.find((item) => item.id === id)?.title || id}
                    </Button>
                  ))}
                </p>
              )}
              <div className="handover-cards">
                {related.map((item) => (
                  <RecordCard row={item} definitions={definitions} onOpen={onOpen} key={item.id} />
                ))}
              </div>
              {!related.length && (
                <p className="handover-empty">尚无相关记录。补充真实信息后再确认。</p>
              )}
            </>
          )}
          {row.kind === 'source' && (
            <section className="handover-form-section">
              <div className="handover-actions">
                <Button
                  onClick={() =>
                    void client
                      .download(
                        `/sources/${row.id}/original`,
                        text(row.payload.filename).split(/[\\/]/).pop() || '原始资料',
                      )
                      .catch(setError)
                  }
                >
                  下载原始附件
                </Button>
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
                    <Button onClick={() => void onCurrentSource(row).catch(setError)}>
                      在源码阅读器打开
                    </Button>
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
          {row.kind === 'package' && (
            <div className="handover-actions">
              {['docx', 'zip'].map((format) => (
                <Button
                  key={format}
                  onClick={() =>
                    void client
                      .download(
                        `/packages/${row.id}/export?format=${format}&version=${row.version}`,
                        `${row.title}.${format}`,
                      )
                      .catch(setError)
                  }
                >
                  下载{format === 'docx' ? ' Word 交接包' : '完整归档含原始附件'}
                </Button>
              ))}
              {!readOnly && (
                <Button
                  onClick={() =>
                    onNew('receipt', { package_id: row.id, package_version: row.version })
                  }
                >
                  记录接收与复述
                </Button>
              )}
            </div>
          )}
          {!readOnly && !version && row.kind !== 'job' && (
            <div className="handover-actions handover-form-section">
              {row.state !== 'archived' &&
                row.state !== 'confirmed' &&
                row.kind !== 'candidate' && (
                  <Button disabled={busy} onClick={() => setAction('confirm')}>
                    人工确认此版本
                  </Button>
                )}
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
              <h3>
                {action === 'confirm'
                  ? '确认当前版本'
                  : action === 'archive'
                    ? '归档记录'
                    : '恢复记录'}
              </h3>
              <p>请填写实际姓名和复核意见；确认会留下版本记录。</p>
              <div className="handover-fields">
                <label>
                  <span>确认人</span>
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
                  <span>复核意见</span>
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
          <details className="handover-form-section">
            <summary>修改与确认历史</summary>
            <ErrorText error={history.error} />
            {history.data?.map((item) => (
              <div className="handover-history" key={item.version}>
                <Button onClick={() => onOpen(identifier, item.version)}>
                  v{item.version} · {definitions.states[item.state]}
                </Button>
                <span>
                  {item.confirmation?.actor || '草稿保存'} · {localTime(item.created_at)}
                </span>
              </div>
            ))}
          </details>
        </>
      )}
    </HandoverModal>
  );
}
