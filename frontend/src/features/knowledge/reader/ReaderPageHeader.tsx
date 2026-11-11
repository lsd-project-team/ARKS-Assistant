import type { ReactNode } from 'react';
import type { Route } from '../routes';

export function ReaderPageHeader({
  title,
  summary,
  navigate,
  actions,
}: {
  title: string;
  summary: string;
  navigate: (route: Route) => void;
  actions?: ReactNode;
}) {
  return (
    <div className="page-header reader-page-header">
      <div>
        <h1>{title}</h1>
        <p>{summary}</p>
      </div>
      <div className="header-actions">
        <button className="button" onClick={() => navigate({ kind: 'graphs' })}>
          全部图谱
        </button>
        {actions}
      </div>
    </div>
  );
}
