import { useProjectApi } from '../hooks/useProjectApi';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { query } from '../lib/api';
import { useWorkspace } from '../lib/store';
import type { FileEntry } from '../types';
import { FileIcon } from './FileIcon';
import { Highlight } from './Highlight';
import { ErrorText } from './ui';

export function FileNode({
  entry,
  depth,
  highlightQuery = '',
}: {
  entry: FileEntry;
  depth: number;
  highlightQuery?: string;
}) {
  const api = useProjectApi();
  const activePath = useWorkspace((state) => state.activePath);
  const expanded = useWorkspace((state) => state.expandedDirectories.includes(entry.path));
  const setExpanded = (value: boolean) =>
    useWorkspace.getState().setDirectoryExpanded(entry.path, value);
  const children = useQuery({
    queryKey: ['files', entry.path],
    queryFn: () => api<FileEntry[]>(`/files?path=${query(entry.path)}`),
    enabled: expanded && !!entry.is_dir,
  });
  return (
    <>
      <button
        className={`file-row ${activePath === entry.path ? 'active' : ''}`}
        style={{ paddingLeft: 8 + depth * 12 }}
        title={entry.path}
        data-path={entry.path}
        role="treeitem"
        aria-level={depth + 1}
        aria-selected={!entry.is_dir && activePath === entry.path}
        aria-expanded={entry.is_dir ? expanded : undefined}
        onClick={() =>
          entry.is_dir
            ? setExpanded(!expanded)
            : useWorkspace.getState().openFile(entry.path, undefined, 'preview')
        }
        onDoubleClick={() => !entry.is_dir && useWorkspace.getState().keepFile(entry.path)}
        onKeyDown={(event) => {
          if (event.key === 'ArrowRight' && entry.is_dir) {
            event.preventDefault();
            setExpanded(true);
          }
          if (event.key !== 'ArrowLeft') return;
          event.preventDefault();
          if (entry.is_dir && expanded) setExpanded(false);
          else
            event.currentTarget
              .closest('[role="tree"]')
              ?.querySelector<HTMLElement>(
                `[data-path="${CSS.escape(entry.path.split('/').slice(0, -1).join('/'))}"]`,
              )
              ?.focus();
        }}
      >
        {entry.is_dir ? (
          expanded ? (
            <ChevronDown size={12} />
          ) : (
            <ChevronRight size={12} />
          )
        ) : (
          <FileIcon name={entry.name} />
        )}
        <span className="file-name">
          <Highlight text={entry.name} query={highlightQuery} />
          {highlightQuery && (
            <small>
              <Highlight
                text={entry.path.split('/').slice(0, -1).join('/') || 'trunk'}
                query={highlightQuery}
              />
            </small>
          )}
        </span>
      </button>
      {expanded && entry.is_dir && (
        <>
          <ErrorText error={children.error} />
          {children.isPending && (
            <p className="muted padded" data-tree-loading>
              正在读取目录…
            </p>
          )}
          {children.data?.map((child) => (
            <FileNode key={child.path} entry={child} depth={depth + 1} />
          ))}
        </>
      )}
    </>
  );
}
