export type VerificationStatus =
  'queued' | 'building' | 'testing' | 'passed' | 'failed' | 'cancelled' | 'interrupted';
export interface WorkStatus {
  exists: boolean;
  configured: boolean;
  prepared?: boolean;
  revision?: number;
  source_version?: string;
  files?: { path: string; kind: 'modified' | 'added'; version: string }[];
  verification_current?: boolean;
  verification?: {
    id: string;
    revision: number;
    status: VerificationStatus;
    error: string;
    scope?: string;
    attempt?: number;
    run_id?: string;
    requirements?: WorkRequirement[];
    requirements_results?: WorkCheckResult[];
    desktop_results?: WorkCheckResult[];
    artifacts?: { name: string; kind: 'image' | 'report'; version: string }[];
    steps: {
      name: string;
      status: string;
      exit_code: number | null;
      checks?: number;
      log: string;
    }[];
  } | null;
  scope?: string;
  source_path?: string;
  source_pinned?: boolean;
  workspace_path?: string;
  requirements?: WorkRequirement[];
  desktop_flow?: boolean;
  merge_plan_id?: string;
  merge_paths?: string[];
  recovery?: {
    id: string;
    target: string;
    files: { path: string; version: string; before: string; after: string }[];
  }[];
  history?: WorkHistory[];
  verification_history?: {
    id: string;
    run_id?: string;
    revision: number;
    status: VerificationStatus;
    finished_at: string;
  }[];
  applied?: {
    id: string;
    status: 'applied' | 'rolled_back';
    target: string;
    files: string[];
    created_at: string;
    actor?: { name?: string };
    rolled_back_at?: string;
  }[];
}
export interface WorkDiff {
  path: string;
  before: string;
  after: string;
  diff: string;
  version: string;
  historical?: boolean;
  run_id?: string;
  hunks?: WorkHunk[];
}
export interface WorkHunk {
  id: string;
  old_start: number;
  old_lines: number;
  new_start: number;
  new_lines: number;
  before: string;
  after: string;
}
export interface WorkCheckResult {
  id: string;
  name?: string;
  expectation?: string;
  assertions: number;
  status: string;
  error?: string;
  screenshot?: string;
}
export interface WorkRequirement {
  id: string;
  version: string;
  name: string;
  expectation: string;
  code: string;
  enabled: boolean;
}
export interface WorkHistory {
  id: string;
  run_id: string;
  revision: number;
  started_at: string;
  updated_at: string;
  files: string[];
  action: string;
}
export interface MergeRow {
  path: string;
  kind: string;
  status: 'ready' | 'resolved' | 'conflict';
  additions: number;
  deletions: number;
}
export interface MergePlan {
  id: string;
  revision: number;
  target: string;
  files: MergeRow[];
  conflicts: string[];
  rebase_conflicts: string[];
  source_changed: boolean;
  status: string;
  can_apply: boolean;
  verification?: WorkStatus['verification'];
  resolutions?: Record<string, { choice: 'source' | 'workspace' | 'manual'; content: string }>;
}
export interface MergeDiff extends WorkDiff {
  base: string;
  source: string;
  workspace: string;
  status: string;
}
export interface WorkSummary {
  exists: boolean;
  revision: number;
  additions: number;
  deletions: number;
  files: {
    path: string;
    kind: 'modified' | 'added';
    version: string;
    additions: number;
    deletions: number;
  }[];
}
export interface WorkEnvironment {
  source_root: string;
  msbuild: string;
  timeout_seconds: number;
  version: string;
  windows: boolean;
}
export const verificationLabels: Record<VerificationStatus, string> = {
  queued: '等待验证',
  building: '正在编译',
  testing: '正在仿真',
  passed: '验证通过',
  failed: '验证失败',
  cancelled: '验证已停止',
  interrupted: '验证未完成',
};
export const verificationBusy = (value?: WorkStatus['verification']) =>
  !!value && ['queued', 'building', 'testing'].includes(value.status);
