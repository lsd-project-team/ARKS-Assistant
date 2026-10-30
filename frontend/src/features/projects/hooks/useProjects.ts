import { useQuery } from '@tanstack/react-query';
import { api } from '../../../app/api/client';
import { useWorkspace } from '../../../app/state/store';
import type { Project, ProjectList } from '../../../shared/types/api';

export function useProjects(state = 'active') {
  return useQuery({
    queryKey: ['projects', state],
    queryFn: () => api<ProjectList>(`/projects?state=${state}`),
    refetchInterval: 10000,
  });
}
export function useCurrentProject() {
  const id = useWorkspace((state) => state.projectId);
  return useQuery({
    queryKey: ['project', id],
    queryFn: () => api<Project>(`/projects/${id}`),
    enabled: !!id && id !== 'independent',
  });
}
