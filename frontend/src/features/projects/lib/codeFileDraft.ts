import { workspaceStorageKey } from '../../../app/state/accountWorkspace.ts';
import type { ChangeFile } from '../types/codeWork';

export interface CodeDraftScope {
  accountId: string;
  projectId: string;
  changeId: string;
}
export interface CodeFileDraft {
  file: ChangeFile;
  draft: string;
}
type DraftStorage = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>;

export function codeFileDraftKey(scope: CodeDraftScope) {
  if (!scope.accountId || !scope.projectId || !scope.changeId) return '';
  return `${workspaceStorageKey(scope.accountId)}:code-work:${encodeURIComponent(scope.projectId)}:${encodeURIComponent(scope.changeId)}`;
}

export function browserDraftStorage(): DraftStorage | undefined {
  try {
    return typeof window === 'undefined' ? undefined : window.sessionStorage;
  } catch {
    return undefined;
  }
}

export function readCodeFileDraft(
  storage: DraftStorage | undefined,
  scope: CodeDraftScope,
): CodeFileDraft | undefined {
  const key = codeFileDraftKey(scope);
  if (!storage || !key) return undefined;
  try {
    const saved = JSON.parse(storage.getItem(key) || 'null');
    const file = saved?.file;
    if (
      saved?.schema !== 1 ||
      saved.accountId !== scope.accountId ||
      saved.projectId !== scope.projectId ||
      saved.changeId !== scope.changeId ||
      !file ||
      typeof file.path !== 'string' ||
      !file.path ||
      typeof file.content !== 'string' ||
      typeof file.version !== 'string' ||
      typeof saved.draft !== 'string' ||
      saved.draft.length > 2000000 ||
      file.content.length > 2000000 ||
      saved.draft === file.content ||
      (!/^[a-f0-9]{64}$/.test(file.version) &&
        !(file.exists === false && file.version === '' && file.content === ''))
    )
      return undefined;
    return {
      file: {
        path: file.path,
        content: file.content,
        version: file.version,
        ...(typeof file.requirements_version === 'string'
          ? { requirements_version: file.requirements_version }
          : {}),
        ...(typeof file.exists === 'boolean' ? { exists: file.exists } : {}),
      },
      draft: saved.draft,
    };
  } catch {
    return undefined;
  }
}

export function writeCodeFileDraft(
  storage: DraftStorage | undefined,
  scope: CodeDraftScope,
  value: CodeFileDraft,
) {
  const key = codeFileDraftKey(scope);
  if (!storage || !key) return false;
  try {
    if (value.file.content === value.draft) storage.removeItem(key);
    else storage.setItem(key, JSON.stringify({ schema: 1, ...scope, ...value }));
    return true;
  } catch {
    return false;
  }
}
