import type { ProjectList } from '../../../shared/types/api';

export function newConversationProject(list: ProjectList | undefined, requestedId?: string) {
  // 归属由新建入口明确指定，不能从当前阅读的项目或默认项目推断。
  if (!requestedId || requestedId === 'independent') return 'independent';
  return list?.projects.find((project) => project.id === requestedId && project.state === 'active')
    ?.id;
}
