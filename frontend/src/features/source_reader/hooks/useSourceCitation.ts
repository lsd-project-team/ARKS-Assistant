import { useQueryClient } from '@tanstack/react-query';
import { api, query } from '../../../app/api/client';
import { useWorkspace } from '../../../app/state/store';
import { toast } from '../../../shared/utils/toasts';
import type { SourceFile } from '../../../shared/types/api';
import { useCurrentProject } from '../../projects/hooks/useProjects';

export function useSourceCitation() {
  const cache = useQueryClient();
  const project = useCurrentProject();
  const projectId = useWorkspace((state) => state.projectId);
  return async (
    path: string,
    start = 1,
    end = start,
    expectedVersion?: string,
    sourceId?: string,
  ) => {
    try {
      const attachedSource = project.data?.source_folders?.find(
        (folder) => folder.source_id === sourceId,
      );
      if (sourceId && sourceId !== project.data?.source_workspace_id && !attachedSource) {
        const source = await api<SourceFile>(`/sources/${sourceId}/file?path=${query(path)}`);
        if (useWorkspace.getState().projectId !== projectId) return false;
        if (expectedVersion && source.version !== expectedVersion)
          toast('原始目录中的文件已变化，显示当前版本供核对');
        const invalid = start < 1 || end < start || end > source.line_count;
        if (invalid) toast(`原引用 L${start}–${end} 已失效，显示原始文件当前版本供核对`);
        useWorkspace.setState({
          historicalSource: {
            source,
            start: invalid ? 1 : start,
            end: invalid ? Math.min(20, source.line_count) : end,
          },
        });
        return true;
      }
      const source = await cache.fetchQuery({
        queryKey: ['source', path],
        queryFn: () => api<SourceFile>(`/file?path=${query(path)}`, undefined, projectId),
        staleTime: 0,
      });
      if (useWorkspace.getState().projectId !== projectId) return false;
      if (expectedVersion && source.version !== expectedVersion) {
        toast('文件已变化，打开当前版本，请重新定位原引用');
        useWorkspace.getState().openFile(path);
        return false;
      }
      if (start === 0 && end === 0 && source.line_count === 0) {
        useWorkspace.getState().openFile(path);
        return true;
      }
      if (start < 1 || end < start || end > source.line_count) {
        toast(
          `引用 L${start}–${end} 已失效，当前文件共 ${source.line_count} 行`,
          undefined,
          'error',
        );
        useWorkspace.getState().openFile(path);
        return false;
      }
      useWorkspace.getState().openFile(path, start, 'pinned', end);
      return true;
    } catch (error) {
      toast(
        `无法打开 ${path}：${error instanceof Error ? error.message : '文件不可用'}`,
        undefined,
        'error',
      );
      return false;
    }
  };
}
