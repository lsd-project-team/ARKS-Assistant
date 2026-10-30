import { useMemo } from 'react';
import { api } from '../../../app/api/client';
import { useWorkspace } from '../../../app/state/store';
import { boundProjectApi } from '../lib/projectRequest';

export function useProjectApi() {
  const id = useWorkspace((state) => state.projectId);
  return useMemo(() => boundProjectApi(id, api), [id]);
}
