import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, apiUrl } from '../../../app/api/client';
import { Button, ErrorText } from '../../../shared/ui/ui';
import type { WorkStatus } from './types';
import { VerificationReport } from './VerificationReport';

export function WorkHistory({
  status,
  base,
  projectId,
  onSelect,
}: {
  status: WorkStatus;
  base: string;
  projectId: string;
  onSelect: (runId: string) => void;
}) {
  const [jobId, setJobId] = useState('');
  const report = useQuery({
    queryKey: ['code-work', projectId, base, 'historical-report', jobId],
    queryFn: () =>
      api<NonNullable<WorkStatus['verification']>>(
        `${base}/report?job_id=${jobId}`,
        undefined,
        projectId,
      ),
    enabled: !!jobId,
  });
  return (
    <div className="code-work-history">
      <strong>修改记录</strong>
      {!status.history?.length && (
        <p className="muted">旧副本的累计差异仍可查看；新增修改开始保存逐轮快照。</p>
      )}
      {status.history?.map((item) => (
        <div key={item.id}>
          <div>
            <strong>副本版本 {item.revision}</strong>
            <time>{new Date(item.updated_at).toLocaleString('zh-CN')}</time>
            <small>
              {item.run_id
                ? `轮次 ${item.run_id.slice(0, 8)}`
                : item.action === 'revert'
                  ? '手动撤销'
                  : item.action === 'revert_hunk'
                    ? '撤销修改块'
                    : '手动修改'}{' '}
              · {item.files.length} 个文件
            </small>
          </div>
          {item.run_id && <Button onClick={() => onSelect(item.run_id)}>查看本轮快照</Button>}
        </div>
      ))}
      {!!status.verification_history?.length && (
        <>
          <strong>验证记录</strong>
          {report.data && (
            <VerificationReport
              job={report.data}
              current={status.verification?.id === jobId && !!status.verification_current}
              base={base}
              projectId={projectId}
            />
          )}
          <ErrorText error={report.error} />
          {[...status.verification_history].reverse().map((item) => (
            <div key={item.id}>
              <span>
                版本 {item.revision} ·{' '}
                {item.status === 'passed'
                  ? '通过'
                  : item.status === 'cancelled'
                    ? '已停止'
                    : item.status === 'failed'
                      ? '失败'
                      : item.status}
              </span>
              <time>{item.finished_at && new Date(item.finished_at).toLocaleString('zh-CN')}</time>
              <Button onClick={() => setJobId(item.id)}>查看验证详情</Button>
              <a
                href={apiUrl(`${base}/report?job_id=${item.id}`, projectId)}
                target="_blank"
                rel="noreferrer"
              >
                完整报告
              </a>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
