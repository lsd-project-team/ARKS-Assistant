import { useMutation } from '@tanstack/react-query';
import { api, jsonBody } from '../../../app/api/client';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { toast } from '../../../shared/utils/toasts';
import type { WorkStatus } from './types';

export function WorkspaceInfo({
  status,
  base,
  projectId,
}: {
  status: WorkStatus;
  base: string;
  projectId: string;
}) {
  const open = useMutation({
    mutationFn: (location: 'source' | 'workspace') =>
      api(`${base}/open-directory`, { method: 'POST', body: jsonBody({ location }) }, projectId),
  });
  const copy = async (path: string) => {
    try {
      await navigator.clipboard.writeText(path);
      toast('工程路径已复制');
    } catch {
      toast('复制失败，请手动选择路径', undefined, 'error');
    }
  };
  return (
    <details className="code-work-locations">
      <summary>工程位置与来源版本</summary>
      {(
        [
          ['source', '原工程', status.source_path],
          ['workspace', '当前副本', status.workspace_path],
        ] as const
      ).map(
        ([location, label, path]) =>
          path && (
            <div key={location}>
              <strong>{label}</strong>
              <code>{path}</code>
              <Button onClick={() => void copy(path)}>复制路径</Button>
              <Button disabled={open.isPending} onClick={() => open.mutate(location)}>
                打开目录
              </Button>
            </div>
          ),
      )}
      {status.source_pinned === false && (
        <p className="muted">旧副本未记录来源路径，合并时请核对当前配置的目标目录。</p>
      )}
      <small className="muted">来源指纹 {status.source_version}</small>
      <ErrorText error={open.error} />
    </details>
  );
}
