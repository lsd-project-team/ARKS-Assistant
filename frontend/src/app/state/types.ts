import type { Selection, SourceOptions, SourceFile } from '../../shared/types/api.ts';
import type { PaneWidths, WorkspaceVisibility } from '../layouts/paneLayout.ts';
import type { ChatPosition, MessageJump } from '../../features/chat/lib/chatNavigation.ts';
import type { ProjectSession } from '../../features/projects/lib/projectSessions.ts';
import type { SidebarView, ThreadEntry } from '../../features/chat/lib/sidebarNavigation.ts';
import type {
  FileLocation,
  FileNavigation,
  FileOpenMode,
} from '../../features/source_reader/lib/fileNavigation.ts';
import type { ConversationDraft } from '../../features/chat/state/drafts.ts';
export interface WorkspaceState extends FileNavigation {
  historicalSource: { source: SourceFile; start: number; end: number } | null;
  projectId: string;
  projectSessions: Record<string, ProjectSession>;
  sourceBindings: Record<string, string>;
  sidebarView: SidebarView;
  expandedProjects: Record<string, boolean>;
  threadEntries: Record<string, ThreadEntry>;
  setThreadEntry: (id: string, entry: ThreadEntry) => void;
  setSidebarView: (view: SidebarView) => void;
  setProjectExpanded: (id: string, expanded: boolean) => void;
  switchProject: (id: string) => void;
  startConversation: (projectId: string) => void;
  initializeProject: (id: string) => void;
  resetProjectSource: (id: string) => void;
  threadId: string;
  messageJump: MessageJump;
  chatPositions: Record<string, ChatPosition>;
  closedFiles: FileLocation[];
  sourceFontSize: number;
  sourceLineHeight: number;
  drafts: Record<string, ConversationDraft>;
  chatRatio: number;
  explorerWidth: number;
  navigationWidth: number;
  codeOpen: boolean;
  explorerOpen: boolean;
  collapsed: boolean;
  readingFocused: boolean;
  workspaceRestore: WorkspaceVisibility | null;
  focusChatRatio: number;
  expandedDirectories: string[];
  rootExpanded: boolean;
  explorerScroll: number;
  revealTime: number;
  wordWrap: boolean;
  sourceModes: Record<string, boolean>;
  jump: { line: number; time: number; align: 'start' | 'center'; endLine?: number };
  mobile: 'code' | 'chat';
  openFile: (path: string, line?: number, mode?: FileOpenMode, endLine?: number) => void;
  closeFile: (path: string) => void;
  keepFile: (path: string) => void;
  closeOtherFiles: (path: string) => void;
  closeAllFiles: () => void;
  closeRightFiles: (path: string) => void;
  reopenFile: () => void;
  setReader: (fontSize: number, lineHeight: number) => void;
  resetLayout: () => void;
  navigateHistory: (direction: number) => void;
  toggleReadingFocus: () => void;
  setDirectoryExpanded: (path: string, expanded: boolean) => void;
  collapseDirectories: () => void;
  revealFile: () => void;
  completeReveal: () => void;
  saveExplorerScroll: (top: number) => void;
  setRootExpanded: (expanded: boolean) => void;
  setWordWrap: (wrap: boolean) => void;
  setSourceMode: (path: string, source: boolean) => void;
  selectThread: (id: string) => void;
  jumpToMessage: (threadId: string, messageId: string) => void;
  clearMessageJump: () => void;
  saveChatPosition: (id: string, position: ChatPosition) => void;
  forgetThread: (id: string) => void;
  restoreDraft: (id: string, draft: ConversationDraft) => void;
  attachNewDraft: (id: string) => void;
  addSelection: (selection: Selection) => void;
  removeSelection: (index: number) => void;
  clearSelections: () => void;
  setMobile: (tab: 'code' | 'chat') => void;
  navigationVersion: number;
  setWorkspaceOpen: (open: boolean) => void;
  collapsePane: (kind: 'chat' | 'files', restore?: PaneWidths) => void;
  setDraft: (content: string) => void;
  setSourceOptions: (options: SourceOptions) => void;
  consumeDraft: (key: string, draft: ConversationDraft) => void;
  consumeCommand: (key: string, draft: ConversationDraft) => void;
  savePosition: (path: string, line: number) => void;
  restoreReadingPosition: () => void;
  setLayout: (
    layout: Partial<
      Pick<
        WorkspaceState,
        | 'chatRatio'
        | 'focusChatRatio'
        | 'explorerWidth'
        | 'navigationWidth'
        | 'codeOpen'
        | 'explorerOpen'
        | 'collapsed'
      >
    >,
  ) => void;
}
export type WorkspaceSet = (
  changes: Partial<WorkspaceState> | ((state: WorkspaceState) => Partial<WorkspaceState>),
) => void;
