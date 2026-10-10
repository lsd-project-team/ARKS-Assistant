import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Folder, ChevronDown, Search, SquarePen, Pencil, PanelLeftClose } from 'lucide-react';
import { api, jsonBody } from '../lib/api';
import { useWorkspace } from '../lib/store';
import type { Thread } from '../types';
import { ErrorText } from './ui';

interface SidebarProps {
  onCollapse: () => void;
  onNavigate: () => void;
  onShowSource: () => void;
  connected: boolean;
}

export function Sidebar({ onCollapse, onNavigate, onShowSource, connected }: SidebarProps) {
  const [filter, setFilter] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const [rename, setRename] = useState('');
  const [title, setTitle] = useState('');
  const [error, setError] = useState<unknown>();
  const { threadId, selectThread } = useWorkspace();
  const cache = useQueryClient();
  const threads = useQuery({ queryKey: ['threads'], queryFn: () => api<Thread[]>('/threads') });
  const create = useMutation({
    mutationFn: () =>
      api<Thread>('/threads', { method: 'POST', body: jsonBody({ title: '新对话' }) }),
    onSuccess: (row) => {
      selectThread(row.id);
      onNavigate();
      void cache.invalidateQueries({ queryKey: ['threads'] });
    },
  });
  async function saveTitle() {
    if (!title.trim() || !rename) return;
    try {
      await api(`/threads/${rename}`, { method: 'PATCH', body: jsonBody({ title: title.trim() }) });
      setRename('');
      setError(undefined);
      void cache.invalidateQueries({ queryKey: ['threads'] });
      void cache.invalidateQueries({ queryKey: ['thread', rename] });
    } catch (reason) {
      setError(reason);
    }
  }
  const visibleThreads = threads.data?.filter((thread) =>
    thread.title.toLocaleLowerCase().includes(filter.toLocaleLowerCase()),
  );
  return (
    <aside className="sidebar" aria-label="会话导航">
      <div className="sidebar-heading">
        <strong>Trunk</strong>
        <div>
          <button
            aria-label="搜索对话"
            onClick={() => {
              setSearchOpen(!searchOpen);
              setFilter('');
            }}
          >
            <Search size={15} />
          </button>
          <button aria-label="折叠侧栏" onClick={onCollapse}>
            <PanelLeftClose size={16} />
          </button>
        </div>
      </div>
      <button className="new-chat" onClick={() => create.mutate()} disabled={create.isPending}>
        <SquarePen size={16} />
        新对话
      </button>
      {searchOpen && (
        <label className="search-box thread-search">
          <Search size={14} />
          <input
            autoFocus
            aria-label="搜索对话"
            placeholder="搜索对话…"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
          />
        </label>
      )}
      <div className="sidebar-scroll">
        <div className="section-label">项目</div>
        <button className="project-row" onClick={onShowSource}>
          <Folder size={16} />
          <span>trunk</span>
          <ChevronDown size={12} />
        </button>
        <div className="section-label recent-label">最近对话</div>
        <ErrorText error={create.error || threads.error || error} />
        {visibleThreads?.map((thread) => (
          <div key={thread.id} className={`thread-row ${threadId === thread.id ? 'active' : ''}`}>
            {rename === thread.id ? (
              <input
                autoFocus
                value={title}
                aria-label="对话名称"
                onChange={(event) => setTitle(event.target.value)}
                onBlur={() => void saveTitle()}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') void saveTitle();
                  if (event.key === 'Escape') setRename('');
                }}
              />
            ) : (
              <>
                <button
                  className="thread-select"
                  title={thread.title}
                  onClick={() => {
                    selectThread(thread.id);
                    onNavigate();
                  }}
                >
                  <span>{thread.title}</span>
                </button>
                <button
                  className="rename-button"
                  aria-label={`重命名${thread.title}`}
                  onClick={() => {
                    setRename(thread.id);
                    setTitle(thread.title);
                  }}
                >
                  <Pencil size={12} />
                </button>
              </>
            )}
          </div>
        ))}
        {visibleThreads?.length === 0 && (
          <p className="muted sidebar-empty">{filter ? '没有匹配的对话' : '从新对话开始'}</p>
        )}
      </div>
      <div className={`sidebar-footer ${connected ? '' : 'offline'}`}>
        <span className="tiny-dot" />
        <span>{connected ? '本机工作区' : '服务未连接'}</span>
      </div>
    </aside>
  );
}
