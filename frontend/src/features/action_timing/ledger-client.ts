import { api, apiUrl } from '../../app/api/client';
import { sessionFetch } from '../auth/session';
import { requestJsonResponse } from '../../shared/api/http';
import type {
  ActionValues,
  DuplicateMode,
  ImportCounts,
  ImportPreview,
  LedgerData,
  LedgerFilters,
  TimingAction,
  TimingCategory,
} from './ledger-types';

const root = '/action-timing/ledger';

export function ledgerClient(scope: string) {
  function json<T>(path: string, method: string, body: unknown, signal?: AbortSignal) {
    return api<T>(`${root}${path}`, { method, body: JSON.stringify(body), signal }, scope);
  }
  return {
    list: (filters: LedgerFilters, offset: number, signal?: AbortSignal) =>
      api<LedgerData>(
        `${root}?${new URLSearchParams({ ...filters, offset: String(offset), limit: '20' })}`,
        { signal },
        scope,
      ),
    saveCategory: (name: string, category?: TimingCategory | null, signal?: AbortSignal) =>
      json<TimingCategory>(
        category ? `/categories/${category.id}` : '/categories',
        category ? 'PATCH' : 'POST',
        { name, ...(category ? { version: category.version } : {}) },
        signal,
      ),
    deleteCategory: (category: TimingCategory, target: string, signal?: AbortSignal) =>
      json(
        `/categories/${category.id}`,
        'DELETE',
        { version: category.version, target_id: target || null },
        signal,
      ),
    saveAction: (values: ActionValues, action?: TimingAction | null, signal?: AbortSignal) =>
      json<TimingAction>(
        action ? `/actions/${action.id}` : '/actions',
        action ? 'PATCH' : 'POST',
        { ...values, ...(action ? { version: action.version } : {}) },
        signal,
      ),
    deleteAction: (action: TimingAction, signal?: AbortSignal) =>
      api(
        `${root}/actions/${action.id}?version=${action.version}`,
        { method: 'DELETE', signal },
        scope,
      ),
    preview: (file: File, mode: DuplicateMode, signal?: AbortSignal) =>
      api<ImportPreview>(
        `${root}/import-preview?${new URLSearchParams({ filename: file.name, mode })}`,
        {
          method: 'POST',
          body: file,
          headers: { 'Content-Type': 'application/octet-stream' },
          signal,
        },
        scope,
      ),
    commit: (preview: ImportPreview, mode: DuplicateMode, signal?: AbortSignal) =>
      json<{ counts: ImportCounts }>(
        '/imports',
        'POST',
        {
          mode,
          revision: preview.revision,
          rows: preview.rows.map(({ row_number, category, name, duration_seconds, notes }) => ({
            row_number,
            category,
            name,
            duration_seconds,
            notes,
          })),
        },
        signal,
      ),
    download: async (
      format: 'csv' | 'xlsx',
      filters?: LedgerFilters,
      template = false,
      signal?: AbortSignal,
    ) => {
      const params = new URLSearchParams({ ...filters, format, template: String(template) });
      const response = await requestJsonResponse(
        sessionFetch,
        apiUrl(`${root}/export?${params}`, scope),
        { signal },
      );
      const blob = await response.blob();
      if (signal?.aborted) return;
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `动作耗时${template ? '-导入模板' : ''}.${format}`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
  };
}
