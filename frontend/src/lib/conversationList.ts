export function conversationGroup(
  thread: { pinned_order?: number | null; updated_at: string },
  now = new Date(),
) {
  if (thread.pinned_order !== null && thread.pinned_order !== undefined) return '置顶';
  const date = new Date(thread.updated_at);
  const midnight = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (date >= midnight) return '今天';
  const yesterday = new Date(midnight);
  yesterday.setDate(yesterday.getDate() - 1);
  if (date >= yesterday) return '昨天';
  const week = new Date(midnight);
  week.setDate(week.getDate() - 7);
  return date >= week ? '最近七天' : '更早';
}

export function threadStatus(status?: string | null) {
  return status === 'queued'
    ? '排队中'
    : status === 'running'
      ? '正在回复'
      : status === 'failed'
        ? '回复失败'
        : '';
}
