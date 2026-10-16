import type { StateStorage } from 'zustand/middleware';

const mapFields = [
  'drafts',
  'chatPositions',
  'positions',
  'sourceModes',
  'projectSessions',
  'sourceBindings',
  'expandedProjects',
  'threadEntries',
];
type Snapshot = { state: Record<string, unknown>; version?: number };

export function mergedStorage(storage: StateStorage): StateStorage {
  const previous = new Map<string, Snapshot>();
  return {
    getItem(name) {
      const value = storage.getItem(name);
      if (typeof value === 'string') {
        try {
          previous.set(name, JSON.parse(value));
        } catch {
          /* 由持久化层处理旧的损坏记录。 */
        }
      }
      return value;
    },
    setItem(name, value) {
      try {
        const incoming: Snapshot = JSON.parse(value);
        const old = previous.get(name)?.state || {};
        const stored = storage.getItem(name);
        const latest: Snapshot = typeof stored === 'string' ? JSON.parse(stored) : { state: {} };
        const next = { ...incoming, state: { ...incoming.state } };
        for (const field of mapFields) {
          const before = (old[field] || {}) as Record<string, unknown>;
          const local = (incoming.state[field] || {}) as Record<string, unknown>;
          const merged = { ...(latest.state[field] || {}) } as Record<string, unknown>;
          for (const key of new Set([...Object.keys(before), ...Object.keys(local)])) {
            if (JSON.stringify(before[key]) === JSON.stringify(local[key])) continue;
            if (key in local) merged[key] = local[key];
            else delete merged[key];
          }
          next.state[field] = merged;
        }
        // 基线保留本窗口的状态；其他窗口新增的草稿不能被下一次布局写入当成删除。
        previous.set(name, incoming);
        return storage.setItem(name, JSON.stringify(next));
      } catch {
        return storage.setItem(name, value);
      }
    },
    removeItem(name) {
      previous.delete(name);
      return storage.removeItem(name);
    },
  };
}
