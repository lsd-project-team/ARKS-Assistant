import type { SourceContext } from '../../../shared/types/api';

export function citationPath(context: SourceContext, path: string, sourceId?: string) {
  const addressed = path.match(/^@sources\/([\w-]+)\//)?.[1];
  if (addressed && sourceId && addressed !== sourceId)
    throw new Error('引用中的源码目录身份不一致');
  if (!sourceId || sourceId === context.source_workspace_id) return path;
  if (!context.attached_source_ids.includes(sourceId)) return null;
  const prefix = `@sources/${sourceId}/`;
  return path.startsWith(prefix) ? path : prefix + path;
}
