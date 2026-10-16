import { useState } from 'react';
import {
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  FileText,
  MessageSquare,
  CircleDot,
} from 'lucide-react';
import { Status } from './RecordView';
import { eventActionLabels } from './overviewData';
import { localTime } from './format';
import { text, type Definitions, type Event, type HandoverRecord } from './types';

export function compactTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      });
}

function useListPage<T>(items: T[], size: number) {
  const [page, setPage] = useState(0);
  const current = Math.min(page, Math.max(0, Math.ceil(items.length / size) - 1));
  return { rows: items.slice(current * size, (current + 1) * size), page: current, setPage };
}

function ListPager({
  total,
  page,
  size,
  onPage,
  label,
}: {
  total: number;
  page: number;
  size: number;
  onPage: (page: number) => void;
  label: string;
}) {
  if (total <= size) return null;
  return (
    <div className="dashboard-list-pager" role="group" aria-label={label + '分页'}>
      <span>
        {page * size + 1}–{Math.min((page + 1) * size, total)} / {total}
      </span>
      <div>
        <button disabled={!page} onClick={() => onPage(page - 1)} aria-label={'上一页' + label}>
          <ChevronLeft size={13} />
        </button>
        <button
          disabled={(page + 1) * size >= total}
          onClick={() => onPage(page + 1)}
          aria-label={'下一页' + label}
        >
          <ChevronRight size={13} />
        </button>
      </div>
    </div>
  );
}

export function SelectionHeading({
  label,
  count,
  filtered,
  onReset,
}: {
  label: string;
  count: number;
  filtered?: boolean;
  onReset?: () => void;
}) {
  return (
    <div className="dashboard-selection-heading">
      <h3>
        {label}
        <span aria-live="polite">{count}</span>
      </h3>
      {filtered && <button onClick={onReset}>清除筛选</button>}
    </div>
  );
}

export function DashboardRecordList({
  rows,
  definitions,
  onOpen,
  empty,
  limit = 2,
}: {
  rows: HandoverRecord[];
  definitions: Definitions;
  onOpen: (id: string) => void;
  empty: string;
  limit?: number;
}) {
  const pagination = useListPage(rows, limit);
  return (
    <div className="dashboard-record-list">
      {pagination.rows.map((row) => (
        <button
          key={row.id}
          className="dashboard-record-row"
          onClick={() => onOpen(row.id)}
          aria-label={'查看记录：' + row.title}
        >
          <span className="dashboard-record-icon">
            {row.kind === 'interview' ? (
              <MessageSquare size={15} />
            ) : row.kind === 'task' ? (
              <CircleDot size={15} />
            ) : (
              <FileText size={15} />
            )}
          </span>
          <div>
            <strong title={row.title}>{row.title}</strong>
            <span>
              {row.kind === 'task'
                ? text(row.payload.owner) || '未指定负责人'
                : definitions.kinds[row.kind]}
              <i>·</i>
              <time dateTime={row.updated_at} title={localTime(row.updated_at)}>
                {compactTime(row.updated_at)}
              </time>
            </span>
          </div>
          <Status row={row} definitions={definitions} />
          <ArrowUpRight className="dashboard-row-arrow" size={14} />
        </button>
      ))}
      {!rows.length && <p className="dashboard-empty">{empty}</p>}
      <ListPager
        total={rows.length}
        page={pagination.page}
        size={limit}
        onPage={pagination.setPage}
        label="记录"
      />
    </div>
  );
}

export function DashboardEventList({
  events,
  records,
  onOpen,
}: {
  events: Event[];
  records: HandoverRecord[];
  onOpen: (id: string, version?: number) => void;
}) {
  const titles = new Map(records.map((row) => [row.id, row.title]));
  const pagination = useListPage(events, 2);
  return (
    <div className="dashboard-event-list">
      {pagination.rows.map((event) => (
        <button
          key={event.id}
          className="dashboard-event-row"
          onClick={() => onOpen(event.record_id, event.version)}
          aria-label={
            '查看历史：' + (titles.get(event.record_id) || '交接记录') + '，v' + event.version
          }
          title={event.detail}
        >
          <i
            className={
              'dashboard-event-dot ' +
              (event.action === 'invalidated' ? 'dashboard-dot-warning' : 'dashboard-dot-green')
            }
          />
          <div>
            <span className="dashboard-event-meta">
              {eventActionLabels[event.action] || event.action}
              <time dateTime={event.created_at}>{compactTime(event.created_at)}</time>
            </span>
            <strong>{titles.get(event.record_id) || '交接记录'}</strong>
            <small>
              {event.actor || '未记录操作人'}
              <i>·</i>v{event.version}
            </small>
          </div>
          <ArrowUpRight size={14} />
        </button>
      ))}
      {!events.length && <p className="dashboard-empty">此筛选范围暂无操作记录</p>}
      <ListPager
        total={events.length}
        page={pagination.page}
        size={2}
        onPage={pagination.setPage}
        label="日志"
      />
    </div>
  );
}
