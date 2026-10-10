import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronRight, ChevronDown, File, Search, PanelRightClose, Folder } from 'lucide-react';
import { api, query } from '../lib/api';
import { useWorkspace } from '../lib/store';
import type { FileEntry } from '../types';
import { ErrorText } from './ui';

function FileNode({ entry, depth }: { entry: FileEntry; depth: number }) {
  const activePath = useWorkspace((state) => state.activePath);
  const openFile = useWorkspace((state) => state.openFile);
  const [expanded, setExpanded] = useState(false);
  useEffect(() => {
    if (entry.is_dir && activePath.startsWith(`${entry.path}/`)) setExpanded(true);
  }, [activePath, entry.is_dir, entry.path]);
  const children = useQuery({
    queryKey: ['files', entry.path],
    queryFn: () => api<FileEntry[]>(`/files?path=${query(entry.path)}`),
    enabled: expanded && !!entry.is_dir,
  });
  return (
    <>
      <button
        className={`file-row ${activePath === entry.path ? 'active' : ''}`}
        style={{ paddingLeft: 10 + depth * 16 }}
        title={entry.path}
        aria-expanded={entry.is_dir ? expanded : undefined}
        onClick={() => (entry.is_dir ? setExpanded(!expanded) : openFile(entry.path))}
      >
        {entry.is_dir ? (
          expanded ? (
            <ChevronDown size={12} />
          ) : (
            <ChevronRight size={12} />
          )
        ) : (
          <File size={14} strokeWidth={1.5} />
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

export function FileExplorer({ onClose }: { onClose: () => void }) {
  const [filter, setFilter] = useState('');
  const [rootExpanded, setRootExpanded] = useState(true);
  const files = useQuery({
    queryKey: ['files', '', filter],
    queryFn: () => api<FileEntry[]>(`/files?query=${query(filter)}`),
  });
  return (
    <aside className="file-explorer" aria-label="源码文件树">
      <div className="explorer-heading">
        <span>
          <Folder size={15} />
          文件
        </span>
        <button aria-label="收起文件树" onClick={onClose}>
          <PanelRightClose size={16} />
        </button>
      </div>
      <label className="search-box">
        <Search size={14} />
        <input
          aria-label="筛选文件"
          placeholder="筛选文件…"
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
        />
      </label>
      <div className="explorer-scroll">
        <button
          className="tree-root"
          aria-expanded={rootExpanded}
          onClick={() => setRootExpanded(!rootExpanded)}
        >
          {rootExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}trunk
        </button>
        <ErrorText error={files.error} />
        {files.isPending && <p className="muted padded">正在读取文件…</p>}
        {rootExpanded &&
          files.data?.map((entry) => (
            <FileNode key={entry.path} entry={entry} depth={filter ? 0 : 1} />
          ))}
        {files.data?.length === 0 && <p className="muted padded">没有匹配的文件</p>}
      </div>
    </aside>
  );
}
