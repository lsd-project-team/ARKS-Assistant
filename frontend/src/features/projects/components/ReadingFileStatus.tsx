import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ErrorText } from '../../../shared/ui/ui';
import { useProjectApi } from '../hooks/useProjectApi';

interface ReadingFile {
  id: string;
  path: string;
  status: string;
  read: boolean;
  analyzed: boolean;
  reviewed: boolean;
  stale: boolean;
  error: string;
}

const labels: Record<string, string> = {
  pending: '待处理',
  reading: '读取中',
  analyzed: '已分析',
  failed: '失败',
  excluded: '已排除',
};

export function ReadingFileStatus({
  projectId,
  jobId,
  version,
}: {
  projectId: string;
  jobId: string;
  version: string;
}) {
  const [open, setOpen] = useState(false);
  const api = useProjectApi();
  const files = useQuery({
    queryKey: ['project-reading', projectId, jobId, 'files', version],
    queryFn: ({ signal }) =>
      api<{ files: ReadingFile[] }>(`/project-reading/${encodeURIComponent(jobId)}/files`, {
        signal,
      }),
    enabled: open,
  });
  return (
    <details
      className="code-work-config"
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary>查看文件状态、失败与排除原因</summary>
      {open && (
        <>
          <ErrorText error={files.error} />
          {files.isPending ? (
            <p className="muted">正在读取文件状态…</p>
          ) : (
            <div className="code-work-file-status">
              <table className="code-work-table">
                <thead>
                  <tr>
                    <th>文件</th>
                    <th>状态</th>
                    <th>处理情况</th>
                    <th>原因</th>
                  </tr>
                </thead>
                <tbody>
                  {files.data?.files.map((file) => (
                    <tr key={file.id}>
                      <th scope="row">{file.path}</th>
                      <td>{file.stale ? '已过期' : labels[file.status] || file.status}</td>
                      <td>
                        {file.read ? '已读' : '未读'} / {file.analyzed ? '已分析' : '未分析'} /{' '}
                        {file.reviewed ? '已评审' : '未评审'}
                      </td>
                      <td>{file.error || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </details>
  );
}
