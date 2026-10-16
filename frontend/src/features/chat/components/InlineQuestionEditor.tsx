import { useLayoutEffect, useRef, useState } from 'react';
import { ErrorText } from '../../../shared/ui/ui';

export function InlineQuestionEditor({
  content,
  onSubmit,
  onCancel,
}: {
  content: string;
  onSubmit?: (content: string) => Promise<unknown>;
  onCancel: () => void;
}) {
  const [text, setText] = useState(content);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const input = useRef<HTMLTextAreaElement>(null);
  const submitting = useRef(false);
  useLayoutEffect(() => {
    const element = input.current;
    if (!element) return;
    element.style.height = 'auto';
    element.style.height = `${Math.min(280, Math.max(40, element.scrollHeight))}px`;
    element.style.overflowY = element.scrollHeight > 280 ? 'auto' : 'hidden';
  }, [text]);
  async function submit() {
    if (submitting.current || !onSubmit || !text.trim()) return;
    submitting.current = true;
    setBusy(true);
    setError(undefined);
    try {
      await onSubmit(text.trim());
    } catch (reason) {
      setError(reason);
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }
  return (
    <form
      className="message user inline-question-editor"
      aria-label="编辑最近问题"
      aria-busy={busy}
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <textarea
        ref={input}
        autoFocus
        aria-label="编辑问题内容"
        value={text}
        rows={1}
        disabled={busy}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => {
          if (event.nativeEvent.isComposing) return;
          if (event.key === 'Escape' && !busy) {
            event.preventDefault();
            onCancel();
          } else if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            void submit();
          }
        }}
      />
      <ErrorText error={error} />
      <div className="inline-question-actions">
        <button type="button" disabled={busy} onClick={onCancel}>
          取消
        </button>
        <button
          type="submit"
          className="inline-question-send"
          title="发送修改并重新回答"
          disabled={busy || !onSubmit || !text.trim()}
        >
          {busy ? '发送中…' : '发送'}
        </button>
      </div>
    </form>
  );
}
