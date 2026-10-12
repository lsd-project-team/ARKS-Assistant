import { useMemo } from 'react';
import { api } from '../lib/api';
import { useWorkspace } from '../lib/store';
import { boundProjectApi } from '../lib/projectRequest';

export function useProjectApi() {
  const id = useWorkspace((state) => state.projectId);
  return useMemo(() => boundProjectApi(id, api), [id]);
}
