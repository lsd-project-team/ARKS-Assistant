import { Select } from '../../../shared/ui/Select';
import type { FlowchartCatalogEntry } from '../types';
import { displayDiagramTitle } from '../data/presentation';

export function GraphViewSelector({
  entries,
  selected,
  onSelect,
}: {
  entries: FlowchartCatalogEntry[];
  selected: string;
  onSelect: (id: string) => void;
}) {
  if (entries.length < 2) return null;
  return (
    <div className="graph-view-selector">
      <span>查看图谱</span>
      <Select aria-label="选择主图或细节图" value={selected} onValueChange={onSelect}>
        {entries.map((entry, index) => (
          <option key={entry.id} value={entry.id}>
            {displayDiagramTitle(entry.id, entry.title)}
            {index === 0 ? '（主图）' : ''}
          </option>
        ))}
      </Select>
      <span className="muted">共 {entries.length} 张图</span>
    </div>
  );
}
