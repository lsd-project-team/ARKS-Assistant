import { useState } from 'react';
import { ListOrdered, Pencil, X } from 'lucide-react';
import type { QueuedQuestion } from '../../../shared/types/api';
import type { useQuestionQueue } from '../hooks/useQuestionQueue';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { QuestionEditor } from './QuestionEditor';
import { toast } from '../../../shared/utils/toasts';

export function QuestionQueuePanel({
  queue,
  threadId,
}: {
  queue: ReturnType<typeof useQuestionQueue>;
  threadId: string;
}) {
  const [editing, setEditing] = useState<QueuedQuestion>();
  const state = queue.query.data;
  // 出队后的编辑窗口仍保留输入，让过期提交的错误可以被用户看到。
  if (!state?.items.length && !editing) return <ErrorText error={queue.query.error} />;
  async function remove(item: QueuedQuestion) {
    try {
      await queue.remove.mutateAsync(item);
      toast('待发送问题已移除');
    } catch (error) {
      toast(error instanceof Error ? error.message : '移除失败，请重试', undefined, 'error');
    }
  }
  return (
    <div className="question-queue">
      {!!state?.items.length && (
        <details open={state.paused || undefined}>
          <summary>
            <ListOrdered size={14} />
            <span>等待发送 · {state.items.length} 个问题</span>
            <small>{state.paused ? '已暂停' : '依次发送'}</small>
          </summary>
          <div className="queue-controls">
            <span>
              {state.paused ? '停止或失败后，等待你继续发送。' : '当前回复完成后依次发送。'}
            </span>
            <Button
              disabled={queue.control.isPending}
              onClick={() =>
                queue.control.mutate({ id: threadId, action: state.paused ? 'continue' : 'pause' })
              }
            >
              {state.paused ? '继续发送队列' : '暂停队列'}
            </Button>
          </div>
          <ol>
            {state.items.map((item) => (
              <li key={item.id}>
                <button
                  className="queue-question"
                  onClick={() => setEditing(item)}
                  title={item.content}
                >
                  <span>{item.content}</span>
                  {item.selections.length > 0 && <small>{item.selections.length} 个选区</small>}
                </button>
                <button
                  aria-label={`编辑待发送问题 ${item.content}`}
                  onClick={() => setEditing(item)}
                >
                  <Pencil size={13} />
                </button>
                <button
                  aria-label={`取消待发送问题 ${item.content}`}
                  disabled={queue.remove.isPending && queue.remove.variables?.id === item.id}
                  onClick={() => void remove(item)}
                >
                  <X size={14} />
                </button>
              </li>
            ))}
          </ol>
          <ErrorText error={queue.control.error} />
        </details>
      )}
      {editing && (
        <QuestionEditor
          key={editing.id}
          title="编辑待发送问题"
          content={editing.content}
          selections={editing.selections}
          sourceOptions={editing.source_options}
          submitLabel="保存待发送问题"
          onClose={() => setEditing(undefined)}
          onSubmit={async (content, selections, source_options) => {
            await queue.edit.mutateAsync({
              item: editing,
              draft: { content, selections, source_options },
            });
            toast('待发送问题已更新');
          }}
        />
      )}
    </div>
  );
}
