import { manualById } from '../data/manualCatalog';
import { OriginalDiagram } from '../OriginalDiagram';
import { ReaderFrame } from '../reader/ReaderFrame';

export function ManualReader({
  id,
  theme,
}: {
  id: string;
  section?: string;
  theme: 'dark' | 'light';
}) {
  const entry = manualById(id)!;
  return (
    <div className="unified-reader" data-reader-layout="diagram">
      <ReaderFrame title={entry.title}>
        <OriginalDiagram
          path={`docs/archify/manuals/${entry.file}`}
          title={entry.title}
          theme={theme}
        />
      </ReaderFrame>
    </div>
  );
}
