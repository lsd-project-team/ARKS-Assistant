import { useQueryClient, type QueryClient } from '@tanstack/react-query';
import { api, query } from '../../../app/api/client';
import { useWorkspace } from '../../../app/state/store';
import { toast } from '../../../shared/utils/toasts';
import type { SourceFile } from '../../../shared/types/api';
import { sourceContextQuery } from './useSourceContext';
import { citationPath } from '../lib/citationPath';

export async function readCitationSource(
  cache: QueryClient,
  projectId: string,
  path: string,
  sourceId?: string,
) {
  const context = await cache.fetchQuery(sourceContextQuery(projectId));
  if (useWorkspace.getState().projectId !== projectId) throw new Error('当前项目已切换');
  const localPath = citationPath(context, path, sourceId);
  const detached = localPath === null;
  const target = localPath ?? path;
  const source = await cache.fetchQuery({
    queryKey: detached ? ['source', path, sourceId] : ['source', target],
    queryFn: () =>
      api<SourceFile>(
        detached ? `/sources/${sourceId}/file?path=${query(path)}` : `/file?path=${query(target)}`,
        undefined,
        projectId,
      ),
    staleTime: 0,
  });
  return { source, path: target, detached };
}

export function useSourceCitation() {
  const cache = useQueryClient();
  const projectId = useWorkspace((state) => state.projectId);
  return async (
    path: string,
    start = 1,
    end = start,
    expectedVersion?: string,
    sourceId?: string,
  ) => {
    try {
      const resolved = await readCitationSource(cache, projectId, path, sourceId);
      const source = resolved.source;
      if (resolved.detached) {
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
        return !invalid && (!expectedVersion || source.version === expectedVersion);
      }
      path = resolved.path;
      const openFile = (line?: number, endLine?: number) => {
        useWorkspace.getState().openFile(path, line, 'pinned', endLine);
        useWorkspace.getState().revealFile();
      };
      if (useWorkspace.getState().projectId !== projectId) return false;
      if (expectedVersion && source.version !== expectedVersion) {
        toast('文件已变化，打开当前版本，请重新定位原引用');
        openFile();
        return false;
      }
      if (start === 0 && end === 0 && source.line_count === 0) {
        openFile();
        return true;
      }
      if (start < 1 || end < start || end > source.line_count) {
        toast(
          `引用 L${start}–${end} 已失效，当前文件共 ${source.line_count} 行`,
          undefined,
          'error',
        );
        openFile();
        return false;
      }
      openFile(start, end);
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
