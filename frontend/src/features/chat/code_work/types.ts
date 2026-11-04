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
    steps: {
      name: string;
      status: string;
      exit_code: number | null;
      checks?: number;
      log: string;
    }[];
  } | null;
  scope?: string;
}
export interface WorkDiff {
  path: string;
  before: string;
  after: string;
  diff: string;
  version: string;
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
