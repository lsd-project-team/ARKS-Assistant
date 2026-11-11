import type { FlowchartCatalogEntry } from '../types';
import { presentationTopics } from '../data/presentation';
import { manualById } from '../data/manualCatalog';
import { CoordinateReader } from '../coordinates/CoordinateReader';
import { AtlasReader } from '../atlas/AtlasReader';
import { ManualReader } from '../manuals/ManualReader';
import { CatalogReader } from './CatalogReader';
import { GraphReadingNotes } from './GraphReadingNotes';

export function DiagramContent({
  entry,
  focusedSignal,
  theme,
}: {
  entry: FlowchartCatalogEntry;
  focusedSignal?: string;
  theme: 'dark' | 'light';
}) {
  if (manualById(entry.id)) return <ManualReader id={entry.id} theme={theme} />;
  const reading = presentationTopics.find((item) => item.id === entry.inlineTopic);
  if (reading)
    return (
      <>
        {reading.id === 'g0' ? <CoordinateReader /> : <AtlasReader page={reading.id} />}
        <GraphReadingNotes reading={reading} />
      </>
    );
  return <CatalogReader entry={entry} focusedSignal={focusedSignal} theme={theme} />;
}
