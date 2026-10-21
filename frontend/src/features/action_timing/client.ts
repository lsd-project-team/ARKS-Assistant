import { api, apiUrl } from '../../app/api/client';
import { sessionFetch } from '../auth/session';
import type { TimingAction, TimingRun, TimingSummary, TimingEvent } from './types';

export function timingClient(scope: string) {
  const root = '/action-timing';
  return {
    catalog: (signal?: AbortSignal) =>
      api<{ actions: TimingAction[] }>(`${root}/catalog`, { signal }, scope),
    runs: (offset = 0, signal?: AbortSignal) =>
      api<{ items: TimingRun[]; total: number }>(
        `${root}/runs?limit=50&offset=${offset}`,
        { signal },
        scope,
      ),
    summary: (id: string, signal?: AbortSignal) =>
      api<TimingSummary>(`${root}/runs/${encodeURIComponent(id)}/summary`, { signal }, scope),
    events: (id: string, code: string, status: string, offset: number, signal?: AbortSignal) =>
      api<{ items: TimingEvent[]; total: number }>(
        `${root}/runs/${encodeURIComponent(id)}/events?${new URLSearchParams({ action_code: code, ...(status ? { status } : {}), offset: String(offset), limit: '25' })}`,
        { signal },
        scope,
      ),
    detail: (id: string, event: string, signal?: AbortSignal) =>
      api<{ action: TimingAction; event: TimingEvent; stages: TimingEvent[] }>(
        `${root}/runs/${encodeURIComponent(id)}/events/${encodeURIComponent(event)}`,
        { signal },
        scope,
      ),
    import: (file: File) =>
      api<{ run: TimingRun; duplicate: boolean; imported: number }>(
        `${root}/imports`,
        { method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: file },
        scope,
      ),
    download: async (id: string, format: 'json' | 'csv') => {
      const response = await sessionFetch(
        apiUrl(`${root}/runs/${encodeURIComponent(id)}/export?format=${format}`, scope),
      );
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || '导出失败，请重试');
      }
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `action-timing-${id}.${format}`;
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
  };
}
