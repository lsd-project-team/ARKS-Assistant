import { FileText } from 'lucide-react';
import { useState } from 'react';
import { filterCatalogRecords } from '../shared/catalogRecords';
import { CatalogCard, CatalogEmpty, CatalogToolbar } from '../shared/RecordCatalog';
import { text, type Definitions, type HandoverRecord } from '../shared/types';
import { materialPreview } from './materialRecords';

export function MaterialsPage({
  rows,
  definitions,
  archived,
  onOpen,
}: {
  rows: HandoverRecord[];
  definitions: Definitions;
  archived: boolean;
  onOpen: (id: string) => void;
}) {
  const [search, setSearch] = useState('');
  const [state, setState] = useState('');
  // 历史访谈作为文本资料展示，保留原类型、原记录与固定版本引用。
  const matches = filterCatalogRecords(
    rows,
    ['source', 'interview'],
    search,
    archived ? '' : state,
  );
  return (
    <section aria-label="资料记录">
      <CatalogToolbar
        search={search}
        onSearch={setSearch}
        label="搜索资料"
        placeholder="搜索资料名称、内容或提供人…"
        state={state}
        onState={setState}
        archived={archived}
        definitions={definitions}
        count={matches.length}
        unit="份资料"
      />
      <div className="record-catalog-grid">
        {matches.map((row) => (
          <CatalogCard
            key={row.id}
            row={row}
            definitions={definitions}
            icon={FileText}
            label="资料"
            preview={materialPreview(row)}
            metadata={[
              text(row.payload.provider) || text(row.payload.author),
              row.updated_at.slice(0, 10),
            ]
              .filter(Boolean)
              .join(' · ')}
            onOpen={onOpen}
          />
        ))}
      </div>
      {!matches.length && (
        <CatalogEmpty icon={FileText} filtered={!!(search || (!archived && state))} />
      )}
    </section>
  );
}
