import { verificationBusy, verificationLabels, type WorkStatus } from './types';
import { CircleCheck, CircleDashed, CirclePause, CircleX, LoaderCircle } from 'lucide-react';

export function VerificationSummary({
  status,
  onDetails,
  inline = false,
}: {
  status: WorkStatus;
  onDetails: () => void;
  inline?: boolean;
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
  const Icon = active
    ? LoaderCircle
    : stale || !job
      ? CircleDashed
      : job.status === 'passed'
        ? CircleCheck
        : job.status === 'failed'
          ? CircleX
          : CirclePause;
  return (
    <button
      type="button"
      className={`code-verification-summary${inline ? ' code-verification-inline' : ''}`}
      data-status={stale ? 'stale' : job?.status || 'none'}
      onClick={onDetails}
      title={`${label} · 查看验证详情与日志`}
      aria-label="查看验证详情"
    >
      {inline && <Icon size={15} aria-hidden="true" className={active ? 'spin' : undefined} />}
      <span role="status" className={inline ? 'code-review-sr-only' : undefined}>
        {label}
      </span>
      {!inline && <span>查看详情</span>}
    </button>
  );
}
