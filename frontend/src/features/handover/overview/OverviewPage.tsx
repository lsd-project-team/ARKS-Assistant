import { useMemo } from 'react';
import { RefreshCw } from 'lucide-react';
import { MaterialsPanel, TasksPanel, PackagesPanel, ActivityPanel } from './DashboardPanels';
import { overviewSummary } from './overviewData';
import { localTime } from '../shared/format';
import type { Definitions, Event, Overview, Tab } from '../shared/types';
import './dashboard.css';

export function OverviewPage({
  overview,
  definitions,
  events,
  eventsError = false,
  onOpen,
  onNavigate,
  onImport,
  syncedAt = 0,
  syncing = false,
  canReview = false,
}: {
  overview: Overview;
  definitions: Definitions;
  events?: Event[];
  eventsError?: boolean;
  onOpen: (id: string, version?: number) => void;
  onNavigate: (tab: Tab) => void;
  onImport: () => void;
  syncedAt?: number;
  syncing?: boolean;
  canReview?: boolean;
}) {
  const data = useMemo(() => overviewSummary(overview, events), [overview, events]);
  const panelProps = { data, definitions, onOpen, onNavigate };
  return (
    <div className="handover-dashboard">
      <div className="dashboard-intro">
        <div>
          <h2>交接概况</h2>
          <p>掌握资料、工作进度与最新交接动态</p>
        </div>
        <div
          className="dashboard-sync"
          aria-label={
            syncing ? '正在同步交接数据' : eventsError ? '日志暂未同步' : '交接数据自动同步'
          }
        >
          <RefreshCw size={12} className={syncing ? 'dashboard-syncing' : undefined} />
          <span>{syncing ? '同步中' : eventsError ? '日志暂未同步' : '自动同步'}</span>
          {!!syncedAt && (
            <time title={localTime(new Date(syncedAt).toISOString())}>
              {new Date(syncedAt).toLocaleTimeString('zh-CN', { hour12: false })}
            </time>
          )}
        </div>
      </div>
      <div className="dashboard-grid">
        <MaterialsPanel {...panelProps} onImport={onImport} />
        <TasksPanel {...panelProps} />
        <PackagesPanel {...panelProps} />
        {canReview && (
          <ActivityPanel
            data={data}
            overview={overview}
            events={events}
            eventsError={eventsError}
            onOpen={onOpen}
            onNavigate={onNavigate}
            syncedAt={syncedAt}
          />
        )}
      </div>
    </div>
  );
}
