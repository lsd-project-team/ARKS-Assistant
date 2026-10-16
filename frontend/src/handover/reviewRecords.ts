import type { Event, HandoverRecord } from './types';
import { canReviewRecord } from './reviewPolicy.ts';

export const reviewCategories = [
  { id: 'all', label: '全部' },
  { id: 'source', label: '资料' },
  { id: 'interview', label: '访谈' },
  { id: 'package', label: '交接包' },
  { id: 'other', label: '其他记录' },
] as const;
export type ReviewCategory = (typeof reviewCategories)[number]['id'];

function categoryOf(row: HandoverRecord): ReviewCategory {
  if (row.kind === 'source' || row.kind === 'interview' || row.kind === 'package') return row.kind;
  return 'other';
}

export function pendingReviewRows(rows: HandoverRecord[]) {
  // 统一入口同时处理首次确认与重新复核，工作和 AI 记录仍使用各自的流程。
  return rows.filter((row) => canReviewRecord(row));
}

export function reviewCounts(rows: HandoverRecord[]): Record<ReviewCategory, number> {
  const counts = { all: 0, source: 0, interview: 0, package: 0, other: 0 };
  for (const row of pendingReviewRows(rows)) {
    counts.all += 1;
    counts[categoryOf(row)] += 1;
  }
  return counts;
}

export function selectReviewRows(rows: HandoverRecord[], category: ReviewCategory) {
  return pendingReviewRows(rows).filter(
    (row) => category === 'all' || categoryOf(row) === category,
  );
}

export function reviewReason(row: HandoverRecord, events: Event[], rows: HandoverRecord[]) {
  if (row.state !== 'needs_review') return '';
  // 日志接口只返回最近操作，只匹配当前版本，避免将历史失效原因套用到新版本。
  const event = events.reduce<Event | undefined>((latest, item) => {
    if (
      item.record_id !== row.id ||
      item.version !== row.version ||
      !['updated', 'invalidated', 'restore'].includes(item.action)
    )
      return latest;
    return !latest || item.id > latest.id ? item : latest;
  }, undefined);
  if (!event) return '未读取到当前版本的复核原因，请查看修改记录。';
  const detail = event.detail.trim().replace(/影响来源 ([\w-]+)/g, (match, identifier: string) => {
    const source = rows.find((item) => item.id === identifier);
    return source ? `影响来源「${source.title}」` : match;
  });
  if (event.action === 'restore')
    return `归档记录已恢复${detail ? `：${detail}` : '，需要重新复核。'}`;
  if (event.action === 'updated')
    return `本记录内容已修改${detail ? `：${detail}` : '，需要重新复核。'}`;
  return detail || '关联内容已变化，需要重新复核。';
}
