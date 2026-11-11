import { useState } from 'react';
import type { ReactNode } from 'react';
import { archifyData } from './data/archifyData';
import { presentationTopics, topicForDiagram, displayDiagramTitle } from './data/presentation';
import { diagramReadings, isSupportingEntry } from './data/diagramReading';
import type { FlowchartCatalogEntry } from './types';
import type { Route } from './routes';
import { UiIcon } from './UiIcon';
import { Select } from '../../shared/ui/Select';
import { CoordinateReader } from './coordinates/CoordinateReader';
import { AtlasReader } from './atlas/AtlasReader';
import { CatalogReader } from './reader/CatalogReader';
import { ReaderPageHeader } from './reader/ReaderPageHeader';
import { manualById } from './data/manualCatalog';
import { ManualReader } from './manuals/ManualReader';
import { GraphReadingNotes } from './reader/GraphReadingNotes';
const catalog = archifyData.flowchartCatalog.entries;
const publicCatalog = catalog.filter((entry) => !isSupportingEntry(entry));
export const diagramRoute = (id: string): Route =>
  archifyData.graphs.some((graph) => graph.slug === id)
    ? { kind: 'graph', slug: id }
    : { kind: 'catalog', id };
function PageHeader({
  eyebrow,
  title,
  children,
  actions,
}: {
  eyebrow?: string;
  title: ReactNode;
  children: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="page-header">
      <div>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        <p>{children}</p>
      </div>
      {actions && <div className="header-actions">{actions}</div>}
    </div>
  );
}

function InlineDiagramReader({ id, navigate }: { id: string; navigate: (route: Route) => void }) {
  const topic = presentationTopics.find((topic) => topic.id === id);
  if (!topic) return <Missing onBack={() => navigate({ kind: 'graphs' })} />;
  return (
    <>
      <ReaderPageHeader title={topic.title} summary={topic.summary} navigate={navigate} />
      {topic.id === 'g0' ? <CoordinateReader /> : <AtlasReader page={topic.id} />}
      <GraphReadingNotes reading={topic} />
    </>
  );
}

export function GraphAtlas({ navigate }: { navigate: (route: Route) => void }) {
  const [query, setQuery] = useState('');
  const [type, setType] = useState('all');
  const [level, setLevel] = useState('all');
  const entries = publicCatalog.filter(
    (entry) =>
      `${displayDiagramTitle(entry.id, entry.title)} ${entry.title} ${entry.id} ${diagramReadings[entry.id]?.summary} ${topicForDiagram(entry.id)?.title} ${manualById(entry.id)?.searchText ?? ''}`
        .toLowerCase()
        .includes(query.toLowerCase()) &&
      (type === 'all' || entry.type === type) &&
      (level === 'all' || (level === 'main' ? Boolean(entry.chapter) : !entry.chapter)),
  );
  const main = entries.filter((entry) => entry.chapter);
  const detailed = entries.filter((entry) => !entry.chapter);
  return (
    <>
      <PageHeader
        title="找到你要了解的流程"
        actions={
          <>
            <span className="pill">
              {entries.length} / {publicCatalog.length} 张图
            </span>
          </>
        }
      >
        先读 8 条生产主流程，再按问题查找具体图谱，图和说明在同一页阅读。
      </PageHeader>
      <div className="filter-row">
        <input
          aria-label="搜索图谱"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="搜索名称或你关心的问题…"
        />
        <Select aria-label="阅读层级" value={level} onValueChange={setLevel}>
          <option value="all">全部层级</option>
          <option value="main">生产主流程</option>
          <option value="detail">深入阅读</option>
        </Select>
        <Select aria-label="图谱类型" value={type} onValueChange={setType}>
          <option value="all">全部类型</option>
          {[...new Map(publicCatalog.map((entry) => [entry.type, entry.typeLabel])).entries()].map(
            ([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ),
          )}
        </Select>
      </div>
      {[
        [main, '生产主流程', '按生产环节建立整体认识'],
        [detailed, '深入阅读', '按具体问题查看条件、交接与恢复'],
      ].map(([list, title, description]) => {
        const group = list as FlowchartCatalogEntry[];
        return (
          group.length > 0 && (
            <section className="section" key={title as string}>
              <div className="section-heading">
                <div>
                  <h2>{title as string}</h2>
                  <p>{description as string}</p>
                </div>
                <span className="pill">{group.length} 张图</span>
              </div>
              <div className="graph-grid">
                {group.map((entry) => (
                  <CatalogCard
                    key={entry.id}
                    entry={entry}
                    onOpen={() => navigate(diagramRoute(entry.id))}
                  />
                ))}
              </div>
            </section>
          )
        );
      })}
      {!entries.length && (
        <div className="empty-state compact">
          <h2>没有匹配的图谱</h2>
          <button
            className="button"
            onClick={() => {
              setQuery('');
              setType('all');
              setLevel('all');
            }}
          >
            清除筛选
          </button>
        </div>
      )}
    </>
  );
}

function CatalogCard({ entry, onOpen }: { entry: FlowchartCatalogEntry; onOpen: () => void }) {
  return (
    <article className="card graph-card catalog-card" data-main={Boolean(entry.chapter)}>
      <div className="graph-card-head">
        <span className="graph-symbol">
          {entry.chapter ? (
            String(entry.chapter).padStart(2, '0')
          ) : (
            <UiIcon
              name={
                entry.type === 'sequence'
                  ? 'sequence'
                  : entry.type === 'dataflow'
                    ? 'dataflow'
                    : entry.type === 'architecture'
                      ? 'architecture'
                      : 'flow'
              }
            />
          )}
        </span>
        <span className="pill">
          {manualById(entry.id) ? '模块图解' : entry.chapter ? '生产主流程' : entry.typeLabel}
        </span>
      </div>
      <h3>{displayDiagramTitle(entry.id, entry.title)}</h3>
      <p className="diagram-question">{diagramReadings[entry.id]?.summary}</p>
      <div className="card-actions">
        <button className="graph-read-button" onClick={onOpen}>
          查看图谱
          <UiIcon name="arrow" />
        </button>
      </div>
    </article>
  );
}

export function DiagramDetail({
  id,
  focusedSignal,
  section,
  navigate,
  theme,
}: {
  id: string;
  focusedSignal?: string;
  section?: string;
  navigate: (route: Route) => void;
  theme: 'dark' | 'light';
}) {
  const entry = catalog.find((entry) => entry.id === id);
  if (!entry || isSupportingEntry(entry))
    return <Missing onBack={() => navigate({ kind: 'graphs' })} />;
  if (manualById(id))
    return <ManualReader id={id} section={section} navigate={navigate} theme={theme} />;
  const topic = topicForDiagram(id);
  const related = publicCatalog.filter(
    (item) => item.id !== id && topic?.diagrams.includes(item.id),
  );
  return (
    <>
      {entry.inlineTopic ? (
        <InlineDiagramReader id={entry.inlineTopic} navigate={navigate} />
      ) : (
        <CatalogReader
          entry={entry}
          focusedSignal={focusedSignal}
          navigate={navigate}
          theme={theme}
        />
      )}
      {related.length > 0 && (
        <section className="section">
          <div className="section-heading">
            <h2>继续阅读</h2>
          </div>
          <div className="graph-grid">
            {related.map((entry) => (
              <CatalogCard
                key={entry.id}
                entry={entry}
                onOpen={() => navigate(diagramRoute(entry.id))}
              />
            ))}
          </div>
        </section>
      )}
    </>
  );
}

function Missing({ onBack }: { onBack: () => void }) {
  return (
    <div className="empty-state">
      <h2>找不到这个内容</h2>
      <button className="button" onClick={onBack}>
        返回目录
      </button>
    </div>
  );
}
