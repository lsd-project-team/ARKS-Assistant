import type { ToolEvent } from '../../../shared/types/api.ts';

export function toolState(tool: ToolEvent) {
  if (tool.execution_status === 'skipped' || tool.result?.startsWith('本轮检索预算已用尽'))
    return 'skipped';
  if (tool.status === 'error') return 'failed';
  return tool.result === undefined ? 'pending' : 'success';
}

export function toolCounts(tools: ToolEvent[]) {
  const result = {
    attempted: tools.length,
    success: 0,
    skipped: 0,
    failed: 0,
    pending: 0,
    cached: 0,
  };
  for (const tool of tools) {
    result[toolState(tool)] += 1;
    if (tool.cached) result.cached += 1;
  }
  return result;
}

export function toolSummary(tools: ToolEvent[]) {
  const counts = toolCounts(tools);
  return [
    `成功 ${counts.success}`,
    counts.skipped ? `未执行 ${counts.skipped}` : '',
    counts.failed ? `失败 ${counts.failed}` : '',
    counts.pending ? `进行中 ${counts.pending}` : '',
    counts.cached ? `复用 ${counts.cached}` : '',
  ]
    .filter(Boolean)
    .join(' · ');
}
