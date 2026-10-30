import { QueryClient } from '@tanstack/react-query';

const caches = new Map<string, QueryClient>();
export function clearProjectCaches() {
  for (const cache of caches.values()) cache.clear();
  caches.clear();
}
export function projectCache(id: string) {
  if (!caches.has(id))
    caches.set(
      id,
      new QueryClient({ defaultOptions: { queries: { staleTime: 15000, retry: 1 } } }),
    );
  return caches.get(id)!;
}

export function invalidateProjectCaches(groups: string[]) {
  // 其他项目的缓存也要失效；切回时才能立即看到被移动的对话和新的项目名称。
  return Promise.all(
    [...caches.values()].flatMap((cache) =>
      groups.map((group) => cache.invalidateQueries({ queryKey: [group] })),
    ),
  );
}
