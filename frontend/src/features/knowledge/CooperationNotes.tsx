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

export function ModuleCoordination({
  graph,
  focusedSignal,
}: {
  graph: FlowGraph;
  focusedSignal?: string;
}) {
  const entries = coordinationSignals(graph.slug);
  const active = entries.filter(hasActivity);
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
  const entries = coordinationSignals(graph.slug).filter(
    (signal) => hasActivity(signal) && node.signals.includes(signal.name),
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
