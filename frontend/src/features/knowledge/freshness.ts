export interface FileCheck {
  status: 'match' | 'changed' | 'missing' | 'unavailable';
  version?: string;
}
export type FileChecks = Record<string, FileCheck>;

// 资料中的 current 只描述生成索引时的状态；显示时还要核对当前工作区。
export function refreshSnapshot<T>(snapshot: T, checks: FileChecks): T {
  function visit(value: unknown): unknown {
    if (Array.isArray(value)) return value.map(visit);
    if (!value || typeof value !== 'object') return value;
    const original = value as Record<string, unknown>;
    const next = Object.fromEntries(
      Object.entries(original).map(([key, item]) => [key, visit(item)]),
    );
    const fileId =
      typeof original.fileId === 'string'
        ? original.fileId
        : typeof original.path === 'string' && typeof original.id === 'string'
          ? original.id
          : undefined;
    if (fileId && 'current' in next) {
      next.current = original.current === true && checks[fileId]?.status === 'match';
      if ('exists' in next && checks[fileId]?.status === 'missing') next.exists = false;
    }
    if (Array.isArray(next.declarations) && 'current' in next && next.declarations.length) {
      next.current =
        original.current === true &&
        next.declarations.every((d) => checks[d.fileId]?.status === 'match');
    }
    if (Array.isArray(next.evidence) && 'current' in next) {
      next.current =
        original.current === true && next.evidence.every((evidence) => evidence.current === true);
    }
    if (Array.isArray(next.samples) && 'current' in next) {
      next.current =
        original.current === true && next.samples.every((sample) => sample.current === true);
    }
    if (
      'current' in next &&
      typeof next.from === 'string' &&
      typeof next.to === 'string' &&
      checks[next.from] &&
      checks[next.to]
    ) {
      next.current =
        next.current === true &&
        checks[next.from].status === 'match' &&
        checks[next.to].status === 'match';
    }
    if (Array.isArray(next.files) && 'reviewCurrent' in next) {
      next.staleFiles = next.files.filter((file) => !file.current).length;
      const evidence = new Map<string, boolean>();
      if (Array.isArray(next.relationships)) {
        for (const relation of next.relationships) {
          for (const item of relation.evidence ?? []) evidence.set(item.id, item.current === true);
        }
      }
      const review = next.review as { evidenceIds?: string[] } | undefined;
      if (review?.evidenceIds)
        next.currentEvidence = review.evidenceIds.filter((id) =>
          checks[id] ? checks[id].status === 'match' : evidence.get(id) === true,
        ).length;
      const evidenceCount = next.evidenceCount ?? review?.evidenceIds?.length;
      next.reviewCurrent =
        original.reviewCurrent === true &&
        next.staleFiles === 0 &&
        next.currentEvidence === evidenceCount &&
        (!Array.isArray(next.outgoing) ||
          next.outgoing.every((dependency) => dependency.current === true));
    }
    return next;
  }
  return visit(snapshot) as T;
}
