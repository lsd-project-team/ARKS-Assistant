export type DurationStatus = 'all' | 'filled' | 'missing';
export type TimingProject = { id: string; name: string; version: number };
export type TimingProjectList = { projects: TimingProject[]; default_project_id: string };
export type ActionSort = 'name' | 'duration_asc' | 'duration_desc';
export type ImportUnit = 'auto' | 's' | 'ms';
export type DuplicateMode = 'skip' | 'update';
export type LedgerFilters = {
  category_id: string;
  search: string;
  duration_status: DurationStatus;
  sort: ActionSort;
};
export type TimingCategory = { id: string; name: string; version: number; count: number };
export type TimingAction = {
  id: string;
  name: string;
  category_id: string | null;
  category: string;
  duration_seconds: number | null;
  notes: string;
  version: number;
  created_at: string;
  updated_at: string;
};
export type ActionValues = Pick<
  TimingAction,
  'name' | 'category_id' | 'duration_seconds' | 'notes'
>;
export type LedgerData = {
  items: TimingAction[];
  total: number;
  action_count: number;
  uncategorized_count: number;
  categories: TimingCategory[];
  revision: string;
  writable: boolean;
};
export type ImportRow = {
  row_number: number;
  category: string;
  name: string;
  duration_seconds: number | null;
  notes: string;
};
export type ImportCounts = { add: number; update: number; skip: number };
export type ImportPreview = {
  rows: (ImportRow & {
    operation: 'add' | 'update' | 'skip';
    effective_duration_seconds: number | null;
  })[];
  counts: ImportCounts;
  errors: { row_number: number; message: string }[];
  revision: string;
};
