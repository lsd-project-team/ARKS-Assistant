import { useState } from 'react';
import { Button } from '../components/ui';
import { HandoverSelect } from './Controls';
import { RecordCard } from './RecordView';
import type { Definitions, Event, HandoverRecord, Kind, Overview, Payload, Tab } from './types';
import { text } from './types';
import { localTime } from './format';
import { effectiveWorkStatus, workStatusLabel } from './workStatus';

export function OverviewPage({
  overview,
  definitions,
  onOpen,
  onNavigate,
  onNew,
  onImport,
  onKnowledge,
  knowledgeAvailable,
  readOnly = false,
}: {
  overview: Overview;
  definitions: Definitions;
  onOpen: (id: string) => void;
  onNavigate: (tab: Tab) => void;
  onNew: (kind: Kind, initial?: Payload) => void;
  onImport: () => void;
  onKnowledge: (kind: 'graphs' | 'modules') => void;
  knowledgeAvailable: boolean;
  readOnly?: boolean;
}) {
  const active = overview.records.filter(
    (row) => row.state !== 'archived' && !['job', 'candidate'].includes(row.kind),
  );
  const tasks = active.filter((row) => row.kind === 'task');
  const blocked = tasks.filter((row) => overview.blocks[row.id]?.length);
  const pending = active.filter((row) => row.state !== 'confirmed');
  const baseline = active.filter((row) => row.kind === 'baseline');
  return (
    <>
      <div className="handover-metrics">
        {[
          [
            '未完成工作',
            tasks.filter((row) => effectiveWorkStatus(row) !== 'accepted').length,
            'tasks',
          ],
          ['接续阻塞', blocked.length, 'tasks'],
          ['待人工复核', pending.length, 'updates'],
          ['已确认记录', active.length - pending.length, 'updates'],
        ].map(([label, count, tab]) => (
          <button key={label} onClick={() => onNavigate(tab as Tab)}>
            <span>{label}</span>
            <strong>{count}</strong>
          </button>
        ))}
      </div>
      {!active.length && !readOnly && (
        <section className="handover-onboarding">
          <span className="handover-eyebrow">建立第一份交接记录</span>
          <h2>从原始资料和原作者说明开始</h2>
          <p>
            先固定软件版本与设备环境，再整理未完成工作、设计意图和约束，最后形成可执行的接续计划。
          </p>
          <div className="handover-actions">
            <Button className="primary" onClick={onImport}>
              添加交接资料
            </Button>
            <Button onClick={() => onNew('interview')}>记录原作者访谈</Button>
          </div>
        </section>
      )}
      <div className="handover-overview-grid">
        <section className="handover-panel">
          <header>
            <div>
              <h2>优先接续的工作</h2>
              <p>根据阻塞和优先级整理</p>
            </div>
            <Button onClick={() => onNavigate('tasks')}>查看全部</Button>
          </header>
          {[...tasks]
            .sort(
              (a, b) =>
                Number(!!overview.blocks[b.id]?.length) - Number(!!overview.blocks[a.id]?.length) ||
                ['critical', 'high', 'normal', 'low'].indexOf(text(a.payload.priority)) -
                  ['critical', 'high', 'normal', 'low'].indexOf(text(b.payload.priority)),
            )
            .slice(0, 5)
            .map((row) => (
              <div className="handover-priority-row" key={row.id}>
                <RecordCard row={row} definitions={definitions} onOpen={onOpen} />
                {overview.blocks[row.id]?.length > 0 && (
                  <small className="handover-risk-text">{overview.blocks[row.id][0]}</small>
                )}
              </div>
            ))}
          {!tasks.length && (
            <p className="handover-empty">暂无工作项。可以手动新增，也可以审核 AI 提取的候选。</p>
          )}
          <Button disabled={readOnly} onClick={() => onNew('task')}>
            新增未完成工作
          </Button>
        </section>
        <section className="handover-panel">
          <header>
            <div>
              <h2>源码基线与接收环境</h2>
              <p>明确代码版本与设备条件</p>
            </div>
            <Button disabled={readOnly} onClick={() => onNew('baseline')}>
              添加基线
            </Button>
          </header>
          {baseline.map((row) => (
            <RecordCard key={row.id} row={row} definitions={definitions} onOpen={onOpen} />
          ))}
          {!baseline.length && (
            <p className="handover-empty">
              尚未建立基线。版本、固件、SDK、配方、标定和构建环境应在接续前核对。
            </p>
          )}
          <h3>框架与功能培训</h3>
          <p className="handover-muted">
            补齐入口、模块职责、运行条件、时序和异常恢复，并记录覆盖范围及确认结果。
          </p>
          {knowledgeAvailable && (
            <div className="handover-actions">
              <Button onClick={() => onKnowledge('graphs')}>打开现有流程图谱</Button>
              <Button onClick={() => onKnowledge('modules')}>打开现有功能说明</Button>
            </div>
          )}
          <div className="handover-actions">
            <Button disabled={readOnly} onClick={() => onNew('framework')}>
              补充框架说明
            </Button>
            <Button disabled={readOnly} onClick={() => onNew('training')}>
              补充培训内容
            </Button>
          </div>
        </section>
      </div>
      <section className="handover-panel">
        <h2>交接进度</h2>
        <div className="handover-coverage">
          {(
            [
              'source',
              'interview',
              'framework',
              'training',
              'task',
              'decision',
              'constraint',
              'baseline',
              'verification',
              'issue',
              'plan',
              'receipt',
            ] as Kind[]
          ).map((kind) => {
            const rows = active.filter((row) => row.kind === kind);
            return (
              <div key={kind}>
                <strong>{definitions.kinds[kind]}</strong>
                <span>
                  {rows.filter((row) => row.state === 'confirmed').length} / {rows.length} 已确认
                </span>
                <small>{rows.length ? '逐条核对内容与证据' : '尚无记录，需核对是否适用'}</small>
              </div>
            );
          })}
        </div>
      </section>
    </>
  );
}

export function TaskPage({
  rows,
  definitions,
  blocks,
  onOpen,
}: {
  rows: HandoverRecord[];
  definitions: Definitions;
  blocks: Overview['blocks'];
  onOpen: (id: string) => void;
}) {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [category, setCategory] = useState('');
  const [mode, setMode] = useState('list');
  const statuses = ['todo', 'doing', 'blocked', 'done', 'accepted'];
  const filtered = rows.filter(
    (row) =>
      row.kind === 'task' &&
      `${row.title} ${text(row.payload.goal)} ${text(row.payload.owner)}`
        .toLowerCase()
        .includes(search.toLowerCase()) &&
      (!status || effectiveWorkStatus(row) === status) &&
      (!category || row.payload.category === category),
  );
  return (
    <>
      <div className="handover-toolbar">
        <input
          aria-label="搜索未完成工作"
          placeholder="搜索标题、目标、负责人"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <HandoverSelect
          label="工作状态"
          value={status}
          onValueChange={setStatus}
          options={[
            { value: '', label: '所有工作状态' },
            ...statuses.map((value) => ({ value, label: definitions.values[value] })),
          ]}
        />
        <HandoverSelect
          label="工作类别"
          value={category}
          onValueChange={setCategory}
          options={[
            { value: '', label: '所有类别' },
            ...['feature', 'bug', 'untested', 'site'].map((value) => ({
              value,
              label: definitions.values[value],
            })),
          ]}
        />
        <div className="handover-view-switch" aria-label="工作视图">
          <Button aria-pressed={mode === 'list'} onClick={() => setMode('list')}>
            列表
          </Button>
          <Button aria-pressed={mode === 'board'} onClick={() => setMode('board')}>
            看板
          </Button>
        </div>
      </div>
      {mode === 'board' ? (
        <div className="handover-board">
          {statuses.map((status) => (
            <section key={status}>
              <h3>
                {definitions.values[status]}{' '}
                <span>{filtered.filter((row) => effectiveWorkStatus(row) === status).length}</span>
              </h3>
              {filtered
                .filter((row) => effectiveWorkStatus(row) === status)
                .map((row) => (
                  <RecordCard key={row.id} row={row} definitions={definitions} onOpen={onOpen} />
                ))}
            </section>
          ))}
        </div>
      ) : (
        <div className="handover-table-wrap">
          <table className="handover-task-table">
            <thead>
              <tr>
                <th>工作项</th>
                <th>工作状态</th>
                <th>证据状态</th>
                <th>负责人</th>
                <th>接续条件</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => (
                <tr key={row.id}>
                  <td>
                    <button onClick={() => onOpen(row.id)}>{row.title}</button>
                    <small>
                      {definitions.values[text(row.payload.category)]} ·{' '}
                      {definitions.values[text(row.payload.priority)]} ·{' '}
                      {definitions.states[row.state]}
                    </small>
                  </td>
                  <td>{workStatusLabel(row, definitions.values)}</td>
                  <td>{definitions.values[text(row.payload.evidence_status)]}</td>
                  <td>{text(row.payload.owner) || '未指定'}</td>
                  <td className={blocks[row.id]?.length ? 'handover-risk-text' : ''}>
                    {blocks[row.id]?.[0] || '请核对详情与证据'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!filtered.length && <p className="handover-empty">暂无符合条件的工作项。</p>}
    </>
  );
}

const actionLabels: Record<string, string> = {
  created: '新增',
  updated: '修改',
  confirm: '人工确认',
  invalidated: '需要重新复核',
  archive: '归档',
  restore: '恢复',
  merged: '审核合并',
  promoted: '候选已合并',
};
export function ActivityPage({
  events,
  rows,
  definitions,
  onOpen,
}: {
  events: Event[];
  rows: HandoverRecord[];
  definitions: Definitions;
  onOpen: (id: string, version?: number) => void;
}) {
  return (
    <>
      <section className="handover-panel">
        <h2>需要重新复核</h2>
        <div className="handover-cards">
          {rows
            .filter((row) => row.state === 'needs_review')
            .map((row) => (
              <RecordCard key={row.id} row={row} definitions={definitions} onOpen={onOpen} />
            ))}
        </div>
        {!rows.some((row) => row.state === 'needs_review') && (
          <p className="handover-empty">暂无因更新而需要重新复核的记录。</p>
        )}
      </section>
      <section className="handover-panel">
        <h2>修改与确认记录</h2>
        <ol className="handover-timeline">
          {events.map((event) => (
            <li key={event.id}>
              <div>
                <strong>{actionLabels[event.action] || event.action}</strong>
                <time>{localTime(event.created_at)}</time>
              </div>
              <Button onClick={() => onOpen(event.record_id, event.version)}>
                {rows.find((row) => row.id === event.record_id)?.title || '交接记录'} · v
                {event.version}
              </Button>
              <p>{event.detail}</p>
              <small>{event.actor}</small>
            </li>
          ))}
        </ol>
        {!events.length && <p className="handover-empty">尚无交接操作记录。</p>}
      </section>
    </>
  );
}
