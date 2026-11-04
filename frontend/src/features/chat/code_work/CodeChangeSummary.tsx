import { useId, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ChevronUp, FileDiff } from 'lucide-react';
import { api } from '../../../app/api/client';
import { Button, ErrorText } from '../../../shared/ui/ui';
import type { WorkSummary } from './types';
import './change-summary.css';

const number = new Intl.NumberFormat('zh-CN');

function LineCounts({ additions, deletions }: { additions: number; deletions: number }) {
  return (
    <span className="code-change-counts" aria-label={`新增 ${additions} 行，删除 ${deletions} 行`}>
      <span className="code-change-add">+{number.format(additions)}</span>
      <span className="code-change-delete">−{number.format(deletions)}</span>
    </span>
  );
}

export function CodeChangeSummary({
  threadId,
  projectId,
  busy,
  refreshKey,
  onOpen,
}: {
  threadId: string;
  projectId: string;
  busy: boolean;
  refreshKey: string;
  onOpen: (path?: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const filesId = useId();
  const query = useQuery({
    queryKey: ['code-work', projectId, threadId, 'summary', refreshKey],
    queryFn: () => api<WorkSummary>(`/threads/${threadId}/code-work/summary`, undefined, projectId),
    enabled: !!threadId,
    refetchInterval: busy ? 1500 : false,
  });
  if (query.error)
    return (
      <div className="code-change-error">
        <ErrorText error={query.error} />
        <Button onClick={() => void query.refetch()}>重试修改摘要</Button>
      </div>
    );
  const summary = query.data;
  if (!summary?.files.length) return null;
  const visible = expanded ? summary.files : summary.files.slice(0, 3);
  return (
    <section className="code-change-summary" aria-label="代码修改摘要">
      <div className="code-change-heading">
        <span className="code-change-icon">
          <FileDiff size={19} aria-hidden="true" />
        </span>
        <div className="code-change-title">
          <strong>已修改 {number.format(summary.files.length)} 个文件</strong>
          <span className="code-change-subtitle">
            当前副本 <LineCounts {...summary} />
          </span>
        </div>
        <Button onClick={() => onOpen()}>查看变更</Button>
      </div>
      <ul id={filesId} className="code-change-files">
        {visible.map((file) => (
          <li key={file.path}>
            <button
              type="button"
              title={file.path}
              aria-label={`查看文件差异：${file.path}`}
              onClick={() => onOpen(file.path)}
            >
              <span className="code-change-path">
                <span className="code-change-directory">
                  {file.path.slice(0, file.path.lastIndexOf('/') + 1)}
                </span>
                <span className="code-change-name">{file.path.split('/').at(-1)}</span>
              </span>
              <LineCounts additions={file.additions} deletions={file.deletions} />
            </button>
          </li>
        ))}
      </ul>
      {summary.files.length > 3 && (
        <button
          type="button"
          className="code-change-expand"
          aria-expanded={expanded}
          aria-controls={filesId}
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? '收起文件列表' : `再显示 ${number.format(summary.files.length - 3)} 个文件`}
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      )}
    </section>
  );
}
