import { useState } from 'react';
import { presentationTopics, displayDiagramTitle } from './data/presentation';
import { diagramReadings } from './data/diagramReading';
import type { FlowchartCatalogEntry } from './types';
import { diagramRoute, type Route } from './routes';
import { UiIcon } from './UiIcon';
import { Select } from '../../shared/ui/Select';
import { ReaderPageHeader } from './reader/ReaderPageHeader';
import { manualById } from './data/manualCatalog';
import { DiagramContent } from './reader/DiagramContent';
import { GraphViewSelector } from './reader/GraphViewSelector';
import { graphOwner, selectedGraphId } from './data/graphCollections';
import {
  graphEntry,
  graphMembers,
  publicGraphs,
  relatedGraphs,
  searchGraphDirectory,
} from './data/graphDirectory';
export { diagramRoute } from './routes';
export function GraphAtlas({ navigate }: { navigate: (route: Route) => void }) {
  const [query, setQuery] = useState('');
  const [type, setType] = useState('all');
  const [level, setLevel] = useState('all');
  const entries = searchGraphDirectory(query, type, level);
  const main = entries.filter(({ entry }) => entry.chapter);
  const detailed = entries.filter(({ entry }) => !entry.chapter);
  return (
    <>
      <section className="showcase-hero card" aria-label="系统与流程介绍">
        <div className="showcase-intro">
          <span className="eyebrow hero-kicker">
            <UiIcon name="flow" />
            ZX2200 · 系统与流程
          </span>
          <h1>
            从生产全局
            <br />
            <span>读懂每个环节</span>
          </h1>
          <p>从业务流程理解模块职责，查看各环节的执行条件、协作关系与异常处理。</p>
        </div>
        <div className="showcase-outline">
          <span className="eyebrow">阅读路线</span>
          <ol>
            {[
              ['建立系统模型', '理解边界与模块职责'],
              ['阅读生产主流程', '串起启动、加工与交接'],
              ['展开图谱与条件', '了解执行条件与异常处理'],
              ['理解协作与异常', '查看模块交接与失败分支'],
            ].map(([title, description], index) => (
              <li key={title}>
                <span className="route-number">{String(index + 1).padStart(2, '0')}</span>
                <div>
                  <b>{title}</b>
                  <small>{description}</small>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>
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
          {[...new Map(publicGraphs.map((entry) => [entry.type, entry.typeLabel])).entries()].map(
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
        const group = list as typeof entries;
        return (
          group.length > 0 && (
            <section className="section" key={title as string}>
              <div className="section-heading">
                <div>
                  <h2>{title as string}</h2>
                  <p>{description as string}</p>
                </div>
                <span className="pill">{group.length} 个图谱</span>
              </div>
              <div className="graph-grid">
                {group.map(({ entry, match }) => (
                  <CatalogCard
                    key={entry.id}
                    entry={entry}
                    matchedTitle={
                      entry.id !== match.id ? displayDiagramTitle(match.id, match.title) : undefined
                    }
                    onOpen={() => navigate(diagramRoute(match.id))}
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

function CatalogCard({
  entry,
  matchedTitle,
  onOpen,
}: {
  entry: FlowchartCatalogEntry;
  matchedTitle?: string;
  onOpen: () => void;
}) {
  const count = graphMembers(entry.id).length;
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
      {matchedTitle && <p className="graph-match">匹配图：{matchedTitle}</p>}
      {count > 1 && <span className="muted">含 {count} 张主图与细节图</span>}
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
  view,
  focusedSignal,
  navigate,
  theme,
}: {
  id: string;
  view?: string;
  focusedSignal?: string;
  section?: string;
  navigate: (route: Route) => void;
  theme: 'dark' | 'light';
}) {
  const owner = graphOwner(id);
  const entry = graphEntry(owner);
  const selected = graphEntry(selectedGraphId(id, view));
  if (!entry || !selected) return <Missing onBack={() => navigate({ kind: 'graphs' })} />;
  const related = relatedGraphs(owner);
  const members = graphMembers(owner);
  const summary = entry.inlineTopic
    ? (presentationTopics.find((item) => item.id === entry.inlineTopic)?.summary ?? '')
    : (diagramReadings[owner]?.summary ?? '');
  return (
    <>
      <ReaderPageHeader
        title={displayDiagramTitle(owner, entry.title)}
        summary={summary}
        navigate={navigate}
      />
      <GraphViewSelector
        entries={members}
        selected={selected.id}
        onSelect={(view) => navigate(diagramRoute(owner, { view }))}
      />
      {selected.id !== owner && (
        <div className="graph-view-heading">
          <h2>{displayDiagramTitle(selected.id, selected.title)}</h2>
          <p>{diagramReadings[selected.id]?.summary}</p>
        </div>
      )}
      <div key={selected.id} data-graph-view={selected.id}>
        <DiagramContent entry={selected} focusedSignal={focusedSignal} theme={theme} />
      </div>
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
