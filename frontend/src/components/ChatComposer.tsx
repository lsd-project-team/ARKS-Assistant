import { useId, useLayoutEffect, useState, type ReactNode, type RefObject } from 'react';
import { ArrowUp, ListPlus, Plus, Square, Zap } from 'lucide-react';
import { exactCommand, matchingCommands, type ComposerCommand } from '../lib/composerCommands';
import { Button } from './ui';

export function ChatComposer({
  inputRef,
  draft,
  onChange,
  onSend,
  onCommand,
  onStop,
  onShowSource,
  sending,
  busy,
  queueing = false,
  stopping,
  canContext,
  canCompact,
  compactDisabledReason,
  model,
  modelControl,
  context,
  readOnly = false,
}: {
  inputRef: RefObject<HTMLTextAreaElement | null>;
  draft: string;
  onChange: (content: string) => void;
  onSend: () => void;
  onCommand: (command: ComposerCommand) => void;
  onStop: () => void;
  onShowSource: () => void;
  sending: boolean;
  busy: boolean;
  queueing?: boolean;
  stopping: boolean;
  canContext: boolean;
  canCompact: boolean;
  compactDisabledReason: string;
  model: string;
  modelControl?: ReactNode;
  context: ReactNode;
  readOnly?: boolean;
}) {
  const listId = useId();
  useLayoutEffect(() => {
    const input = inputRef.current;
    if (!input) return;
    input.style.height = 'auto';
    input.style.height = `${Math.min(240, Math.max(48, input.scrollHeight))}px`;
    input.style.overflowY = input.scrollHeight > 240 ? 'auto' : 'hidden';
  }, [draft, inputRef]);
  const [selected, setSelected] = useState(0);
  const [dismissed, setDismissed] = useState(false);
  const matches = matchingCommands(draft);
  const menuOpen = !dismissed && matches.length > 0;
  const selectedCommand = matches[Math.min(selected, matches.length - 1)];
  const available = (command: ComposerCommand) => (command === 'context' ? canContext : canCompact);
  const command = exactCommand(draft) || (menuOpen ? selectedCommand?.id : undefined);
  const canSubmit = !sending && !readOnly && (command ? available(command) : !!draft.trim());
  function submit() {
    if (!canSubmit) return;
    if (command) {
      setDismissed(true);
      onCommand(command);
    } else onSend();
  }
  return (
    <form
      className="composer"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) {
          setDismissed(true);
        }
      }}
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      {menuOpen && (
        <div className="composer-commands" id={listId} role="listbox" aria-label="输入框命令">
          {matches.map((item, index) => (
            <button
              key={item.id}
              id={`${listId}-${item.id}`}
              type="button"
              role="option"
              aria-selected={selectedCommand?.id === item.id}
              aria-disabled={!available(item.id)}
              className={selectedCommand?.id === item.id ? 'selected' : ''}
              onMouseDown={(event) => event.preventDefault()}
              onMouseEnter={() => setSelected(index)}
              onClick={() => {
                if (available(item.id)) {
                  setDismissed(true);
                  onCommand(item.id);
                }
              }}
            >
              <span>
                <code>/{item.id}</code>
                <strong>{item.label}</strong>
              </span>
              <small>
                {available(item.id)
                  ? item.description
                  : item.id === 'context'
                    ? '请先开始一段对话'
                    : compactDisabledReason}
              </small>
            </button>
          ))}
          <div className="command-keyboard-hint">↑ ↓ 选择 · Enter 执行 · Esc 收起</div>
        </div>
      )}
      <textarea
        ref={inputRef}
        value={draft}
        disabled={sending || readOnly}
        onChange={(event) => {
          onChange(event.target.value);
          setSelected(0);
          setDismissed(false);
        }}
        placeholder={readOnly ? '项目已归档，恢复后可以继续对话' : '询问代码，或输入 / 使用命令…'}
        aria-label="对话输入"
        aria-controls={menuOpen ? listId : undefined}
        aria-expanded={menuOpen}
        aria-autocomplete="list"
        aria-activedescendant={menuOpen ? `${listId}-${selectedCommand.id}` : undefined}
        rows={2}
        onKeyDown={(event) => {
          if (event.nativeEvent.isComposing) return;
          if (menuOpen && ['ArrowUp', 'ArrowDown'].includes(event.key)) {
            event.preventDefault();
            const direction = event.key === 'ArrowDown' ? 1 : -1;
            setSelected((value) => (value + direction + matches.length) % matches.length);
          } else if (menuOpen && event.key === 'Escape') {
            event.preventDefault();
            setDismissed(true);
          } else if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            submit();
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
          {modelControl || (
            <span className="model-label" title={model}>
              <Zap size={12} fill="currentColor" />
              <span>{model}</span>
            </span>
          )}
        </div>
        <div className="composer-send-actions">
          {busy && (
            <Button
              type="button"
              className="send-button stop"
              aria-label="停止回复"
              disabled={stopping}
              onClick={onStop}
            >
              <Square size={13} fill="currentColor" />
            </Button>
          )}
          {(!busy || !!draft.trim()) && (
            <Button
              className="send-button"
              type="submit"
              aria-label={command ? '执行命令' : busy || queueing ? '加入等待发送队列' : '发送消息'}
              title={
                busy || queueing
                  ? '加入队列，按顺序发送；Shift + Enter 换行'
                  : 'Enter 执行，Shift + Enter 换行'
              }
              disabled={!canSubmit}
            >
              {busy || queueing ? <ListPlus size={17} /> : <ArrowUp size={17} />}
            </Button>
          )}
        </div>
      </div>
      {context}
    </form>
  );
}
