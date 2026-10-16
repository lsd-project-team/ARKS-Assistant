import { Button } from '../../../shared/ui/ui';
import { localTime } from '../shared/format';
import { EmptyState } from '../shared/Presentation';
import type { Definitions, Event, HandoverRecord } from '../shared/types';
import { ReviewQueue } from './ReviewQueue';

const actionLabels: Record<string, string> = {
  created: '新增',
  updated: '修改',
  confirm: '人工确认',
  reject: '审核拒绝',
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
      <ReviewQueue rows={rows} events={events} definitions={definitions} onOpen={onOpen} />
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
        {!events.length && (
          <EmptyState title="尚无操作记录">
            新增、修改与人工确认后，记录会按时间排列在这里。
          </EmptyState>
        )}
      </section>
    </>
  );
}
