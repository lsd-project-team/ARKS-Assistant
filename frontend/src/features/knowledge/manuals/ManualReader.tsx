import { manualById, manualsForTopic } from '../data/manualCatalog';
import { presentationTopics } from '../data/presentation';
import { OriginalDiagram } from '../OriginalDiagram';
import type { Route } from '../routes';
import { ReaderFrame } from '../reader/ReaderFrame';
import { ReaderPageHeader } from '../reader/ReaderPageHeader';

type Navigate = (route: Route) => void;

export function ManualCards({ topic, navigate }: { topic: string; navigate: Navigate }) {
  const entries = manualsForTopic(topic);
  if (!entries.length) return null;
  return (
    <section className="section" aria-label="模块图解">
      <div className="section-heading">
        <div>
          <h2>模块图解</h2>
          <p>按模块查看架构、执行链路和节点关系。</p>
        </div>
      </div>
      <div className="graph-grid">
        {entries.map((entry) => (
          <article className="card panel" key={entry.id}>
            <span className="eyebrow">模块图解</span>
            <h3>{entry.title}</h3>
            <p>{entry.summary}</p>
            <div className="card-actions">
              <button
                className="button"
                onClick={() => navigate({ kind: 'catalog', id: entry.id })}
              >
                查看图解
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export function ManualReader({
  id,
  navigate,
  theme,
}: {
  id: string;
  section?: string;
  navigate: Navigate;
  theme: 'dark' | 'light';
}) {
  const entry = manualById(id)!;
  const topic = presentationTopics.find((item) => item.id === entry.topicIds[0])!;
  return (
    <>
      <ReaderPageHeader
        title={entry.title}
        summary={entry.summary}
        topic={topic}
        navigate={navigate}
      />
      <div className="unified-reader" data-reader-layout="diagram">
        <ReaderFrame title={entry.title}>
          <OriginalDiagram
            path={`docs/archify/manuals/${entry.file}`}
            title={entry.title}
            theme={theme}
          />
        </ReaderFrame>
      </div>
    </>
  );
}
