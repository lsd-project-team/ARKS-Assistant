import { useProjectApi } from '../hooks/useProjectApi';
import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search } from 'lucide-react';
import { query } from '../lib/api';
import { useWorkspace } from '../lib/store';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import type { FileEntry } from '../types';
import { Modal, ErrorText } from './ui';
import { FileIcon } from './FileIcon';
import { Highlight } from './Highlight';

export function QuickOpen({
  open,
  onOpen,
  onClose,
}: {
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
}) {
  const api = useProjectApi();
  const [filter, setFilter] = useState('');
  const [selected, setSelected] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const settled = useDebouncedValue(filter.trim());
  const openFile = useWorkspace((state) => state.openFile);
  const files = useQuery({
    queryKey: ['quick-open', settled],
    queryFn: () => api<FileEntry[]>(`/files/quick-open?query=${query(settled)}`),
    enabled: open,
  });
  const entries = filter.trim() === settled ? files.data || [] : [];
  useEffect(() => {
    function shortcut(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'p') {
        event.preventDefault();
        onOpen();
      }
    }
    window.addEventListener('keydown', shortcut);
    return () => window.removeEventListener('keydown', shortcut);
  }, [onOpen]);
  useEffect(() => {
    if (open) {
      setFilter('');
      setSelected(0);
    }
  }, [open]);
  useEffect(() => {
    document.getElementById(`quick-file-${selected}`)?.scrollIntoView({ block: 'nearest' });
  }, [selected]);
  function choose(path: string) {
    openFile(path);
    onClose();
  }
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="快速打开文件"
      className="quick-open-dialog"
      description="输入文件名或路径；方向键选择，Enter 打开，Esc 关闭。"
    >
      <div className="quick-open-body">
        <label className="search-box quick-open-search">
          <Search size={16} />
          <input
            ref={input}
            autoFocus
            role="combobox"
            aria-label="快速查找文件"
            aria-expanded={open}
            aria-controls="quick-files"
            aria-activedescendant={entries[selected] ? `quick-file-${selected}` : undefined}
            autoComplete="off"
            value={filter}
            placeholder="文件名或路径…"
            onChange={(event) => {
              setFilter(event.target.value);
              setSelected(0);
            }}
            onKeyDown={(event) => {
              if (['ArrowDown', 'ArrowUp'].includes(event.key)) {
                event.preventDefault();
                setSelected((index) =>
                  Math.max(
                    0,
                    Math.min(entries.length - 1, index + (event.key === 'ArrowDown' ? 1 : -1)),
                  ),
                );
              }
              if (event.key === 'Enter' && entries[selected]) {
                event.preventDefault();
                choose(entries[selected].path);
              }
            }}
          />
        </label>
        <ErrorText error={files.error} />
        <div className="quick-file-list" id="quick-files" role="listbox" aria-label="匹配文件">
          {entries.map((entry, index) => (
            <button
              key={entry.path}
              id={`quick-file-${index}`}
              role="option"
              aria-selected={index === selected}
              className={index === selected ? 'selected' : ''}
              onMouseEnter={() => setSelected(index)}
              onClick={() => choose(entry.path)}
            >
              <FileIcon name={entry.name} />
              <span>
                <strong>
                  <Highlight text={entry.name} query={settled} />
                </strong>
                <small>
                  <Highlight text={entry.path} query={settled} />
                </small>
              </span>
            </button>
          ))}
          {!entries.length && (
            <p className="muted padded">
              {files.isFetching || filter.trim() !== settled ? '正在查找…' : '没有匹配文件'}
            </p>
          )}
        </div>
      </div>
    </Modal>
  );
}
