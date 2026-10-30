import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { useInfiniteQuery } from '@tanstack/react-query';
import { Search, X, MessageSquare, LoaderCircle } from 'lucide-react';
import { api } from '../../../app/api/client';
import { useWorkspace } from '../../../app/state/store';
import { conversationGroup } from '../lib/conversationList';
import {
  conversationSearchPageSize,
  conversationSearchTitle,
  searchConversations,
} from '../lib/conversationSearch';
import type { SidebarView } from '../lib/sidebarNavigation';
import { useDebouncedValue } from '../../../shared/hooks/useDebouncedValue';
import type { Thread } from '../../../shared/types/api';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { Highlight } from '../../../shared/ui/markdown/Highlight';
import { Select } from '../../../shared/ui/Select';

export function ConversationSearchDialog({
  view,
  onNavigate,
}: {
  view: SidebarView;
  onNavigate: (row: Thread) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <button
          aria-label="搜索对话"
          title={`${conversationSearchTitle(view)}：标题、正文和代码选区`}
        >
          <Search size={15} />
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="modal-overlay conversation-search-overlay" />
        <Dialog.Content className="modal-content conversation-search-dialog">
          <Dialog.Title className="conversation-search-accessible">
            {conversationSearchTitle(view)}
          </Dialog.Title>
          <Dialog.Description className="conversation-search-accessible">
            {conversationSearchTitle(view)}的标题、正文和代码选区；方向键选择，Enter{' '}
            {view === 'deleted' ? '定位' : '打开'}，Esc 关闭。
          </Dialog.Description>
          <ConversationSearchBody
            view={view}
            onChoose={(row) => {
              setOpen(false);
              onNavigate(row);
            }}
          />
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function ConversationSearchBody({
  view,
  onChoose,
}: {
  view: SidebarView;
  onChoose: (row: Thread) => void;
}) {
  const [filter, setFilter] = useState('');
  const [scope, setScope] = useState(view === 'active' ? 'current' : 'all');
  const [selected, setSelected] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const listId = useId();
  const trimmed = filter.trim();
  const settled = useDebouncedValue(trimmed);
  const { projectId, selectThread, jumpToMessage } = useWorkspace();
  const threads = useInfiniteQuery({
    queryKey: ['threads', 'search', view, projectId, settled, scope],
    initialPageParam: 0,
    queryFn: ({ pageParam, signal }) =>
      searchConversations(api, {
        filter: settled,
        offset: pageParam,
        signal,
        projectId,
        all: scope === 'all',
        view,
      }),
    getNextPageParam: (page, _pages, previous) =>
      page.hasMore ? previous + conversationSearchPageSize : undefined,
  });
  // 防抖期间隐藏旧结果，避免 Enter 打开上一个关键词的命中。
  const entries = trimmed === settled ? threads.data?.pages.flatMap((page) => page.rows) || [] : [];
  if (settled) entries.sort((left, right) => right.updated_at.localeCompare(left.updated_at));
  const activeIndex = Math.min(selected, Math.max(0, entries.length - 1));
  const waiting = trimmed !== settled || threads.isPending;
  useEffect(() => {
    document.getElementById(`${listId}-${activeIndex}`)?.scrollIntoView({ block: 'nearest' });
  }, [listId, activeIndex, entries.length]);

  function choose(row: Thread) {
    // 已删除对话先定位到回收站条目，保持当前聊天和项目，恢复后才能打开。
    if (row.state === 'deleted') {
      onChoose(row);
      return;
    }
    useWorkspace.getState().switchProject(row.project_id || 'independent');
    if (row.matched_message_id) jumpToMessage(row.id, row.matched_message_id);
    else selectThread(row.id);
    useWorkspace.getState().setThreadEntry(row.id, 'recent');
    onChoose(row);
  }
  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    // 中文输入法确认候选词时，不将 Enter 当成打开会话。
    if (event.nativeEvent.isComposing) return;
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      setSelected(
        Math.max(
          0,
          Math.min(entries.length - 1, activeIndex + (event.key === 'ArrowDown' ? 1 : -1)),
        ),
      );
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      if (entries[activeIndex]) choose(entries[activeIndex]);
    }
  }
  return (
    <>
      <div className="conversation-search-input">
        <Search size={19} aria-hidden="true" />
        <input
          ref={input}
          autoFocus
          role="combobox"
          aria-label="搜索对话"
          aria-expanded="true"
          aria-autocomplete="list"
          aria-controls={listId}
          aria-activedescendant={entries[activeIndex] ? `${listId}-${activeIndex}` : undefined}
          autoComplete="off"
          maxLength={300}
          placeholder={`${conversationSearchTitle(view)}…`}
          value={filter}
          onChange={(event) => {
            setFilter(event.target.value);
            setSelected(0);
          }}
          onKeyDown={handleKeyDown}
        />
        {filter && (
          <button
            className="conversation-search-clear"
            aria-label="清除搜索"
            onClick={() => {
              setFilter('');
              setSelected(0);
              input.current?.focus();
            }}
          >
            <X size={15} />
          </button>
        )}
        <Dialog.Close asChild>
          <button className="conversation-search-close" aria-label="关闭搜索" title="Esc 关闭">
            <kbd>Esc</kbd>
          </button>
        </Dialog.Close>
      </div>
      <div className="conversation-search-section project-search-scope">
        <span>
          {trimmed
            ? '搜索结果'
            : view === 'active'
              ? '最近对话'
              : view === 'archived'
                ? '已归档对话'
                : '已删除对话'}
        </span>
        <Select value={scope} onValueChange={setScope} aria-label="对话搜索范围">
          <option value="current">
            当前项目{view === 'active' ? '' : view === 'archived' ? '的归档对话' : '的已删除对话'}
          </option>
          <option value="all">
            {view === 'active'
              ? '全部项目与独立对话'
              : view === 'archived'
                ? '全部归档范围'
                : '全部已删除对话'}
          </option>
        </Select>
      </div>
      <div className="conversation-search-results" aria-busy={waiting}>
        <ErrorText error={trimmed === settled ? threads.error : undefined} />
        <div
          id={listId}
          role="listbox"
          aria-label={
            trimmed
              ? '匹配对话'
              : view === 'active'
                ? '最近对话'
                : view === 'archived'
                  ? '已归档对话'
                  : '已删除对话'
          }
        >
          {entries.map((row, index) => (
            <ConversationSearchResult
              key={row.id}
              id={`${listId}-${index}`}
              row={row}
              filter={settled}
              selected={index === activeIndex}
              onHover={() => setSelected(index)}
              onChoose={() => choose(row)}
            />
          ))}
        </div>
        {!entries.length && !threads.isError && (
          <p className="conversation-search-empty" role="status">
            {waiting
              ? '正在查找…'
              : trimmed
                ? '没有匹配的对话，试试其他关键词'
                : view === 'active'
                  ? '暂无最近对话'
                  : view === 'archived'
                    ? '暂无归档对话'
                    : '回收站为空'}
          </p>
        )}
        {threads.hasNextPage && !waiting && (
          <Button
            className="conversation-search-more"
            disabled={threads.isFetchingNextPage}
            onClick={() => void threads.fetchNextPage()}
          >
            {threads.isFetchingNextPage && <LoaderCircle size={13} className="spin" />}
            加载更多
          </Button>
        )}
      </div>
      <div className="conversation-search-footer">
        <span>
          <kbd>↑</kbd>
          <kbd>↓</kbd> 选择
        </span>
        <span>
          <kbd>Enter</kbd> {view === 'deleted' ? '定位' : '打开'}
        </span>
        <span>
          <kbd>Esc</kbd> 关闭
        </span>
      </div>
    </>
  );
}

function ConversationSearchResult({
  id,
  row,
  filter,
  selected,
  onHover,
  onChoose,
}: {
  id: string;
  row: Thread;
  filter: string;
  selected: boolean;
  onHover: () => void;
  onChoose: () => void;
}) {
  return (
    <button
      id={id}
      role="option"
      aria-selected={selected}
      tabIndex={-1}
      className="conversation-search-result"
      title={row.title}
      onMouseEnter={onHover}
      onClick={onChoose}
    >
      <MessageSquare size={16} aria-hidden="true" />
      <span className="conversation-search-copy">
        <strong>
          <Highlight text={row.title} query={filter} />
        </strong>
        {row.project_name && <small>{row.project_name}</small>}
        {filter && row.snippet && row.snippet !== row.title && (
          <small>
            <Highlight text={row.snippet} query={filter} />
          </small>
        )}
      </span>
      <span className="conversation-search-meta">
        {row.state === 'deleted'
          ? '已删除'
          : row.state === 'archived'
            ? '已归档'
            : row.project_state === 'archived'
              ? '已归档项目'
              : conversationGroup(row)}
      </span>
    </button>
  );
}
