export interface WorkStatus {
  exists: boolean;
  configured: boolean;
  root: string;
  revision?: number;
  files?: {
    path: string;
    kind: 'modified' | 'added';
    version: string;
    additions: number;
    deletions: number;
  }[];
  file_count?: number;
  additions?: number;
  deletions?: number;
  approvals?: WorkApproval[];
  commands?: WorkCommand[];
}

export interface WorkApproval {
  id: string;
  command: string;
  argv: string[];
  cwd: string;
  status: string;
  created_at: string;
}

export interface WorkCommand {
  id: string;
  argv: string[];
  cwd: string;
  status: string;
  exit_code: number | null;
  output?: string;
  started_at?: string;
  finished_at?: string;
}

export interface WorkDiff {
  path: string;
  before: string;
  after: string;
  diff: string;
  version: string;
  additions: number;
  deletions: number;
  historical?: boolean;
}

export interface WorkSettings {
  root: string;
  auto_approve: boolean;
  approval_timeout_seconds: number;
  command_timeout_seconds: number;
  commands: string[][];
  version: string;
  windows: boolean;
}

export const commandLabels: Record<string, string> = {
  pending: '等待批准',
  passed: '成功',
  failed: '失败',
  timeout: '超时',
  denied: '已拒绝',
};
