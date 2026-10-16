import { useState } from 'react';
import { jsonBody } from '../../../app/api/client';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { useProjectApi } from '../hooks/useProjectApi';
import { codeWorkError } from '../lib/codeWorkRules';
import type { Verification } from '../types/codeWork';

const fields = [
  ['problem', '问题现象'],
  ['conditions', '发生条件'],
  ['device', '设备'],
  ['software_version', '软件版本'],
  ['module', '模块'],
  ['cause', '已确认原因'],
  ['solution', '处理办法'],
  ['verification', '实际验证结果'],
] as const;

export function ChangeExperience({
  changeId,
  verification,
  disabled,
}: {
  changeId: string;
  verification: Verification;
  disabled: boolean;
}) {
  const api = useProjectApi();
  const [title, setTitle] = useState('');
  const [values, setValues] = useState<Record<string, string>>({});
  const [resolved, setResolved] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const [record, setRecord] = useState<{ id: string; version: number; title: string }>();

  async function save() {
    if (disabled || pending) return;
    setPending(true);
    setError(undefined);
    try {
      if (!title.trim() || !values.problem?.trim()) throw new Error('请填写经验标题和问题现象');
      if (!values.verification?.trim()) throw new Error('请填写实际验证结果');
      if (resolved && !values.solution?.trim()) throw new Error('确认已解决时，请填写实际处理办法');
      const saved = await api<{ id: string; version: number; title: string }>(
        `/code-changes/${encodeURIComponent(changeId)}/experience`,
        {
          method: 'POST',
          body: jsonBody({
            title: title.trim(),
            verification_id: verification.id,
            change_version: verification.change_version,
            payload: {
              problem: '',
              conditions: '',
              environment: '',
              device: '',
              software_version: '',
              module: '',
              investigation: '',
              cause: '',
              solution: '',
              verification: '',
              keywords: [],
              notes: '',
              ...values,
              resolution_status: resolved ? 'resolved' : 'open',
            },
          }),
        },
      );
      setRecord(saved);
    } catch (reason) {
      setError(codeWorkError(reason));
    } finally {
      setPending(false);
    }
  }

  return (
    <details className="code-work-config">
      <summary>记录调试经验</summary>
      <p className="muted">
        仅保存你填写并确认的事实。本次配置命令通过不等同于设备验收；实际验证结果请据实填写。
      </p>
      {record ? (
        <p role="status">
          已保存“{record.title}” · v{record.version}{' '}
          <a
            href={`#handover/issues?record=${encodeURIComponent(record.id)}&version=${record.version}`}
          >
            查看调试问题
          </a>
        </p>
      ) : (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <label>
            经验标题
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              maxLength={200}
              required
              disabled={disabled || pending}
            />
          </label>
          {fields.map(([key, label]) => (
            <label key={key}>
              {label}
              <textarea
                rows={key === 'problem' || key === 'solution' ? 3 : 2}
                value={values[key] || ''}
                required={key === 'problem' || key === 'verification'}
                disabled={disabled || pending}
                maxLength={['device', 'software_version', 'module'].includes(key) ? 2000 : 30000}
                onChange={(event) =>
                  setValues((previous) => ({ ...previous, [key]: event.target.value }))
                }
              />
            </label>
          ))}
          <label className="code-work-check">
            <input
              type="checkbox"
              checked={resolved}
              onChange={(event) => setResolved(event.target.checked)}
              disabled={disabled || pending}
            />
            我确认该问题已解决
          </label>
          <ErrorText error={error} />
          <Button type="submit" disabled={disabled || pending || !verification.change_version}>
            保存调试经验
          </Button>
        </form>
      )}
    </details>
  );
}
