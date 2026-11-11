import { manualById } from '../data/manualCatalog';
import { OriginalDiagram } from '../OriginalDiagram';
import type { Route } from '../routes';
import { ReaderFrame } from '../reader/ReaderFrame';
import { ReaderPageHeader } from '../reader/ReaderPageHeader';

type Navigate = (route: Route) => void;

export function ManualReader({
  id,
  navigate,
  theme,
}: {
  id: string;
  section?: string;
  navigate: Navigate;
  theme: 'dark' | 'light';
}) {
  const entry = manualById(id)!;
  return (
    <>
      <ReaderPageHeader title={entry.title} summary={entry.summary} navigate={navigate} />
      <div className="unified-reader" data-reader-layout="diagram">
        <ReaderFrame title={entry.title}>
          <OriginalDiagram
            path={`docs/archify/manuals/${entry.file}`}
            title={entry.title}
            theme={theme}
          />
        </ReaderFrame>
      </div>
    </>
  );
}
