import { useEffect } from 'react';
import { archifyData } from './data/archifyData';
import { coordinationSummaries, signalGuides } from './moduleCoordination';
import type { FlowGraph, GraphNode, SignalDefinition } from './types';

const signals = Object.values(archifyData.signals) as SignalDefinition[];
export const coordinationSignals = (slug: string) =>
  signals.filter((signal) => signalGuides[signal.name]?.chapters.includes(slug));
const hasActivity = (signal: SignalDefinition) =>
  signal.references.some((reference) => reference.operation !== 'ReSet');
const signalElementId = (name: string) => `coordination-${name}`;

function SignalDescriptions({
  entries,
  focusedSignal,
  identify = false,
}: {
  entries: SignalDefinition[];
  focusedSignal?: string;
  identify?: boolean;
}) {
  return (
    <ul className="coordination-list">
      {entries.map((signal) => (
        <li
          key={signal.name}
          id={identify ? signalElementId(signal.name) : undefined}
          data-selected={signal.name === focusedSignal}
        >
          <b>{signalGuides[signal.name].title}</b>
          <p>{signalGuides[signal.name].description}</p>
        </li>
      ))}
    </ul>
  );
}

function SignalEvidence({ signal }: { signal: SignalDefinition }) {
  return (
    <details className="coordination-evidence">
      <summary>
        {signalGuides[signal.name].title}
        <code>{signal.name}</code>
      </summary>
      <p>{signalGuides[signal.name].description}</p>
      <p>
        复位方式：{signal.resetMode ?? '未登记'} · 声明：{signal.declarationPath ?? 'SignalPool.cs'}
        :{signal.declarationLine ?? '—'}
      </p>
      {signal.references.length ? (
        <div className="signal-refs">
          {signal.references.map((reference, index) => (
            <details
              key={`${reference.path}-${reference.line}-${index}`}
              className="card evidence-item"
            >
              <summary>
                <strong>{reference.operation}</strong>
                <small>
                  {reference.path}:{reference.line}
                </small>
              </summary>
              <div className="evidence-body">
                <pre>{reference.code}</pre>
              </div>
            </details>
          ))}
        </div>
      ) : (
        <p>此项仅保留声明，当前数据没有活动引用。</p>
      )}
    </details>
  );
}

export function ModuleCoordination({
  graph,
  focusedSignal,
}: {
  graph: FlowGraph;
  focusedSignal?: string;
}) {
  const entries = coordinationSignals(graph.slug);
  const active = entries.filter(hasActivity);
  const reserved = entries.filter((signal) => !hasActivity(signal));
  useEffect(() => {
    if (focusedSignal && entries.some((signal) => signal.name === focusedSignal)) {
      document.getElementById(signalElementId(focusedSignal))?.scrollIntoView({ block: 'center' });
    }
  }, [focusedSignal, graph.slug]);
  return (
    <section className="section card panel module-coordination" aria-label="模块协作说明">
      <div className="panel-title">
        <div>
          <span className="eyebrow">协作条件</span>
          <h2>模块如何协作</h2>
          <p>{coordinationSummaries[graph.slug]}</p>
        </div>
      </div>
      {active.length > 0 && (
        <SignalDescriptions entries={active} focusedSignal={focusedSignal} identify />
      )}
      {entries.length > 0 && (
        <details
          className="coordination-source"
          open={
            Boolean(focusedSignal && reserved.some((signal) => signal.name === focusedSignal)) ||
            undefined
          }
        >
          <summary>
            查看协作依据<span>信号定义与相关操作</span>
          </summary>
          {entries.map((signal) => (
            <div
              key={signal.name}
              id={hasActivity(signal) ? undefined : signalElementId(signal.name)}
              data-selected={signal.name === focusedSignal}
            >
              <SignalEvidence signal={signal} />
            </div>
          ))}
        </details>
      )}
    </section>
  );
}

export function TopicCoordination({ diagrams }: { diagrams: string[] }) {
  const graphs = archifyData.graphs.filter((graph) => diagrams.includes(graph.slug));
  if (!graphs.length) return null;
  return (
    <section className="section">
      <div className="section-heading">
        <div>
          <h2>模块协作与交接条件</h2>
          <p>结合这个环节，了解谁发出通知、谁等待条件</p>
        </div>
      </div>
      <div className="coordination-topics">
        {graphs.map((graph) => {
          const active = coordinationSignals(graph.slug).filter(hasActivity);
          return (
            <article key={graph.slug} className="card panel">
              <h3>{graph.title.replace(/^\d+ · /, '')}</h3>
              <p>{coordinationSummaries[graph.slug]}</p>
              {active.length > 0 && (
                <details className="module-cooperation">
                  <summary>查看协作条件 · {active.length} 项</summary>
                  <SignalDescriptions entries={active} />
                </details>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}

export function NodeSignalNotes({ graph, node }: { graph: FlowGraph; node: GraphNode }) {
  const code = node.refs.map((id) => archifyData.refs[id]?.code ?? '').join('\n');
  const entries = coordinationSignals(graph.slug).filter(
    (signal) => hasActivity(signal) && new RegExp(`\\b${signal.name}\\b`).test(code),
  );
  if (!entries.length) return null;
  return (
    <div className="node-coordination">
      <h3>相关协作条件</h3>
      <ul>
        {entries.map((signal) => (
          <li key={signal.name}>
            <b>{signalGuides[signal.name].title}</b>
            <p>{signalGuides[signal.name].description}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
