import { lazy, Suspense, useRef } from 'react';
import { manualById, manualsForTopic } from '../data/manualCatalog';
import { presentationTopics } from '../data/presentation';
import { OriginalDiagram } from '../OriginalDiagram';
import type { Route } from '../routes';
import './manuals.css';
import { ReaderTabs } from '../reader/ReaderTabs';
import { ReaderFrame } from '../reader/ReaderFrame';
import { ReaderPageHeader } from '../reader/ReaderPageHeader';

const ManualDocument = lazy(() => import('./ManualDocument'));
type Navigate = (route: Route) => void;

export function ManualCards({ topic, navigate }: { topic: string; navigate: Navigate }) {
  const entries = manualsForTopic(topic);
  if (!entries.length) return null;
  return (
    <section className="section" aria-label="模块图解与详细说明">
      <div className="section-heading">
        <div>
          <h2>模块图解与详细说明</h2>
          <p>先看模块全景，再按章节阅读执行条件、按钮分支与异常处理。</p>
        </div>
      </div>
      <div className="graph-grid">
        {entries.map((entry) => (
          <article className="card panel" key={entry.id}>
            <span className="eyebrow">模块详解</span>
            <h3>{entry.title}</h3>
            <p>{entry.summary}</p>
            <div className="card-actions">
              <button
                className="button"
                onClick={() => navigate({ kind: 'catalog', id: entry.id })}
              >
                查看图解
              </button>
              <button
                className="text-button"
                onClick={() =>
                  navigate({ kind: 'catalog', id: entry.id, section: entry.detailAnchor })
                }
              >
                详细说明 →
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
  section,
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
  const lastSection = useRef(section ?? entry.detailAnchor);
  if (section !== undefined) lastSection.current = section;
  const open = (document: boolean) =>
    navigate({ kind: 'catalog', id, ...(document ? { section: lastSection.current } : {}) });
  return (
    <>
      <ReaderPageHeader
        title={entry.title}
        summary={entry.summary}
        topic={topic}
        navigate={navigate}
      />
      <ReaderTabs
        documentOpen={section !== undefined}
        onDocumentChange={open}
        graph={(openDocument) => (
          <ReaderFrame title={entry.title} onDocument={openDocument}>
            <OriginalDiagram
              path={`docs/archify/manuals/${entry.file}`}
              title={entry.title}
              theme={theme}
            />
          </ReaderFrame>
        )}
        document={
          <Suspense fallback={<p role="status">正在加载详细说明…</p>}>
            <ManualDocument
              key={id}
              entry={entry}
              anchor={section ?? lastSection.current}
              navigate={navigate}
            />
          </Suspense>
        }
      />
    </>
  );
}
