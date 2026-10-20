import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Copy, FileCode2, Info } from 'lucide-react';
import { api } from '../../../app/api/client';
import { useWorkspace } from '../../../app/state/store';
import type { RunContext, Selection } from '../../../shared/types/api';
import { toast } from '../../../shared/utils/toasts';
import { readCitationSource, useSourceCitation } from '../../source_reader/hooks/useSourceCitation';
import { SelectionPreview } from '../components/SelectionPreview';
import { resolveSourceEvidence } from './sourceEvidence';
import type { SourcePointer } from './types';

export function SourceReference({
  source,
  runId,
  sourceId,
}: {
  source: SourcePointer;
  runId?: string;
  sourceId?: string;
}) {
  const projectId = useWorkspace((state) => state.projectId);
  const cache = useQueryClient();
  const openCitation = useSourceCitation();
  const [preview, setPreview] = useState<Selection>();
  const [error, setError] = useState('');
  const [opening, setOpening] = useState(false);
  const context = useQuery({
    queryKey: ['source-evidence', projectId, runId],
    queryFn: () => api<RunContext>(`/runs/${runId}/context`, undefined, projectId),
    enabled: !!runId,
    staleTime: 15000,
    retry: false,
  });
  const resolved = resolveSourceEvidence(source, context.data?.source_evidence || [], sourceId);
  const evidence = resolved.evidence;
  const reason = !runId
    ? '这条引用没有关联可核对的运行记录'
    : context.isPending
      ? '正在核对源码证据…'
      : context.error
        ? '无法读取本轮引用依据，可重试核对'
        : resolved.reason;
  const label = `${source.path.split('/').at(-1)}:${source.start_line}${source.end_line && source.end_line !== source.start_line ? `–${source.end_line}` : ''}`;
  async function navigate(previewOnly: boolean) {
    if (reason || !evidence) return;
    setOpening(true);
    setError('');
    try {
      const origin = evidence.source_workspace_id || sourceId;
      const end = source.end_line || source.start_line;
      if (!previewOnly) {
        const opened = await openCitation(
          evidence.path,
          source.start_line,
          end,
          evidence.version,
          origin,
        );
        if (!opened) setError('未能定位原引用，请检查当前源码或重新核对版本。');
        return;
      }
      const result = await readCitationSource(cache, projectId, evidence.path, origin);
      if (useWorkspace.getState().projectId !== projectId) return;
      if (result.source.version !== evidence.version)
        throw new Error('源码已变化，不能将当前内容作为原引用预览');
      if (source.start_line < 1 || end > result.source.line_count)
        throw new Error('原引用行号已失效');
      const lines = result.source.content.split(/\r?\n/);
      setPreview({
        path: evidence.path,
        start_line: source.start_line,
        end_line: end,
        start_column: 1,
        end_column: (lines[end - 1]?.length || 0) + 1,
        version: evidence.version,
        source_workspace_id: origin,
        content: lines.slice(source.start_line - 1, end).join('\n'),
      });
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : '无法读取源码');
    } finally {
      setOpening(false);
    }
  }
  return (
    <div className="rich-source-reference">
      <div className="rich-source-controls">
        <button
          className="rich-source-link"
          type="button"
          disabled={!!reason || opening}
          title={reason || `${source.path} · 打开源码`}
          aria-label={`打开源码 ${label}`}
          onClick={() => void navigate(false)}
        >
          <FileCode2 size={12} aria-hidden="true" />
          {label}
          {reason && <small>未核实</small>}
        </button>
        <details className="rich-source-info">
          <summary aria-label={`查看引用详情 ${label}`} title="引用详情">
            <Info size={13} aria-hidden="true" />
            <span className="rich-sr-only">引用详情</span>
          </summary>
          <div className="rich-source-panel">
            <p className="rich-source-path">{source.path}</p>
            <p>
              行号 {source.start_line}–{source.end_line || source.start_line}
            </p>
            <p>
              原始引用：source:{encodeURIComponent(source.path)}#L{source.start_line}-L
              {source.end_line || source.start_line}
            </p>
            {evidence && (
              <p>
                来源：{evidence.source_workspace_id || sourceId || '当前源码目录'} · 版本{' '}
                {evidence.version}
              </p>
            )}
            {reason && <p role="status">{reason}</p>}
            <div className="rich-source-actions">
              <button
                type="button"
                disabled={!!reason || opening}
                onClick={() => void navigate(true)}
              >
                预览源码
              </button>
              <button
                type="button"
                onClick={() =>
                  void navigator.clipboard
                    .writeText(source.path)
                    .then(() => toast('源码路径已复制'))
                    .catch(() => setError('复制路径失败，请手动选择完整路径。'))
                }
              >
                <Copy size={12} aria-hidden="true" />
                复制路径
              </button>
              {runId && (
                <button
                  type="button"
                  disabled={context.isFetching}
                  onClick={() => void context.refetch()}
                >
                  重新核对
                </button>
              )}
            </div>
          </div>
        </details>
      </div>
      {error && (
        <p className="rich-source-error" role="alert">
          {error}
        </p>
      )}
      {preview && <SelectionPreview selection={preview} onClose={() => setPreview(undefined)} />}
    </div>
  );
}
