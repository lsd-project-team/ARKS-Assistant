import type { ProjectList } from '../types';

export function newConversationProject(
  list: ProjectList | undefined,
  currentId: string,
  requestedId?: string,
) {
  const active = list?.projects.filter((project) => project.state === 'active') || [];
  // 项目内的入口固定该项目；公共入口才在没有当前项目时回退到默认项目。
  if (requestedId) return active.find((project) => project.id === requestedId)?.id;
  return (
    active.find((project) => project.id === currentId)?.id ||
    active.find((project) => project.id === list?.default_project_id)?.id ||
    active[0]?.id
  );
}
