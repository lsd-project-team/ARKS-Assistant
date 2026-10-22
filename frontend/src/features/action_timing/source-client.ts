import { api } from '../../app/api/client';
import { actionTableCsv } from './presentation';
import type { SourceAction, SourceTimingReport } from './source-types';
export { knownDelay } from './format';

export function sourceTimingClient(scope: string) {
  const root = '/action-timing/source-analysis';
  return {
    report: (signal?: AbortSignal) => api<SourceTimingReport>(root, { signal }, scope),
    detail: (id: string, signal?: AbortSignal) =>
      api<SourceAction>(`${root}/${encodeURIComponent(id)}`, { signal }, scope),
    download: (rows: SourceAction[]) => {
      const url = URL.createObjectURL(
        new Blob([actionTableCsv(rows)], { type: 'text/csv;charset=utf-8' }),
      );
      const link = document.createElement('a');
      link.href = url;
      link.download = 'zx2200-action-timing.csv';
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
  };
}
