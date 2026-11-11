import { apiUrl } from '../../../app/api/client';
import type { WorkStatus } from './types';
import { verificationLabels } from './types';

export function VerificationReport({
  job,
  current,
  base,
  projectId,
  planId = '',
}: {
  job: NonNullable<WorkStatus['verification']>;
  current: boolean;
  base: string;
  projectId: string;
  planId?: string;
}) {
  const reportUrl = (name: string) =>
    apiUrl(
      `${base}/report?job_id=${encodeURIComponent(job.id)}&name=${encodeURIComponent(name)}${planId ? `&plan_id=${encodeURIComponent(planId)}` : ''}`,
      projectId,
    );
  return (
    <div className="code-verification" data-status={current ? job.status : 'stale'} role="status">
      <strong>{current ? verificationLabels[job.status] : '代码或测试已修改，需重新验证'}</strong>
      <span>
        验证版本 {job.revision}
        {job.attempt ? ` · 本轮第 ${job.attempt}/3 次` : ''}
      </span>
      {job.error && <p className="error-text">{job.error}</p>}
      {!job.requirements?.length && (
        <p className="muted">未配置需求断言；基础回归结果不代表本次需求已验证。</p>
      )}
      {job.steps.map((step, index) => (
        <details key={`${job.id}:${index}`}>
          <summary>
            {step.name} ·{' '}
            {step.status === 'passed'
              ? '通过'
              : step.status === 'failed'
                ? '未通过'
                : step.status === 'cancelled'
                  ? '已停止'
                  : '进行中'}
            {step.checks ? `（${step.checks} 项）` : ''}
          </summary>
          <pre>{step.log || '执行中，完成后显示日志。'}</pre>
        </details>
      ))}
      {!!job.requirements_results?.length && (
        <ul>
          {job.requirements_results.map((row) => (
            <li key={row.id}>
              {row.name} · {row.assertions} 项断言 · {row.status === 'passed' ? '通过' : '未通过'}
              {row.expectation && <small>{row.expectation}</small>}
            </li>
          ))}
        </ul>
      )}
      {!!job.desktop_results?.length && (
        <ul>
          {job.desktop_results.map((row) => (
            <li key={row.id}>
              {row.name} · {row.status === 'passed' ? '通过' : '未通过'}
              {row.screenshot && (
                <a href={reportUrl(row.screenshot)} target="_blank" rel="noreferrer">
                  查看步骤截图
                </a>
              )}
            </li>
          ))}
        </ul>
      )}
      {!!job.artifacts?.length && (
        <div className="code-work-artifacts">
          {job.artifacts
            .filter((item) => item.kind === 'image')
            .map((item) => (
              <a key={item.name} href={reportUrl(item.name)} target="_blank" rel="noreferrer">
                <img src={reportUrl(item.name)} alt={`仿真步骤截图 ${item.name}`} loading="lazy" />
              </a>
            ))}
        </div>
      )}
    </div>
  );
}
