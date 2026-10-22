import { archifyData } from './data/archifyData';
import { presentationTopics, displayDiagramTitle } from './data/presentation';
import { isSupportingEntry } from './data/diagramReading';
import type { PresentationTopic } from './data/presentation';
import { UiIcon } from './UiIcon';

interface Navigation {
  onTopic: (id: string) => void;
  onDiagram: (id: string) => void;
  onAllDiagrams: () => void;
}

export function ShowcaseHome({ onTopic, onDiagram, onAllDiagrams }: Navigation) {
  return (
    <div className="showcase-page">
      <section className="showcase-hero card">
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
          <p>从业务流程理解模块职责，沿节点进入调用关系和对应源码，查看梳理与复核进度。</p>
          <div className="card-actions">
            <button className="button primary" onClick={() => onTopic('architecture')}>
              从系统架构开始
              <UiIcon name="arrow" />
            </button>
            <button className="button hero-secondary" onClick={() => onDiagram('startup-workflow')}>
              阅读启动流程
            </button>
          </div>
        </div>
        <div className="showcase-outline">
          <span className="eyebrow">阅读路线</span>
          <ol>
            {[
              ['建立系统模型', '理解边界与模块职责'],
              ['阅读生产主流程', '串起启动、加工与交接'],
              ['展开专题与条件', '了解执行条件与异常处理'],
              ['定位调用与完整源码', '从业务节点追溯代码实现'],
            ].map(([text, description], index) => (
              <li key={text}>
                <span className="route-number">{String(index + 1).padStart(2, '0')}</span>
                <div>
                  <b>{text}</b>
                  <small>{description}</small>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>
      <div className="presentation-metrics">
        <span>
          <b>{presentationTopics.length.toString().padStart(2, '0')}</b>
          <small>阅读专题</small>
        </span>
        <span>
          <b>{archifyData.graphs.length.toString().padStart(2, '0')}</b>
          <small>生产主流程</small>
        </span>
        <span>
          <b>
            {
              archifyData.flowchartCatalog.entries.filter((entry) => !isSupportingEntry(entry))
                .length
            }
          </b>
          <small>流程图谱</small>
        </span>
      </div>
      <section className="section">
        <div className="section-heading">
          <div>
            <h2>生产主流程</h2>
            <p>沿启动、来料、加工、交接与恢复逐步阅读</p>
          </div>
          <button className="text-button" onClick={onAllDiagrams}>
            全部图谱
            <UiIcon name="arrow" />
          </button>
        </div>
        <div className="production-chapters">
          {archifyData.graphs.map((graph, index) => (
            <button
              key={graph.slug}
              className="card production-chapter"
              onClick={() => onDiagram(graph.slug)}
            >
              <span>{String(index + 1).padStart(2, '0')}</span>
              <b>{displayDiagramTitle(graph.slug, graph.title)}</b>
              <UiIcon name="arrow" />
            </button>
          ))}
        </div>
      </section>
      <TopicDirectory onOpen={onTopic} embedded />
    </div>
  );
}

export function TopicDirectory({
  onOpen,
  embedded = false,
}: {
  onOpen: (id: string) => void;
  embedded?: boolean;
}) {
  return (
    <section className="section topic-directory">
      {!embedded && (
        <div className="page-header">
          <div>
            <span className="eyebrow">功能与流程</span>
            <h1>按你关心的问题阅读</h1>
            <p>从系统全局到生产、维护与数据，查看用途、条件、异常处理和相关原始图谱。</p>
          </div>
        </div>
      )}
      {embedded && (
        <div className="section-heading">
          <div>
            <h2>功能与专题</h2>
            <p>把已形成的成果按实际用途整理</p>
          </div>
        </div>
      )}
      <div className="topic-grid">
        {presentationTopics.map((topic, index) => {
          const count = archifyData.flowchartCatalog.entries.filter(
            (entry) => topic.diagrams.includes(entry.id) && !isSupportingEntry(entry),
          ).length;
          return (
            <button key={topic.id} className="card topic-card" onClick={() => onOpen(topic.id)}>
              <div className="topic-card-meta">
                <span className="eyebrow">{String(index + 1).padStart(2, '0')}</span>
                <span>{count} 个图谱与说明</span>
              </div>
              <h2>{topic.title}</h2>
              <p>{topic.summary}</p>
              <strong>
                阅读专题
                <UiIcon name="arrow" />
              </strong>
            </button>
          );
        })}
      </div>
    </section>
  );
}

export function TopicReading({ topic }: { topic: PresentationTopic }) {
  return (
    <section className="section reading-summary">
      <article className="card panel">
        <span className="eyebrow">功能用途</span>
        <h2>这个环节做什么</h2>
        <p>{topic.purpose}</p>
      </article>
      <article className="card panel">
        <span className="eyebrow">运行条件</span>
        <h2>哪些条件影响执行</h2>
        <ul>
          {topic.conditions.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
      </article>
      <article className="card panel">
        <span className="eyebrow">异常与边界</span>
        <h2>失败时如何理解</h2>
        <ul>
          {topic.exceptions.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
      </article>
    </section>
  );
}
