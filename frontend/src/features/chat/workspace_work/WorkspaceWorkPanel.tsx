import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, FolderTree, RefreshCw, RotateCcw, X } from 'lucide-react';
import { api, jsonBody } from '../../../app/api/client';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { DiffLines } from './DiffLines';
import { commandLabels, type WorkDiff, type WorkStatus } from './types';
import './workspace-work.css';

export function WorkspaceWorkPanel({
  threadId,
  projectId,
  busy,
  onClose,
  onConfigure,
}: {
  threadId: string;
  projectId: string;
  busy: boolean;
  onClose: () => void;
  onConfigure?: () => void;
}) {
  const cache = useQueryClient();
  const base = `/threads/${threadId}/workspace-work`;
  const key = ['workspace-work', projectId, threadId];
  const [selected, setSelected] = useState('');
  const [expanded, setExpanded] = useState('');
  const status = useQuery({
    queryKey: key,
    queryFn: () => api<WorkStatus>(base, undefined, projectId),
    refetchInterval: 2000,
  });
  const diff = useQuery({
    queryKey: [...key, 'diff', selected],
    queryFn: () =>
      api<WorkDiff>(`${base}/diff?path=${encodeURIComponent(selected)}`, undefined, projectId),
    enabled: !!selected,
  });
  const refresh = () => {
    void status.refetch();
    if (selected) void diff.refetch();
  };
  const restore = useMutation({
    mutationFn: (path: string) =>
      api(base + '/restore', { method: 'POST', body: jsonBody({ path }) }, projectId),
    onSuccess: () => {
      setSelected('');
      void cache.invalidateQueries({ queryKey: key });
    },
  });
  const decide = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: 'approve' | 'deny' }) =>
      api(
        `${base}/approvals/${id}`,
        { method: 'POST', body: jsonBody({ decision }) },
        projectId,
      ),
    onSuccess: refresh,
  });
  const data = status.data;
  const files = data?.files || [];
  const commands = data?.commands || [];
  return (
    <section className="code-pane work-panel" aria-label="代码工作区">
      <header className="work-panel-header">
        <div className="work-panel-title">
          <FolderTree size={15} />
          <strong>代码工作区</strong>
          {data?.exists && (
            <span className="muted" title={data.root}>
              {data.root}
            </span>
          )}
        </div>
        <div className="work-panel-actions">
          {!!data?.exists && (
            <span className="work-counts" aria-label="当前改动行数">
              <span className="add">+{data.additions || 0}</span>
              <span className="del">−{data.deletions || 0}</span>
            </span>
          )}
          <Button className="icon-button" title="刷新" aria-label="刷新工作区" onClick={refresh}>
            <RefreshCw size={14} />
          </Button>
          <Button
            className="icon-button"
            title="还原本对话的全部修改"
            aria-label="还原全部修改"
            disabled={!files.length || busy || restore.isPending}
            onClick={() => {
              if (window.confirm('把本对话修改过的文件还原到第一次修改前？')) restore.mutate('');
            }}
          >
            <RotateCcw size={14} />
          </Button>
          <Button className="icon-button" title="关闭" aria-label="关闭代码工作区" onClick={onClose}>
            <X size={15} />
          </Button>
        </div>
      </header>
      {!data && status.isPending && <p className="muted work-empty">正在读取工作区…</p>}
      {data && !data.configured && (
        <div className="work-empty">
          <p>本项目还没有配置代码工作目录。</p>
          {onConfigure && <Button onClick={onConfigure}>去管理员配置</Button>}
        </div>
      )}
      {data?.configured && (
        <div className="work-body">
          {!!data.approvals?.length && (
            <div className="work-approvals" role="alert">
              {data.approvals.map((approval) => (
                <div key={approval.id} className="work-approval">
                  <div>
                    <strong>请求执行命令</strong>
                    <code>
                      {approval.argv.join(' ')} {approval.cwd && `（${approval.cwd}）`}
                    </code>
                  </div>
                  <div className="work-approval-actions">
                    <Button
                      disabled={decide.isPending}
                      onClick={() => decide.mutate({ id: approval.id, decision: 'approve' })}
                    >
                      <Check size={13} /> 批准
                    </Button>
                    <Button
                      disabled={decide.isPending}
                      onClick={() => decide.mutate({ id: approval.id, decision: 'deny' })}
                    >
                      <X size={13} /> 拒绝
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
          <div className="work-files" aria-label="修改文件">
            {files.length ? (
              files.map((file) => (
                <div key={file.path} className="work-file">
                  <div className="work-file-heading">
                    <button
                      type="button"
                      className="work-file-toggle"
                      aria-expanded={selected === file.path}
                      onClick={() => setSelected(selected === file.path ? '' : file.path)}
                    >
                      <span className="work-file-name">{file.path}</span>
                      <span className="work-file-kind">{file.kind === 'added' ? '新增' : ''}</span>
                      <span className="work-counts">
                        <span className="add">+{file.additions}</span>
                        <span className="del">−{file.deletions}</span>
                      </span>
                    </button>
                    <Button
                      className="icon-button"
                      title="还原此文件"
                      aria-label={`还原 ${file.path}`}
                      disabled={busy || restore.isPending}
                      onClick={() => restore.mutate(file.path)}
                    >
                      <RotateCcw size={13} />
                    </Button>
                  </div>
                  {selected === file.path && (
                    <div className="work-file-diff">
                      {diff.isPending && <p className="muted">正在读取差异…</p>}
                      {diff.data && <DiffLines diff={diff.data.diff} />}
                      <ErrorText error={diff.error} />
                    </div>
                  )}
                </div>
              ))
            ) : (
              <p className="muted work-empty">本对话还没有修改文件。让 AI 读取并修改工作区代码。</p>
            )}
          </div>
          <div className="work-commands">
            <h3>命令记录</h3>
            {commands.length ? (
              commands.map((item) => (
                <div key={item.id} className="work-command">
                  <button
                    type="button"
                    className="work-command-head"
                    aria-expanded={expanded === item.id}
                    onClick={() => setExpanded(expanded === item.id ? '' : item.id)}
                  >
                    <code>{item.argv.join(' ')}</code>
                    <span className={`work-command-status ${item.status}`}>
                      {commandLabels[item.status] || item.status}
                      {item.exit_code !== null && item.exit_code !== undefined
                        ? ` · ${item.exit_code}`
                        : ''}
                    </span>
                  </button>
                  {expanded === item.id && (
                    <pre className="work-command-output">{item.output || '（没有输出）'}</pre>
                  )}
                </div>
              ))
            ) : (
              <p className="muted">还没有执行命令。</p>
            )}
          </div>
        </div>
      )}
      <ErrorText error={status.error || restore.error || decide.error} />
    </section>
  );
}
