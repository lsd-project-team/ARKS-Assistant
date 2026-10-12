import { useProjects } from './useProjects';
import { useWorkspace } from '../lib/store';
import { newConversationProject } from '../lib/conversationCreation';
import { toast } from '../lib/toasts';

export function useNewConversation() {
  const projects = useProjects();
  return (requestedId?: string) => {
    const state = useWorkspace.getState();
    const projectId = newConversationProject(projects.data, state.projectId, requestedId);
    if (!projectId) {
      toast(projects.isPending ? '正在读取项目，请稍后再试' : '请先新建或恢复项目，再创建对话');
      return false;
    }
    state.startConversation(projectId);
    return true;
  };
}
