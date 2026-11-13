import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ChevronDown, ChevronUp, Code2, Undo2 } from 'lucide-react';
import { useState } from 'react';
import { useWorkspace } from '../../../app/state/store';
import { api } from '../../../app/api/client';
import type { CodingChanges as CodingChangesPayload, CodingChangeFile } from '../../../shared/types/api';
import { toast } from '../../../shared/utils/toasts';

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

export function CodingChanges({
  runId,
  streaming = false,
}: {
  runId?: string;
  streaming?: boolean;
}) {
  const projectId = useWorkspace((state) => state.projectId);
  const [showAll, setShowAll] = useState(false);
  const cache = useQueryClient();
  const [undone, setUndone] = useState(false);
  const context = useQuery({
    queryKey: ['coding-changes', projectId, runId],
    queryFn: () =>
      api<{ coding_changes: CodingChangesPayload | null }>(
        `/runs/${runId}/coding`,
        undefined,
        projectId,
      ),
    enabled: !!runId,
    staleTime: 300000,
    retry: false,
    refetchInterval: streaming ? 4000 : false,
  });
  const undo = useMutation({
    mutationFn: () =>
      api('/coding/restore-run', { method: 'POST', body: JSON.stringify({ run_id: runId }) }),
    onSuccess: () => {
      setUndone(true);
      void cache.invalidateQueries({ queryKey: ['coding-changes'] });
      void cache.invalidateQueries({ queryKey: ['coding-checkpoints'] });
      toast('已撤销本轮修改');
    },
    onError: (error: Error) => toast(error.message, undefined, 'error'),
  });
  const changes = context.data?.coding_changes;
  if (!runId || undone || !changes?.files.length) return null;
  const patches = splitPatches(changes.diff || '');
  const visible = showAll ? changes.files : changes.files.slice(0, 4);
  return (
    <section className="answer-coding-changes" aria-label="本次修改">
      <div className="answer-coding-heading">
        <span className="answer-coding-icon" aria-hidden="true">
          <Code2 size={20} strokeWidth={2} />
        </span>
        <div className="answer-coding-heading-text">
          <strong>已编辑 {changes.files.length} 个文件</strong>
          <span>在侧边栏预览</span>
        </div>
        {!streaming && (
          <button
            type="button"
            className="answer-coding-undo"
            title="撤销本轮修改；本轮之后已有新修改时不可用"
            disabled={undo.isPending}
            onClick={() => {
              if (window.confirm('撤销本轮修改？只回滚本轮涉及的文件，已生成的内容保留。'))
                undo.mutate();
            }}
          >
            <Undo2 size={14} />
            撤销本轮
          </button>
        )}
      </div>
      <ul className="answer-coding-files">
        {visible.map((file: CodingChangeFile) => {
          const patch = file.patch || patches[file.path] || '';
          return (
            <li key={file.path}>
              <button
                type="button"
                className="answer-coding-row"
                title={
                  patch ? `在右侧查看 ${file.path} 的代码对比` : `${file.path} 没有可显示的 diff`
                }
                disabled={!patch}
                onClick={() =>
                  useWorkspace.getState().openDiff({
                    path: file.path,
                    text: patch,
                    additions: file.additions,
                    deletions: file.deletions,
                  })
                }
              >
                <span className="answer-coding-path">{file.path}</span>
                {file.binary ? (
                  <span className="answer-coding-binary">二进制</span>
                ) : (
                  <span className="answer-coding-lines">
                    <span className="added">+{file.additions ?? 0}</span>
                    <span className="removed">-{file.deletions ?? 0}</span>
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
      {changes.files.length > 4 && (
        <button type="button" className="answer-coding-more" onClick={() => setShowAll(!showAll)}>
          {showAll ? (
            <>
              收起 <ChevronUp size={14} />
            </>
          ) : (
            <>
              全部 {changes.files.length} 个文件 <ChevronDown size={14} />
            </>
          )}
        </button>
      )}
      {changes.truncated && <p className="answer-coding-note">部分文件 diff 过长，已截断。</p>}
    </section>
  );
}
