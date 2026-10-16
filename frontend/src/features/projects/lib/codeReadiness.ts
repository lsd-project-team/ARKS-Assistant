import type {
  CodeChange,
  Verification,
  VerificationExecutor,
  VerificationProfile,
} from '../types/codeWork';

export function lines(value: string) {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function executorPayload(executor: VerificationExecutor) {
  const image = executor.image.trim();
  const context = executor.context.trim() || 'default';
  if (executor.kind === 'container' && !/^(?:[\w./:-]+@)?sha256:[a-f0-9]{64}$/.test(image))
    throw new Error('容器镜像须使用固定 SHA-256 digest，不能填写 latest 等标签');
  return { ...executor, image: executor.kind === 'container' ? image : '', context };
}

export function executionLabel(executor?: VerificationExecutor) {
  if (!executor) return '执行环境未提供';
  return executor.kind === 'trusted_host'
    ? `${executor.platform || '宿主平台未记录'} · 可信宿主（非沙箱）`
    : `${executor.platform} · ${executor.platform === 'windows' ? 'Hyper-V 容器配置' : '隔离容器'} · ${executor.context || 'default'}`;
}

export function requirementsPayload(criteria: string, constraints: string, paths: string) {
  const acceptance_criteria = lines(criteria);
  const allowed_paths = lines(paths).map((path) => path.replace(/\\/g, '/'));
  if (
    acceptance_criteria.length > 50 ||
    allowed_paths.length > 100 ||
    [...acceptance_criteria, ...allowed_paths].some((item) => item.length > 2000) ||
    constraints.length > 10000
  )
    throw new Error('验收标准最多50条、路径最多100条，单条最多2000字；约束最多10000字');
  if (
    allowed_paths.some(
      (path) =>
        path.startsWith('/') ||
        path.includes(':') ||
        path.split('/').some((part) => part === '..' || part === '.') ||
        path.includes('\0'),
    )
  )
    throw new Error('修改范围须为项目内相对路径或 glob，不能越界');
  return { acceptance_criteria, constraints: constraints.trim(), allowed_paths };
}

export function deliveryVersionCurrent(change: CodeChange) {
  return (
    !!change.change_version &&
    !!change.requirements_version &&
    change.review?.change_version === change.change_version &&
    change.review?.requirements_version === change.requirements_version
  );
}

export function reviewMissing(
  change: CodeChange,
  profile?: VerificationProfile,
  history: Verification[] = [],
) {
  const missing = [];
  if (!change.requirements_version) missing.push('缺少需求版本，请刷新后审核');
  if (!change.acceptance_criteria?.some((item) => item.trim()))
    missing.push('尚未填写明确验收标准');
  const result = change.latest_verification;
  if (
    change.status !== 'passed' ||
    result?.status !== 'passed' ||
    result.stale ||
    result.purpose === 'baseline' ||
    !change.change_version ||
    result.change_version !== change.change_version
  )
    missing.push('当前修改版本尚未通过验证');
  if (
    profile?.baseline_required &&
    !history.some(
      (item) =>
        item.purpose === 'baseline' &&
        item.profile_id === profile.id &&
        item.status === 'passed' &&
        !item.stale,
    )
  )
    missing.push('尚无同一配置的有效原版本基线');
  return missing;
}

export function bytesLabel(value: number) {
  return `${((Number.isFinite(value) ? value : 0) / 1024 / 1024).toFixed(1)} MB`;
}
