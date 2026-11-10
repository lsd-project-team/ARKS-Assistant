import { useEffect, useRef, useState } from 'react';
import { coordinateDiagrams } from '../data/coordinateDiagrams';
import type { CoordinateDiagram } from '../data/coordinateDiagrams';
import { useAppearance } from '../../settings/lib/appearance';
import { ReadingDiagram } from './ReadingDiagram';
import { useReaderCanvas } from '../reader/ReaderFrame';
import { DiagramViewport } from '../reader/DiagramViewport';

export function ArchifyFigure({ id }: { id: (typeof coordinateDiagrams)[number]['id'] }) {
  const diagram: CoordinateDiagram = coordinateDiagrams.find((item) => item.id === id)!;
  return <ReadingFigure diagram={diagram} />;
}

export function ReadingFigure({ diagram }: { diagram: CoordinateDiagram }) {
  const appearance = useAppearance((state) => state.mode);
  const reader = useReaderCanvas();
  if (reader) return <ReaderFigure diagram={diagram} />;
  return (
    <figure className="g0-archify">
      <div className="panel-title">
        <span className="eyebrow">Archify · {diagram.title}</span>
        <a
          className="button"
          href={`/archify/${diagram.path}?theme=${appearance === 'dark' ? 'dark' : 'light'}&review=${diagram.sha256.slice(0, 16)}`}
          target="_blank"
          rel="noreferrer"
        >
          完整图谱 ↗
        </a>
      </div>
      <ReadingDiagram
        source={diagram.reading ?? diagram}
        narrow={diagram.narrow}
        title={diagram.title}
        readingMinWidth={diagram.readingMinWidth}
        readingFontSize={diagram.readingFontSize}
      />
    </figure>
  );
}

function ReaderFigure({ diagram }: { diagram: CoordinateDiagram }) {
  const container = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState<number>();
  useEffect(() => {
    if (!container.current) return;
    const observer = new ResizeObserver(([entry]) => {
      if (entry.contentRect.width > 0) setWidth(entry.contentRect.width);
    });
    observer.observe(container.current);
    return () => observer.disconnect();
  }, []);
  const source =
    diagram.narrow && width !== undefined && width < (diagram.readingMinWidth ?? 640)
      ? diagram.narrow
      : (diagram.reading ?? diagram);
  return (
    <div ref={container} data-archify-source={source.path}>
      <DiagramViewport
        path={`/archify/${source.path}`}
        revision={source.sha256.slice(0, 16)}
        title={diagram.title}
      />
    </div>
  );
}
