import type { SourceEvidence } from '../../../shared/types/api';

export function citationEndLine(
  path: string,
  start: number,
  explicitEnd: string | undefined,
  label: string,
  evidence: SourceEvidence[],
) {
  if (explicitEnd) return Number(explicitEnd);
  const shown = label.trim().match(/^([^/\\:]+):(\d+)[-–](\d+)$/);
  const end = Number(shown?.[3]);
  // 旧回复可能只写起始锚点；只有同名、同起点且已有读取证据覆盖时才恢复标签中的范围。
  if (
    shown &&
    shown[1] === path.split('/').at(-1) &&
    Number(shown[2]) === start &&
    Number.isSafeInteger(end) &&
    end >= start &&
    evidence.some((row) => row.path === path && row.start_line <= start && row.end_line >= end)
  )
    return end;
  return start;
}
