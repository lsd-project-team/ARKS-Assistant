import type { Thread } from '../types';

export type SidebarView = 'active' | 'archived' | 'deleted';
export type ThreadEntry = 'project' | 'recent';
export const projectThreadPreview = 3;
export const recentThreadPreview = 8;

export const threadProject = (row: Thread) => row.project_id || 'independent';

export function threadSelectedAt(
  row: Thread,
  entry: ThreadEntry,
  current: {
    projectId: string;
    threadId: string;
    projectPage: boolean;
    threadEntries: Record<string, ThreadEntry>;
  },
) {
  // 同一对话在两处出现时，只高亮最后点击的入口；独立对话只有最近列表入口。
  const chosen = row.project_id ? current.threadEntries[row.id] || 'project' : 'recent';
  return (
    !current.projectPage &&
    current.projectId === threadProject(row) &&
    current.threadId === row.id &&
    chosen === entry
  );
}

export function visibleThreads(rows: Thread[], selected: Thread | undefined, preview?: number) {
  const visible = preview === undefined ? rows : rows.slice(0, preview);
  if (!selected || visible.some((row) => row.id === selected.id)) return visible;
  // 从搜索或展开列表打开较早的对话后，收起预览仍应看得到当前选中项。
  return [
    ...(preview === undefined ? visible : visible.slice(0, Math.max(0, preview - 1))),
    selected,
  ];
}

// 归档项目同时保留正常和已归档对话，两类分页合并时按统一规则排序并去重。
export function projectThreadOrder(rows: Thread[]): Thread[] {
  return [...new Map(rows.map((row) => [row.id, row])).values()].sort((left, right) => {
    const pinned = (left.pinned_order ?? Infinity) - (right.pinned_order ?? Infinity);
    return (
      (Number.isNaN(pinned) ? 0 : pinned) ||
      right.updated_at.localeCompare(left.updated_at) ||
      left.id.localeCompare(right.id)
    );
  });
}
