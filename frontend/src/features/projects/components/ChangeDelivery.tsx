import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { jsonBody } from '../../../app/api/client';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { useProjectApi } from '../hooks/useProjectApi';
import { deliveryVersionCurrent, executionLabel, reviewMissing } from '../lib/codeReadiness';
import type {
  CodeChange,
  ReadinessReport,
  Verification,
  VerificationProfile,
} from '../types/codeWork';

export function ChangeDelivery({
  projectId,
  change,
  profiles,
  disabled,
  sourceUnchanged,
  onChanged,
  onDownload,
}: {
  projectId: string;
  change: CodeChange;
  profiles: VerificationProfile[];
  disabled: boolean;
  sourceUnchanged: boolean;
  onChanged: (value: CodeChange) => void;
  onDownload: (path: string, filename: string, method?: 'GET' | 'POST') => Promise<void>;
}) {
  const api = useProjectApi();
  const [notes, setNotes] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const history = useQuery({
    queryKey: ['change-verifications', projectId, change.id, change.updated_at],
    queryFn: ({ signal }) =>
      api<{ verifications: Verification[] }>(
        `/code-changes/${encodeURIComponent(change.id)}/verifications`,
        { signal },
      ),
    refetchInterval: change.status === 'verifying' ? 2000 : false,
  });
  const readiness = useQuery({
    queryKey: ['code-work-readiness', projectId],
    queryFn: ({ signal }) => api<ReadinessReport>('/code-changes/readiness', { signal }),
  });
  const profile = profiles.find((item) => item.id === change.latest_verification?.profile_id);
  const missing = reviewMissing(change, profile, history.data?.verifications || []);
  if (!sourceUnchanged) missing.push('原始源码已有变化或尚未完成核对');
  if (!readiness.data) missing.push('交付策略尚未可用');
  if (
    readiness.data?.policy.require_sandbox_delivery &&
    change.latest_verification?.executor?.kind !== 'container'
  )
    missing.push('交付策略要求当前修改通过沙箱验证');
  const reviewed = deliveryVersionCurrent(change) && sourceUnchanged;
  async function review() {
    setBusy(true);
    setError(undefined);
    try {
      onChanged(
        await api<CodeChange>(`/code-changes/${encodeURIComponent(change.id)}/review`, {
          method: 'POST',
          body: jsonBody({ change_version: change.change_version, notes }),
        }),
      );
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="code-work-verification" aria-label="审核与交付">
      <h3>当前版本审核与交付</h3>
      <p className="code-work-source-version">
        当前修改版本：{change.change_version || '尚未提供'}
      </p>
      {!!missing.length && (
        <ul className="muted">
          {missing.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
      {reviewed ? (
        <p role="status">
          当前版本已审核 · {change.review?.actor} · {change.review?.reviewed_at}
        </p>
      ) : (
        <>
          <p className="muted">
            审核绑定当前版本；文件或源码变化后需重新验证与审核。未审核仍可下载草稿补丁。
          </p>
          <label>
            审核说明
            <textarea
              value={notes}
              rows={2}
              maxLength={5000}
              onChange={(event) => setNotes(event.target.value)}
              disabled={disabled || busy}
            />
          </label>
          <Button disabled={disabled || busy || !!missing.length} onClick={() => void review()}>
            审核当前固定版本
          </Button>
        </>
      )}
      <Button
        disabled={disabled || busy || !reviewed || !!missing.length}
        onClick={() =>
          void onDownload(
            `/code-changes/${encodeURIComponent(change.id)}/delivery`,
            `delivery-${change.id}.zip`,
            'POST',
          )
        }
      >
        下载已审核交付包
      </Button>
      <p className="muted">
        交付包含补丁、基线/验证/验收信息及应用与反向回退说明；不会自动修改业务原件。
      </p>
      <ErrorText error={error || history.error || readiness.error} />
      {!!history.data?.verifications.length && (
        <details>
          <summary>查看原版本与修改验证历史</summary>
          <ul className="code-work-file-list">
            {history.data.verifications.map((item) => (
              <li key={item.id}>
                <strong>
                  {item.purpose === 'baseline' ? '原版本基线' : '修改验证'} · {item.status}
                </strong>
                <span>{executionLabel(item.executor)}</span>
                <small>
                  版本 {item.change_version || '未知'} · 退出码 {item.exit_code ?? '尚无'}
                  {item.stale ? ' · 已失效' : ''}
                </small>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
