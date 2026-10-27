import { coordinateDiagrams } from '../data/coordinateDiagrams';
import type { CoordinateDiagram } from '../data/coordinateDiagrams';
import { useAppearance } from '../../settings/lib/appearance';
import { ReadingDiagram } from './ReadingDiagram';

export function ArchifyFigure({ id }: { id: (typeof coordinateDiagrams)[number]['id'] }) {
  const diagram: CoordinateDiagram = coordinateDiagrams.find((item) => item.id === id)!;
  const appearance = useAppearance((state) => state.mode);
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
      />
    </figure>
  );
}
