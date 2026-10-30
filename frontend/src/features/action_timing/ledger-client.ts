import { api, apiUrl } from '../../app/api/client';
import { sessionFetch } from '../auth/session';
import { requestJsonResponse } from '../../shared/api/http';
import type {
  ActionValues,
  DuplicateMode,
  ImportCounts,
  ImportPreview,
  ImportUnit,
  LedgerData,
  LedgerFilters,
  TimingAction,
  TimingCategory,
} from './ledger-types';

const root = '/action-timing/ledger';

export function ledgerClient(scope: string) {
  function endpoint(path: string) {
    return `${root}${path}${path.includes('?') ? '&' : '?'}timing_project=${encodeURIComponent(scope)}`;
  }
  function json<T>(path: string, method: string, body: unknown, signal?: AbortSignal) {
    return api<T>(endpoint(path), { method, body: JSON.stringify(body), signal });
  }
  return {
    list: (filters: LedgerFilters, offset: number, signal?: AbortSignal) =>
      api<LedgerData>(
        endpoint(`?${new URLSearchParams({ ...filters, offset: String(offset), limit: '20' })}`),
        { signal },
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
      api(endpoint(`/actions/${action.id}?version=${action.version}`), {
        method: 'DELETE',
        signal,
      }),
    preview: (file: File, mode: DuplicateMode, unit: ImportUnit, signal?: AbortSignal) =>
      api<ImportPreview>(
        endpoint(`/import-preview?${new URLSearchParams({ filename: file.name, mode, unit })}`),
        {
          method: 'POST',
          body: file,
          headers: { 'Content-Type': 'application/octet-stream' },
          signal,
        },
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
      templateUnit: 's' | 'ms' = 's',
    ) => {
      const params = new URLSearchParams({
        ...filters,
        format,
        template: String(template),
        template_unit: templateUnit,
      });
      const response = await requestJsonResponse(
        sessionFetch,
        apiUrl(endpoint(`/export?${params}`)),
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
