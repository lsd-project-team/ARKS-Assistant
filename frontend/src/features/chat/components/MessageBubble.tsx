import { useRef, useState } from 'react';
import { Copy, Check, RotateCcw, FileCode2, Pencil, MessageSquare } from 'lucide-react';
import { useWorkspace } from '../../../app/state/store';
import type { Message, Run } from '../../../shared/types/api';
import { Markdown } from '../../../app/components/Markdown';
import { AnswerMarkdown } from './AnswerMarkdown';
import { RunTrace } from './RunTrace';
import { ErrorText } from '../../../shared/ui/ui';
import { SelectionPreview } from './SelectionPreview';
import type { Selection } from '../../../shared/types/api';
import { toast } from '../../../shared/utils/toasts';
import { elapsedRun } from '../lib/runFeedback';
import { useCurrentProject } from '../../projects/hooks/useProjects';
import { RunKnowledgeSummary } from './RunKnowledgeSummary';
import { InlineQuestionEditor } from './InlineQuestionEditor';
import { contentToMarkdown } from '../rich/contentToMarkdown';

export function MessageBubble({
  message,
  run,
  canRegenerate,
  onRegenerate,
  onEdit,
  recent = false,
}: {
  message: Message;
  run?: Run;
  canRegenerate?: boolean;
  onRegenerate: (id: string) => void;
  onEdit?: (content: string) => Promise<unknown>;
  recent?: boolean;
}) {
  const editButton = useRef<HTMLButtonElement>(null);
  const [editing, setEditing] = useState(false);
  const [preview, setPreview] = useState<Selection>();
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<unknown>();
  const project = useCurrentProject();
  const Content = message.role === 'assistant' ? AnswerMarkdown : Markdown;
  async function copy() {
    try {
      await navigator.clipboard.writeText(
        message.role === 'assistant' ? contentToMarkdown(message.content) : message.content,
      );
      setCopied(true);
      toast('回复已复制');
      setError(undefined);
    } catch {
      setError('复制失败，请检查浏览器剪贴板权限或手动选择文字复制');
    }
  }
  if (message.role === 'user' && editing) {
    return (
      <InlineQuestionEditor
        content={message.content}
        onCancel={() => {
          setEditing(false);
          requestAnimationFrame(() => editButton.current?.focus({ preventScroll: true }));
        }}
        onSubmit={
          onEdit
            ? async (content) => {
                await onEdit(content);
                setEditing(false);
              }
            : undefined
        }
      />
    );
  }
  return (
    <div className={`message ${message.role}`}>
      <div className="message-bubble">
        <div className="message-label">
          {message.role === 'user' ? '你' : 'ARKS软件智能助手'}
          {message.role === 'assistant' && run?.finished_at && (
            <small title="包含等待时间">耗时 {elapsedRun(run)}</small>
          )}
        </div>
        {message.selections?.map((selection, index) => (
          <button
            className="context-citation"
            key={index}
            title={selection.path}
            onClick={() =>
              setPreview({
                ...selection,
                source_workspace_id:
                  selection.source_workspace_id || message.source_workspace_id || undefined,
              })
            }
          >
            <FileCode2 size={12} />
            {selection.path.split('/').at(-1)}
            <span>
              L{selection.start_line}–{selection.end_line}
            </span>
            {selection.stale && <span>旧版本</span>}
          </button>
        ))}
        {run && <RunTrace runId={run.id} />}
        <div>
          <Content
            content={message.content}
            runId={run?.id}
            sourceId={message.source_workspace_id || undefined}
          />
        </div>
        {message.role === 'assistant' && run?.status === 'completed' && (
          <RunKnowledgeSummary
            runId={run.id}
            answer={message.content}
            projectId={project.data?.id || useWorkspace.getState().projectId}
            recent={recent}
          />
        )}
      </div>
      <div className={`answer-actions ${message.role === 'user' ? 'question-actions' : ''}`}>
        {message.role === 'assistant' && (
          <>
            <button
              aria-label={copied ? '已复制回复' : '复制回复'}
              title={copied ? '已复制' : '复制回复'}
              onClick={() => void copy()}
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
            </button>
            {canRegenerate && run && (
              <button
                aria-label="重新生成回复"
                title="重新生成回复"
                onClick={() => onRegenerate(run.id)}
              >
                <RotateCcw size={14} />
              </button>
            )}
          </>
        )}
        {onEdit && (
          <button
            ref={editButton}
            aria-label="编辑最近问题"
            title="编辑问题并重新回答"
            onClick={() => setEditing(true)}
          >
            <Pencil size={14} />
          </button>
        )}
        {message.role === 'assistant' && (
          <button
            type="button"
            aria-label="反馈回复"
            title="反馈回复"
            onClick={() => toast('反馈功能暂未开放')}
          >
            <MessageSquare size={14} />
            <span>反馈</span>
          </button>
        )}
        {message.created_at && (
          <time
            dateTime={message.created_at}
            title={new Date(message.created_at).toLocaleString('zh-CN')}
          >
            {new Date(message.created_at).toLocaleTimeString('zh-CN', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </time>
        )}
      </div>
      <ErrorText error={error} />
      {preview && <SelectionPreview selection={preview} onClose={() => setPreview(undefined)} />}
    </div>
  );
}
