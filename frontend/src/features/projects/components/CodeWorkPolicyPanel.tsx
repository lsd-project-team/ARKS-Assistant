import { useState } from 'react';
import { jsonBody } from '../../../app/api/client';
import { useAuth } from '../../auth/AuthContext';
import { Button, ErrorText } from '../../../shared/ui/ui';
import type { ProjectRequest } from '../lib/projectRequest';
import type { CodeWorkPolicy } from '../types/codeWork';

const fields = [
  ['max_storage_mb', '空间上限（MB）', 100, 1000000],
  ['min_free_mb', '最少空闲空间（MB）', 0, 1000000],
  ['max_log_mb', '单次日志上限（MB）', 1, 1024],
  ['windows_scratch_mb', 'Windows 验证临时磁盘预算（MB）', 20480, 1048576],
  ['max_active_verifications', '同时验证上限', 1, 16],
  ['retention_days', '临时文件保留天数', 1, 3650],
] as const;

export function CodeWorkPolicyPanel({
  policy,
  api,
  disabled,
  onSaved,
}: {
  policy: CodeWorkPolicy;
  api: ProjectRequest;
  disabled: boolean;
  onSaved: () => void;
}) {
  const admin = useAuth().session?.user.role === 'admin';
  const [draft, setDraft] = useState(policy);
  const [preview, setPreview] = useState<{
    eligible: number;
    removed: number;
    bytes: number;
    skipped: number;
  }>();
  const [busy, setBusy] = useState(false);
  const [cleaned, setCleaned] = useState<{ removed: number; bytes: number; skipped: number }>();
  const [error, setError] = useState<unknown>();
  if (!admin) return null;
  async function act(action: 'save' | 'preview' | 'cleanup') {
    setBusy(true);
    setError(undefined);
    try {
      if (action === 'save') {
        await api('/code-changes/policy', { method: 'PUT', body: jsonBody(draft) });
        onSaved();
      } else {
        const result = await api<{
          eligible: number;
          removed: number;
          bytes: number;
          skipped: number;
        }>('/code-changes/cleanup', {
          method: 'POST',
          body: jsonBody({ dry_run: action === 'preview' }),
        });
        setPreview(action === 'preview' ? result : undefined);
        if (action === 'cleanup') setCleaned(result);
        onSaved();
      }
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }
  return (
    <details className="code-work-config">
      <summary>本项目用量与清理（管理员）</summary>
      <p className="muted">
        策略仅作用于当前项目；聊天和项目阅读共享按 UTC 日结算的模型 token 额度。 Windows
        临时磁盘预算包含系统写入层，执行前核对节点可用空间。
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void act('save');
        }}
      >
        {fields.map(([key, label, min, max]) => (
          <label key={key}>
            {label}
            <input
              type="number"
              min={min}
              max={max}
              step={1}
              value={draft[key]}
              disabled={disabled || busy}
              onChange={(event) => setDraft({ ...draft, [key]: Number(event.target.value) })}
              required
            />
          </label>
        ))}
        <div className="code-work-token-policy">
          <span>项目每日模型 token 上限（UTC）</span>
          <label className="code-work-check">
            <input
              type="checkbox"
              aria-label="项目每日模型 token 无上限"
              checked={draft.reading_token_limit === null}
              disabled={disabled || busy}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  reading_token_limit: event.target.checked
                    ? null
                    : (policy.reading_token_limit ?? 500000),
                })
              }
            />
            无上限
          </label>
          {draft.reading_token_limit !== null && (
            <input
              aria-label="项目每日模型 token 上限（UTC）"
              type="number"
              min={1000}
              max={100000000}
              step={1}
              value={draft.reading_token_limit}
              disabled={disabled || busy}
              onChange={(event) =>
                setDraft({ ...draft, reading_token_limit: Number(event.target.value) })
              }
              required
            />
          )}
        </div>
        <label className="code-work-check">
          <input
            type="checkbox"
            checked={draft.require_sandbox_delivery}
            disabled={disabled || busy}
            onChange={(event) =>
              setDraft({ ...draft, require_sandbox_delivery: event.target.checked })
            }
          />
          交付必须通过沙箱验证
        </label>
        <Button disabled={disabled || busy} type="submit">
          保存本项目资源策略
        </Button>
      </form>
      <p className="muted">
        仅清理到期且已丢弃或已交付的临时文件，保留业务记录、活跃副本与未交付修改。
      </p>
      <Button disabled={disabled || busy} onClick={() => void act('preview')}>
        预览可清理文件
      </Button>
      {preview && (
        <div>
          <p>
            可清理 {preview.eligible} 项 · {preview.bytes} 字节 · 跳过 {preview.skipped} 项
          </p>
          <Button
            disabled={disabled || busy || !preview.eligible}
            onClick={() => void act('cleanup')}
          >
            确认清理到期临时文件
          </Button>
        </div>
      )}
      {cleaned && (
        <p role="status">
          已清理 {cleaned.removed} 项 · {cleaned.bytes} 字节 · 跳过 {cleaned.skipped} 项
        </p>
      )}
      <ErrorText error={error} />
    </details>
  );
}
