import { verificationBusy, verificationLabels, type WorkStatus } from './types';

export function VerificationSummary({
  status,
  onDetails,
}: {
  status: WorkStatus;
  onDetails: () => void;
}) {
  const job = status.verification;
  const active = verificationBusy(job);
  const stale = !!job && !active && !status.verification_current;
  const label = !job
    ? '尚未验证'
    : stale
      ? job.status === 'passed'
        ? '需重新验证'
        : `需重新验证（上次${verificationLabels[job.status].replace('验证', '')}）`
      : job.status === 'passed' && !job.requirements?.length
        ? '基础回归通过'
        : verificationLabels[job.status];
  return (
    <button
      type="button"
      className="code-verification-summary"
      data-status={stale ? 'stale' : job?.status || 'none'}
      onClick={onDetails}
      title="查看验证详情与日志"
      aria-label="查看验证详情"
    >
      <span role="status">{label}</span>
      <span>查看详情</span>
    </button>
  );
}
