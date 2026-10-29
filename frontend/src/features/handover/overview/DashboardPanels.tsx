import { useMemo, useState, type ReactNode } from 'react';
import { ArrowUpRight, BookOpen, CircleDot, Package, Activity, NotebookPen } from 'lucide-react';
import { InteractiveRing, OperationBars, PackageBars } from './DashboardCharts';
import {
  DashboardEventList,
  DashboardMaterialList,
  DashboardRecordList,
  SelectionHeading,
} from './DashboardRecords';
import {
  eventsInRange,
  overviewSummary,
  selectEvents,
  selectTasks,
  selectIssues,
  selectMaterials,
} from './overviewData';
import { tabs, type Definitions, type Event, type Overview, type Tab } from '../shared/types';

type Summary = ReturnType<typeof overviewSummary>;
type PanelProps = {
  data: Summary;
  definitions: Definitions;
  onOpen: (id: string, version?: number) => void;
  onNavigate: (tab: Tab) => void;
};

function DashboardPanel({
  tab,
  icon,
  count,
  unit,
  summary,
  children,
  onNavigate,
  hint,
}: {
  tab: Tab;
  icon: ReactNode;
  count: number | undefined;
  unit: string;
  summary?: string;
  children: ReactNode;
  onNavigate: (tab: Tab) => void;
  hint?: string;
}) {
  const title = tabs.find((item) => item.id === tab)!.label;
  return (
    <section className={'dashboard-panel dashboard-panel-' + tab} aria-label={title + '概况'}>
      <header className="dashboard-panel-heading">
        <div>
          <h2>
            <span className="dashboard-panel-icon">{icon}</span>
            {title}
          </h2>
          {summary && <p>{summary}</p>}
        </div>
        <div className="dashboard-panel-metric">
          <strong>{count === undefined ? '—' : count}</strong>
          <span>{unit}</span>
        </div>
      </header>
      <div className="dashboard-panel-content">{children}</div>
      <footer>
        {hint && <span>{hint}</span>}
        <button onClick={() => onNavigate(tab)} className="dashboard-page-link">
          查看全部
          <ArrowUpRight size={14} />
        </button>
      </footer>
    </section>
  );
}

export function MaterialsPanel({ data, onOpen, onNavigate }: PanelProps) {
  const [fileType, setFileType] = useState('all');
  const rows = selectMaterials(data.materials, fileType);
  const active = data.materialTypes.find((item) => item.id === fileType);
  return (
    <DashboardPanel
      tab="materials"
      icon={<BookOpen size={17} />}
      count={data.materials.length}
      unit="份"
      onNavigate={onNavigate}
    >
      <div className="dashboard-chart-heading">
        <span>文件类型分布</span>
      </div>
      <InteractiveRing
        data={data.materialTypes}
        selected={fileType}
        onSelect={setFileType}
        label="资料文件类型分布"
        unit="份"
        totalLabel="资料总数"
      />
      <SelectionHeading
        label={active ? active.label + '资料' : '最近资料'}
        count={rows.length}
        filtered={fileType !== 'all'}
        onReset={() => setFileType('all')}
      />
      <DashboardMaterialList key={fileType} rows={rows} onOpen={onOpen} />
    </DashboardPanel>
  );
}

export function TasksPanel({ data, definitions, onOpen, onNavigate }: PanelProps) {
  const [stage, setStage] = useState('all');
  const selectedRows = selectTasks(data.tasks, stage);
  const active = data.workStages.find((item) => item.id === stage);
  return (
    <DashboardPanel
      tab="tasks"
      icon={<CircleDot size={17} />}
      count={data.tasks.length}
      unit="项"
      summary={
        '进行中 ' +
        (data.workStages.find((item) => item.id === 'doing')?.value || 0) +
        ' · 阻塞 ' +
        data.blocked.length +
        ' · 已完成 ' +
        data.completed.length
      }
      onNavigate={onNavigate}
    >
      <div className="dashboard-chart-heading">
        <span>工作状态分布</span>
      </div>
      <InteractiveRing
        data={data.workStages}
        selected={stage}
        onSelect={setStage}
        label="工作状态分布"
        unit="项"
        totalLabel="工作总数"
        summary={{
          value: data.tasks.length
            ? Math.round((data.completed.length / data.tasks.length) * 100) + '%'
            : '—',
          label: '工作完成率',
        }}
      />
      <SelectionHeading
        label={active ? active.label + '工作' : '工作记录'}
        count={selectedRows.length}
        filtered={stage !== 'all'}
        onReset={() => setStage('all')}
      />
      <DashboardRecordList
        rows={selectedRows}
        key={stage}
        definitions={definitions}
        onOpen={onOpen}
        empty="此状态暂无工作"
      />
    </DashboardPanel>
  );
}

export function PackagesPanel({ data, onOpen, onNavigate }: PanelProps) {
  return (
    <DashboardPanel
      tab="packages"
      icon={<Package size={17} />}
      count={data.packages.length}
      unit="份"
      summary={
        '已确认 ' +
        data.packageConfirmed +
        ' · 待确认或复核 ' +
        (data.packages.length - data.packageConfirmed)
      }
      onNavigate={onNavigate}
    >
      {data.packageBars.length ? (
        <PackageBars data={data.packageBars} onOpen={onOpen} />
      ) : (
        <p className="dashboard-empty dashboard-empty-chart">尚未生成交接包</p>
      )}
      <div className="dashboard-package-summary">
        <div>
          <span>已确认交接包</span>
          <strong>
            {data.packageConfirmed}
            <small> / {data.packages.length}</small>
          </strong>
        </div>
      </div>
    </DashboardPanel>
  );
}

export function IssuesPanel({ data, definitions, onOpen, onNavigate }: PanelProps) {
  const [recordType, setRecordType] = useState('all');
  const selectedRows = selectIssues(data.issues, recordType);
  const active = data.issueTypes.find((item) => item.id === recordType);
  return (
    <DashboardPanel
      tab="issues"
      icon={<NotebookPen size={17} />}
      count={data.issues.length}
      unit="条"
      summary={`未解决 ${data.issueOpen} · 已解决 ${data.issueResolved} · 已记录 ${data.issueRecorded}`}
      onNavigate={onNavigate}
    >
      <div className="dashboard-chart-heading">
        <span>记录类型分布</span>
      </div>
      <InteractiveRing
        data={data.issueTypes}
        selected={recordType}
        onSelect={setRecordType}
        label="问题与经验类型分布"
        unit="条"
        totalLabel="记录总数"
      />
      <SelectionHeading
        label={active ? active.label + '记录' : '最近记录'}
        count={selectedRows.length}
        filtered={recordType !== 'all'}
        onReset={() => setRecordType('all')}
      />
      <DashboardRecordList
        key={recordType}
        rows={selectedRows}
        definitions={definitions}
        onOpen={onOpen}
        empty="此类型暂无问题与经验记录"
      />
    </DashboardPanel>
  );
}

export function ActivityPanel({
  data,
  overview,
  events,
  eventsError,
  onOpen,
  onNavigate,
  syncedAt,
}: Omit<PanelProps, 'definitions'> & {
  overview: Overview;
  events?: Event[];
  eventsError: boolean;
  syncedAt: number;
}) {
  const [days, setDays] = useState(0);
  const [action, setAction] = useState('all');
  const rangeEvents = useMemo(() => eventsInRange(events || [], days), [events, days, syncedAt]);
  const bars = useMemo(
    () => overviewSummary(overview, rangeEvents).eventBars,
    [overview, rangeEvents],
  );
  const selectedEvents = selectEvents(rangeEvents, action);
  const active = bars.find((item) => item.id === action);
  return (
    <DashboardPanel
      tab="updates"
      hint={events ? '按最近 ' + events.length + ' 次操作统计' : '等待同步操作记录'}
      icon={<Activity size={17} />}
      count={events ? rangeEvents.length : undefined}
      unit="次"
      summary={data.reviewCount + ' 条记录待重新复核'}
      onNavigate={onNavigate}
    >
      <div className="dashboard-activity-controls">
        <span>近期操作分布</span>
        <div className="dashboard-segmented" role="group" aria-label="筛选日志时间">
          {[
            { value: 0, label: '全部' },
            { value: 7, label: '7天' },
            { value: 30, label: '30天' },
          ].map((item) => (
            <button
              key={item.value}
              aria-pressed={days === item.value}
              onClick={() => {
                setDays(item.value);
                setAction('all');
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>
      {events ? (
        <>
          <OperationBars data={bars} selected={action} onSelect={setAction} />
          <SelectionHeading
            label={active ? active.label + '记录' : '最近动态'}
            count={selectedEvents.length}
            filtered={action !== 'all'}
            onReset={() => setAction('all')}
          />
          <DashboardEventList
            key={days + ':' + action}
            events={selectedEvents}
            records={overview.records}
            onOpen={onOpen}
          />
        </>
      ) : (
        <p className="dashboard-empty dashboard-empty-chart" role="status">
          {eventsError ? '操作记录加载失败，请点击顶部刷新重试。' : '正在加载操作记录…'}
        </p>
      )}
    </DashboardPanel>
  );
}
