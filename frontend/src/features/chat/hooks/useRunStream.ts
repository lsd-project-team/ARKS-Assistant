import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type {
  ContextUsage,
  ErrorFeedback,
  Run,
  ToolEvent,
  KnowledgeReference,
  KnowledgeSearch,
  MemorySaveFeedback,
} from '../../../shared/types/api';
import { apiUrl } from '../../../app/api/client';
import { useWorkspace } from '../../../app/state/store';

export function useRunStream(run: Run | undefined) {
  const cache = useQueryClient();
  const projectId = useWorkspace((state) => state.projectId);
  const [answer, setAnswer] = useState('');
  const [tools, setTools] = useState<ToolEvent[]>([]);
  const [notice, setNotice] = useState('');
  const [connectionNotice, setConnectionNotice] = useState('');
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState<ErrorFeedback>();
  const [noticeFeedback, setNoticeFeedback] = useState<ErrorFeedback>();
  const [stage, setStage] = useState('queued');
  const [detail, setDetail] = useState('');
  const [context, setContext] = useState<ContextUsage>();
  const [finished, setFinished] = useState(false);
  const [references, setReferences] = useState<KnowledgeReference[]>([]);
  const [searches, setSearches] = useState<KnowledgeSearch[]>([]);
  const [memorySaves, setMemorySaves] = useState<MemorySaveFeedback[]>([]);
  useEffect(() => {
    setAnswer('');
    setTools([]);
    setNotice('');
    setConnectionNotice('');
    setError('');
    setFeedback(undefined);
    setNoticeFeedback(undefined);
    setStage(run?.stage || 'queued');
    setDetail('');
    setFinished(false);
    setReferences([]);
    setSearches([]);
    setMemorySaves([]);
    setContext(undefined);
    if (!run || !['queued', 'running'].includes(run.status)) return;
    const source = new EventSource(apiUrl(`/runs/${run.id}/events`, projectId));
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
    listen('knowledge_reference', (payload) =>
      setReferences((previous) => [...previous, payload as unknown as KnowledgeReference]),
    );
    listen('knowledge_search', (payload) =>
      setSearches((previous) => [...previous, payload as unknown as KnowledgeSearch]),
    );
    listen('memory_save', (payload) =>
      setMemorySaves((previous) => [...previous, payload as unknown as MemorySaveFeedback]),
    );
    listen('answer_replace', (payload) => setAnswer(String(payload.text)));
    listen('retrieval_budget', (payload) => setNotice(String(payload.text)));
    listen('answer_completion', (payload) => {
      if (!payload.continuing && payload.output !== 'complete')
        setNotice(
          payload.output === 'incomplete'
            ? '回复未完整，已保留内容，可继续。'
            : '回复可能被截断，完整度待确认。',
        );
    });
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
    listen('stage', (payload) => {
      setStage(String(payload.stage));
      setDetail(String(payload.detail || ''));
    });
    listen('notice', (payload) => {
      setNotice(String(payload.text));
      setNoticeFeedback(payload as unknown as ErrorFeedback);
    });
    listen('compaction', (payload) => setNotice(String(payload.text)));
    listen('context', (payload) => setContext(payload as unknown as typeof context));
    listen('error', (payload) => {
      setError(String(payload.text));
      setFeedback(payload as unknown as ErrorFeedback);
    });
    listen('done', (payload) => {
      if (payload.answer) setAnswer(String(payload.answer));
      setFinished(true);
      setConnectionNotice('');
      setStage(String(payload.stage || payload.status));
      setDetail('');
      source.close();
      void cache.invalidateQueries({ queryKey: ['thread', run.thread_id] });
      void cache.invalidateQueries({ queryKey: ['threads'] });
      void cache.invalidateQueries({ queryKey: ['queue', run.thread_id] });
      void cache.invalidateQueries({ queryKey: ['memories'] });
      void cache.invalidateQueries({ queryKey: ['context', run.thread_id] });
    });
    // 重连提示独立于 MCP / 压缩提示，恢复连接后只撤掉断线状态。
    source.onopen = () => setConnectionNotice('');
    source.onerror = () => setConnectionNotice('连接中断，正在恢复消息…');
    return () => source.close();
  }, [run?.id, run?.status, cache, projectId]);
  return {
    references,
    searches,
    memorySaves,
    answer,
    tools,
    notice: connectionNotice || notice,
    error,
    feedback,
    noticeFeedback: connectionNotice ? undefined : noticeFeedback,
    stage,
    detail,
    context,
    finished,
  };
}
