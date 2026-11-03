import { lazy, Suspense } from 'react';
import { manualById, manualsForTopic } from '../data/manualCatalog';
import { presentationTopics } from '../data/presentation';
import { OriginalDiagram } from '../OriginalDiagram';
import type { Route } from '../routes';
import './manuals.css';

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
  const open = (anchor?: string) =>
    navigate({ kind: 'catalog', id, ...(anchor ? { section: anchor } : {}) });
  return (
    <>
      <div className="page-header">
        <div>
          <span className="eyebrow">{topic.title} · 模块详解</span>
          <h1>{entry.title}</h1>
          <p>{entry.summary}</p>
        </div>
        <div className="header-actions">
          <button className="button" onClick={() => navigate({ kind: 'topic', id: topic.id })}>
            ← 返回业务专题
          </button>
          <button className="button" onClick={() => navigate({ kind: 'graphs' })}>
            全部图谱
          </button>
        </div>
      </div>
      <div className="manual-tabs" role="group" aria-label="阅读方式">
        <button aria-pressed={section === undefined} onClick={() => open()}>
          交互图解
        </button>
        <button aria-pressed={section !== undefined} onClick={() => open(entry.detailAnchor)}>
          详细说明
        </button>
      </div>
      {section === undefined ? (
        <>
          <OriginalDiagram
            path={`docs/archify/manuals/${entry.file}`}
            title={entry.title}
            theme={theme}
            reader
          />
          <div className="card panel manual-detail-entry">
            <p>详细说明包含模块职责、执行条件、按钮分支、配置保存与原有风险记录。</p>
            <button className="button primary" onClick={() => open(entry.detailAnchor)}>
              按章节阅读详细说明 →
            </button>
          </div>
        </>
      ) : (
        <Suspense fallback={<p role="status">正在加载详细说明…</p>}>
          <ManualDocument key={id} entry={entry} anchor={section} navigate={navigate} />
        </Suspense>
      )}
    </>
  );
}
