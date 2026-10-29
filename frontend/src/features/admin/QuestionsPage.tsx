import { useState } from 'react';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import ReactMarkdown, { defaultUrlTransform } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ArrowLeft, ArrowUpRight, Search } from 'lucide-react';
import { Button, ErrorText, Modal } from '../../shared/ui/ui';
import { Select } from '../../shared/ui/Select';
import { useDebouncedValue } from '../../shared/hooks/useDebouncedValue';
import type { ProjectList } from '../../shared/types/api';
import { adminApi, dateTime, duration, runLabels } from './client';
import type { ManagedAccount, QuestionDetail, QuestionSummary, RecordedRun } from './types';
import {
  handoverDocumentText,
  handoverReference,
  isKnowledgeReference,
} from '../knowledge/lib/knowledgeReference';
import { debugIssueFields } from '../handover/debug_issues/debugIssues';
import { text as fieldText, type HandoverRecord } from '../handover/shared/types';

export function QuestionsPage({ identifier }: { identifier?: string }) {
  const [text, setText] = useState('');
  const [user, setUser] = useState('');
  const [project, setProject] = useState('');
  const [status, setStatus] = useState('');
  const [after, setAfter] = useState('');
  const [before, setBefore] = useState('');
  const [offset, setOffset] = useState(0);
  const settled = useDebouncedValue(text);
  const users = useQuery({
    queryKey: ['admin-accounts'],
    queryFn: () => adminApi<ManagedAccount[]>('/admin/accounts'),
  });
  const projects = useQuery({
    queryKey: ['admin-projects'],
    queryFn: async () => {
      const [active, archived] = await Promise.all([
        adminApi<ProjectList>('/projects'),
        adminApi<ProjectList>('/projects?state=archived'),
      ]);
      return { ...active, projects: [...active.projects, ...archived.projects] };
    },
  });
  const parameters = new URLSearchParams({
    query: settled,
    user_id: user,
    project_id: project,
    status,
    offset: String(offset),
  });
  if (after) parameters.set('after', new Date(`${after}T00:00:00`).toISOString());
  if (before) parameters.set('before', new Date(`${before}T23:59:59.999`).toISOString());
  const list = useQuery({
    queryKey: ['admin-questions', parameters.toString()],
    queryFn: () =>
      adminApi<{ items: QuestionSummary[]; total: number }>(`/admin/questions?${parameters}`),
    enabled: !identifier,
    refetchInterval: 15000,
  });
  const change = (set: (value: string) => void, value: string) => {
    set(value);
    setOffset(0);
  };
  if (identifier) return <QuestionViewer identifier={identifier} />;
  return (
    <div className="admin-page">
      <header className="admin-heading">
        <div>
          <h1>AI 问答记录</h1>
        </div>
      </header>
      <section className="admin-panel">
        <div className="admin-filter-grid">
          <label className="admin-search">
            <Search size={16} />
            <input
              aria-label="搜索问答记录"
              placeholder="搜索对话标题或问答正文"
              value={text}
              onChange={(e) => change(setText, e.target.value)}
            />
          </label>
          <Select
            aria-label="筛选问答用户"
            value={user}
            onValueChange={(value) => change(setUser, value)}
          >
            <option value="">全部用户</option>
            <option value="unknown">身份未记录</option>
            {users.data?.map((row) => (
              <option value={row.id} key={row.id}>
                {row.display_name}（{row.username}）
              </option>
            ))}
          </Select>
          <Select
            aria-label="筛选问答项目"
            value={project}
            onValueChange={(value) => change(setProject, value)}
          >
            <option value="">全部项目</option>
            {projects.data?.projects.map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
              </option>
            ))}
          </Select>
          <Select
            aria-label="筛选问答状态"
            value={status}
            onValueChange={(value) => change(setStatus, value)}
          >
            <option value="">全部状态</option>
            {Object.entries(runLabels).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </Select>
          <label>
            开始日期
            <input
              aria-label="问答开始日期"
              type="date"
              value={after}
              onChange={(e) => change(setAfter, e.target.value)}
            />
          </label>
          <label>
            结束日期
            <input
              aria-label="问答结束日期"
              type="date"
              min={after}
              value={before}
              onChange={(e) => change(setBefore, e.target.value)}
            />
          </label>
        </div>
        <ErrorText error={list.error || users.error || projects.error} />
        {list.isError && <Button onClick={() => void list.refetch()}>重新加载</Button>}
        {list.isPending && <p role="status">正在读取问答记录…</p>}
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>对话</th>
                <th>用户</th>
                <th>所属项目</th>
                <th>提问数</th>
                <th>最近状态</th>
                <th>更新时间</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {list.data?.items.map((row) => (
                <tr key={row.id}>
                  <td>
                    <a className="admin-title-link" href={`#admin/questions/${row.id}`}>
                      {row.title}
                    </a>
                    {row.state !== 'active' && (
                      <small>{row.state === 'deleted' ? '已移入回收站' : '已归档'}</small>
                    )}
                  </td>
                  <td>{row.users.join('、')}</td>
                  <td>{row.project_name}</td>
                  <td>{row.questions}</td>
                  <td>
                    <span
                      className={`admin-badge ${row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : ''}`}
                    >
                      {runLabels[row.status] || row.status}
                    </span>
                  </td>
                  <td>{dateTime(row.updated_at)}</td>
                  <td>
                    <a aria-label={`查看 ${row.title}`} href={`#admin/questions/${row.id}`}>
                      <ArrowUpRight size={17} />
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {list.data && !list.data.items.length && (
          <p className="admin-empty">没有匹配的问答记录。</p>
        )}
        <div className="admin-pagination">
          <span>共 {list.data?.total || 0} 个对话</span>
          <Button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 30))}>
            上一页
          </Button>
          <Button
            disabled={!list.data || offset + 30 >= list.data.total}
            onClick={() => setOffset(offset + 30)}
          >
            下一页
          </Button>
        </div>
      </section>
    </div>
  );
}

function QuestionViewer({ identifier }: { identifier: string }) {
  const [reference, setReference] = useState<{ href: string; run?: RecordedRun }>();
  const detail = useInfiniteQuery({
    queryKey: ['admin-question', identifier],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      adminApi<QuestionDetail>(`/admin/questions/${identifier}?offset=${pageParam}`),
    getNextPageParam: (last) =>
      last.offset + last.messages.length < last.total
        ? last.offset + last.messages.length
        : undefined,
    refetchInterval: 15000,
  });
  const first = detail.data?.pages[0];
  const messages = detail.data?.pages.flatMap((page) => page.messages) || [];
  const runs = [
    ...new Map(
      detail.data?.pages.flatMap((page) => page.runs).map((run) => [run.id, run]),
    ).values(),
  ];
  const markdown = (content: string, run?: RecordedRun) => (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      urlTransform={(url) => (isKnowledgeReference(url) ? url : defaultUrlTransform(url))}
      components={{
        a: ({ href, children }) =>
          isKnowledgeReference(href || '') ? (
            <button className="source-link" onClick={() => setReference({ href: href!, run })}>
              {children}
            </button>
          ) : (
            <a href={href} target="_blank" rel="noreferrer">
              {children}
            </a>
          ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
  return (
    <div className="admin-page admin-question-view">
      <a className="admin-back" href="#admin/questions">
        <ArrowLeft size={16} />
        返回问答记录
      </a>
      <header className="admin-heading">
        <div>
          <h1>{first?.thread.title || '问答详情'}</h1>
          <p>
            {first?.project_name} · {first?.total || 0} 条消息
          </p>
        </div>
      </header>
      <ErrorText error={detail.error} />
      {detail.isError && <Button onClick={() => void detail.refetch()}>重试</Button>}
      {detail.isPending && <p role="status">正在读取问答…</p>}
      {messages.map((message) => {
        const run = runs.find((row) => row.response_message_id === message.id);
        const questionRuns = runs.filter((row) => row.message_id === message.id);
        return (
          <article className={`admin-message ${message.role}`} key={message.id}>
            <div className="admin-message-heading">
              <strong>
                {message.role === 'user'
                  ? message.actor.display_name || '用户 · 身份未记录'
                  : 'AI 回答'}
              </strong>
              <span>
                {message.role === 'user' && message.actor.username
                  ? `${message.actor.username} · `
                  : ''}
                {dateTime(message.created_at)}
              </span>
            </div>
            {!message.context_active && <p className="admin-collection-note">已保留为历史版本</p>}
            {message.origin_message_id && (
              <p className="admin-collection-note">来自对话分支的原始消息</p>
            )}
            <div className="admin-markdown">{markdown(message.content, run)}</div>
            {message.selections.map((selection, index) => (
              <details className="admin-evidence" key={index}>
                <summary>
                  代码选区 · {selection.path}:{selection.start_line}–{selection.end_line}
                </summary>
                <p className="muted">提交时保存的版本：{selection.version}</p>
                <pre>{selection.content}</pre>
              </details>
            ))}
            {questionRuns.map((item) => (
              <RunDetails
                key={item.id}
                run={item}
                onReference={(href) => setReference({ href, run: item })}
              >
                {!item.response_message_id && item.answer ? markdown(item.answer, item) : null}
              </RunDetails>
            ))}
          </article>
        );
      })}
      {first && !messages.length && <p className="admin-empty">此对话暂无消息。</p>}
      {detail.hasNextPage && (
        <Button disabled={detail.isFetchingNextPage} onClick={() => void detail.fetchNextPage()}>
          {detail.isFetchingNextPage ? '正在加载…' : '加载后续消息'}
        </Button>
      )}
      {reference && (
        <ReferenceDialog
          href={reference.href}
          run={reference.run}
          onClose={() => setReference(undefined)}
        />
      )}
    </div>
  );
}

function RunDetails({
  run,
  children,
  onReference,
}: {
  run: RecordedRun;
  children: React.ReactNode;
  onReference: (href: string) => void;
}) {
  const usage = run.evidence
    .filter((event) => event.kind === 'provider_usage')
    .map((event) => event.payload as Record<string, unknown>);
  const actual = usage.filter(
    (item) => typeof item.input_tokens === 'number' || typeof item.output_tokens === 'number',
  );
  const input = actual.reduce((sum, item) => sum + Number(item.input_tokens || 0), 0);
  const output = actual.reduce((sum, item) => sum + Number(item.output_tokens || 0), 0);
  const sources = run.evidence.filter((event) => event.kind === 'source_evidence');
  return (
    <details
      className="admin-evidence"
      open={run.status === 'failed' || run.status === 'cancelled' || run.status === 'interrupted'}
    >
      <summary>
        <span
          className={`admin-badge ${run.status === 'completed' ? 'success' : run.status === 'failed' ? 'danger' : ''}`}
        >
          {runLabels[run.status] || run.status}
        </span>{' '}
        {String(run.model_snapshot.profile_name || run.model_snapshot.model || '模型未记录')}
        {run.resumed_from ? ' · 恢复运行' : run.regenerated_from ? ' · 重新生成' : ''}
      </summary>
      <dl className="admin-run-facts">
        <div>
          <dt>开始时间</dt>
          <dd>{dateTime(run.started_at)}</dd>
        </div>
        <div>
          <dt>耗时</dt>
          <dd>
            {run.started_at && run.finished_at
              ? duration(new Date(run.finished_at).getTime() - new Date(run.started_at).getTime())
              : ['queued', 'running'].includes(run.status)
                ? '尚未完成'
                : '未记录'}
          </dd>
        </div>
        <div>
          <dt>供应商实报用量</dt>
          <dd>{actual.length ? `输入 ${input} / 输出 ${output} tokens` : '未返回用量'}</dd>
        </div>
      </dl>
      {run.error && <p className="admin-run-error">{run.error}</p>}
      {children && <div className="admin-markdown">{children}</div>}
      {!!sources.length && (
        <div className="admin-source-links">
          {sources.map((source) => {
            const payload = source.payload as {
              path: string;
              start_line: number;
              end_line: number;
            };
            return (
              <button
                key={source.id}
                onClick={() =>
                  onReference(`source:${payload.path}#L${payload.start_line}-L${payload.end_line}`)
                }
              >
                {payload.path}:{payload.start_line}–{payload.end_line}
              </button>
            );
          })}
        </div>
      )}
      {run.evidence
        .filter((event) => event.kind === 'context_sources')
        .map((event) => (
          <details key={event.id}>
            <summary>带入的资料与记忆</summary>
            <ContextSources value={event.payload} onReference={onReference} />
          </details>
        ))}
    </details>
  );
}

function ContextSources({
  value,
  onReference,
}: {
  value: unknown;
  onReference: (href: string) => void;
}) {
  const sources = value as {
    materials?: { id: string; title: string; version: number; citation?: string }[];
    memories?: { name: string; scope: string; version?: string }[];
  };
  return (
    <div>
      <p>
        项目资料：{sources.materials?.length || 0} 份 · 长期记忆：{sources.memories?.length || 0} 条
      </p>
      {sources.materials?.map((material) => (
        <p key={material.id}>
          {material.citation && /^material:/.test(material.citation) ? (
            <button className="source-link" onClick={() => onReference(material.citation!)}>
              {material.title} · v{material.version}
            </button>
          ) : (
            `${material.title} · v${material.version}`
          )}
        </p>
      ))}
      {sources.memories?.map((memory) => (
        <p key={`${memory.scope}/${memory.name}`}>
          {memory.name} · {memory.scope === 'project' ? '项目记忆' : '用户偏好'}
          {memory.version ? ` · ${memory.version}` : ''}
        </p>
      ))}
    </div>
  );
}

function ReferenceDialog({
  href,
  run,
  onClose,
}: {
  href: string;
  run?: RecordedRun;
  onClose: () => void;
}) {
  const source = /^source:(.+)#L(\d+)(?:-L?(\d+))?$/.exec(href);
  const material = /^material:([\w-]+)\/([\w-]+)\/(\d+)#L(\d+)(?:-L?(\d+))?$/.exec(href);
  const handover = handoverReference(href);
  let sourcePath = source?.[1] || '';
  try {
    sourcePath = decodeURIComponent(sourcePath);
  } catch {
    /* 保留原始路径交给服务端校验。 */
  }
  const evidence = run?.evidence
    .filter((event) => event.kind === 'source_evidence')
    .map(
      (event) => event.payload as { path: string; version: string; source_workspace_id?: string },
    )
    .find((row) => row.path === sourcePath);
  const content = useQuery({
    queryKey: ['admin-reference', href, evidence?.source_workspace_id],
    queryFn: async () => {
      if (handover) {
        const row = await adminApi<HandoverRecord>(
          `/handover/records/${handover.id}?version=${handover.version}`,
        );
        // 固定读取回答引用的历史版本，避免新版方案替换当时的依据。
        const content =
          handover.kind === 'debug-issue'
            ? debugIssueFields
                .filter(({ key }) => fieldText(row.payload[key]))
                .map(({ key, label }) => `${label}：${fieldText(row.payload[key])}`)
                .join('\n\n')
            : handoverDocumentText(row)
                .split('\n')
                .slice(handover.start - 1, handover.end)
                .join('\n');
        return { title: row.title, text: content, warning: `引用版本 v${row.version}` };
      }
      if (material) {
        const saved = await adminApi<{ title: string; content: string }>(
          `/projects/${material[1]}/materials/${material[2]}?version=${material[3]}`,
        );
        return { title: saved.title, text: saved.content, warning: '' };
      }
      if (!source || !evidence?.source_workspace_id)
        throw new Error('此历史引用未保存源码目录身份，请查看原始代码选区及来源记录。');
      const saved = await adminApi<{ path: string; content: string; version: string }>(
        `/sources/${evidence.source_workspace_id}/file?path=${encodeURIComponent(sourcePath)}`,
      );
      const start = Math.max(1, Number(source[2]));
      const end = Number(source[3] || source[2]);
      return {
        title: `${saved.path}:${start}–${end}`,
        text: saved.content
          .split('\n')
          .slice(start - 1, end)
          .join('\n'),
        warning:
          saved.version !== evidence.version
            ? '源码已变化，以下为当前版本；历史依据版本为 ' + evidence.version
            : '源码版本与本轮依据一致',
      };
    },
  });
  return (
    <Modal open title={content.data?.title || '引用来源'} onClose={onClose}>
      <div className="dialog-body">
        <ErrorText error={content.error} />
        {content.isPending && <p role="status">正在读取来源…</p>}
        {content.data && (
          <>
            <p className="muted">{content.data.warning}</p>
            <pre className="admin-reference-text">{content.data.text}</pre>
          </>
        )}
      </div>
      <div className="modal-footer">
        <Button onClick={onClose}>关闭</Button>
      </div>
    </Modal>
  );
}
