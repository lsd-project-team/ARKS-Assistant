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
      row.start_line <= source.start_line &&
      row.end_line >= end &&
      (!source.version || row.version === source.version) &&
      (!identity || (row.source_workspace_id || addressed || defaultSourceId) === identity),
  );
  if (!candidates.length) return { reason: '本轮没有匹配路径、版本和范围的源码证据' };
  if (
    new Set(candidates.map((row) => `${row.source_workspace_id || identity}:${row.version}`)).size >
    1
  )
    return { reason: '引用对应多个源码版本，请核对版本后重试' };
  const matched = candidates.at(-1)!;
  if (matched.current_status === 'changed')
    return { reason: '源码版本已变化，原引用需要重新核对', evidence: matched };
  if (matched.current_status !== 'match')
    return { reason: '原始源码当前不可读取', evidence: matched };
  return { evidence: matched, reason: undefined };
}
