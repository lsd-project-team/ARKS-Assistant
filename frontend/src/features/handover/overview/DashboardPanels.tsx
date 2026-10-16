import { useMemo, useState, type ReactNode } from 'react';
import { ArrowUpRight, BookOpen, CircleDot, Package, Activity } from 'lucide-react';
import { Button } from '../../../shared/ui/ui';
import { InteractiveRing, OperationBars, PackageBars } from './DashboardCharts';
import { DashboardEventList, DashboardRecordList, SelectionHeading } from './DashboardRecords';
import {
  eventsInRange,
  overviewSummary,
  selectEvents,
  selectMaterials,
  selectTasks,
  type ChartDatum,
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
  hint = '点击图表探索记录',
}: {
  tab: Tab;
  icon: ReactNode;
  count: number | undefined;
  unit: string;
  summary: string;
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
          <p>{summary}</p>
        </div>
        <div className="dashboard-panel-metric">
          <strong>{count === undefined ? '—' : count}</strong>
          <span>{unit}</span>
        </div>
      </header>
      <div className="dashboard-panel-content">{children}</div>
      <footer>
        <span>{hint}</span>
        <button onClick={() => onNavigate(tab)} className="dashboard-page-link">
          查看全部
          <ArrowUpRight size={14} />
        </button>
      </footer>
    </section>
  );
}

export function MaterialsPanel({
  data,
  definitions,
  onOpen,
  onNavigate,
  onImport,
}: PanelProps & {
  onImport: () => void;
}) {
  const [state, setState] = useState('all');
  const typedRows = data.materials;
  const selectedRows = selectMaterials(data.materials, 'all', state);
  const chartData: ChartDatum[] = [
    {
      id: 'confirmed',
      label: '已确认',
      tone: 'green',
      value: typedRows.filter((row) => row.state === 'confirmed').length,
    },
    {
      id: 'draft',
      label: '待确认',
      tone: 'blue',
      value: typedRows.filter((row) => row.state === 'draft').length,
    },
    {
      id: 'needs_review',
      label: '待复核',
      tone: 'amber',
      value: typedRows.filter((row) => row.state === 'needs_review').length,
    },
  ];
  return (
    <DashboardPanel
      tab="materials"
      icon={<BookOpen size={17} />}
      count={data.materials.length}
      unit="份"
      summary={'资料 ' + data.materials.length + ' · 已确认 ' + data.materialConfirmed}
      onNavigate={onNavigate}
    >
      <InteractiveRing
        data={chartData}
        selected={state}
        onSelect={setState}
        label="资料确认分布"
        unit="份"
        totalLabel="资料总数"
        summary={{
          value: typedRows.length
            ? Math.round((chartData[0].value / typedRows.length) * 100) + '%'
            : '—',
          label: '已确认比例',
        }}
      />
      <SelectionHeading
        label={
          state === 'all' ? '最近资料' : chartData.find((item) => item.id === state)!.label + '记录'
        }
        count={selectedRows.length}
        filtered={state !== 'all'}
        onReset={() => {
          setState('all');
        }}
      />
      <DashboardRecordList
        key={state}
        rows={selectedRows}
        definitions={definitions}
        onOpen={onOpen}
        empty="此筛选范围暂无资料"
      />
      {!data.materials.length && (
        <div className="handover-actions dashboard-onboarding">
          <Button onClick={onImport}>添加资料</Button>
        </div>
      )}
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
        <small>状态与记录联动</small>
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
      hint="点击横条查看交接包"
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
      <p className="dashboard-chart-note">收录数量随包内固定版本保存；点击横条查看内容与来源。</p>
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
