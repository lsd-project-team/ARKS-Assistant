import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { BookOpen, RefreshCw } from 'lucide-react';
import { jsonBody } from '../../../app/api/client';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { Select } from '../../../shared/ui/Select';
import { useProjectApi } from '../hooks/useProjectApi';
import {
  codeWorkError,
  documentCanReview,
  readingCanStart,
  readingStatusLabels,
} from '../lib/codeWorkRules';
import type { ReadingDocument, ReadingJob } from '../types/codeWork';
import { ReadingFileStatus } from './ReadingFileStatus';

export function ProjectReadingPanel({
  projectId,
  readOnly,
}: {
  projectId: string;
  readOnly: boolean;
}) {
  const api = useProjectApi();
  const cache = useQueryClient();
  const [selectedId, setSelectedId] = useState('');
  const [title, setTitle] = useState('');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState<unknown>();
  const prefix = ['project-reading', projectId];
  const listing = useQuery({
    queryKey: prefix,
    queryFn: ({ signal }) =>
      api<{ jobs: ReadingJob[]; latest: ReadingJob | null }>('/project-reading', { signal }),
    refetchInterval: (query) =>
      query.state.data?.jobs.some((job) => job.status === 'running') ? 2500 : false,
  });
  const id = selectedId || listing.data?.latest?.id || listing.data?.jobs[0]?.id || '';
  const detail = useQuery({
    queryKey: [...prefix, id],
    queryFn: ({ signal }) =>
      api<ReadingJob>(`/project-reading/${encodeURIComponent(id)}`, { signal }),
    enabled: !!id,
    refetchInterval: (query) => (query.state.data?.status === 'running' ? 2000 : false),
  });
  const job = detail.data;
  const documents = useQuery({
    queryKey: [...prefix, id, 'documents', job?.updated_at],
    queryFn: ({ signal }) =>
      api<{ documents: ReadingDocument[] }>(
        `/project-reading/${encodeURIComponent(id)}/documents`,
        { signal },
      ),
    enabled: !!id,
    refetchInterval: job?.status === 'running' ? 4000 : false,
  });

  async function act(action: 'create' | 'start' | 'pause' | 'refresh') {
    setBusy(action);
    setError(undefined);
    try {
      const next = await api<ReadingJob>(
        action === 'create'
          ? '/project-reading'
          : `/project-reading/${encodeURIComponent(id)}/${action}`,
        {
          method: 'POST',
          ...(action === 'create' ? { body: jsonBody({ title: title.trim() || undefined }) } : {}),
        },
      );
      setSelectedId(next.id);
      cache.setQueryData([...prefix, next.id], next);
      if (action === 'create') setTitle('');
      await cache.invalidateQueries({ queryKey: prefix });
    } catch (reason) {
      setError(codeWorkError(reason));
    } finally {
      setBusy('');
    }
  }

  async function review(document: ReadingDocument, decision: 'approved' | 'needs_changes') {
    setBusy(document.id);
    setError(undefined);
    try {
      await api(
        `/project-reading/${encodeURIComponent(id)}/documents/${encodeURIComponent(document.id)}/review`,
        {
          method: 'POST',
          body: jsonBody({ version: document.version, decision }),
        },
      );
      await cache.invalidateQueries({ queryKey: prefix });
    } catch (reason) {
      setError(codeWorkError(reason));
    } finally {
      setBusy('');
    }
  }

  return (
    <section className="code-work-panel" aria-label="全项目阅读">
      <div className="code-work-heading">
        <div>
          <h2>
            <BookOpen size={17} />
            全项目阅读
          </h2>
          <p className="muted">按源码快照持续阅读，分别保留读取、分析与人工评审进度。</p>
        </div>
        <Button
          disabled={!!busy}
          onClick={() => void cache.invalidateQueries({ queryKey: prefix })}
        >
          <RefreshCw size={14} />
          刷新状态
        </Button>
      </div>
      <p className="muted">
        开始或继续会调用已配置模型，使用供应商额度。每次默认最多分析 64
        个分块，预算用完会保存进度并暂停，可再次继续。
      </p>
      <form
        className="code-work-inline"
        onSubmit={(event) => {
          event.preventDefault();
          void act('create');
        }}
      >
        <input
          aria-label="阅读计划名称"
          maxLength={200}
          placeholder="阅读计划名称（可选）"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          disabled={readOnly || !!busy}
        />
        <Button disabled={readOnly || !!busy} type="submit">
          建立阅读快照
        </Button>
      </form>
      <ErrorText error={error || listing.error || detail.error || documents.error} />
      {listing.isPending ? (
        <p className="muted">正在读取阅读计划…</p>
      ) : !listing.data?.jobs.length ? (
        <p className="code-work-empty">还没有阅读计划。建立快照后可开始、暂停，并在中断后继续。</p>
      ) : (
        <>
          <Select value={id} onValueChange={setSelectedId} aria-label="选择阅读计划">
            {listing.data.jobs.map((item) => (
              <option key={item.id} value={item.id}>
                {item.title} · {readingStatusLabels[item.status]}
              </option>
            ))}
          </Select>
          {job && (
            <>
              <div className="code-work-summary">
                <strong role="status">{readingStatusLabels[job.status]}</strong>
                <span>源码快照 {String(job.snapshot_version)}</span>
              </div>
              <ErrorText error={job.error} />
              <div className="code-work-actions">
                {readingCanStart(job) && (
                  <Button
                    className="primary"
                    disabled={readOnly || !!busy}
                    onClick={() => void act('start')}
                  >
                    {job.status === 'ready' ? '开始阅读' : '继续阅读'}
                  </Button>
                )}
                {job.status === 'running' && (
                  <Button disabled={readOnly || !!busy} onClick={() => void act('pause')}>
                    暂停阅读
                  </Button>
                )}
                <Button
                  disabled={readOnly || !!busy || job.status === 'running'}
                  onClick={() => void act('refresh')}
                >
                  核对源码变化
                </Button>
              </div>
              <ReadingCoverage job={job} />
              <div className="code-work-table-wrap">
                <table className="code-work-table">
                  <caption>模块覆盖</caption>
                  <thead>
                    <tr>
                      <th>模块</th>
                      <th>总计</th>
                      <th>已读</th>
                      <th>已分析</th>
                      <th>已评审</th>
                      <th>待处理</th>
                      <th>失败 / 过期</th>
                    </tr>
                  </thead>
                  <tbody>
                    {job.modules.map((module) => (
                      <tr key={module.name}>
                        <th scope="row">{module.name}</th>
                        <td>{module.total}</td>
                        <td>{module.read}</td>
                        <td>{module.analyzed}</td>
                        <td>{module.reviewed}</td>
                        <td>{module.pending}</td>
                        <td>
                          {module.failed} / {module.stale}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <ReadingFileStatus projectId={projectId} jobId={job.id} version={job.updated_at} />
              <h3>阅读成果与待核实内容</h3>
              {documents.isPending ? (
                <p className="muted">正在读取成果…</p>
              ) : !documents.data?.documents.length ? (
                <p className="code-work-empty">
                  尚无分析成果。已建立索引或读取文件不代表已完成分析。
                </p>
              ) : (
                documents.data.documents.map((document) => (
                  <ReadingResult
                    key={document.id}
                    document={document}
                    disabled={readOnly || !!busy || job.status === 'running'}
                    onReview={(decision) => void review(document, decision)}
                  />
                ))
              )}
            </>
          )}
        </>
      )}
    </section>
  );
}

function ReadingCoverage({ job }: { job: ReadingJob }) {
  const values = [
    ['文件', job.counts.files],
    ['已索引', job.counts.indexed],
    ['已读取', job.counts.read],
    ['已分析', job.counts.analyzed],
    ['已评审', job.counts.reviewed],
    ['待处理', job.counts.pending],
    ['失败', job.counts.failed],
    ['已排除', job.counts.excluded],
    ['已过期', job.counts.stale],
  ];
  return (
    <dl className="code-work-counts">
      {values.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function ReadingResult({
  document,
  disabled,
  onReview,
}: {
  document: ReadingDocument;
  disabled: boolean;
  onReview: (decision: 'approved' | 'needs_changes') => void;
}) {
  return (
    <details className="code-work-document">
      <summary>
        <strong>{document.path}</strong>
        <span>
          第 {document.start_line}–{document.end_line} 行 · v{document.version} · {document.status}
        </span>
      </summary>
      <div className="code-work-document-body">
        <p className="code-work-source-version">源码版本：{document.source_version}</p>
        <p className="code-work-prose">{document.summary || '本段尚无分析结论。'}</p>
        {!!document.entrypoints?.length && <p>入口：{document.entrypoints.join('、')}</p>}
        {!!document.dependencies?.length && <p>依赖：{document.dependencies.join('、')}</p>}
        {!!document.references?.length && (
          <details>
            <summary>源码依据</summary>
            <ul>
              {document.references.map((reference, index) => (
                <li className="code-work-source-version" key={index}>
                  {reference.path} · 第 {reference.start_line}–{reference.end_line} 行 ·{' '}
                  {reference.source_version}
                </li>
              ))}
            </ul>
          </details>
        )}
        <h4>未知与待核实</h4>
        {document.unknowns?.length ? (
          <ul>
            {document.unknowns.map((unknown, index) => (
              <li key={index}>{unknown}</li>
            ))}
          </ul>
        ) : (
          <p className="muted">本段未列出额外未知项；这不代表设备行为已经验证。</p>
        )}
        <div className="code-work-actions">
          <Button
            disabled={disabled || !documentCanReview(document)}
            onClick={() => onReview('approved')}
          >
            确认本版成果
          </Button>
          <Button
            disabled={disabled || !documentCanReview(document)}
            onClick={() => onReview('needs_changes')}
          >
            需要修订
          </Button>
        </div>
      </div>
    </details>
  );
}
