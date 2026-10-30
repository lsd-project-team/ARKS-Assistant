import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { MoreHorizontal, Pin, LoaderCircle, CircleAlert } from 'lucide-react';
import type { Thread } from '../../../shared/types/api';
import { threadStatus } from '../lib/conversationList';
import { Highlight } from '../../../shared/ui/markdown/Highlight';
import { usePopupPosition } from '../../../shared/hooks/usePopupPosition';

export type ThreadAction =
  'rename' | 'pin' | 'archive' | 'restore' | 'delete' | 'purge' | 'export' | 'up' | 'down' | 'move';
const labels: Record<ThreadAction, string> = {
  rename: '重命名',
  pin: '置顶',
  archive: '归档',
  restore: '恢复到最近对话',
  delete: '移入回收站',
  purge: '彻底删除',
  export: '导出对话',
  up: '向上移动',
  down: '向下移动',
  move: '移动至项目',
};

export function ThreadItem({
  row,
  selected,
  filter,
  busy,
  readOnly = false,
  onSelect,
  onAction,
  onRename,
}: {
  row: Thread;
  selected: boolean;
  filter: string;
  busy: boolean;
  readOnly?: boolean;
  onSelect: () => void;
  onAction: (action: ThreadAction) => void;
  onRename: (title: string) => Promise<unknown>;
}) {
  const [menu, setMenu] = useState<'trigger' | { top: number; left: number }>();
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(row.title);
  const [error, setError] = useState('');
  const cancelled = useRef(false);
  const saving = useRef(false);
  const popup = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const menuPosition = usePopupPosition(
    !!menu,
    popup,
    trigger,
    typeof menu === 'object' ? menu : undefined,
  );
  const pinned = row.pinned_order !== undefined && row.pinned_order !== null;
  useEffect(() => {
    if (menu && menuPosition.visibility === 'visible')
      popup.current
        ?.querySelector<HTMLButtonElement>('button:not(:disabled)')
        ?.focus({ preventScroll: true });
  }, [menu, menuPosition.visibility]);
  useEffect(() => {
    if (!menu) return;
    const close = (event: PointerEvent) => {
      if (
        !popup.current?.contains(event.target as Node) &&
        !trigger.current?.contains(event.target as Node)
      )
        setMenu(undefined);
    };
    const onScroll = (event: Event) => {
      if (!popup.current?.contains(event.target as Node)) setMenu(undefined);
    };
    document.addEventListener('pointerdown', close);
    window.addEventListener('scroll', onScroll, true);
    return () => {
      document.removeEventListener('pointerdown', close);
      window.removeEventListener('scroll', onScroll, true);
    };
  }, [menu]);
  async function save() {
    // Enter 后的失焦会再次触发保存；用同步标记守住同一次提交与 Esc 取消。
    if (saving.current || cancelled.current) return;
    if (!title.trim()) {
      setError('标题不能为空');
      return;
    }
    saving.current = true;
    try {
      await onRename(title.trim());
      setEditing(false);
      setError('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '保存失败');
    } finally {
      saving.current = false;
    }
  }
  function choose(action: ThreadAction) {
    setMenu(undefined);
    if (action === 'rename') {
      setTitle(row.title);
      cancelled.current = false;
      setEditing(true);
    } else {
      trigger.current?.focus();
      onAction(action);
    }
  }
  const actions: ThreadAction[] =
    row.state === 'deleted'
      ? ['restore', 'purge']
      : readOnly
        ? ['export']
        : row.state === 'archived'
          ? ['restore', 'rename', 'move', 'export', 'delete']
          : [
              'rename',
              'pin',
              ...(pinned ? (['up', 'down'] as ThreadAction[]) : []),
              'archive',
              'move',
              'export',
              'delete',
            ];
  return (
    <div
      className={`thread-row ${selected ? 'active' : ''} ${editing ? 'editing' : ''}`}
      onContextMenu={(event) => {
        if (editing) return;
        event.preventDefault();
        setMenu({
          left: event.clientX,
          top: event.clientY,
        });
      }}
    >
      {editing ? (
        <div className="thread-rename">
          <input
            autoFocus
            value={title}
            maxLength={120}
            aria-label="对话名称"
            disabled={busy}
            aria-invalid={!!error}
            onChange={(event) => setTitle(event.target.value)}
            onBlur={() => void save()}
            onKeyDown={(event) => {
              if (event.nativeEvent.isComposing) return;
              if (event.key === 'Enter') {
                event.preventDefault();
                void save();
              }
              if (event.key === 'Escape') {
                cancelled.current = true;
                setEditing(false);
                setError('');
              }
            }}
          />
          {error && <small role="alert">{error}</small>}
        </div>
      ) : (
        <>
          <button
            className="thread-select"
            title={row.title}
            aria-current={selected ? 'true' : undefined}
            disabled={row.state === 'deleted'}
            onClick={onSelect}
          >
            <span className="thread-title">
              <Highlight text={row.title} query={filter} />
            </span>
            {row.snippet && (
              <small className="thread-snippet">
                <Highlight text={row.snippet} query={filter} />
              </small>
            )}
          </button>
          <span className="thread-indicators" title={threadStatus(row.latest_status)}>
            {['running', 'queued'].includes(row.latest_status || '') ? (
              <LoaderCircle size={12} className="spin" />
            ) : row.latest_status === 'failed' ? (
              <CircleAlert size={12} />
            ) : row.has_unread && !selected ? (
              <span className="unread-dot" />
            ) : null}
            {pinned && <Pin size={11} />}
          </span>
          <button
            ref={trigger}
            className="thread-more"
            aria-label={`更多操作：${row.title}`}
            title="更多会话操作"
            aria-haspopup="menu"
            aria-expanded={!!menu}
            disabled={busy}
            onClick={() => {
              setMenu(menu ? undefined : 'trigger');
            }}
          >
            <MoreHorizontal size={15} />
          </button>
        </>
      )}
      {menu &&
        createPortal(
          <div
            className="thread-menu"
            role="menu"
            aria-label={`会话操作：${row.title}`}
            ref={popup}
            style={menuPosition}
            onKeyDown={(event) => {
              if (event.key === 'Escape') {
                setMenu(undefined);
                trigger.current?.focus();
                return;
              }
              if (event.key === 'Tab') {
                setMenu(undefined);
                trigger.current?.focus();
                return;
              }
              if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
              event.preventDefault();
              const items = Array.from(
                event.currentTarget.querySelectorAll<HTMLButtonElement>('button:not(:disabled)'),
              );
              const index = items.indexOf(document.activeElement as HTMLButtonElement);
              const next =
                event.key === 'Home'
                  ? 0
                  : event.key === 'End'
                    ? items.length - 1
                    : (index + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
              items[next]?.focus();
            }}
          >
            {actions.map((action) => (
              <button
                key={action}
                role="menuitem"
                disabled={busy}
                className={['delete', 'purge'].includes(action) ? 'danger' : ''}
                onClick={() => choose(action)}
              >
                {action === 'pin' && pinned ? '取消置顶' : labels[action]}
              </button>
            ))}
          </div>,
          document.body,
        )}
    </div>
  );
}
