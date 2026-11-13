import type { Route } from '../routes';

export function ReaderPageHeader({
  title,
  summary,
  navigate,
}: {
  title: string;
  summary: string;
  navigate: (route: Route) => void;
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
      </div>
    </div>
  );
}
