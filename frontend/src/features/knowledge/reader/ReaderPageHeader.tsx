import type { ReactNode } from 'react';
import type { Route } from '../routes';

export function ReaderPageHeader({
  title,
  summary,
  topic,
  navigate,
  actions,
}: {
  title: string;
  summary: string;
  topic?: { id: string; title: string };
  navigate: (route: Route) => void;
  actions?: ReactNode;
}) {
  return (
    <div className="page-header reader-page-header">
      <div>
        <nav className="reader-breadcrumb" aria-label="当前位置">
          <button type="button" onClick={() => navigate({ kind: 'modules' })}>
            功能与流程
          </button>
          {topic && (
            <>
              <span>/</span>
              <button type="button" onClick={() => navigate({ kind: 'topic', id: topic.id })}>
                {topic.title}
              </button>
            </>
          )}
        </nav>
        <h1>{title}</h1>
        <p>{summary}</p>
      </div>
      <div className="header-actions">
        {topic && (
          <button className="button" onClick={() => navigate({ kind: 'topic', id: topic.id })}>
            ← 返回业务专题
          </button>
        )}
        <button className="button" onClick={() => navigate({ kind: 'graphs' })}>
          全部图谱
        </button>
        {actions}
      </div>
    </div>
  );
}
