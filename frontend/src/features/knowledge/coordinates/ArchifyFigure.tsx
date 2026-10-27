import { OriginalDiagram } from '../OriginalDiagram';
import { coordinateDiagrams } from '../data/coordinateDiagrams';
import { useAppearance } from '../../settings/lib/appearance';

export function ArchifyFigure({ id }: { id: (typeof coordinateDiagrams)[number]['id'] }) {
  const diagram = coordinateDiagrams.find((item) => item.id === id)!;
  const appearance = useAppearance((state) => state.mode);
  return (
    <OriginalDiagram
      compact
      path={diagram.path}
      title={diagram.title}
      artifactRevision={diagram.sha256}
      theme={appearance === 'dark' ? 'dark' : 'light'}
    />
  );
}
