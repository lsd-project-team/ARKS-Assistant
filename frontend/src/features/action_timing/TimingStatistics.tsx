import { branchLabel, milliseconds, statusLabels } from './format';
import type { TimingRow } from './types';

function ActionRow({ row, onSelect }: { row: TimingRow; onSelect: () => void }) {
  return (
    <tr>
      <td>
        <button className="timing-action-link" onClick={onSelect}>
          {row.name}
        </button>
        <small>{row.class_name}</small>
        {(row.branches.length > 0 || row.stages.length > 0) && (
          <details className="timing-breakdown">
            <summary>分支与阶段</summary>
            {row.branches.map((branch) => (
              <p key={branch.branch}>
                {branchLabel(branch.branch)}：{branch.valid_count} 次有效 · 平均{' '}
                {milliseconds(branch.mean_ms)} ms
              </p>
            ))}
            {row.stages.map((stage, index) => (
              <p key={index}>
                {stage.stage}：{milliseconds(stage.mean_ms)} ms{' '}
                <small>{branchLabel(stage.branch)}</small>
              </p>
            ))}
          </details>
        )}
      </td>
      <td>{row.count}</td>
      <td>{row.valid_count}</td>
      <td>{row.branches.length > 1 ? '按分支查看' : milliseconds(row.mean_ms)}</td>
      <td>{row.branches.length > 1 ? '—' : milliseconds(row.min_ms)}</td>
      <td>{row.branches.length > 1 ? '—' : milliseconds(row.max_ms)}</td>
      <td>{row.branches.length > 1 ? '—' : milliseconds(row.p50_ms)}</td>
      <td>{row.branches.length > 1 ? '—' : milliseconds(row.p95_ms)}</td>
      <td>
        <span className={`timing-status ${row.valid_count ? 'success' : 'noop'}`}>
          {row.valid_count ? '有有效样本' : row.count ? '无有效样本' : '未采样'}
        </span>
        {Object.entries(row.statuses)
          .filter(([key]) => key !== 'success')
          .map(([key, value]) => (
            <small key={key}>
              {statusLabels[key as keyof typeof statusLabels]} {value}
            </small>
          ))}
      </td>
    </tr>
  );
}

export function TimingStatistics({
  rows,
  onSelect,
}: {
  rows: TimingRow[];
  onSelect: (code: string) => void;
}) {
  return (
    <div className="timing-table-wrap">
      <table className="timing-table">
        <thead>
          <tr>
            {['动作', '调用', '有效', '平均', '最小', '最大', 'P50', 'P95', '采样状态'].map(
              (label) => (
                <th key={label}>{label}</th>
              ),
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <ActionRow key={row.code} row={row} onSelect={() => onSelect(row.code)} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
