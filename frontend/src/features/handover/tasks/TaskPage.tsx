import { useState } from 'react';
import { ErrorText, Button } from '../../../shared/ui/ui';
import { HandoverSelect } from '../shared/Controls';
import { EmptyState } from '../shared/Presentation';
import { localTime } from '../shared/format';
import { text, type HandoverRecord } from '../shared/types';
import {
  taskCounts,
  taskRows,
  taskSearch,
  taskStage,
  taskStages,
  type TaskStage,
} from './taskProgress';
import { TaskStatus } from './TaskStatus';
import './task-progress.css';

export function TaskPage({
  rows,
  archived,
  onOpen,
  onStatusChange,
}: {
  rows: HandoverRecord[];
  archived: boolean;
  onOpen: (id: string) => void;
  onStatusChange: (row: HandoverRecord, status: TaskStage) => Promise<void>;
}) {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [mode, setMode] = useState('list');
  const [busy, setBusy] = useState<string[]>([]);
  const [error, setError] = useState<unknown>();
  const tasks = taskRows(rows);
  const counts = taskCounts(tasks);
  const filtered = tasks.filter(
    (row) => taskSearch(row, search) && (!status || taskStage(row.payload) === status),
  );
  async function updateStatus(row: HandoverRecord, next: string) {
    if (next === taskStage(row.payload)) return;
    setError(undefined);
    setBusy((ids) => [...ids, row.id]);
    try {
      await onStatusChange(row, next as TaskStage);
    } catch (error) {
      setError(error);
    } finally {
      setBusy((ids) => ids.filter((id) => id !== row.id));
    }
  }
  return (
    <section className="task-progress" aria-label="工作项统计">
      <div className="task-metrics">
        {[
          { value: '', label: archived ? '归档工作总数' : '工作总数', count: counts.total },
          ...taskStages.map((stage) => ({ ...stage, count: counts[stage.value] })),
        ].map((item) => (
          <button
            key={item.value}
            aria-pressed={status === item.value}
            onClick={() => setStatus(item.value)}
          >
            <span>{item.label}</span>
            <strong>{item.count}</strong>
          </button>
        ))}
      </div>
      <div className="handover-toolbar task-toolbar" role="search" aria-label="筛选工作项">
        <input
          aria-label="搜索工作项"
          placeholder="搜索工作名称、负责人或备注"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <HandoverSelect
          label="筛选工作状态"
          value={status}
          onValueChange={setStatus}
          options={[{ value: '', label: '所有状态' }, ...taskStages]}
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
      <ErrorText error={error} reveal />
      <p className="handover-result-count">
        {archived ? '归档工作' : '工作项'} {tasks.length} 项
        {filtered.length !== tasks.length ? ` · 当前显示 ${filtered.length} 项` : ''}
      </p>
      {mode === 'board' ? (
        <div className="task-board">
          {taskStages.map((stage) => (
            <section key={stage.value}>
              <h3>
                {stage.label}
                <span>
                  {filtered.filter((row) => taskStage(row.payload) === stage.value).length}
                </span>
              </h3>
              {filtered
                .filter((row) => taskStage(row.payload) === stage.value)
                .map((row) => (
                  <button className="task-board-card" key={row.id} onClick={() => onOpen(row.id)}>
                    <strong>{row.title}</strong>
                    <span>{text(row.payload.owner) || '未指定负责人'}</span>
                    <time dateTime={row.updated_at}>{localTime(row.updated_at)}</time>
                  </button>
                ))}
              {!filtered.some((row) => taskStage(row.payload) === stage.value) && (
                <p className="handover-board-empty">暂无工作</p>
              )}
            </section>
          ))}
        </div>
      ) : (
        <div className="handover-table-wrap">
          <table className="handover-task-table task-table">
            <thead>
              <tr>
                <th>工作名称</th>
                <th>负责人</th>
                <th>状态</th>
                <th>更新时间</th>
              </tr>
            </thead>
            <tbody>
              {!filtered.length && (
                <tr>
                  <td colSpan={4}>
                    <EmptyState title={tasks.length ? '未找到符合条件的工作' : '暂无工作项'}>
                      {tasks.length
                        ? '调整搜索内容或状态筛选。'
                        : archived
                          ? '归档后的工作会显示在这里。'
                          : '点击「新增工作」，填写名称即可开始记录。'}
                    </EmptyState>
                  </td>
                </tr>
              )}
              {filtered.map((row) => (
                <tr key={row.id}>
                  <td>
                    <button onClick={() => onOpen(row.id)}>{row.title}</button>
                    {text(row.payload.notes) && (
                      <small className="task-note-preview" title={text(row.payload.notes)}>
                        {text(row.payload.notes)}
                      </small>
                    )}
                  </td>
                  <td>{text(row.payload.owner) || '未指定'}</td>
                  <td>
                    {archived ? (
                      <TaskStatus row={row} />
                    ) : (
                      <HandoverSelect
                        label={`更新工作状态：${row.title}`}
                        value={taskStage(row.payload)}
                        onValueChange={(next) => void updateStatus(row, next)}
                        options={[...taskStages]}
                        disabled={busy.includes(row.id)}
                      />
                    )}
                  </td>
                  <td>
                    <time dateTime={row.updated_at}>{localTime(row.updated_at)}</time>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
