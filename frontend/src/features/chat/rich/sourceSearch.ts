import type { SourceEvidence, ToolEvent } from '../../../shared/types/api.ts';
import type { SourcePointer } from './types.ts';
import { resolveSourceEvidence } from './sourceEvidence.ts';

function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function searchHit(source: SourcePointer, tools: ToolEvent[]) {
  const end = source.end_line ?? source.start_line;
  if (
    !Number.isSafeInteger(source.start_line) ||
    !Number.isSafeInteger(end) ||
    source.start_line < 1 ||
    end < source.start_line
  )
    return;
  // 不从日志文本、工具参数或同名文件猜测；只接受后端成功搜索返回的结构化命中。
  if (
    /^(?:[\\/]|[a-z]:)/i.test(source.path) ||
    source.path.includes('\0') ||
    source.path.split(/[\\/]/).some((part) => !part || part === '.' || part === '..')
  )
    return;
  for (const tool of tools) {
    if (
      tool.name !== 'search_source' ||
      tool.status !== 'success' ||
      tool.execution_status === 'skipped' ||
      typeof tool.result !== 'string'
    )
      continue;
    let result: unknown;
    try {
      result = JSON.parse(tool.result);
    } catch {
      continue;
    }
    if (!object(result) || !Array.isArray(result.matches)) continue;
    for (const hit of result.matches) {
      if (
        object(hit) &&
        hit.path === source.path &&
        typeof hit.line === 'number' &&
        Number.isSafeInteger(hit.line) &&
        hit.line >= source.start_line &&
        hit.line <= end &&
        typeof hit.text === 'string' &&
        hit.text.trim()
      )
        return hit.line;
    }
  }
}

export function resolveSourceReference(
  source: SourcePointer,
  evidence: SourceEvidence[],
  tools: ToolEvent[] = [],
  defaultSourceId?: string,
) {
  const read = {
    ...resolveSourceEvidence(source, evidence, defaultSourceId),
    kind: 'read' as const,
  };
  // 已读引用及显式版本引用继续使用原校验，搜索结果不能把失效版本降级成当前版本。
  if (read.evidence || source.version !== undefined) return read;
  const addressed = source.path.match(/^@sources\/([\w-]+)\//)?.[1];
  const origin = addressed || defaultSourceId;
  if (source.source_workspace_id && source.source_workspace_id !== origin) return read;
  const related = evidence.filter(
    (row) =>
      row.path === source.path && (!origin || (row.source_workspace_id || origin) === origin),
  );
  const identities = new Set(
    related.map((row) => JSON.stringify([row.source_workspace_id || origin, row.version])),
  );
  if (identities.size > 1 || related.some((row) => row.current_status !== 'match')) return read;
  const line = searchHit(source, tools);
  if (line === undefined) return read;
  // 搜索历史没有文件版本；仅保留真实命中行，不把整个引用范围登记成“已读取”。
  const hit: SourcePointer = {
    path: source.path,
    start_line: line,
    end_line: line,
    source_workspace_id: origin,
  };
  return { evidence: hit, kind: 'search' as const, reason: undefined };
}
