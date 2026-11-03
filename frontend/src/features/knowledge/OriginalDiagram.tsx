import { archifyData } from './data/archifyData';
import { ReaderFrame, useReaderCanvas } from './reader/ReaderFrame';
import { DiagramViewport } from './reader/DiagramViewport';

export function OriginalDiagram({
  path,
  title,
  onNode,
}: {
  path: string;
  title: string;
  onNode?: (id: string) => void;
  theme: 'dark' | 'light';
  reader?: boolean;
}) {
  const context = useReaderCanvas();
  const revision = archifyData.flowchartCatalog.entries
    .find((entry) => entry.html === path)
    ?.htmlSha256?.slice(0, 16);
  const canvas = (
    <DiagramViewport
      path={`/archify/${path.replace(/^docs[\\/]archify[\\/]/, '')}`}
      revision={revision}
      title={title}
    />
  );
  return context ? (
    canvas
  ) : (
    <ReaderFrame title={title} onSelect={onNode}>
      {canvas}
    </ReaderFrame>
  );
}
