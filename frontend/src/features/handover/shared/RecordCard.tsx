import { TaskStatus } from '../tasks/TaskStatus';
import type { Definitions, HandoverRecord } from './types';
import { text } from './types';
import { debugStatus } from '../debug_issues/debugIssues';

export function Status({ row, definitions }: { row: HandoverRecord; definitions: Definitions }) {
  if (row.kind === 'task') return <TaskStatus row={row} />;
  if (row.kind === 'debug_issue')
    return <span className="debug-status">{debugStatus(row.payload)}</span>;
  return (
    <span className={`handover-status handover-status-${row.state}`}>
      {definitions.states[row.state]}
    </span>
  );
}

export function RecordCard({
  row,
  definitions,
  onOpen,
  compact = false,
  reviewReason,
}: {
  row: HandoverRecord;
  definitions: Definitions;
  onOpen: (id: string) => void;
  compact?: boolean;
  reviewReason?: string;
}) {
  return (
    <button
      className={`handover-record-card${compact ? ' handover-record-compact' : ''}`}
      onClick={() => onOpen(row.id)}
    >
      <div>
        <span className="handover-eyebrow">
          {definitions.kinds[row.kind]}
          {!['debug_issue', 'package'].includes(row.kind) && ` · v${row.version}`}
        </span>
        <Status row={row} definitions={definitions} />
      </div>
      <strong>{row.title}</strong>
      <p>
        {text(
          row.payload.goal ||
            row.payload.question ||
            row.payload.intent ||
            row.payload.condition ||
            row.payload.scope ||
            row.payload.topic ||
            row.payload.parse_notes ||
            row.payload.prerequisites ||
            row.payload.operation ||
            row.payload.understanding,
        ) || '打开查看内容与来源'}
      </p>
      {reviewReason && (
        <span className="handover-review-reason">
          <b>复核原因</b>
          {reviewReason}
        </span>
      )}
      <small>
        {text(
          row.payload.owner || row.payload.author || row.payload.receiver || row.payload.provider,
        ) || '未指定负责人'}{' '}
        · {row.updated_at.slice(0, 10)}
      </small>
    </button>
  );
}
