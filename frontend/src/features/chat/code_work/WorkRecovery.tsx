import { useEffect, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { api, jsonBody } from '../../../app/api/client';
import { Button, ErrorText } from '../../../shared/ui/ui';
import type { WorkDiff, WorkStatus } from './types';
import { ReviewDiff } from './ReviewDiff';

export function WorkRecovery({
  items,
  base,
  projectId,
  admin,
  busy,
  onChanged,
}: {
  items: NonNullable<WorkStatus['recovery']>;
  base: string;
  projectId: string;
  admin: boolean;
  busy: boolean;
  onChanged: () => void;
}) {
  const item = items[0];
  const [selected, setSelected] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const versions = JSON.stringify(item?.files);
  useEffect(() => {
    setConfirmed(false);
  }, [versions]);
  const file = item?.files.find((file) => file.path === selected) || item?.files[0];
  const diff = useQuery({
    queryKey: ['code-work', projectId, base, 'recovery', item?.id, file?.path, file?.version],
    queryFn: () =>
      api<WorkDiff>(
        `${base}/recovery/${item.id}/diff?path=${encodeURIComponent(file!.path)}`,
        undefined,
        projectId,
      ),
    enabled: !!file,
  });
  const resolve = useMutation({
    mutationFn: () =>
      api(
        `${base}/recovery/${item.id}/resolve`,
        {
          method: 'POST',
          body: jsonBody({
            confirm_target: item.target,
            versions: Object.fromEntries(item.files.map((file) => [file.path, file.version])),
          }),
        },
        projectId,
      ),
    onSuccess: onChanged,
  });
  if (!item) return null;
  return (
    <section className="code-work-recovery" role="region" aria-label="合并恢复冲突">
      <strong>写回中断：发现后续人工修改</strong>
      <p>其余文件和工程副本已恢复。以下原文件保留当前内容，请核对差异后重新生成合并预览。</p>
      <code>{item.target}</code>
      <div className="code-review-toolbar">
        {item.files.map((file) => (
          <Button
            key={file.path}
            onClick={() => setSelected(file.path)}
            aria-pressed={file.path === selected}
          >
            {file.path}
          </Button>
        ))}
      </div>
      {diff.data && <ReviewDiff diff={diff.data} />}
      {admin ? (
        <>
          <label className="code-work-checkbox">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(event) => setConfirmed(event.target.checked)}
            />
            已核对，保留上述原文件的当前内容
          </label>
          <Button
            disabled={!confirmed || busy || resolve.isPending || diff.isFetching || !!diff.error}
            onClick={() => resolve.mutate()}
          >
            确认保留并结束恢复
          </Button>
        </>
      ) : (
        <p className="muted">请管理员核对并确认结束恢复。</p>
      )}
      <ErrorText error={diff.error || resolve.error} />
    </section>
  );
}
