import { archifyData } from '../data/archifyData';
import { diagramReadings } from '../data/diagramReading';
import { displayDiagramTitle, topicForDiagram } from '../data/presentation';
import { NodeSignalNotes } from '../CooperationNotes';
import type { FlowchartCatalogEntry, FlowGraph } from '../types';
import type { Route } from '../routes';
import { OriginalDiagram } from '../OriginalDiagram';
import { ReaderFrame, DiagramNodeDetail, type DiagramNode } from './ReaderFrame';
import { ReaderPageHeader } from './ReaderPageHeader';
import { SourceGuidePanel } from '../SourceGuidePanel';
import { guideForPage } from '../sourceGuides';
import { GraphReadingNotes } from './GraphReadingNotes';

export function CatalogReader({
  entry,
  focusedSignal,
  navigate,
  theme,
}: {
  entry: FlowchartCatalogEntry;
  focusedSignal?: string;
  navigate: (route: Route) => void;
  theme: 'light' | 'dark';
}) {
  const id = entry.id;
  const title = displayDiagramTitle(id, entry.title);
  const reading = diagramReadings[id];
  const graph = archifyData.graphs.find((graph) => graph.slug === id);
  const topic = topicForDiagram(id);
  const readingNotes = topic?.diagrams[0] === id ? topic : undefined;
  const guide = readingNotes && guideForPage(readingNotes.id);
  const initialNode = graph?.nodes.find(
    (node) => focusedSignal && node.signals.includes(focusedSignal),
  );
  const diagram = (
    <ReaderFrame
      title={title}
      initialSelectedId={initialNode?.id}
      detail={(node, select) => <CatalogNodeDetail node={node} select={select} graph={graph} />}
    >
      {entry.html ? (
        <OriginalDiagram path={entry.html} title={title} theme={theme} />
      ) : (
        <div className="reader-loading">原图尚未生成</div>
      )}
    </ReaderFrame>
  );
  return (
    <>
      <ReaderPageHeader
        title={title}
        summary={reading.summary}
        navigate={navigate}
        actions={
          graph && (
            <button className="button" onClick={() => navigate({ kind: 'chat', flow: graph.slug })}>
              讨论这个流程
            </button>
          )
        }
      />
      {guide ? (
        <SourceGuidePanel page={guide.topic} overview={diagram} />
      ) : (
        <div className="unified-reader" data-reader-layout="diagram">
          {diagram}
        </div>
      )}
      {readingNotes && <GraphReadingNotes reading={readingNotes} includeSummary />}
    </>
  );
}

function CatalogNodeDetail({
  node,
  select,
  graph,
}: {
  node?: DiagramNode;
  select: (id: string) => void;
  graph?: FlowGraph;
}) {
  const detailed = graph?.nodes.find((item) => item.id === node?.id);
  if (!node || !detailed || !graph) return <DiagramNodeDetail node={node} select={select} />;
  return (
    <>
      <span className="reader-kicker">当前节点</span>
      <h2>{detailed.label}</h2>
      <section>
        <h3>作用与执行条件</h3>
        <p>{detailed.detail}</p>
      </section>
      {node.branches.length > 0 && (
        <section>
          <h3>后续分支</h3>
          <div className="reader-branches">
            {node.branches.map((branch) => (
              <button key={branch.id} type="button" onClick={() => select(branch.target)}>
                {branch.label}
              </button>
            ))}
          </div>
        </section>
      )}
      <NodeSignalNotes graph={graph} node={detailed} />
    </>
  );
}
