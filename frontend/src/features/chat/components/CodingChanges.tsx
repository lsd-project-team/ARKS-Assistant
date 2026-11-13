import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ChevronUp, ExternalLink, FileDiff, FilePlus2, FileX2 } from 'lucide-react';
import { useState } from 'react';
import { useWorkspace } from '../../../app/state/store';
import { api } from '../../../app/api/client';
import type { RunContext } from '../../../shared/types/api';

const labels = { added: '新增', modified: '修改', deleted: '删除', renamed: '重命名' } as const;

function splitPatches(diff: string) {
  const patches: Record<string, string> = {};
  let path = '';
  let lines: string[] = [];
  const flush = () => {
    if (path) patches[path] = lines.join('\n');
  };
  for (const line of diff.split('\n')) {
    if (line.startsWith('diff --git ')) {
      flush();
      const match = /^diff --git a\/(.*) b\/(.*)$/.exec(line);
      path = match ? match[2] : '';
      lines = [line];
    } else if (path) {
      lines.push(line);
    }
  }
  flush();
  return patches;
}

export function CodingChanges({ runId, streaming = false }: { runId?: string; streaming?: boolean }) {
  const projectId = useWorkspace((state) => state.projectId);
  const [showAll, setShowAll] = useState(false);
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
  const additions = changes.files.reduce((total, file) => total + (file.additions ?? 0), 0);
  const deletions = changes.files.reduce((total, file) => total + (file.deletions ?? 0), 0);
  const patches = splitPatches(changes.diff || '');
  const visible = showAll ? changes.files : changes.files.slice(0, 4);
  return (
    <section className="answer-coding-changes" aria-label="本次修改">
      <div className="answer-coding-heading">
        <FileDiff size={15} />
        <strong>已编辑 {changes.files.length} 个文件</strong>
        <span className="answer-coding-lines">
          <span className="added">+{additions}</span>
          <span className="removed">-{deletions}</span>
        </span>
      </div>
      <ul className="answer-coding-files">
        {visible.map((file) => (
          <li key={file.path}>
            <button
              type="button"
              className="answer-coding-row"
              title={
                file.patch || patches[file.path]
                  ? '在右侧查看代码对比'
                  : `${file.path} 没有可显示的 diff`
              }
              disabled={!(file.patch || patches[file.path])}
              onClick={() =>
                useWorkspace.getState().openDiff({
                  path: file.path,
                  text: file.patch || patches[file.path] || '',
                  additions: file.additions,
                  deletions: file.deletions,
                })
              }
            >
              {file.status === 'added' ? (
                <FilePlus2 size={14} />
              ) : file.status === 'deleted' ? (
                <FileX2 size={14} />
              ) : (
                <FileDiff size={14} />
              )}
              <span className="answer-coding-path">{file.path}</span>
              <span className="answer-coding-status">{labels[file.status]}</span>
              {file.binary ? (
                <span className="muted">二进制</span>
              ) : (
                <span className="answer-coding-lines">
                  <span className="added">+{file.additions ?? 0}</span>
                  <span className="removed">-{file.deletions ?? 0}</span>
                </span>
              )}
            </button>
            <button
              type="button"
              className="answer-coding-open"
              title={`打开 ${file.path}`}
              aria-label={`打开 ${file.path}`}
              onClick={() => useWorkspace.getState().openFile(file.path, 1, 'pinned')}
            >
              <ExternalLink size={13} />
            </button>
          </li>
        ))}
      </ul>
      {changes.files.length > 4 && (
        <button type="button" className="answer-coding-more" onClick={() => setShowAll(!showAll)}>
          {showAll ? (
            <>
              收起 <ChevronUp size={13} />
            </>
          ) : (
            <>
              全部 {changes.files.length} 个文件 <ChevronDown size={13} />
            </>
          )}
        </button>
      )}
      {changes.truncated && <p className="muted">部分文件 diff 过长，已截断。</p>}
    </section>
  );
}
