import { api, apiUrl } from '../../app/api/client';
import { sessionFetch } from '../auth/session';
import type { SourceAction, SourceTimingReport } from './source-types';
export { knownDelay } from './format';

export function sourceTimingClient(scope: string) {
  const root = '/action-timing/source-analysis';
  return {
    report: (signal?: AbortSignal) => api<SourceTimingReport>(root, { signal }, scope),
    detail: (id: string, signal?: AbortSignal) =>
      api<SourceAction>(`${root}/${encodeURIComponent(id)}`, { signal }, scope),
    download: async () => {
      const response = await sessionFetch(apiUrl(`${root}/export`, scope));
      if (!response.ok) throw new Error('导出源码耗时分析失败');
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement('a');
      link.href = url;
      link.download = 'zx2200-source-action-timing.csv';
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
  };
}
