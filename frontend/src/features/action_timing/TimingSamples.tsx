import { Button } from '../../shared/ui/ui';
import { branchLabel, eventDuration, milliseconds, statusLabels } from './format';
import type { TimingAction, TimingEvent } from './types';

export function TimingSamples({
  actions = [],
  samples,
  action,
  status,
  offset,
  setAction,
  setStatus,
  setOffset,
  setDetail,
}: {
  actions?: TimingAction[];
  samples?: { items: TimingEvent[]; total: number };
  action: string;
  status: string;
  offset: number;
  setAction: (value: string) => void;
  setStatus: (value: string) => void;
  setOffset: (value: number) => void;
  setDetail: (value: string) => void;
}) {
  return (
    <>
      <div className="timing-section-heading">
        <h2>调用明细</h2>
        <div>
          <select
            aria-label="筛选动作"
            value={action}
            onChange={(event) => setAction(event.target.value)}
          >
            <option value="">全部动作</option>
            {actions.map((row) => (
              <option key={row.code} value={row.code}>
                {row.name}
              </option>
            ))}
          </select>
          <select
            aria-label="筛选结果"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="">全部结果</option>
            {Object.entries(statusLabels).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="timing-table-wrap">
        <table className="timing-table">
          <thead>
            <tr>
              {['动作', '目标 / 工序', '分支', '耗时 ms', '结果', '详情'].map((label) => (
                <th key={label}>{label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {samples?.items.map((row) => (
              <tr key={row.event_id}>
                <td>
                  {actions.find((item) => item.code === row.action_code)?.name || row.action_code}
                </td>
                <td>
                  {row.context.bond_position || '—'}
                  <small>{row.context.process_step || '—'}</small>
                </td>
                <td>{branchLabel(row.branch)}</td>
                <td>{milliseconds(eventDuration(row))}</td>
                <td>
                  <span className={`timing-status ${row.status}`}>{statusLabels[row.status]}</span>
                </td>
                <td>
                  <Button onClick={() => setDetail(row.event_id)}>查看阶段</Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {samples?.total === 0 && <p className="timing-caption">当前筛选条件下没有调用记录。</p>}
      </div>
      <div className="timing-pagination">
        <span>
          共 {samples?.total || 0} 条调用 · 第 {Math.floor(offset / 25) + 1} 页
        </span>
        <Button disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 25))}>
          上一页
        </Button>
        <Button
          disabled={offset + 25 >= (samples?.total || 0)}
          onClick={() => setOffset(offset + 25)}
        >
          下一页
        </Button>
      </div>
    </>
  );
}
