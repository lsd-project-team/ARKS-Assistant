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
  runId = '',
  showCumulative = true,
}: {
  threadId: string;
  projectId: string;
  busy: boolean;
  refreshKey: string;
  onOpen: (path?: string, runId?: string) => void;
  runId?: string;
  showCumulative?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const [scope, setScope] = useState<'turn' | 'all'>('turn');
  const filesId = useId();
  const cumulative = useQuery({
    queryKey: ['code-work', projectId, threadId, 'summary', refreshKey],
    queryFn: () => api<WorkSummary>(`/threads/${threadId}/code-work/summary`, undefined, projectId),
    enabled: !!threadId && showCumulative,
    refetchInterval: busy ? 1500 : false,
  });
  const turn = useQuery({
    queryKey: ['code-work', projectId, threadId, 'summary', runId, refreshKey],
    queryFn: () =>
      api<WorkSummary>(
        `/threads/${threadId}/code-work/summary?run_id=${encodeURIComponent(runId)}`,
        undefined,
        projectId,
      ),
    enabled: !!threadId && !!runId,
    refetchInterval: busy ? 1500 : false,
  });
  const useTurn = !!runId && scope === 'turn' && (!!turn.data?.files.length || !showCumulative);
  const query = useTurn ? turn : cumulative;
  if (query.error)
    return (
      <div className="code-change-error">
        <ErrorText error={query.error} />
        <Button onClick={() => void query.refetch()}>重试修改摘要</Button>
      </div>
    );
  const summary = query.data;
  if (!summary || (!summary.files.length && !(runId && showCumulative && turn.data?.files.length)))
    return null;
  const visible = expanded ? summary.files : summary.files.slice(0, 3);
  return (
    <section className="code-change-summary" aria-label="代码修改摘要">
      <div className="code-change-heading">
        <span className="code-change-icon">
          <FileDiff size={19} aria-hidden="true" />
        </span>
        <div className="code-change-title">
          <strong>
            {summary.files.length
              ? `已修改 ${number.format(summary.files.length)} 个文件`
              : '暂无待合入修改'}
          </strong>
          <span className="code-change-subtitle">
            {useTurn ? '本轮修改' : '全部待合入'} <LineCounts {...summary} />
          </span>
        </div>
        <Button onClick={() => onOpen(undefined, useTurn ? runId : '')}>查看变更</Button>
      </div>
      {runId && showCumulative && !!turn.data?.files.length && (
        <div className="code-change-scope" role="group" aria-label="修改摘要范围">
          <button type="button" aria-pressed={useTurn} onClick={() => setScope('turn')}>
            本轮修改
          </button>
          <button type="button" aria-pressed={!useTurn} onClick={() => setScope('all')}>
            全部待合入
          </button>
        </div>
      )}
      <ul id={filesId} className="code-change-files">
        {visible.map((file) => (
          <li key={file.path}>
            <button
              type="button"
              title={file.path}
              aria-label={`查看文件差异：${file.path}`}
              onClick={() => onOpen(file.path, useTurn ? runId : '')}
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
