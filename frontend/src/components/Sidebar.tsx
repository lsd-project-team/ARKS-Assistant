import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ChevronRight,
  ChevronDown,
  FileCode2,
  Folder,
  FolderOpen,
  Search,
  Plus,
  MessageSquare,
  Pencil,
} from 'lucide-react';
import { api, query, jsonBody } from '../lib/api';
import { useWorkspace } from '../lib/store';
import type { FileEntry, Thread } from '../types';
import { Button, ErrorText } from './ui';

function FileNode({ entry, depth }: { entry: FileEntry; depth: number }) {
  const [expanded, setExpanded] = useState(false);
  const active = useWorkspace((state) => state.activePath === entry.path);
  const openFile = useWorkspace((state) => state.openFile);
  const children = useQuery({
    queryKey: ['files', entry.path],
    queryFn: () => api<FileEntry[]>(`/files?path=${query(entry.path)}`),
    enabled: expanded && !!entry.is_dir,
  });
  return (
    <>
      <button
        className={`file-row ${active ? 'active' : ''}`}
        style={{ paddingLeft: 12 + depth * 14 }}
        title={entry.path}
        onClick={() => (entry.is_dir ? setExpanded(!expanded) : openFile(entry.path))}
      >
        {entry.is_dir ? (
          expanded ? (
            <ChevronDown size={12} />
          ) : (
            <ChevronRight size={12} />
          )
        ) : (
          <span className="tree-spacer" />
        )}
        {entry.is_dir ? (
          expanded ? (
            <FolderOpen size={15} />
          ) : (
            <Folder size={15} />
          )
        ) : (
          <FileCode2 size={15} />
        )}
        <span>{entry.name}</span>
      </button>
      {expanded && (
        <>
          <ErrorText error={children.error} />
          {children.data?.map((child) => (
            <FileNode key={child.path} entry={child} depth={depth + 1} />
          ))}
        </>
      )}
    </>
  );
}

export function Sidebar() {
  const [filter, setFilter] = useState('');
  const [rename, setRename] = useState('');
  const [title, setTitle] = useState('');
  const { sidebar, setSidebar, threadId, selectThread } = useWorkspace();
  const cache = useQueryClient();
  const files = useQuery({
    queryKey: ['files', '', filter],
    queryFn: () => api<FileEntry[]>(`/files?query=${query(filter)}`),
  });
  const threads = useQuery({ queryKey: ['threads'], queryFn: () => api<Thread[]>('/threads') });
  const create = useMutation({
    mutationFn: () =>
      api<Thread>('/threads', { method: 'POST', body: jsonBody({ title: '新对话' }) }),
    onSuccess: (row) => {
      selectThread(row.id);
      cache.invalidateQueries({ queryKey: ['threads'] });
    },
  });
  async function saveTitle() {
    if (!title.trim()) return;
    await api(`/threads/${rename}`, { method: 'PATCH', body: jsonBody({ title: title.trim() }) });
    setRename('');
    cache.invalidateQueries({ queryKey: ['threads'] });
  }
  return (
    <aside className="sidebar">
      <div className="project-header">
        <div className="project-icon">
          <FolderOpen size={18} />
        </div>
        <div>
          <strong>trunk</strong>
          <span>本地源码工作区</span>
        </div>
        <span className="local-dot" title="本机运行" />
      </div>
      <div className="sidebar-switch">
        <button
          className={sidebar === 'files' ? 'selected' : ''}
          onClick={() => setSidebar('files')}
        >
          文件
        </button>
        <button
          className={sidebar === 'threads' ? 'selected' : ''}
          onClick={() => setSidebar('threads')}
        >
          对话 <span>{threads.data?.length || 0}</span>
        </button>
      </div>
      {sidebar === 'files' ? (
        <>
          <label className="search-box">
            <Search size={14} />
            <input
              aria-label="筛选文件"
              placeholder="搜索文件名…"
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
            />
            <kbd>⌕</kbd>
          </label>
          <div className="section-label">
            EXPLORER <span>只读</span>
          </div>
          <div className="sidebar-scroll">
            <ErrorText error={files.error} />
            {files.isPending && <p className="muted padded">正在读取文件…</p>}
            {files.data?.map((entry) => (
              <FileNode key={entry.path} entry={entry} depth={0} />
            ))}
            {files.data?.length === 0 && <p className="muted padded">没有匹配的文件</p>}
          </div>
        </>
      ) : (
        <>
          <div className="sidebar-actions">
            <Button onClick={() => create.mutate()} disabled={create.isPending}>
              <Plus size={14} />
              新建对话
            </Button>
          </div>
          <ErrorText error={create.error || threads.error} />
          <div className="sidebar-scroll">
            {threads.data?.map((thread) => (
              <div
                key={thread.id}
                className={`thread-row ${threadId === thread.id ? 'active' : ''}`}
              >
                {rename === thread.id ? (
                  <input
                    autoFocus
                    value={title}
                    aria-label="对话名称"
                    onChange={(e) => setTitle(e.target.value)}
                    onBlur={() => void saveTitle()}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') void saveTitle();
                      if (e.key === 'Escape') setRename('');
                    }}
                  />
                ) : (
                  <>
                    <button className="thread-select" onClick={() => selectThread(thread.id)}>
                      <MessageSquare size={14} />
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
          </div>
        </>
      )}
      <div className="sidebar-footer">
        <span className="tiny-dot" />
        Windows 本机<span>持久化已启用</span>
      </div>
    </aside>
  );
}
