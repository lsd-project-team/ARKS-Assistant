import { useCallback, useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { SettingsDialog } from '../components/SettingsDialog';
import { ProjectEditor } from '../components/ProjectEditor';
import { ProjectDocuments } from '../components/ProjectDocuments';
import { Button, ErrorText } from '../components/ui';
import { Select } from '../components/Select';
import { useWorkspace } from '../lib/store';
import type { Project, ProjectList } from '../types';
import { adminApi, dateTime } from './client';

export function ConfigurationPage({
  dataOnly,
  onDirtyChange,
}: {
  dataOnly: boolean;
  onDirtyChange?: (dirty: boolean) => void;
}) {
  const projectId = useWorkspace((state) => state.projectId);
  const projects = useQuery({
    queryKey: ['projects', 'admin-config'],
    queryFn: () => adminApi<ProjectList>('/projects'),
  });
  const current = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => adminApi<Project>(`/projects/${projectId}`),
    enabled: !!projectId && projectId !== 'independent',
  });
  const [editing, setEditing] = useState(false);
  const [dirty, setDirty] = useState(false);
  const dirtyChanged = useCallback(
    (value: boolean) => {
      setDirty(value);
      onDirtyChange?.(value);
    },
    [onDirtyChange],
  );
  const [documents, setDocuments] = useState(false);
  const events = useQuery({
    queryKey: ['admin-events'],
    queryFn: () =>
      adminApi<
        {
          id: string;
          actor: string;
          action: string;
          target: string;
          detail: string;
          created_at: string;
        }[]
      >('/admin/events'),
    refetchInterval: 15000,
    enabled: !dataOnly,
  });
  useEffect(() => {
    setDocuments(false);
  }, [projectId]);
  return (
    <div className="admin-page">
      <header className="admin-heading">
        <div>
          <span className="admin-eyebrow">WORKSPACE / {dataOnly ? 'DATA' : 'CONFIGURATION'}</span>
          <h1>{dataOnly ? '数据维护' : '系统配置'}</h1>
          <p>
            {dataOnly ? '查看数据占用，导出与校验本地备份。' : '维护模型连接、源码关联与知识配置。'}
          </p>
        </div>
      </header>
      {!dataOnly && (
        <section className="admin-panel">
          <div className="admin-panel-heading">
            <div>
              <h2>源码与知识配置</h2>
              <p>为用户问答选择对应的源码、仓库与共享资料。</p>
            </div>
            <Button disabled={!current.data} onClick={() => setEditing(true)}>
              编辑源码与项目指令
            </Button>
          </div>
          <div className="admin-source-selector">
            <label>
              当前配置项目
              <Select
                aria-label="选择配置项目"
                disabled={dirty}
                value={projectId}
                onValueChange={(value) => useWorkspace.getState().switchProject(value)}
              >
                {projects.data?.projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </Select>
            </label>
            <div>
              <span className="muted">源码目录</span>
              <p>{current.data?.source_root || '未关联源码目录'}</p>
            </div>
            <div>
              <span className="muted">DeepWiki 仓库</span>
              <p>{current.data?.deepwiki_repo || '未关联仓库'}</p>
            </div>
          </div>
          <ErrorText error={projects.error || current.error} />
          <div className="admin-row-actions">
            <Button disabled={!current.data} onClick={() => setDocuments(!documents)}>
              {documents ? '收起项目资料' : '项目资料与共享结论'}
            </Button>
          </div>
          {documents && (
            <ProjectDocuments
              key={projectId}
              projectId={projectId}
              readOnly={current.data?.state !== 'active'}
            />
          )}
        </section>
      )}
      <SettingsDialog
        key={`${dataOnly}:${projectId}`}
        open
        embedded
        initialTab={dataOnly ? 'data' : 'model'}
        onDirtyChange={dirtyChanged}
        allowedTabs={dataOnly ? ['data'] : ['model', 'mcp', 'sources', 'memory', 'appearance']}
        onClose={() => {}}
      />
      {dataOnly && (
        <section className="admin-panel">
          <h2>恢复备份</h2>
          <p>
            先使用上方“选择备份并校验”核对备份。实际恢复需要停止服务后执行项目中的恢复工具，恢复完成再启动服务。
          </p>
          <details className="admin-metric-rules">
            <summary>查看恢复步骤</summary>
            <p>在服务所在电脑打开 PowerShell，进入本项目目录。先校验备份，再停止服务并应用恢复：</p>
            <pre className="admin-reference-text">{`.\\scripts\\RestoreData.ps1 -Backup '备份 ZIP 的完整路径'\n.\\Stop.ps1\n.\\scripts\\RestoreData.ps1 -Backup '备份 ZIP 的完整路径' -Apply\n.\\Start.ps1`}</pre>
            <p>
              现有密钥配置保留，替换前的旧数据会保存到恢复目录供核对。恢复中断时，保持停服，执行恢复工具的
              -Rollback 后再启动。
            </p>
          </details>
        </section>
      )}
      {!dataOnly && (
        <section className="admin-panel">
          <div className="admin-panel-heading">
            <h2>近期管理操作</h2>
            <Button onClick={() => void events.refetch()}>刷新</Button>
          </div>
          <ErrorText error={events.error} />
          {events.data?.map((event) => (
            <div className="admin-recent-row" key={event.id}>
              <div>
                <strong>
                  {event.action} · {event.target}
                </strong>
                <small>
                  {event.actor}
                  {event.detail ? ` · ${event.detail}` : ''}
                </small>
              </div>
              <small>{dateTime(event.created_at)}</small>
            </div>
          ))}
          {events.data && !events.data.length && <p className="admin-empty">暂无管理操作记录。</p>}
        </section>
      )}
      {editing && current.data && (
        <ProjectEditor
          project={current.data}
          onClose={() => {
            setEditing(false);
            void current.refetch();
          }}
        />
      )}
    </div>
  );
}
