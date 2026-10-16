import { useEffect } from 'react';
import { QueryClientProvider, useQuery } from '@tanstack/react-query';
import { api } from '../../../app/api/client';
import { useWorkspace } from '../../../app/state/store';
import type { ProjectList, Project } from '../../../shared/types/api';
import { Button, ErrorText } from '../../../shared/ui/ui';
import App from '../../../app/App';
import { projectCache } from '../lib/projectCache';

export function ProjectShell() {
  const projectId = useWorkspace((state) => state.projectId);
  const list = useQuery({
    queryKey: ['projects', 'bootstrap'],
    queryFn: () => api<ProjectList>('/projects'),
    refetchInterval: 10000,
  });
  useEffect(() => {
    if (!list.data) return;
    // 首次进入保持独立；已有选择由持久化状态恢复，空草稿也不能自动归入项目。
    useWorkspace.getState().initializeProject('independent');
    const selected = useWorkspace.getState().projectId;
    if (selected === 'independent') return;
    void api<Project>(`/projects/${selected}`)
      .then((project) => {
        if (useWorkspace.getState().projectId !== selected) return;
        const binding = JSON.stringify([project.source_root, project.source_folders]);
        const previous = useWorkspace.getState().sourceBindings[selected];
        // 其他窗口改过目录后，也不能继续沿用旧目录的标签、行号和展开状态。
        if (previous && previous !== binding) {
          useWorkspace.getState().resetProjectSource(selected);
          for (const key of ['source', 'files', 'symbols'])
            projectCache(selected).removeQueries({ queryKey: [key] });
        }
        if (previous !== binding)
          useWorkspace.setState((state) => ({
            sourceBindings: { ...state.sourceBindings, [selected]: binding },
          }));
      })
      .catch((error) => {
        if (error.status === 404 && useWorkspace.getState().projectId === selected)
          useWorkspace.getState().switchProject('independent');
      });
  }, [list.data, projectId]);
  if (!projectId || !list.data)
    return (
      <div className="project-loading" role="status">
        {list.isError ? (
          <>
            <ErrorText error={list.error} />
            <Button onClick={() => void list.refetch()}>重新连接</Button>
          </>
        ) : (
          '正在读取项目…'
        )}
      </div>
    );
  // 每个项目使用独立查询缓存；旧请求返回时不会覆盖当前项目的源码或会话。
  return (
    <QueryClientProvider client={projectCache(projectId)}>
      <App key={projectId} />
    </QueryClientProvider>
  );
}
