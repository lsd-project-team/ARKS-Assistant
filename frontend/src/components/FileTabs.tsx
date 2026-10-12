import { ChevronLeft, ChevronRight, X } from 'lucide-react';
import { useWorkspace } from '../lib/store';
import { tabLabel } from '../lib/fileNavigation';
import { useFileTabScroll } from '../hooks/useFileTabScroll';
import { FileIcon } from './FileIcon';
import { OpenFilesMenu } from './OpenFilesMenu';
import { useCurrentProject } from '../hooks/useProjects';
import { displaySourcePath } from '../lib/sourceDisplay';

export function FileTabs() {
  const { paths, activePath, previewPath, openFile, closeFile, keepFile } = useWorkspace();
  const project = useCurrentProject();
  const displayPaths = paths.map((path) => displaySourcePath(path, project.data));
  const { tabs, overflow, backward, forward, scrollTabs } = useFileTabScroll(activePath, paths);
  return (
    <div className="file-tabs">
      <div className="code-tabs" ref={tabs} role="tablist" aria-label="已打开文件">
        {paths.map((path) => (
          <div
            key={path}
            className={`code-tab ${path === activePath ? 'active' : ''} ${path === previewPath ? 'preview-tab' : ''}`}
          >
            <button
              role="tab"
              aria-selected={path === activePath}
              aria-controls="source-reading-panel"
              tabIndex={path === activePath ? 0 : -1}
              title={`${path}${path === previewPath ? ' · 临时预览，双击保留' : ''}`}
              onClick={() => openFile(path, undefined, path === previewPath ? 'preview' : 'pinned')}
              onDoubleClick={() => keepFile(path)}
              onKeyDown={(event) => {
                if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
                event.preventDefault();
                const index = paths.indexOf(path);
                const next =
                  event.key === 'Home'
                    ? 0
                    : event.key === 'End'
                      ? paths.length - 1
                      : (index + (event.key === 'ArrowRight' ? 1 : -1) + paths.length) %
                        paths.length;
                const target = paths[next];
                openFile(target, undefined, target === previewPath ? 'preview' : 'pinned');
                tabs.current?.querySelectorAll<HTMLElement>('[role="tab"]')[next]?.focus();
              }}
            >
              <FileIcon name={path} />
              <span>{tabLabel(displaySourcePath(path, project.data), displayPaths)}</span>
            </button>
            <button aria-label={`关闭 ${path}`} title="关闭标签" onClick={() => closeFile(path)}>
              <X size={12} />
            </button>
          </div>
        ))}
        {!paths.length && <span className="empty-tab">源码浏览器</span>}
      </div>
      {!!paths.length && (
        <div className="file-tab-controls">
          {overflow && (
            <>
              <button
                className="file-tab-button"
                aria-label="向左滚动文件标签"
                title="向左滚动文件标签"
                disabled={!backward}
                onClick={() => scrollTabs(-1)}
              >
                <ChevronLeft size={15} />
              </button>
              <button
                className="file-tab-button"
                aria-label="向右滚动文件标签"
                title="向右滚动文件标签"
                disabled={!forward}
                onClick={() => scrollTabs(1)}
              >
                <ChevronRight size={15} />
              </button>
            </>
          )}
          <OpenFilesMenu />
        </div>
      )}
    </div>
  );
}
