import type { KnowledgeReference, KnowledgeSearch } from '../../../shared/types/api';

export const knowledgeKindLabels = {
  material: '项目资料',
  handover_material: '交接资料',
  debug_issue: '调试记录',
};

export function distinctReferences(rows: KnowledgeReference[]) {
  return [
    ...new Map(
      rows.map((row) => [`${row.kind}:${row.id}:${row.version}:${row.citation}`, row]),
    ).values(),
  ];
}

export function searchNotices(searches: KnowledgeSearch[], references: KnowledgeReference[]) {
  const kinds = [...new Set(searches.map((row) => row.kind))];
  return kinds.flatMap((kind) => {
    const rows = searches.filter((row) => row.kind === kind);
    const latest = rows.at(-1)!;
    const notices: string[] = [];
    if (!rows.some((row) => row.matched > 0) && !references.some((row) => row.kind === kind))
      notices.push(`${knowledgeKindLabels[kind]}：未找到相关可用内容`);
    if (rows.some((row) => row.excluded_conditions))
      notices.push(`${knowledgeKindLabels[kind]}：已排除条件不符的记录`);
    if (rows.some((row) => row.unreadable))
      notices.push(`${knowledgeKindLabels[kind]}：部分附件暂无可检索正文`);
    if (latest.degraded)
      notices.push(`${knowledgeKindLabels[kind]}：语义检索暂不可用，已使用关键词和同义词检索`);
    return notices;
  });
}
