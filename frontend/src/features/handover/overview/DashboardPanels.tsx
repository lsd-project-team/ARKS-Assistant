import { useState, type ReactNode } from 'react';
import { ArrowUpRight, BookOpen, CircleDot, Package, NotebookPen } from 'lucide-react';
import { InteractiveRing, PackageBars } from './DashboardCharts';
import { DashboardMaterialList, DashboardRecordList, SelectionHeading } from './DashboardRecords';
import { overviewSummary, selectTasks, selectIssues, selectMaterials } from './overviewData';
import { tabs, type Definitions, type Tab } from '../shared/types';

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
      summary="按文件类型统计"
      hint="点击图表筛选，点击资料查看原文件"
      onNavigate={onNavigate}
    >
      <div className="dashboard-chart-heading">
        <span>文件类型分布</span>
        <small>类型与资料联动</small>
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
        <small>类型与记录联动</small>
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

