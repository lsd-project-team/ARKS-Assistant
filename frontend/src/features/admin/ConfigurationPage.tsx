import { useCallback, useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { SettingsDialog } from '../settings/components/SettingsDialog';
import { DataMaintenancePanel } from './DataMaintenancePanel';
import { Button, ErrorText } from '../../shared/ui/ui';
import { useWorkspace } from '../../app/state/store';
import { adminApi, dateTime } from './client';

export function ConfigurationPage({
  dataOnly,
  onDirtyChange,
}: {
  dataOnly: boolean;
  onDirtyChange?: (dirty: boolean) => void;
}) {
  const projectId = useWorkspace((state) => state.projectId);
  const [dirty, setDirty] = useState(false);
  const dirtyChanged = useCallback((value: boolean) => {
    setDirty(value);
  }, []);
  useEffect(() => onDirtyChange?.(dirty), [dirty, onDirtyChange]);
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
  return (
    <div className="admin-page">
      <header className="admin-heading">
        <div>
          <h1>{dataOnly ? '数据维护' : '系统配置'}</h1>
        </div>
      </header>
      {dataOnly ? (
        <section className="admin-panel">
          <DataMaintenancePanel />
        </section>
      ) : (
        <SettingsDialog
          key={projectId}
          open
          embedded
          initialTab="model"
          onDirtyChange={dirtyChanged}
          allowedTabs={['model', 'mcp', 'sources', 'memory', 'appearance']}
          onClose={() => {}}
        />
      )}
      {dataOnly && (
        <section className="admin-panel">
          <h2>恢复备份</h2>
          <details className="admin-metric-rules">
            <summary>查看恢复步骤</summary>
            <p>
              先在上方校验备份。然后在服务所在电脑打开 PowerShell，进入项目目录，停止服务后恢复：
            </p>
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
    </div>
  );
}
