import { useProjectApi } from '../hooks/useProjectApi';
import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ChevronRight,
  ChevronDown,
  Search,
  Folder,
  LocateFixed,
  ListCollapse,
  X,
} from 'lucide-react';
import { query } from '../lib/api';
import { useWorkspace } from '../lib/store';
import type { FileEntry } from '../types';
import { ErrorText } from './ui';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { useExplorerScroll } from '../hooks/useExplorerScroll';
import { FileNode } from './FileNode';
import { useCurrentProject } from '../hooks/useProjects';

export function FileExplorer({
  hidden = false,
  onClose,
  onQuickOpen,
}: {
  hidden?: boolean;
  onClose: () => void;
  onQuickOpen: () => void;
}) {
  const api = useProjectApi();
  const [filter, setFilter] = useState('');
  const project = useCurrentProject();
  const rootName = project.data?.source_folders?.length
    ? project.data.name
    : project.data?.source_root?.split(/[\\/]/).filter(Boolean).at(-1) || '源码';
  const settledFilter = useDebouncedValue(filter.trim());
  const rootExpanded = useWorkspace((state) => state.rootExpanded);
  const revealTime = useWorkspace((state) => state.revealTime);
  const activePath = useWorkspace((state) => state.activePath);
  const scroll = useRef<HTMLDivElement>(null);
  const onScroll = useExplorerScroll(scroll, settledFilter);
  useEffect(() => {
    if (revealTime) setFilter('');
  }, [revealTime]);
  const files = useQuery({
    queryKey: ['files', '', settledFilter],
    queryFn: () => api<FileEntry[]>(`/files?query=${query(settledFilter)}`),
  });
  return (
    <aside className="file-explorer" aria-label="源码文件树" hidden={hidden}>
      <div className="explorer-heading">
        <span>
          <Folder size={15} />
          文件
        </span>
        <div className="explorer-tools">
          <button
            aria-label="定位当前文件"
            title="定位当前文件"
            disabled={!activePath}
            onClick={() => useWorkspace.getState().revealFile()}
          >
            <LocateFixed size={15} />
          </button>
          <button
            aria-label="全部折叠"
            title="全部折叠"
            onClick={() => useWorkspace.getState().collapseDirectories()}
          >
            <ListCollapse size={15} />
          </button>
          <button aria-label="关闭文件列表" title="关闭文件列表" onClick={onClose}>
            <X size={16} />
          </button>
        </div>
      </div>
      <label className="search-box">
        <Search size={14} />
        <input
          aria-label="筛选文件"
          placeholder="筛选文件…"
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
        />
        {filter && (
          <button aria-label="清除文件筛选" onClick={() => setFilter('')}>
            <X size={13} />
          </button>
        )}
      </label>
      <button className="quick-open-trigger" onClick={onQuickOpen}>
        快速打开<kbd>Ctrl P</kbd>
      </button>
      <div
        className={`explorer-scroll ${settledFilter ? 'filtered' : ''}`}
        ref={scroll}
        onScroll={onScroll}
        role="tree"
        aria-label={settledFilter ? '筛选结果' : `${rootName} 文件`}
        onKeyDown={(event) => {
          if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
          const rows = Array.from(
            event.currentTarget.querySelectorAll<HTMLElement>('[role="treeitem"]'),
          );
          const index = rows.indexOf(document.activeElement as HTMLElement);
          const next =
            event.key === 'Home'
              ? 0
              : event.key === 'End'
                ? rows.length - 1
                : index + (event.key === 'ArrowDown' ? 1 : -1);
          event.preventDefault();
          rows[Math.max(0, Math.min(rows.length - 1, next))]?.focus();
        }}
      >
        {!settledFilter && (
          <button
            className="tree-root"
            aria-expanded={rootExpanded}
            role="treeitem"
            aria-level={1}
            data-path=""
            onClick={() => useWorkspace.getState().setRootExpanded(!rootExpanded)}
          >
            {rootExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            {rootName}
          </button>
        )}
        <ErrorText error={files.error} />
        {files.isPending && (
          <p className="muted padded" data-tree-loading>
            正在读取文件…
          </p>
        )}
        {(rootExpanded || !!settledFilter) &&
          files.data?.map((entry) => (
            <FileNode
              key={entry.path}
              entry={entry}
              depth={settledFilter ? 0 : 1}
              highlightQuery={settledFilter}
            />
          ))}
        {files.data?.length === 0 && <p className="muted padded">没有匹配的文件</p>}
      </div>
    </aside>
  );
}
