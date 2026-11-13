import { useQuery } from '@tanstack/react-query';
import { FileDiff, FilePlus2, FileX2 } from 'lucide-react';
import { useWorkspace } from '../../../app/state/store';
import { api } from '../../../app/api/client';
import type { RunContext } from '../../../shared/types/api';

const labels = { added: '新增', modified: '修改', deleted: '删除', renamed: '重命名' } as const;

export function CodingChanges({ runId, streaming = false }: { runId?: string; streaming?: boolean }) {
  const projectId = useWorkspace((state) => state.projectId);
  const context = useQuery({
    queryKey: ['coding-changes', projectId, runId],
    queryFn: () => api<RunContext>(`/runs/${runId}/context`, undefined, projectId),
    enabled: !!runId,
    staleTime: 300000,
    retry: false,
    refetchInterval: streaming ? 4000 : false,
  });
  const changes = context.data?.coding_changes;
  if (!runId || !changes?.files.length) return null;
  return (
    <section className="answer-coding-changes" aria-label="本次修改">
      <div className="answer-coding-heading">
        <FileDiff size={14} />
        <strong>本次修改</strong>
        <span className="muted">{changes.files.length} 个文件</span>
      </div>
      <ul className="answer-coding-files">
        {changes.files.map((file) => (
          <li key={file.path}>
            <button
              type="button"
              className="answer-coding-path"
              title={`打开 ${file.path}`}
              onClick={() => useWorkspace.getState().openFile(file.path, 1, 'pinned')}
            >
              {file.status === 'added' ? (
                <FilePlus2 size={13} />
              ) : file.status === 'deleted' ? (
                <FileX2 size={13} />
              ) : (
                <FileDiff size={13} />
              )}
              <span>{file.path}</span>
            </button>
            <span className="answer-coding-status">{labels[file.status]}</span>
            {file.binary ? (
              <span className="muted">二进制</span>
            ) : (
              <span className="answer-coding-lines">
                <span className="added">+{file.additions ?? 0}</span>
                <span className="removed">-{file.deletions ?? 0}</span>
              </span>
            )}
          </li>
        ))}
      </ul>
      {!!changes.diff && (
        <details className="answer-coding-diff">
          <summary>查看代码对比</summary>
          <pre>{changes.diff}</pre>
          {changes.truncated && <p className="muted">diff 过长，仅显示部分。</p>}
        </details>
      )}
    </section>
  );
}
