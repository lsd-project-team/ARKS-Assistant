import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { EngineeringManifest, SourceSymbol } from './engineeringTypes';
import { refreshSnapshot, type FileChecks } from './freshness';

export const EngineeringContext = createContext<EngineeringManifest | null>(null);
export const useEngineering = () => useContext(EngineeringContext);
export const BaselineContext = createContext<FileChecks>({});
const cache = new Map<string, Promise<unknown>>();
export function fetchJSON<T>(url: string): Promise<T> {
  if (!cache.has(url))
    cache.set(
      url,
      fetch(url)
        .then(async (response) => {
          if (!response.ok) throw new Error(`读取失败 (${response.status})`);
          return response.json();
        })
        .catch((error) => {
          cache.delete(url);
          throw error;
        }),
    );
  return cache.get(url) as Promise<T>;
}
export function useResource<T>(url: string | undefined): {
  url?: string;
  data?: T;
  error?: string;
} {
  const checks = useContext(BaselineContext);
  const [result, setResult] = useState<{ url?: string; data?: T; error?: string }>({});
  useEffect(() => {
    let active = true;
    if (url)
      fetchJSON<T>(url)
        .then((data) => active && setResult({ url, data }))
        .catch((error) => active && setResult({ url, error: error.message }));
    return () => {
      active = false;
    };
  }, [url]);
  const data = useMemo(
    () =>
      result.data && url && /\/(files|modules)\//.test(url)
        ? refreshSnapshot(result.data, checks)
        : result.data,
    [result.data, url, checks],
  );
  return result.url === url ? { ...result, data } : {};
}
export function useSymbol(id: string) {
  const checks = useContext(BaselineContext);
  const manifest = useEngineering();
  const resource = useResource<Record<string, SourceSymbol>>(
    manifest ? `${manifest.base}/symbols/${id.slice(0, 2)}.json` : undefined,
  );
  const raw = resource.data?.[id];
  const symbol = useMemo(() => (raw ? refreshSnapshot(raw, checks) : undefined), [raw, checks]);
  return {
    symbol,
    error:
      resource.error ??
      (resource.data && !resource.data[id]
        ? '当前源码版本没有此符号，请返回模块目录。'
        : undefined),
  };
}
export const callKindLabel = (kind: string) =>
  ({
    invokes: '方法调用',
    constructs: '对象构造',
    'method-reference': '方法引用 / 回调',
    'event-reference': '事件关联',
    'dynamic-unresolved': '动态目标待确认',
    'invalid-operation': '依赖缺失 / 绑定失败',
    'operator-call': '运算符调用',
    'conversion-call': '类型转换',
    'direct-call': '直接调用',
    'event-subscription': '事件订阅',
    'task-launch': '异步任务',
    'signal-wait': '信号等待',
    'signal-set': '信号放行',
  })[kind] ?? kind;
export const dispatchLabel = (dispatch: string) =>
  dispatch?.startsWith('statically-bound')
    ? '静态目标'
    : dispatch === 'reference-not-invocation'
      ? '引用，未证明执行'
      : dispatch === 'binding-invalid'
        ? '绑定失败，目标待确认'
        : dispatch?.includes('virtual')
          ? '虚调用：运行时实现待确认'
          : dispatch?.includes('delegate')
            ? '委托：运行时目标待确认'
            : dispatch?.includes('dynamic') || dispatch?.includes('runtime-binding')
              ? '动态目标待确认'
              : dispatch;
