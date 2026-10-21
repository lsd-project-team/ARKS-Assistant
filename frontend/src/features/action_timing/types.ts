export type TimingStatus =
  'success' | 'failed' | 'aborted' | 'retry' | 'skipped' | 'noop' | 'incomplete';
export interface TimingAction {
  code: string;
  name: string;
  station: string;
  class_name: string;
  source_file: string;
}
export interface TimingRun {
  id: string;
  run_id: string;
  created_at: string;
  source_kind: 'zx2200' | 'collector_test';
  mode: string;
  source_revision: string;
  recipe_name: string;
  recipe_fingerprint: string;
  started_at: string;
  finished_at: string;
  state: string;
  dropped_events: number;
  event_count: number;
}
export interface Metrics {
  count: number;
  valid_count: number;
  statuses: Partial<Record<TimingStatus, number>>;
  mean_ms: number | null;
  min_ms: number | null;
  max_ms: number | null;
  p50_ms: number | null;
  p95_ms: number | null;
}
export interface TimingRow extends Metrics, TimingAction {
  branches: (Metrics & { branch: string })[];
  stages: (Metrics & { branch: string; stage: string; category: string })[];
}
export interface TimingSummary {
  run: TimingRun;
  data_complete: boolean;
  action_count: number;
  stage_count: number;
  covered_actions: number;
  statuses: Partial<Record<TimingStatus, number>>;
  active_union_ms: number;
  rows: TimingRow[];
}
export interface TimingEvent {
  event_id: string;
  action_code: string;
  logical_id: string;
  attempt: number;
  start_ms: number;
  end_ms: number | null;
  status: TimingStatus;
  raw_result: string;
  reason: string;
  context: Record<string, string>;
  branch: string;
  station: string;
  stage: string;
  category: string;
}
