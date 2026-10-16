import type { HandoverRecord } from './types';
import { taskStage, taskStageLabel } from './taskProgress';

export function TaskStatus({ row }: { row: HandoverRecord }) {
  return (
    <span className={`task-status task-status-${taskStage(row.payload)}`}>
      {taskStageLabel(row.payload)}
    </span>
  );
}
