import type { Selection, SourceOptions } from '../../../shared/types/api.ts';
import type { WorkspaceState } from '../../../app/state/types.ts';
export interface ConversationDraft {
  content: string;
  selections: Selection[];
  source_options?: Partial<SourceOptions>;
}
const EMPTY_DRAFT: ConversationDraft = { content: '', selections: [] };
export const draftKey = (threadId: string, projectId?: string) =>
  threadId || (projectId ? `new:${projectId}` : 'new');
export const draftFor = (
  state: Pick<WorkspaceState, 'drafts' | 'threadId'> & { projectId?: string },
) => state.drafts[draftKey(state.threadId, state.projectId)] || EMPTY_DRAFT;
export function patchDraft(state: WorkspaceState, changes: Partial<ConversationDraft>) {
  return {
    drafts: {
      ...state.drafts,
      [draftKey(state.threadId, state.projectId)]: { ...draftFor(state), ...changes },
    },
  };
}
