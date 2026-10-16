import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { jsonBody } from '../../../app/api/client';
import { useAuth } from '../../auth/AuthContext';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { useProjectApi } from '../hooks/useProjectApi';
import { codeWorkError, parseCommandArgv } from '../lib/codeWorkRules';
import type { ProjectRequest } from '../lib/projectRequest';
import { executorPayload } from '../lib/codeReadiness';
import type { VerificationExecutor, VerificationProfile } from '../types/codeWork';
import { Select } from '../../../shared/ui/Select';
import { ExecutorFields } from './ExecutorFields';

export function VerificationEnvironmentProbe({
  projectId,
  profile,
  api,
  disabled,
}: {
  projectId: string;
  profile: VerificationProfile;
  api: ProjectRequest;
  disabled: boolean;
}) {
  const admin = useAuth().session?.user.role === 'admin';
  const probe = useQuery({
    queryKey: ['code-profile-probe', projectId, profile.id, JSON.stringify(profile.executor)],
    enabled: false,
    retry: false,
    queryFn: () =>
      api<{ available: boolean; platform?: string; image_id?: string; error?: string }>(
        `/code-changes/profiles/${encodeURIComponent(profile.id)}/probe`,
        { method: 'POST' },
      ),
  });
  if (!admin) return null;
  return (
    <div>
      <Button disabled={disabled || probe.isFetching} onClick={() => void probe.refetch()}>
        {probe.isFetching ? '正在探测环境…' : '探测环境'}
      </Button>
      {probe.data && (
        <p role="status">
          上次探测：{probe.data.available ? '节点与镜像可访问' : '当前环境不可用'}
          {probe.data.platform && ` · ${probe.data.platform}`}
          {probe.data.image_id && (
            <>
              {' '}
              · <code>{probe.data.image_id}</code>
            </>
          )}
          {probe.data.error && ` · ${probe.data.error}`}
        </p>
      )}
      <p className="muted">探测不执行项目命令；可访问仍需原版本基线与修改验证。</p>
      <ErrorText error={probe.error ? codeWorkError(probe.error) : undefined} />
    </div>
  );
}

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
  const [executor, setExecutor] = useState<VerificationExecutor>({
    kind: 'container',
    platform: 'linux',
    image: '',
    context: 'default',
  });
  const [category, setCategory] = useState<VerificationProfile['category']>('test');
  const [environment, setEnvironment] = useState('');
  const [baseline, setBaseline] = useState(true);
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
          executor: executorPayload(executor),
          category,
          environment_label: environment.trim(),
          baseline_required: baseline,
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
          数组保存，执行时不经过 shell。显式选择可信宿主时，副本不限制进程系统权限（非沙箱）。
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
        <ExecutorFields value={executor} onChange={setExecutor} disabled={disabled || pending} />
        <label>
          验证类别
          <Select
            aria-label="验证类别"
            value={category || 'test'}
            onValueChange={(value) => setCategory(value as VerificationProfile['category'])}
            disabled={disabled || pending}
          >
            <option value="build">构建</option>
            <option value="test">项目测试</option>
            <option value="analysis">分析 / 质量评测</option>
            <option value="offline">离线验证</option>
          </Select>
        </label>
        <label>
          环境名称
          <input
            value={environment}
            onChange={(event) => setEnvironment(event.target.value)}
            disabled={disabled || pending}
            maxLength={120}
            placeholder="例如 Windows / .NET Framework 4.8"
          />
        </label>
        <label className="code-work-check">
          <input
            type="checkbox"
            checked={baseline}
            disabled={disabled || pending}
            onChange={(event) => setBaseline(event.target.checked)}
          />
          交付审核前要求有效原版本基线
        </label>
        <ErrorText error={error} />
        <Button type="submit" disabled={disabled || pending}>
          保存命令配置
        </Button>
      </form>
    </details>
  );
}
