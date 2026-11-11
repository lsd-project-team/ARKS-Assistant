import { useEffect, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { api, jsonBody } from '../../../app/api/client';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { ReviewDiff } from './ReviewDiff';
import { VerificationReport } from './VerificationReport';
import { verificationBusy, type MergeDiff, type MergePlan, type WorkStatus } from './types';

type Resolution = { choice: 'source' | 'workspace' | 'manual'; content: string };
export function MergePanel({
  status,
  base,
  projectId,
  admin,
  busy,
  onChanged,
}: {
  status: WorkStatus;
  base: string;
  projectId: string;
  admin: boolean;
  busy: boolean;
  onChanged: () => void;
}) {
  const [paths, setPaths] = useState<string[]>(() =>
    status.merge_plan_id ? status.merge_paths || [] : status.files?.map((file) => file.path) || [],
  );
  const [planId, setPlanId] = useState(status.merge_plan_id || '');
  const [selected, setSelected] = useState('');
  const [resolutions, setResolutions] = useState<Record<string, Resolution>>({});
  const [confirmed, setConfirmed] = useState(false);
  const [needsPreview, setNeedsPreview] = useState(false);
  const [rollbackId, setRollbackId] = useState('');
  useEffect(() => {
    setPaths(
      status.merge_plan_id
        ? status.merge_paths || []
        : status.files?.map((file) => file.path) || [],
    );
    setPlanId(status.merge_plan_id || '');
    setResolutions({});
    setConfirmed(false);
  }, [status.revision]);
  const plan = useQuery({
    queryKey: ['code-work', projectId, base, 'merge', planId],
    queryFn: () => api<MergePlan>(`${base}/merge/${planId}`, undefined, projectId),
    enabled: !!planId,
    refetchInterval: 2000,
  });
  const data = plan.data;
  useEffect(() => {
    if (data?.id) {
      setResolutions(data.resolutions || {});
      setNeedsPreview(false);
    }
  }, [data?.id]);
  const verifying = verificationBusy(data?.verification);
  const file = data?.files.find((item) => item.path === selected) || data?.files[0];
  const diff = useQuery({
    queryKey: ['code-work', projectId, base, 'merge-diff', planId, file?.path],
    queryFn: () =>
      api<MergeDiff>(
        `${base}/merge/${planId}/diff?path=${encodeURIComponent(file!.path)}`,
        undefined,
        projectId,
      ),
    enabled: !!planId && !!file,
  });
  const preview = useMutation({
    mutationFn: () =>
      api<MergePlan>(
        `${base}/merge/preview`,
        { method: 'POST', body: jsonBody({ paths, resolutions }) },
        projectId,
      ),
    onSuccess: (value) => {
      setPlanId(value.id);
      setConfirmed(false);
      setNeedsPreview(false);
      setSelected(value.files[0]?.path || '');
    },
  });
  const verify = useMutation({
    mutationFn: () => api(`${base}/merge/${planId}/verify`, { method: 'POST' }, projectId),
    onSuccess: () => void plan.refetch(),
  });
  const cancel = useMutation({
    mutationFn: () => api(`${base}/cancel`, { method: 'POST' }, projectId),
    onSuccess: () => void plan.refetch(),
  });
  const apply = useMutation({
    mutationFn: () =>
      api(
        `${base}/merge/${planId}/apply`,
        { method: 'POST', body: jsonBody({ confirm_target: data!.target }) },
        projectId,
      ),
    onSuccess: () => {
      setPlanId('');
      setConfirmed(false);
      onChanged();
    },
  });
  const rollback = useMutation({
    mutationFn: (record: NonNullable<WorkStatus['applied']>[number]) =>
      api(
        `${base}/merge/${record.id}/rollback`,
        { method: 'POST', body: jsonBody({ confirm_target: record.target }) },
        projectId,
      ),
    onSuccess: () => {
      setRollbackId('');
      setPlanId('');
      onChanged();
    },
  });
  const lastApplied = status.applied?.filter((item) => item.status === 'applied').at(-1)?.id;
  const pendingResolution = file && resolutions[file.path];
  return (
    <div className="code-merge-panel">
      <strong>合并回原工程</strong>
      <p className="muted">
        先比较原始基线、原工程现状和副本结果。候选工程重新验证通过后，管理员确认目标和文件，再应用改动。
      </p>
      <div className="code-merge-selection">
        {status.files?.map((item) => (
          <label key={item.path}>
            <input
              type="checkbox"
              checked={paths.includes(item.path)}
              disabled={busy || verifying || apply.isPending}
              onChange={(event) => {
                setPaths((value) =>
                  event.target.checked
                    ? [...value, item.path]
                    : value.filter((path) => path !== item.path),
                );
                setPlanId('');
                setResolutions({});
              }}
            />
            {item.path}
          </label>
        ))}
      </div>
      <Button
        disabled={!paths.length || busy || verifying || preview.isPending}
        onClick={() => preview.mutate()}
      >
        {preview.isPending
          ? '正在准备候选工程…'
          : Object.keys(resolutions).length
            ? '按冲突处理重新预览'
            : '生成合并预览'}
      </Button>
      {data && (
        <>
          <p>
            目标原工程：<code>{data.target}</code>
          </p>
          {data.source_changed && (
            <p className="muted">
              原工程已有其他修改，候选已进行三方比较；以本次预览和重新验证结果为准。
            </p>
          )}
          {!!data.rebase_conflicts.length && (
            <p className="error-text">
              未选择文件存在同步冲突，请将这些文件纳入合并：{data.rebase_conflicts.join('、')}
            </p>
          )}
          <div className="code-work-changes">
            <nav aria-label="合并文件">
              {data.files.map((item) => (
                <button
                  key={item.path}
                  className={file?.path === item.path ? 'selected' : ''}
                  onClick={() => setSelected(item.path)}
                >
                  <small>
                    {item.status === 'conflict'
                      ? '有冲突'
                      : item.status === 'resolved'
                        ? '已处理'
                        : item.kind === 'project'
                          ? '工程编译项'
                          : '可合并'}
                  </small>
                  {item.path}
                </button>
              ))}
            </nav>
            <div className="code-work-diff">
              {diff.data && (
                <>
                  <div className="code-work-file-heading">
                    <strong>{file?.path}</strong>
                  </div>
                  {file?.status === 'conflict' && (
                    <div className="code-conflict-resolution">
                      <label>
                        冲突处理
                        <select
                          value={pendingResolution?.choice || ''}
                          onChange={(event) => {
                            setResolutions((value) => ({
                              ...value,
                              [file.path]: {
                                choice: event.target.value as Resolution['choice'],
                                content: diff.data!.after,
                              },
                            }));
                            setConfirmed(false);
                            setNeedsPreview(true);
                          }}
                        >
                          <option value="">请选择处理方式</option>
                          <option value="workspace">采用副本内容</option>
                          <option value="source">保留原工程，放弃此文件的副本修改</option>
                          <option value="manual">手动编辑合并结果</option>
                        </select>
                      </label>
                      {pendingResolution?.choice === 'manual' && (
                        <textarea
                          aria-label="手动合并结果"
                          className="code-test-source"
                          value={pendingResolution.content}
                          maxLength={2000000}
                          onChange={(event) => {
                            setResolutions((value) => ({
                              ...value,
                              [file.path]: { choice: 'manual', content: event.target.value },
                            }));
                            setNeedsPreview(true);
                            setConfirmed(false);
                          }}
                        />
                      )}
                      <details>
                        <summary>查看创建副本时的基线</summary>
                        <pre>{diff.data.base}</pre>
                      </details>
                    </div>
                  )}
                  <ReviewDiff diff={diff.data} />
                </>
              )}
              <ErrorText error={diff.error} />
            </div>
          </div>
          <div className="code-review-toolbar">
            <Button
              disabled={
                busy ||
                verifying ||
                !!data.conflicts.length ||
                !!data.rebase_conflicts.length ||
                verify.isPending ||
                data.status !== 'preview' ||
                needsPreview
              }
              onClick={() => verify.mutate()}
            >
              验证合并结果
            </Button>
            {verifying && <Button onClick={() => cancel.mutate()}>停止验证</Button>}
          </div>
          {data.verification && (
            <VerificationReport
              job={data.verification}
              current
              base={base}
              projectId={projectId}
              planId={planId}
            />
          )}
          {admin ? (
            <>
              <label className="code-work-checkbox">
                <input
                  type="checkbox"
                  checked={confirmed}
                  disabled={!data.can_apply || needsPreview || busy || verifying}
                  onChange={(event) => setConfirmed(event.target.checked)}
                />
                确认将上方文件应用到所示原工程；写回前保存恢复材料。
              </label>
              <Button
                disabled={
                  !confirmed ||
                  !data.can_apply ||
                  needsPreview ||
                  busy ||
                  verifying ||
                  apply.isPending
                }
                onClick={() => apply.mutate()}
              >
                {apply.isPending ? '正在应用…' : '确认应用到原工程'}
              </Button>
            </>
          ) : (
            <p className="muted">合并结果可在此审查和验证；写回原工程由管理员执行。</p>
          )}
        </>
      )}
      {!!status.applied?.length && (
        <div className="code-merge-history">
          <strong>合入记录</strong>
          {[...status.applied].reverse().map((record) => (
            <div key={record.id}>
              <span>
                {new Date(record.created_at).toLocaleString('zh-CN')} · {record.files.length} 个文件
                · {record.status === 'applied' ? '已合入' : '已回退'}
              </span>
              <code>{record.target}</code>
              {admin && record.id === lastApplied && (
                <Button disabled={busy || verifying} onClick={() => setRollbackId(record.id)}>
                  回退这次合并
                </Button>
              )}
              {rollbackId === record.id && (
                <div role="alert">
                  将恢复本次合并前的原工程源码，后续人工改动会阻止回退。副本中的改动继续保留。
                  <Button disabled={rollback.isPending} onClick={() => rollback.mutate(record)}>
                    确认回退
                  </Button>
                  <Button onClick={() => setRollbackId('')}>取消</Button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      <ErrorText
        error={
          plan.error ||
          preview.error ||
          verify.error ||
          cancel.error ||
          apply.error ||
          rollback.error
        }
      />
    </div>
  );
}
