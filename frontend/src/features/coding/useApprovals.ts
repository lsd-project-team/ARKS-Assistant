import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api, jsonBody } from '../../app/api/client';
import { useWorkspace } from '../../app/state/store';
import type { CodingApproval } from '../../shared/types/api';

export const APPROVALS_KEY = 'coding-approvals';

export function useApprovals(pollMs = 3000) {
  const projectId = useWorkspace((state) => state.projectId);
  return useQuery({
    queryKey: [APPROVALS_KEY, projectId],
    queryFn: () => api<{ approvals: CodingApproval[] }>('/coding/approvals'),
    refetchInterval: pollMs,
    refetchOnWindowFocus: true,
    enabled: Boolean(projectId) && projectId !== 'independent',
  });
}

export function useDecideApproval() {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      approved,
      scope = 'once',
    }: {
      id: string;
      approved: boolean;
      scope?: 'once' | 'session';
    }) =>
      api<CodingApproval>(`/coding/approvals/${id}`, {
        method: 'POST',
        body: jsonBody({ approved, scope }),
      }),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: [APPROVALS_KEY] });
      void cache.invalidateQueries({ queryKey: ['coding-approvals-recent'] });
      void cache.invalidateQueries({ queryKey: ['coding-checkpoints'] });
    },
  });
}
