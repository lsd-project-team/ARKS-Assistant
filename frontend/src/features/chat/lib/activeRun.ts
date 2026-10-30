import type { Conversation, Run } from '../../../shared/types/api.ts';

export function activeRun(
  started: Run | undefined,
  conversation: Conversation | undefined,
  threadId: string,
) {
  const latest = conversation?.runs.at(-1);
  const pending = latest && ['queued', 'running'].includes(latest.status) ? latest : undefined;
  // 只在首次 HTTP 响应尚未进入查询缓存时使用临时运行，不能覆盖后续出队的运行。
  if (
    started?.thread_id === threadId &&
    ['queued', 'running'].includes(started.status) &&
    !conversation?.runs.some((run) => run.id === started.id)
  )
    return started;
  return pending;
}
