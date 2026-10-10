import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowUp,
  Plus,
  Folder,
  PanelLeftOpen,
  Zap,
  X,
  Square,
  FileCode2,
  ChevronDown,
  Check,
  LoaderCircle,
  RotateCcw,
  Minimize2,
} from 'lucide-react';
import { api, jsonBody } from '../lib/api';
import { useWorkspace } from '../lib/store';
import { useRunStream } from '../hooks/useRunStream';
import type { Conversation, Message, Run, Settings, Thread, ToolEvent } from '../types';
import { Markdown } from './Markdown';
import { RunTrace } from './RunTrace';
import { Button, ErrorText } from './ui';

function MessageBubble({ message, runId }: { message: Message; runId?: string }) {
  const openFile = useWorkspace((state) => state.openFile);
  return (
    <div className={`message ${message.role}`}>
      <div className="message-label">{message.role === 'user' ? '你' : <>Trunk Agent</>}</div>
      {message.selections?.map((selection, index) => (
        <button
          className="context-citation"
          key={index}
          title={selection.path}
          onClick={() => openFile(selection.path, selection.start_line)}
        >
          <FileCode2 size={12} />
          {selection.path.split('/').at(-1)}
          <span>
            L{selection.start_line}–{selection.end_line}
          </span>
          {selection.stale && <span>旧版本</span>}
        </button>
      ))}
      {runId && <RunTrace runId={runId} />}
      <Markdown content={message.content} />
    </div>
  );
}
function ToolActivity({ tools }: { tools: ToolEvent[] }) {
  return tools.length ? (
    <div className="tool-activity">
      {tools.map((tool) => (
        <details key={tool.id}>
          <summary>
            {tool.result ? <Check size={12} /> : <LoaderCircle size={12} className="spin" />}
            <span>{tool.name.replace('mcp_deepwiki_', '').replaceAll('_', ' ')}</span>
            <ChevronDown size={12} />
          </summary>
          <pre>{JSON.stringify(tool.arguments, null, 2)}</pre>
          {tool.result && <pre>{tool.result}</pre>}
        </details>
      ))}
    </div>
  ) : null;
}

export function ChatPane({
  onShowSource,
  onShowSidebar,
}: {
  onShowSource: () => void;
  onShowSidebar: () => void;
}) {
  const { threadId, selectThread, selections, removeSelection, clearSelections } = useWorkspace();
  const [draft, setDraft] = useState('');
  const [started, setStarted] = useState<Run>();
  const bottom = useRef<HTMLDivElement>(null);
  const composerInput = useRef<HTMLTextAreaElement>(null);
  const mobile = useWorkspace((state) => state.mobile);
  const cache = useQueryClient();
  const conversation = useQuery({
    queryKey: ['thread', threadId],
    queryFn: () => api<Conversation>(`/threads/${threadId}`),
    enabled: !!threadId,
    refetchInterval: (query) =>
      query.state.data?.runs.some((run) => ['queued', 'running'].includes(run.status))
        ? 3000
        : false,
  });
  const settings = useQuery({ queryKey: ['settings'], queryFn: () => api<Settings>('/settings') });
  const latest = conversation.data?.runs.at(-1);
  const pending = latest && ['queued', 'running'].includes(latest.status) ? latest : undefined;
  const active =
    started?.thread_id === threadId &&
    ['queued', 'running'].includes(started.status) &&
    (!latest || latest.id !== started.id)
      ? started
      : pending;
  const stream = useRunStream(active);
  const busy = !!active && !stream.finished;
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth' });
  }, [threadId, stream.answer, conversation.data?.messages.length, stream.tools.length]);
  useEffect(() => {
    if (mobile === 'chat') bottom.current?.scrollIntoView({ behavior: 'smooth' });
  }, [mobile]);
  useEffect(() => {
    if (selections.length) composerInput.current?.focus();
  }, [selections.length]);
  const send = useMutation({
    mutationFn: async () => {
      let id = threadId;
      if (!id) {
        const row = await api<Thread>('/threads', {
          method: 'POST',
          body: jsonBody({ title: draft.trim().slice(0, 28) || '新对话' }),
        });
        id = row.id;
        selectThread(id);
      }
      return api<Run>(`/threads/${id}/runs`, {
        method: 'POST',
        body: jsonBody({ content: draft.trim(), selections }),
      });
    },
    onSuccess: (run) => {
      setStarted(run);
      setDraft('');
      clearSelections();
      void cache.invalidateQueries({ queryKey: ['thread', run.thread_id] });
      void cache.invalidateQueries({ queryKey: ['threads'] });
    },
  });
  const resume = useMutation({
    mutationFn: (id: string) => api<Run>(`/runs/${id}/resume`, { method: 'POST' }),
    onSuccess: (run) => {
      setStarted(run);
      void cache.invalidateQueries({ queryKey: ['thread', threadId] });
    },
  });
  const compact = useMutation({
    mutationFn: () => api<Run>(`/threads/${threadId}/compact`, { method: 'POST' }),
    onSuccess: (run) => {
      setStarted(run);
      void cache.invalidateQueries({ queryKey: ['thread', threadId] });
    },
  });
  async function newConversation() {
    const row = await api<Thread>('/threads', {
      method: 'POST',
      body: jsonBody({ title: '新对话' }),
    });
    selectThread(row.id);
    setStarted(undefined);
    void cache.invalidateQueries({ queryKey: ['threads'] });
  }
  const messages = conversation.data?.messages || [];
  const interrupted = latest && ['failed', 'cancelled', 'interrupted'].includes(latest.status);
  return (
    <section className="chat-pane">
      <div className="chat-heading">
        <div>
          <button className="show-sidebar" aria-label="展开会话导航" onClick={onShowSidebar}>
            <PanelLeftOpen size={16} />
          </button>
          <Folder size={15} />
          <strong title={conversation.data?.title}>{conversation.data?.title || '新对话'}</strong>
        </div>
        <div>
          {threadId && (
            <Button
              className="icon-button"
              aria-label="压缩上下文"
              title="压缩上下文"
              disabled={busy || compact.isPending}
              onClick={() => compact.mutate()}
            >
              <Minimize2 size={14} />
            </Button>
          )}
          <Button
            className="icon-button"
            aria-label="新建对话"
            onClick={() => void newConversation()}
          >
            <Plus size={17} />
          </Button>
        </div>
      </div>
      <div className="chat-scroll">
        {!messages.length && !active && (
          <div className="chat-welcome">
            <h2>想从哪里开始？</h2>
            <p>
              解释代码、追踪模块，或聊聊你的想法。
              <br />
              在右侧打开文件，选中一段代码就可以提问。
            </p>
            <div className="suggestions">
              {['这个项目的模块如何组织？', '帮我理解选中的代码', '如何开始开发一个新模块？'].map(
                (text) => (
                  <button key={text} onClick={() => setDraft(text)}>
                    {text}
                    <Plus size={13} />
                  </button>
                ),
              )}
            </div>
            <div className="welcome-context">
              <span className="tiny-dot" />
              trunk<span>已连接源码工作区</span>
            </div>
          </div>
        )}
        {messages.map((message, index) => (
          <MessageBubble
            key={message.id}
            message={message}
            runId={
              index === messages.length - 1 &&
              message.role === 'assistant' &&
              latest?.status === 'completed'
                ? latest.id
                : undefined
            }
          />
        ))}
        {active && (
          <div className="message assistant">
            <div className="message-label">
              Trunk Agent {busy && <span className="thinking">处理中</span>}
            </div>
            <ToolActivity tools={stream.tools} />
            {stream.answer ? (
              <Markdown content={stream.answer} />
            ) : (
              <span className="muted">
                正在思考<span className="typing-dots">…</span>
              </span>
            )}
            <ErrorText error={stream.error} />
          </div>
        )}
        {interrupted && (
          <div className="run-recovery">
            <ErrorText
              error={latest.error || (latest.status === 'cancelled' ? '已停止回复' : '运行已中断')}
            />
            {latest.answer && <Markdown content={latest.answer} />}
            <Button onClick={() => resume.mutate(latest.id)} disabled={resume.isPending}>
              <RotateCcw size={13} />
              继续运行
            </Button>
          </div>
        )}
        <ErrorText error={conversation.error || send.error || resume.error || compact.error} />
        {stream.notice && <div className="stream-notice">{stream.notice}</div>}
        <div ref={bottom} />
      </div>
      <div className="composer-area">
        {selections.length > 0 && (
          <div className="selection-list">
            {selections.map((selection, index) => (
              <div className="selection-chip" key={index} title={selection.path}>
                <FileCode2 size={13} />
                <span>
                  {selection.path.split('/').at(-1)}
                  <small>
                    L{selection.start_line}–{selection.end_line}
                  </small>
                </span>
                <button aria-label="移除代码选区" onClick={() => removeSelection(index)}>
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        )}
        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            if (!busy && draft.trim()) send.mutate();
          }}
        >
          <textarea
            ref={composerInput}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="询问代码，或聊聊你的想法…"
            aria-label="对话输入"
            rows={2}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                if (draft.trim() && !busy && !send.isPending) send.mutate();
              }
            }}
          />
          <div className="composer-toolbar">
            <div className="composer-tools">
              <button
                type="button"
                className="attach-code"
                aria-label="选择源码"
                title="打开源码文件树"
                onClick={onShowSource}
              >
                <Plus size={18} />
              </button>
              <span className="model-label">
                <Zap size={12} fill="currentColor" />
                {settings.data?.model.model || '配置模型'}
              </span>
            </div>
            {busy ? (
              <Button
                type="button"
                className="send-button stop"
                aria-label="停止回复"
                onClick={() => void api(`/runs/${active.id}/cancel`, { method: 'POST' })}
              >
                <Square size={13} fill="currentColor" />
              </Button>
            ) : (
              <Button
                className="send-button"
                type="submit"
                aria-label="发送消息"
                disabled={!draft.trim() || send.isPending}
              >
                <ArrowUp size={17} />
              </Button>
            )}
          </div>
        </form>
        <div className="composer-footer">
          <span>Enter 发送 · Shift + Enter 换行</span>
          <span title="估算的当前上下文 token 数">
            {stream.context.tokens > 0
              ? `${Math.round((stream.context.tokens / stream.context.limit) * 100)}% 上下文`
              : '本地保存对话'}
          </span>
        </div>
      </div>
    </section>
  );
}
