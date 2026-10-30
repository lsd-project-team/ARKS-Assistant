import type { SourceEvidence } from '../../../shared/types/api.ts';
import type { SourcePointer } from './types.ts';

export function resolveSourceEvidence(
  source: SourcePointer,
  evidence: SourceEvidence[],
  defaultSourceId?: string,
) {
  const end = source.end_line ?? source.start_line;
  const addressed = source.path.match(/^@sources\/([\w-]+)\//)?.[1];
  const identity = source.source_workspace_id || addressed || defaultSourceId;
  if (addressed && source.source_workspace_id && addressed !== source.source_workspace_id)
    return { reason: '引用的源码目录身份不一致' };
  const candidates = evidence.filter(
    (row) =>
      row.path === source.path &&
      row.start_line <= end &&
      row.end_line >= source.start_line &&
      (!source.version || row.version === source.version) &&
      (!identity || (row.source_workspace_id || addressed || defaultSourceId) === identity),
  );
  const groups = new Map<string, SourceEvidence[]>();
  for (const row of candidates) {
    const key = JSON.stringify([row.source_workspace_id || identity, row.version]);
    groups.set(key, [...(groups.get(key) || []), row]);
  }
  // 与后端一致：同一源码版本的连续分段可合并，缺行或跨版本不得拼接。
  const covered = [...groups.values()].filter((rows) => {
    let cursor = source.start_line;
    for (const row of [...rows].sort((a, b) => a.start_line - b.start_line)) {
      if (row.start_line > cursor) return false;
      cursor = Math.max(cursor, row.end_line + 1);
      if (cursor > end) return true;
    }
    return false;
  });
  if (!covered.length) return { reason: '本轮没有匹配路径、版本和范围的源码证据' };
  if (covered.length > 1) return { reason: '引用对应多个源码版本，请核对版本后重试' };
  const rows = covered[0];
  const matched = rows.find((row) => row.current_status !== 'match') || rows.at(-1)!;
  if (matched.current_status === 'changed')
    return { reason: '源码版本已变化，原引用需要重新核对', evidence: matched };
  if (matched.current_status !== 'match')
    return { reason: '原始源码当前不可读取', evidence: matched };
  return { evidence: matched, reason: undefined };
}
