import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../../app/api/client';
import type { Project } from '../../../shared/types/api';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { Select } from '../../../shared/ui/Select';
import { boundProjectApi } from '../lib/projectRequest';
import type { VerificationProfile } from '../types/codeWork';
import { VerificationEnvironmentProbe, VerificationProfiles } from './VerificationProfiles';
import { ReadinessPanel } from './ReadinessPanel';
import { executionLabel } from '../lib/codeReadiness';
import '../styles/code-work.css';

export function ProjectVerificationProfiles({ projects }: { projects: Project[] }) {
  const [selectedId, setSelectedId] = useState('');
  const project = projects.find((item) => item.id === selectedId);
  return (
    <div className="code-work">
      <h2>项目验证命令</h2>
      <p className="muted">选择项目后维护该项目的构建与测试命令。保存配置不会自动执行。</p>
      <Select
        value={project?.id || ''}
        onValueChange={setSelectedId}
        aria-label="选择验证命令所属项目"
      >
        <option value="">请选择项目</option>
        {projects.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
            {item.state === 'archived' ? '（已归档）' : ''}
          </option>
        ))}
      </Select>
      {project ? (
        <ProjectVerificationProfileList
          key={project.id}
          projectId={project.id}
          readOnly={project.state !== 'active'}
        />
      ) : (
        <p className="muted">先选择一个项目，再查看或新增其验证命令。</p>
      )}
    </div>
  );
}

export function ProjectVerificationProfileList({
  projectId,
  readOnly,
}: {
  projectId: string;
  readOnly: boolean;
}) {
  // 管理页的项目选择独立于 useWorkspace；异步保存始终绑定显式选择的项目。
  const request = useMemo(() => boundProjectApi(projectId, api), [projectId]);
  const profiles = useQuery({
    queryKey: ['code-change-profiles-admin', projectId],
    queryFn: ({ signal }) =>
      request<{ profiles: VerificationProfile[] }>('/code-changes/profiles', { signal }),
  });
  return (
    <div className="code-work-panel">
      <div className="code-work-heading">
        <h3>已配置命令</h3>
        <Button onClick={() => void profiles.refetch()}>刷新命令</Button>
      </div>
      <ErrorText error={profiles.error} />
      {profiles.isPending ? (
        <p className="muted">正在读取命令配置…</p>
      ) : profiles.data?.profiles.length ? (
        <ul className="code-work-file-list">
          {profiles.data.profiles.map((profile) => (
            <li key={profile.id}>
              <strong>{profile.name}</strong>
              <span>超时 {profile.timeout_seconds || 120} 秒</span>
              <span>
                {executionLabel(profile.executor)} · {profile.environment_label || '环境未命名'} ·{' '}
                {profile.category || '类别未知'}
              </span>
              {profile.executor?.kind === 'container' && (
                <small>镜像 {profile.executor.image}</small>
              )}
              {profile.baseline_required && <span>要求原版本基线</span>}
              <code className="code-work-command">{JSON.stringify(profile.argv)}</code>
              <VerificationEnvironmentProbe
                projectId={projectId}
                profile={profile}
                api={request}
                disabled={readOnly}
              />
            </li>
          ))}
        </ul>
      ) : (
        <p className="code-work-empty">此项目尚未配置验证命令。</p>
      )}
      {readOnly && <p className="muted">项目已归档，当前只可查看命令配置。</p>}
      <VerificationProfiles
        api={request}
        disabled={readOnly}
        onSaved={() => void profiles.refetch()}
      />
      <ReadinessPanel projectId={projectId} readOnly={readOnly} />
    </div>
  );
}
