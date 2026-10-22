import type { TimingEvent } from './types.ts';

export const statusLabels = {
  success: '成功',
  failed: '失败',
  aborted: '中止',
  retry: '重试',
  skipped: '调度跳过',
  noop: '未进入工作阶段',
  incomplete: '未完成',
};
export function milliseconds(value: number | null | undefined) {
  return value == null || !Number.isFinite(value)
    ? '—'
    : value.toLocaleString('zh-CN', { maximumFractionDigits: 3 });
}
export function eventDuration(event: Pick<TimingEvent, 'start_ms' | 'end_ms'>) {
  return event.end_ms === null ? null : event.end_ms - event.start_ms;
}
export function branchLabel(branch: string) {
  const known: Record<string, string> = {
    drycycle: '空跑',
    'drycycle.s1.vision': '空跑定位',
    'drycycle.s1.dispense': '空跑点胶',
    'drycycle.uplook.one_point': '空跑 · 一点上视',
    'drycycle.uplook.two_point': '空跑 · 两点上视',
    'drycycle.bond': '空跑固晶',
    'drycycle.collector_test': '采集器测试分支',
  };
  return known[branch] || branch.replace('drycycle.pick.', '空跑取片 · ');
}
export function knownDelay(row: {
  known_delay_min_ms: number | null;
  known_delay_max_ms: number | null;
}) {
  const low = row.known_delay_min_ms;
  const high = row.known_delay_max_ms;
  if (low == null) return '未定';
  if (high == null) return low ? `至少 ${low} ms` : '次数 / 参数未定';
  if (low === 0 && high === 0) return '无显式延时';
  return low === high ? `${low} ms` : `${low}–${high} ms`;
}
