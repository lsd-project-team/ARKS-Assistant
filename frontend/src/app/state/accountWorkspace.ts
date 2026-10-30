import type { StateStorage } from 'zustand/middleware';

let accountId = '';
let paused = false;
export const workspaceStorageKey = (id: string) => `trunk-workspace:account:${id}`;

export const accountWorkspaceStorage: StateStorage = {
  getItem: () => (accountId ? localStorage.getItem(workspaceStorageKey(accountId)) : null),
  setItem: (_name, value) => {
    if (accountId && !paused) localStorage.setItem(workspaceStorageKey(accountId), value);
  },
  removeItem: () => {
    if (accountId && !paused) localStorage.removeItem(workspaceStorageKey(accountId));
  },
};

export function changeWorkspaceAccount(id: string, restore: () => void) {
  if (id === accountId) return;
  accountId = id;
  // 重置内存时暂停落盘，避免用空状态覆盖新账号已保存的草稿。
  paused = true;
  try {
    restore();
  } finally {
    paused = false;
  }
}

type Snapshot = { state: Record<string, unknown>; version?: number };
type Entry = { id: string; owner_id?: string | null };

export function ownedLegacyWorkspace(
  snapshot: Snapshot,
  projectIds: Set<string>,
  threadIds: Set<string>,
): Snapshot {
  const original = snapshot.state;
  const ownProject = projectIds.has(String(original.projectId));
  const map = (value: unknown, accepts: (key: string) => boolean) =>
    Object.fromEntries(
      Object.entries((value || {}) as Record<string, unknown>).filter(([key]) => accepts(key)),
    );
  const state: Record<string, unknown> = ownProject ? { ...original } : {};
  for (const field of ['projectSessions', 'sourceBindings', 'expandedProjects'])
    state[field] = map(original[field], (key) => projectIds.has(key));
  for (const field of ['threadEntries', 'chatPositions'])
    state[field] = map(original[field], (key) => threadIds.has(key));
  state.drafts = map(
    original.drafts,
    (key) => threadIds.has(key) || (key.startsWith('new:') && projectIds.has(key.slice(4))),
  );
  if (!threadIds.has(String(state.threadId))) state.threadId = '';
  for (const entry of Object.values(
    state.projectSessions as Record<string, Record<string, unknown>>,
  )) {
    if (!threadIds.has(String(entry.threadId))) entry.threadId = '';
  }
  return { ...snapshot, state };
}

export async function prepareLegacyWorkspace(id: string, request: <T>(path: string) => Promise<T>) {
  const key = workspaceStorageKey(id);
  const legacy = localStorage.getItem('trunk-workspace');
  if (!legacy || localStorage.getItem(key)) return;
  const list = await request<{ projects: Entry[] }>('/api/projects');
  const archived = await request<{ projects: Entry[] }>('/api/projects?state=archived');
  const projectIds = new Set(
    [...list.projects, ...archived.projects]
      .filter((row) => row.owner_id === id)
      .map((row) => row.id),
  );
  const threadIds = new Set<string>();
  for (const state of ['active', 'archived', 'deleted']) {
    for (let offset = 0; ; offset += 200) {
      const rows = await request<Entry[]>(
        `/api/projects/search-threads?state=${state}&limit=200&offset=${offset}`,
      );
      for (const row of rows) if (row.owner_id === id) threadIds.add(row.id);
      if (rows.length < 200) break;
    }
  }
  // 只迁移服务端已确认属于本人的内容；旧公共原件保留，不让下一个账号继承。
  const snapshot = ownedLegacyWorkspace(JSON.parse(legacy), projectIds, threadIds);
  if (!localStorage.getItem(key)) localStorage.setItem(key, JSON.stringify(snapshot));
}
