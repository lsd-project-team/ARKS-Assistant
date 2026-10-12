import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { usePopupPosition } from '../hooks/usePopupPosition';
import {
  ArrowLeft,
  ArrowRight,
  Copy,
  Check,
  PanelRight,
  Code2,
  BookOpen,
  MoreHorizontal,
  Search,
  RefreshCw,
  WrapText,
  Pin,
  X,
} from 'lucide-react';
import { useWorkspace } from '../lib/store';
import { ReaderPreferences } from './ReaderPreferences';
import { FileBreadcrumb } from './FileBreadcrumb';
import { toast } from '../lib/toasts';

export function FileToolbar({
  markdown,
  showSource,
  onSearch,
  onRefresh,
  loading,
  lineCount,
}: {
  markdown: boolean;
  showSource: boolean;
  onSearch: () => void;
  onRefresh: () => void;
  loading: boolean;
  lineCount: number;
}) {
  const {
    activePath,
    paths,
    previewPath,
    history,
    historyIndex,
    explorerOpen,
    wordWrap,
    setSourceMode,
    setWordWrap,
    setLayout,
    navigateHistory,
    keepFile,
    closeOtherFiles,
    closeAllFiles,
    closeRightFiles,
    reopenFile,
    closedFiles,
  } = useWorkspace();
  const [menuOpen, setMenuOpen] = useState(false);
  const [preferences, setPreferences] = useState(false);
  const [copyState, setCopyState] = useState('');
  const menu = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const menuPosition = usePopupPosition(menuOpen, menu, trigger);
  useEffect(() => {
    setMenuOpen(false);
    setCopyState('');
  }, [activePath]);
  useEffect(() => {
    if (menuOpen && menuPosition.visibility === 'visible')
      menu.current
        ?.querySelector<HTMLElement>('button:not(:disabled)')
        ?.focus({ preventScroll: true });
  }, [menuOpen, menuPosition.visibility]);
  useEffect(() => {
    if (!menuOpen) return;
    const close = (event: PointerEvent) => {
      if (
        !menu.current?.contains(event.target as Node) &&
        !trigger.current?.contains(event.target as Node)
      )
        setMenuOpen(false);
    };
    const onScroll = (event: Event) => {
      if (!menu.current?.contains(event.target as Node)) setMenuOpen(false);
    };
    document.addEventListener('pointerdown', close);
    window.addEventListener('scroll', onScroll, true);
    return () => {
      document.removeEventListener('pointerdown', close);
      window.removeEventListener('scroll', onScroll, true);
    };
  }, [menuOpen]);
  useEffect(() => {
    if (!copyState) return;
    const timeout = setTimeout(() => setCopyState(''), 2200);
    return () => clearTimeout(timeout);
  }, [copyState]);
  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if (
        !(event.ctrlKey || event.metaKey) ||
        (event.target as HTMLElement).closest('[role="dialog"]')
      )
        return;
      if (event.key.toLowerCase() === 'g') {
        event.preventDefault();
        setPreferences(true);
      }
      if (event.shiftKey && event.key.toLowerCase() === 't') {
        event.preventDefault();
        reopenFile();
      }
    };
    window.addEventListener('keydown', shortcut);
    return () => window.removeEventListener('keydown', shortcut);
  }, [reopenFile]);
  async function copyPath() {
    try {
      await navigator.clipboard.writeText(activePath);
      setCopyState('已复制路径');
      toast('文件路径已复制');
    } catch {
      setCopyState('复制失败，请从路径栏手动复制');
    }
  }
  function choose(action: () => void) {
    action();
    setMenuOpen(false);
    trigger.current?.focus();
  }
  return (
    <div className="file-toolbar">
      <div className="file-history">
        <button
          aria-label="后退"
          title="后退（Alt + ←）"
          disabled={historyIndex <= 0}
          onClick={() => navigateHistory(-1)}
        >
          <ArrowLeft size={14} />
        </button>
        <button
          aria-label="前进"
          title="前进（Alt + →）"
          disabled={historyIndex >= history.length - 1}
          onClick={() => navigateHistory(1)}
        >
          <ArrowRight size={14} />
        </button>
      </div>
      <FileBreadcrumb path={activePath} />
      <div className="file-toolbar-actions">
        {markdown && (
          <button
            className="file-mode-button"
            aria-label={showSource ? '查看预览' : '查看源代码'}
            title={showSource ? '查看预览' : '查看源代码'}
            onClick={() => setSourceMode(activePath, !showSource)}
          >
            {showSource ? <BookOpen size={14} /> : <Code2 size={14} />}
            <span className="toolbar-label">{showSource ? '预览' : '源代码'}</span>
          </button>
        )}
        <button
          aria-label="复制文件路径"
          title={copyState || '复制文件路径'}
          disabled={!activePath}
          onClick={() => void copyPath()}
        >
          {copyState === '已复制路径' ? <Check size={14} /> : <Copy size={14} />}
        </button>
        <button
          aria-label="切换文件树"
          aria-pressed={explorerOpen}
          title="切换文件树"
          onClick={() => setLayout({ explorerOpen: !explorerOpen })}
        >
          <PanelRight size={15} />
        </button>
        <div className="file-menu-anchor">
          <button
            ref={trigger}
            aria-label="更多文件操作"
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen(!menuOpen)}
          >
            <MoreHorizontal size={16} />
          </button>
          {menuOpen &&
            createPortal(
              <div
                className="file-menu"
                role="menu"
                aria-label="文件操作"
                style={menuPosition}
                ref={menu}
                onKeyDown={(event) => {
                  if (event.key === 'Escape') {
                    event.preventDefault();
                    setMenuOpen(false);
                    trigger.current?.focus();
                    return;
                  }
                  if (event.key === 'Tab') {
                    setMenuOpen(false);
                    trigger.current?.focus();
                    return;
                  }
                  if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
                  event.preventDefault();
                  const items = Array.from(
                    event.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled)'),
                  );
                  const index = items.indexOf(document.activeElement as HTMLElement);
                  const next =
                    event.key === 'Home'
                      ? 0
                      : event.key === 'End'
                        ? items.length - 1
                        : (index + (event.key === 'ArrowDown' ? 1 : -1) + items.length) %
                          items.length;
                  items[next]?.focus();
                }}
              >
                <button
                  role="menuitem"
                  title="搜索源码（Ctrl + Shift + F）"
                  onClick={() => choose(onSearch)}
                >
                  <Search size={14} />
                  搜索源码
                </button>
                <button
                  role="menuitem"
                  disabled={!activePath || loading}
                  onClick={() => choose(onRefresh)}
                >
                  <RefreshCw size={14} />
                  重新读取文件
                </button>
                <button
                  role="menuitemcheckbox"
                  aria-checked={wordWrap}
                  onClick={() => choose(() => setWordWrap(!wordWrap))}
                >
                  <WrapText size={14} />
                  自动换行{wordWrap && <Check size={13} />}
                </button>
                <button
                  role="menuitem"
                  disabled={!previewPath || previewPath !== activePath}
                  onClick={() => choose(() => keepFile(activePath))}
                >
                  <Pin size={14} />
                  保留当前标签
                </button>
                <button
                  role="menuitem"
                  disabled={paths.length < 2}
                  onClick={() => choose(() => closeOtherFiles(activePath))}
                >
                  <X size={14} />
                  关闭其他标签
                </button>
                <button
                  role="menuitem"
                  disabled={paths.indexOf(activePath) === paths.length - 1}
                  onClick={() => choose(() => closeRightFiles(activePath))}
                >
                  <X size={14} />
                  关闭右侧标签
                </button>
                <button
                  role="menuitem"
                  disabled={!paths.length}
                  onClick={() => choose(closeAllFiles)}
                >
                  <X size={14} />
                  关闭全部标签
                </button>
                <button
                  role="menuitem"
                  disabled={!closedFiles.some((item) => !paths.includes(item.path))}
                  onClick={() => choose(reopenFile)}
                >
                  <RefreshCw size={14} />
                  重新打开关闭的标签
                </button>
                <button role="menuitem" onClick={() => choose(() => setPreferences(true))}>
                  <BookOpen size={14} />
                  阅读设置与快捷键
                </button>
              </div>,
              document.body,
            )}
        </div>
      </div>
      <span className="sr-only" role="status">
        {copyState}
      </span>
      {preferences && (
        <ReaderPreferences lineCount={lineCount} onClose={() => setPreferences(false)} />
      )}
    </div>
  );
}
