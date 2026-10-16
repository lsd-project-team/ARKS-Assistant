import type { FileNavigation, FileLocation } from '../../source_reader/lib/fileNavigation.ts';

export interface ProjectSession extends FileNavigation {
  threadId: string;
  closedFiles: FileLocation[];
  expandedDirectories: string[];
  explorerScroll: number;
  rootExpanded: boolean;
  sourceModes: Record<string, boolean>;
  codeOpen: boolean;
  explorerOpen: boolean;
}

export const emptyProjectSession = (): ProjectSession => ({
  threadId: '',
  paths: [],
  activePath: '',
  previewPath: '',
  history: [],
  historyIndex: -1,
  positions: {},
  closedFiles: [],
  expandedDirectories: [],
  explorerScroll: 0,
  rootExpanded: true,
  sourceModes: {},
  codeOpen: false,
  explorerOpen: false,
});

export function projectSession(state: ProjectSession): ProjectSession {
  return Object.fromEntries(
    Object.keys(emptyProjectSession()).map((key) => [key, state[key as keyof ProjectSession]]),
  ) as unknown as ProjectSession;
}
