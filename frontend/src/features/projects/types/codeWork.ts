export interface VerificationProfile {
  id: string;
  name: string;
  argv: string[];
  timeout_seconds?: number;
  executor?: VerificationExecutor;
  baseline_required?: boolean;
  category?: 'build' | 'test' | 'analysis' | 'offline';
  environment_label?: string;
}

export interface VerificationExecutor {
  kind: 'container' | 'trusted_host';
  platform: 'linux' | 'windows';
  image: string;
  context: string;
}

export interface Verification {
  id: string;
  status: 'running' | 'passed' | 'failed' | 'timed_out' | 'cancelled' | 'interrupted';
  profile_id: string;
  argv: string[];
  exit_code: number | null;
  output: string;
  truncated: boolean;
  started_at: string;
  ended_at?: string | null;
  change_version?: string;
  stale?: boolean;
  purpose?: 'baseline' | 'change';
  executor?: VerificationExecutor;
  error?: string;
}

export interface CodeChange {
  id: string;
  title: string;
  goal: string;
  status: 'ready' | 'editing' | 'verifying' | 'passed' | 'failed' | 'interrupted' | 'discarded';
  created_at: string;
  updated_at: string;
  files_changed: number;
  latest_verification: Verification | null;
  error?: string | null;
  change_version?: string;
  acceptance_criteria?: string[];
  requirements_version?: string;
  constraints?: string;
  allowed_paths?: string[];
  review?: {
    change_version: string;
    requirements_version: string;
    actor: string;
    notes: string;
    reviewed_at: string;
  } | null;
}

export interface CodeWorkPolicy {
  windows_scratch_mb: number;
  max_storage_mb: number;
  min_free_mb: number;
  max_log_mb: number;
  max_active_verifications: number;
  retention_days: number;
  reading_token_limit: number | null;
  require_sandbox_delivery: boolean;
}

export interface ReadinessReport {
  project: {
    status: 'needs_baseline' | 'blocked' | 'no_build_files';
    buildable: null;
    primary_only: boolean;
    projects: Array<{ path: string; target_frameworks: string[]; platforms: string[] }>;
    attached_sources?: Array<{ source_id: string; label: string; status: string }>;
    requirements: string[];
    issues: Array<{ code: string; severity: string; path: string; message: string }>;
    baseline_steps: string[];
  };
  policy: CodeWorkPolicy;
  usage: {
    storage_bytes: number;
    logs_bytes: number;
    changes: number;
    active_verifications: number;
    reading_reserved_tokens: number;
    reading_token_limit: number | null;
  };
  unresolved: string[];
}

export interface ChangeFile {
  path: string;
  content: string;
  version: string;
  requirements_version?: string;
  exists?: boolean;
}

export interface ChangeDiff {
  diff: string;
  files: Array<{
    path: string;
    status: string;
    base_version: string | null;
    current_version: string | null;
  }>;
  conflicts: string[];
  source_unchanged: boolean;
}
