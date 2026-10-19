import { useQuery } from '@tanstack/react-query';
import { api } from '../../../app/api/client';
import { useWorkspace } from '../../../app/state/store';
import type { SourceContext } from '../../../shared/types/api';

export function sourceContextQuery(scopeId: string) {
  return {
    // 沿用 project 缓存前缀，修改目录后与项目资料一起失效；独立对话也有真实源码身份。
    queryKey: ['project', scopeId, 'source-context'],
    queryFn: () => api<SourceContext>(`/projects/${encodeURIComponent(scopeId)}/source-context`),
    staleTime: 15000,
  };
}

export function useSourceContext() {
  const scopeId = useWorkspace((state) => state.projectId);
  return useQuery({ ...sourceContextQuery(scopeId), enabled: !!scopeId });
}
