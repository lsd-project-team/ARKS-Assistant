import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { archifyData } from './data/archifyData';
import { presentationTopics, topicForDiagram, displayDiagramTitle } from './data/presentation';
import { diagramReadings, isSupportingEntry } from './data/diagramReading';
import { TopicReading } from './PresentationViews';
import { ModuleCoordination, TopicCoordination, NodeSignalNotes } from './CooperationNotes';
import { useEngineering } from './engineeringData';
import { WorkflowSourceLinks, BindingLinks, TopicSourceModules } from './EngineeringViews';
import type { EvidenceRef, FlowchartCatalogEntry } from './types';
import type { Route } from './routes';
import { UiIcon } from './UiIcon';
import { Select } from '../../shared/ui/Select';
import { SourceGuidePanel } from './SourceGuidePanel';
import { sourceDiagramRevision } from './sourceGuides';
import { useAppearance } from '../settings/lib/appearance';
import diagramChrome from './diagramChrome.css?inline';
import diagramLatinFont from '@fontsource-variable/geist/index.css?inline';
import diagramChineseFont from '@fontsource-variable/noto-sans-sc/index.css?inline';
const catalog = archifyData.flowchartCatalog.entries;
const publicCatalog = catalog.filter((entry) => !isSupportingEntry(entry));
const resourceHref = (href: string) => `/archify/${href.replace(/^docs[\\/]archify[\\/]/, '')}`;
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

function SupportingDocuments({ entries }: { entries: FlowchartCatalogEntry[] }) {
  if (!entries.length) return null;
  return (
    <EvidenceDisclosure>
      <p>以下 {entries.length} 份补充资料用于追溯分析过程，全部保留在这里。</p>
      <div className="asset-list">
        {entries.map(
          (entry) =>
            entry.html && (
              <AssetLink
                key={entry.id}
                label={displayDiagramTitle(entry.id, entry.title)}
                path={entry.html}
              />
            ),
        )}
      </div>
    </EvidenceDisclosure>
  );
}

export function TopicDetail({ id, navigate }: { id: string; navigate: (route: Route) => void }) {
  const topic = presentationTopics.find((topic) => topic.id === id);
  if (!topic) return <Missing onBack={() => navigate({ kind: 'modules' })} />;
  const entries = topic.diagrams
    .map((id) => catalog.find((entry) => entry.id === id))
    .filter((entry): entry is FlowchartCatalogEntry => Boolean(entry));
  return (
    <>
      <PageHeader
        eyebrow="功能与专题"
        title={topic.title}
        actions={
          <button className="button" onClick={() => navigate({ kind: 'modules' })}>
            全部专题
          </button>
        }
      >
        {topic.summary}
      </PageHeader>
      <SourceGuidePanel key={id} page={id} navigate={navigate} />
      <section className="section">
        <div className="section-heading">
          <div>
            <h2>建议阅读顺序</h2>
            <p>先了解整体流程，再阅读具体条件与异常</p>
          </div>
        </div>
        <div className="graph-grid">
          {entries
            .filter((entry) => !isSupportingEntry(entry))
            .map((entry) => (
              <CatalogCard
                key={entry.id}
                entry={entry}
                onOpen={() => navigate(diagramRoute(entry.id))}
              />
            ))}
        </div>
      </section>
      <details className="section card panel reading-disclosure">
        <summary>展开专题概览与协作条件</summary>
        <TopicReading topic={topic} />
        <TopicCoordination diagrams={topic.diagrams} />
      </details>
      <TopicSourceModules
        diagrams={topic.diagrams}
        all={topic.id === 'architecture'}
        navigate={navigate}
      />
      <SupportingDocuments entries={entries.filter(isSupportingEntry)} />
    </>
  );
}

export function GraphAtlas({ navigate }: { navigate: (route: Route) => void }) {
  const [query, setQuery] = useState('');
  const [type, setType] = useState('all');
  const [topic, setTopic] = useState('all');
  const [level, setLevel] = useState('all');
  const entries = publicCatalog.filter(
    (entry) =>
      `${displayDiagramTitle(entry.id, entry.title)} ${entry.title} ${entry.id} ${diagramReadings[entry.id]?.summary} ${topicForDiagram(entry.id)?.title}`
        .toLowerCase()
        .includes(query.toLowerCase()) &&
      (type === 'all' || entry.type === type) &&
      (topic === 'all' || topicForDiagram(entry.id)?.id === topic) &&
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
            <button className="button" onClick={() => navigate({ kind: 'modules' })}>
              ← 功能与流程
            </button>
            <span className="pill">
              {entries.length} / {publicCatalog.length} 张图
            </span>
          </>
        }
      >
        先读 8 条生产主流程，再按问题进入专题图。
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
        <Select aria-label="阅读专题" value={topic} onValueChange={setTopic}>
          <option value="all">全部专题</option>
          {presentationTopics.map((topic) => (
            <option key={topic.id} value={topic.id}>
              {topic.title}
            </option>
          ))}
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
              setTopic('all');
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
        <span className="pill">{entry.chapter ? '生产主流程' : entry.typeLabel}</span>
      </div>
      <h3>{displayDiagramTitle(entry.id, entry.title)}</h3>
      <p className="diagram-question">{diagramReadings[entry.id]?.summary}</p>
      <div className="card-topic">{topicForDiagram(entry.id)?.title}</div>
      <div className="card-actions">
        <button className="graph-read-button" onClick={onOpen}>
          阅读原图与说明
          <UiIcon name="arrow" />
        </button>
      </div>
    </article>
  );
}

export function DiagramDetail({
  id,
  focusedSignal,
  navigate,
  theme,
}: {
  id: string;
  focusedSignal?: string;
  navigate: (route: Route) => void;
  theme: 'dark' | 'light';
}) {
  const entry = catalog.find((entry) => entry.id === id);
  const graph = archifyData.graphs.find((graph) => graph.slug === id);
  const [selected, setSelected] = useState(graph?.nodes[0]?.id);
  const [nodeFocused, setNodeFocused] = useState(false);
  const reader = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    if (nodeFocused) reader.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [selected, nodeFocused]);
  const selectOriginalNode = (nodeId: string) => {
    if (graph?.nodes.some((n) => n.id === nodeId)) {
      setSelected(nodeId);
      setNodeFocused(true);
    }
  };
  if (!entry) return <Missing onBack={() => navigate({ kind: 'graphs' })} />;
  const reading = diagramReadings[id];
  const title = displayDiagramTitle(id, entry.title);
  const record = archifyData.diagramRecords[id];
  const topic = topicForDiagram(id);
  const node = graph?.nodes.find((node) => node.id === selected) ?? graph?.nodes[0];
  const related = publicCatalog.filter(
    (item) => item.id !== id && topic?.diagrams.includes(item.id),
  );
  return (
    <>
      <PageHeader
        eyebrow={topic?.title ?? '流程图谱'}
        title={title}
        actions={
          <>
            <button className="button" onClick={() => navigate({ kind: 'graphs' })}>
              ← 全部图谱
            </button>
            {graph && (
              <button
                className="button"
                onClick={() => navigate({ kind: 'chat', flow: graph.slug })}
              >
                <UiIcon name="chat" />
                讨论这个流程
              </button>
            )}
          </>
        }
      >
        {reading.summary}
      </PageHeader>
      <SourceGuidePanel key={id} page={id} navigate={navigate} />
      {isSupportingEntry(entry) ? (
        <details className="section card panel reading-disclosure">
          <summary>展开补充资料原页</summary>
          {entry.html && <OriginalDiagram path={entry.html} title={title} theme={theme} />}
        </details>
      ) : record.htmlAvailable && entry.html ? (
        <OriginalDiagram
          path={entry.html}
          title={title}
          onNode={selectOriginalNode}
          theme={theme}
        />
      ) : (
        <div className="empty-state compact">原图尚未生成</div>
      )}
      <section className="section" aria-label="业务介绍">
        <div className="section-heading">
          <h2>业务介绍</h2>
        </div>
        <div className="diagram-reading">
          <article className="card panel">
            <span className="eyebrow">用途</span>
            <h2>这张图回答什么</h2>
            <p>{reading.summary}</p>
          </article>
          <article className="card panel">
            <span className="eyebrow">条件</span>
            <h2>执行前看什么</h2>
            <p>{reading.condition}</p>
          </article>
          <article className="card panel">
            <span className="eyebrow">异常</span>
            <h2>结果怎样理解</h2>
            <p>{reading.exception}</p>
          </article>
        </div>
      </section>
      {graph && (
        <details
          className="section card panel reading-disclosure"
          ref={reader}
          open={nodeFocused || Boolean(focusedSignal) || undefined}
        >
          <summary>深入阅读节点与模块协作</summary>
          <ModuleCoordination graph={graph} focusedSignal={focusedSignal} />
          <div className="node-reader">
            <div className="node-tabs" role="group" aria-label="选择节点">
              {graph.nodes.map((item) => (
                <button
                  key={item.id}
                  className={item.id === node?.id ? 'selected' : ''}
                  aria-pressed={item.id === node?.id}
                  onClick={() => setSelected(item.id)}
                >
                  {item.label}
                </button>
              ))}
            </div>
            {node && (
              <article className="selected-node">
                <h2>{node.label}</h2>
                <p>{node.detail}</p>
                <div className="branch-list">
                  <b>后续分支</b>
                  {graph.edges
                    .filter((edge) => edge.from === node.id)
                    .map((edge) => (
                      <button key={edge.id} onClick={() => setSelected(edge.to)}>
                        {edge.label || '继续'} →{' '}
                        {graph.nodes.find((node) => node.id === edge.to)?.label}
                      </button>
                    ))}
                </div>
                <WorkflowSourceLinks graphId={id} nodeId={node.id} navigate={navigate} />
                <NodeSignalNotes graph={graph} node={node} />
                <EvidenceDisclosure source>
                  <div className="evidence-stack">
                    {node.refs.map((id) => (
                      <EvidenceItem key={id} id={id} navigate={navigate} />
                    ))}
                  </div>
                </EvidenceDisclosure>
              </article>
            )}
          </div>
        </details>
      )}
      {related.length > 0 && (
        <section className="section">
          <div className="section-heading">
            <div>
              <h2>继续阅读</h2>
              <p>同一专题的相关图谱</p>
            </div>
            <button
              className="text-button"
              onClick={() => navigate({ kind: 'topic', id: topic!.id })}
            >
              返回专题 →
            </button>
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

function OriginalDiagram({
  path,
  title,
  onNode,
  theme,
}: {
  path: string;
  title: string;
  onNode?: (id: string) => void;
  theme: 'dark' | 'light';
}) {
  const [document, setDocument] = useState<Document | null>(null);
  const [initialTheme] = useState(theme);
  const revision = sourceDiagramRevision(resourceHref(path));
  const diagramURL = (color: string) =>
    `${resourceHref(path)}?theme=${color}${revision ? `&review=${revision}` : ''}`;
  const appearance = useAppearance((state) => state.mode);
  useEffect(() => {
    // 图谱预设控制节点样式，页面外观单独控制工具栏和阅读底色。
    if (document) document.documentElement.dataset.appearance = appearance;
  }, [document, appearance]);
  useEffect(() => {
    if (!document) return;
    const style = document.createElement('style');
    // iframe 有独立的字体上下文；同样引用本地字体，避免原图退回粗重的系统字形。
    style.textContent = `${diagramLatinFont}\n${diagramChineseFont}\n${diagramChrome}`;
    document.head.appendChild(style);
    const guide = document.getElementById('btn-diagram-guide');
    // 原图只比较按钮本身，图标点击会被误判为外部点击；保留按钮原有处理，再阻止冒泡。
    const keepGuideOpen = (event: Event) => event.stopPropagation();
    guide?.addEventListener('click', keepGuideOpen);
    return () => {
      style.remove();
      guide?.removeEventListener('click', keepGuideOpen);
    };
  }, [document]);
  useEffect(() => {
    if (!document || document.documentElement.dataset.theme === theme) return;
    const toggle = document.getElementById('btn-theme');
    if (toggle) toggle.click();
    else document.documentElement.dataset.theme = theme;
  }, [document, theme]);
  useEffect(() => {
    if (!document || !onNode) return;
    const select = (event: Event) => {
      const target = event.target as Element | null;
      const node = target?.closest?.('[data-node-id]');
      if (node) onNode(node.getAttribute('data-node-id')!);
    };
    const selectKeyboard = (event: KeyboardEvent) => {
      if (event.key === 'Enter' || event.key === ' ') select(event);
    };
    document.addEventListener('click', select, true);
    document.addEventListener('keyup', selectKeyboard, true);
    return () => {
      document.removeEventListener('click', select, true);
      document.removeEventListener('keyup', selectKeyboard, true);
    };
  }, [document, onNode]);
  return (
    <section className="section card panel original-diagram">
      <div className="panel-title">
        <div>
          <span className="eyebrow">流程图</span>
          <p>使用图内缩放、查找与演示工具阅读。生产主流程可点击节点，查看下方对应模块与源码。</p>
        </div>
        <a className="button" href={diagramURL(theme)} target="_blank" rel="noreferrer">
          全屏阅读 ↗
        </a>
      </div>
      <iframe
        title={`${title} 流程图`}
        src={diagramURL(initialTheme)}
        onLoad={(event) => setDocument(event.currentTarget.contentDocument)}
      />
    </section>
  );
}
function EvidenceDisclosure({
  children,
  source = false,
}: {
  children: ReactNode;
  source?: boolean;
}) {
  return (
    <details className="section card panel supporting-evidence">
      <summary>
        {source ? '源码依据' : '查看依据'}
        <span>{source ? '关联代码片段、文件路径与行号' : '源码、复核文档与检查记录'}</span>
      </summary>
      <div className="supporting-evidence-body">{children}</div>
    </details>
  );
}
function AssetLink({ label, path, hash }: { label: string; path: string; hash?: string | null }) {
  return (
    <a className="asset-link" href={resourceHref(path)} target="_blank" rel="noreferrer">
      <span>
        <b>{label}</b>
        <small>{path.replace(/^docs\/archify\//, '')}</small>
      </span>
      <span>{hash ? `${hash.slice(0, 12)}…` : '打开 ↗'}</span>
    </a>
  );
}
function EvidenceItem({ id, navigate }: { id: string; navigate: (route: Route) => void }) {
  const engineering = useEngineering();
  const binding =
    engineering &&
    Object.values(engineering.nodeBindings)
      .flat()
      .find((ref) => ref.id === id);
  const ref = archifyData.refs[id] as EvidenceRef | undefined;
  if (!ref) return null;
  return (
    <details className="card evidence-item">
      <summary>
        <span className="evidence-id">{id}</span>
        <strong>{ref.method}</strong>
        <small>
          {ref.path}:{ref.start}
        </small>
      </summary>
      <div className="evidence-body">
        <p>
          {ref.path}:{ref.start}–{ref.end} · SHA-256 {ref.sha256 ?? '未登记'}
        </p>
        <pre>{ref.code}</pre>
        {binding && <BindingLinks binding={binding} navigate={navigate} />}
      </div>
    </details>
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
