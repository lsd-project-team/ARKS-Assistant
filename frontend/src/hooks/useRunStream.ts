import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { Run, ToolEvent } from '../types';

export function useRunStream(run: Run | undefined) {
  const cache = useQueryClient();
  const [answer, setAnswer] = useState('');
  const [tools, setTools] = useState<ToolEvent[]>([]);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [context, setContext] = useState({ tokens: 0, limit: 32768 });
  const [finished, setFinished] = useState(false);
  useEffect(() => {
    setAnswer('');
    setTools([]);
    setNotice('');
    setError('');
    setFinished(false);
    if (!run || !['queued', 'running'].includes(run.status)) return;
    const source = new EventSource(`/api/runs/${run.id}/events`);
    let cursor = 0;
    const listen = (kind: string, handle: (payload: Record<string, unknown>) => void) => {
      source.addEventListener(kind, (event) => {
        const message = event as MessageEvent;
        if (!message.data) return;
        const sequence = Number(message.lastEventId);
        // EventSource 重连会带 Last-Event-ID；此处再去重，避免重复显示 token。
        if (sequence <= cursor) return;
        cursor = sequence;
        handle(JSON.parse(message.data));
      });
    };
    listen('token', (payload) => setAnswer((previous) => previous + String(payload.text)));
    listen('tool_start', (payload) =>
      setTools((previous) => [...previous, payload as unknown as ToolEvent]),
    );
    listen('tool_end', (payload) =>
      setTools((previous) =>
        previous.map((item) =>
          item.id === payload.id ? ({ ...item, ...payload } as ToolEvent) : item,
        ),
      ),
    );
    listen('notice', (payload) => setNotice(String(payload.text)));
    listen('compaction', (payload) => setNotice(String(payload.text)));
    listen('context', (payload) => setContext(payload as unknown as typeof context));
    listen('error', (payload) => setError(String(payload.text)));
    listen('done', (payload) => {
      if (payload.answer) setAnswer(String(payload.answer));
      setFinished(true);
      source.close();
      void cache.invalidateQueries({ queryKey: ['thread', run.thread_id] });
      void cache.invalidateQueries({ queryKey: ['threads'] });
      void cache.invalidateQueries({ queryKey: ['memories'] });
    });
    source.onerror = () => setNotice('连接中断，正在恢复消息…');
    return () => source.close();
  }, [run?.id, run?.status, cache]);
  return { answer, tools, notice, error, context, finished };
}
