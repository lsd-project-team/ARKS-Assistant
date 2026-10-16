import { useState } from 'react';
import { jsonBody } from '../../../app/api/client';
import { useAuth } from '../../auth/AuthContext';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { useProjectApi } from '../hooks/useProjectApi';
import { codeWorkError, parseCommandArgv } from '../lib/codeWorkRules';
import type { ProjectRequest } from '../lib/projectRequest';

export function VerificationProfiles({
  disabled,
  onSaved,
  api: configuredApi,
}: {
  disabled: boolean;
  onSaved: () => void;
  api?: ProjectRequest;
}) {
  const admin = useAuth().session?.user.role === 'admin';
  const projectApi = useProjectApi();
  const api = configuredApi || projectApi;
  const [name, setName] = useState('');
  const [argv, setArgv] = useState('');
  const [timeout, setTimeout] = useState('120');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  if (!admin) return null;

  async function save() {
    setError(undefined);
    setPending(true);
    try {
      const seconds = Number(timeout);
      if (!name.trim()) throw new Error('请填写命令名称');
      if (!Number.isInteger(seconds) || seconds < 1 || seconds > 600)
        throw new Error('超时秒数必须是 1–600 之间的整数');
      await api('/code-changes/profiles', {
        method: 'POST',
        body: jsonBody({
          name: name.trim(),
          argv: parseCommandArgv(argv),
          timeout_seconds: seconds,
        }),
      });
      setName('');
      setArgv('');
      onSaved();
    } catch (reason) {
      setError(codeWorkError(reason));
    } finally {
      setPending(false);
    }
  }

  return (
    <details className="code-work-config">
      <summary>配置构建或测试命令（管理员）</summary>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <p className="muted">
          命令在隔离副本目录执行。请填写你明确配置的构建或测试程序；参数以 JSON
          数组保存，执行时不经过 shell。 副本不限制进程系统权限，仅配置可信构建测试程序。
        </p>
        <label>
          命令名称
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            disabled={disabled || pending}
            required
            maxLength={120}
          />
        </label>
        <label>
          程序与参数
          <textarea
            aria-label="验证命令参数 JSON 数组"
            value={argv}
            onChange={(event) => setArgv(event.target.value)}
            disabled={disabled || pending}
            rows={3}
            placeholder={'["python", "-m", "pytest"]'}
            required
            spellCheck={false}
          />
        </label>
        <label>
          超时（秒）
          <input
            type="number"
            min={1}
            max={600}
            step={1}
            value={timeout}
            onChange={(event) => setTimeout(event.target.value)}
            disabled={disabled || pending}
            required
          />
        </label>
        <ErrorText error={error} />
        <Button type="submit" disabled={disabled || pending}>
          保存命令配置
        </Button>
      </form>
    </details>
  );
}
