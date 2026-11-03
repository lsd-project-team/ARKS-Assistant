import type { Thread } from '../../../shared/types/api';
import type { SidebarView } from './sidebarNavigation';

export const conversationSearchPageSize = 50;
type SearchRequest = <T>(path: string, options?: RequestInit, projectId?: string) => Promise<T>;
interface SearchOptions {
  filter: string;
  offset: number;
  signal: AbortSignal;
  projectId: string;
  all: boolean;
  view: SidebarView;
}

export async function searchConversations(request: SearchRequest, options: SearchOptions) {
  const { filter, offset, signal, projectId, all, view } = options;
  const parameters = new URLSearchParams({
    query: filter,
    limit: String(conversationSearchPageSize),
    offset: String(offset),
  });
  if (view !== 'active') {
    // 回收站始终只返回已删除会话，按当前项目筛选时不混入其他范围。
    parameters.set('view', view);
    if (!all) parameters.set('project_id', projectId || 'independent');
    const rows = await request<Thread[]>(
      `/projects/search-threads?${parameters}`,
      { signal },
      projectId,
    );
    return { rows, hasMore: rows.length === conversationSearchPageSize };
  }
  const rows = await request<Thread[]>(
    `${all ? '/projects/search-threads' : '/threads'}?${parameters}&state=active`,
    { signal },
    projectId,
  );
  return {
    rows,
    hasMore: rows.length === conversationSearchPageSize,
  };
}

export const conversationSearchTitle = (view: SidebarView) =>
  view === 'deleted' ? '搜索已删除对话' : '搜索对话';
