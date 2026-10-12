import { ChevronRight } from 'lucide-react';
import { useCurrentProject } from '../hooks/useProjects';
import { displaySourcePath } from '../lib/sourceDisplay';

export function FileBreadcrumb({ path }: { path: string }) {
  const project = useCurrentProject();
  const rootName = project.data?.source_root?.split(/[\\/]/).filter(Boolean).at(-1) || '源码';
  const parts = path.startsWith('@sources/')
    ? displaySourcePath(path, project.data).split('/').filter(Boolean)
    : [rootName, ...path.split('/').filter(Boolean)];
  const last = parts.length - 1;
  return (
    <div className="file-path-area">
      <nav className="file-path" aria-label="文件路径" title={parts.join('/')} data-deep={last > 2}>
        {parts.map((part, index) => (
          <span
            className={`file-path-segment ${index === last ? 'file-path-current' : index === 0 ? 'file-path-root' : index === last - 1 ? 'file-path-parent' : 'file-path-ancestor'}`}
            key={index}
          >
            {index > 0 && <ChevronRight size={11} aria-hidden="true" />}
            <span
              className="file-path-label"
              aria-current={index === last ? 'location' : undefined}
            >
              {part}
            </span>
            {index === 0 && last > 2 && (
              // 窄路径条折叠中间目录，完整路径始终可通过悬停查看。
              <span className="file-path-ellipsis" aria-hidden="true">
                <ChevronRight size={11} />…
              </span>
            )}
          </span>
        ))}
      </nav>
    </div>
  );
}
