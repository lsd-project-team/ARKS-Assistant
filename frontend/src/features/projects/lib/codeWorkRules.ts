import type { ChangeFile, CodeChange, ReadingJob, ReadingDocument } from '../types/codeWork';

export const readingStatusLabels: Record<ReadingJob['status'], string> = {
  ready: '待开始',
  running: '阅读中',
  paused: '已暂停',
  interrupted: '已中断，可继续',
  completed: '本次阅读完成',
  partial: '部分完成，可继续',
  failed: '阅读失败，可重试',
};

export const changeStatusLabels: Record<CodeChange['status'], string> = {
  ready: '副本已准备',
  editing: '有未验证修改',
  verifying: '验证中',
  passed: '命令验证通过',
  failed: '验证失败',
  interrupted: '验证已中断',
  discarded: '已丢弃',
};

export function readingCanStart(job: ReadingJob) {
  return ['ready', 'paused', 'interrupted', 'partial', 'failed'].includes(job.status);
}

export function documentCanReview(document: ReadingDocument) {
  return !!document.summary?.trim() && !['stale', 'failed', 'pending'].includes(document.status);
}

export function changeCanEdit(change: CodeChange) {
  return !['discarded', 'verifying'].includes(change.status);
}

export function changeCanVerify(change: CodeChange, profileId: string, hasUnsavedChanges = false) {
  return changeCanEdit(change) && !!profileId && !hasUnsavedChanges;
}

export function changeCanRecordExperience(change: CodeChange, hasUnsavedChanges = false) {
  const verification = change.latest_verification;
  return (
    change.status === 'passed' &&
    verification?.status === 'passed' &&
    verification.purpose !== 'baseline' &&
    !verification.stale &&
    !!verification.change_version &&
    !hasUnsavedChanges
  );
}

export function normalizeChangePath(value: string) {
  const path = value.trim().replace(/\\/g, '/');
  if (
    !path ||
    path.startsWith('/') ||
    /^[a-z]:/i.test(path) ||
    path.includes('\0') ||
    path.split('/').some((part) => !part || part === '..' || part === '.')
  )
    throw new Error('请输入副本内的相对文件路径，例如 src/Program.cs');
  return path;
}

export function filePatchRequest(file: ChangeFile, after: string) {
  const newFile = file.exists === false && file.content === '' && file.version === '';
  if (!file.version && !newFile) throw new Error('缺少文件版本，请重新读取文件后保存');
  // 基线必须来自同一次读取；路径输入或轮询不能覆盖正在编辑的旧正文。
  return { path: file.path, before: file.content, after, version: file.version };
}

export function parseCommandArgv(value: string): string[] {
  let argv: unknown;
  try {
    argv = JSON.parse(value);
  } catch {
    throw new Error('命令参数须为 JSON 字符串数组，例如 ["python", "-m", "pytest"]');
  }
  if (
    !Array.isArray(argv) ||
    !argv.length ||
    argv.length > 100 ||
    argv.some(
      (argument) =>
        typeof argument !== 'string' ||
        !argument ||
        argument.includes('\0') ||
        argument.length > 20000,
    ) ||
    !argv[0].trim()
  )
    throw new Error('请填写非空的命令数组，每项为 1–20000 字符的字符串，最多 100 个参数');
  return argv;
}

export function codeWorkError(reason: unknown) {
  const message = reason instanceof Error ? reason.message : String(reason);
  if (
    reason &&
    typeof reason === 'object' &&
    'status' in reason &&
    reason.status === 409 &&
    /版本|基线|冲突|上下文/.test(message)
  )
    return new Error(
      `版本冲突：${message}。编辑内容已保留，请先查看最新差异，再重新读取需要修改的文件。`,
    );
  return reason instanceof Error ? reason : new Error(message);
}

export async function contentHash(content: string) {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(content));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
}
