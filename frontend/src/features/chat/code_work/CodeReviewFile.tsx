import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ChevronDown, ChevronRight, FileCode2 } from 'lucide-react';
import { api, jsonBody } from '../../../app/api/client';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { toast } from '../../../shared/utils/toasts';
import { CodeWorkMenu } from './CodeWorkMenu';
import { ReviewDiff } from './ReviewDiff';
import type { WorkDiff, WorkStatus, WorkSummary } from './types';

export function ReviewLineCounts({
  additions,
  deletions,
}: {
  additions: number;
  deletions: number;
}) {
  return (
    <span className="code-review-counts" aria-label={`新增 ${additions} 行，删除 ${deletions} 行`}>
      <span>+{additions}</span>
      <span>−{deletions}</span>
    </span>
  );
}

export function CodeReviewFile({
  file,
  stats,
  base,
  projectId,
  threadId,
  runId,
  expanded,
  onToggle,
  focus,
  view,
  disabled,
  onChanged,
  onReview,
}: {
  file: NonNullable<WorkStatus['files']>[number];
  stats?: WorkSummary['files'][number];
  base: string;
  projectId: string;
  threadId: string;
  runId: string;
  expanded: boolean;
  onToggle: () => void;
  focus: boolean;
  view: { split: boolean; wrap: boolean };
  disabled: boolean;
  onChanged: () => void;
  onReview?: (request: string) => void;
}) {
  const section = useRef<HTMLElement>(null);
  const [confirm, setConfirm] = useState<{ path: string; version: string } | null>(null);
  const [copyError, setCopyError] = useState<unknown>(null);
  const key = ['code-work', projectId, threadId];
  const diff = useQuery({
    queryKey: [...key, 'diff', file.path, file.version, runId],
    queryFn: () =>
      api<WorkDiff>(
        `${base}/diff?path=${encodeURIComponent(file.path)}${runId ? `&run_id=${encodeURIComponent(runId)}` : ''}`,
        undefined,
        projectId,
      ),
    enabled: expanded,
  });
  useEffect(() => {
    if (focus) section.current?.scrollIntoView?.({ block: 'start' });
  }, [focus]);
  const revert = useMutation({
    mutationKey: [...key, 'edit'],
    mutationFn: (target: { path: string; version: string }) =>
      api(`${base}/revert`, { method: 'POST', body: jsonBody(target) }, projectId),
    onSuccess: () => {
      setConfirm(null);
      onChanged();
    },
  });
  const copyPath = async () => {
    try {
      await navigator.clipboard.writeText(file.path);
      setCopyError(null);
      toast('文件路径已复制');
    } catch {
      setCopyError(new Error('复制失败，请从文件标题选择完整路径'));
    }
  };
  const slash = file.path.lastIndexOf('/');
  return (
    <section ref={section} className="code-review-file" aria-label={`文件变更：${file.path}`}>
      <div className="code-work-file-heading code-review-file-header">
        <button
          type="button"
          className="code-review-file-toggle"
          title={file.path}
          aria-label={`查看修改文件：${file.path}`}
          aria-expanded={expanded}
          onClick={onToggle}
        >
          {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          <FileCode2 size={14} className="code-review-file-icon" aria-hidden="true" />
          <span className="code-review-file-path">
            <span>{file.path.slice(0, slash + 1)}</span>
            <strong title={file.path}>{file.path.slice(slash + 1)}</strong>
          </span>
          {file.kind === 'added' && <small>新增</small>}
        </button>
        {stats && <ReviewLineCounts {...stats} />}
        <CodeWorkMenu
          label={`文件操作：${file.path}`}
          items={[
            { label: '复制路径', onSelect: () => void copyPath() },
            ...(!runId
              ? [
                  {
                    label: '撤销此文件',
                    disabled,
                    onSelect: () => {
                      setConfirm({ path: file.path, version: diff.data?.version ?? file.version });
                    },
                  },
                ]
              : []),
          ]}
        />
      </div>
      {confirm && (
        <div className="code-revert-confirm" role="alert">
          <span>撤销副本中此文件的全部修改？</span>
          <Button disabled={disabled} onClick={() => revert.mutate(confirm)}>
            确认撤销
          </Button>
          <Button onClick={() => setConfirm(null)}>保留修改</Button>
        </div>
      )}
      <div className="code-review-file-content" hidden={!expanded}>
        {diff.data ? (
          <ReviewDiff compact view={view} diff={diff.data} onReview={onReview} />
        ) : (
          expanded && !diff.error && <p className="muted code-review-loading">正在读取差异…</p>
        )}
      </div>
      <ErrorText error={diff.error || revert.error || copyError} />
    </section>
  );
}
