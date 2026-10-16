import { AlignLeft, FileCode2, FileText } from 'lucide-react';
import { useState } from 'react';
import { filterCatalogRecords } from '../shared/catalogRecords';
import { HandoverSelect } from '../shared/Controls';
import { CatalogCard, CatalogEmpty, CatalogToolbar } from '../shared/RecordCatalog';
import { text, type Definitions, type HandoverRecord } from '../shared/types';
import { materialPreview, materialType, materialTypes } from './materialRecords';

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
  const [type, setType] = useState('');
  const [state, setState] = useState('');
  // 历史访谈作为文本资料展示，保留原类型、原记录与固定版本引用。
  const matches = filterCatalogRecords(
    rows,
    ['source', 'interview'],
    search,
    archived ? '' : state,
  ).filter((row) => !type || materialType(row).value === type);
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
      >
        <HandoverSelect
          label="资料类型"
          value={type}
          onValueChange={setType}
          options={[{ value: '', label: '全部类型' }, ...materialTypes]}
        />
      </CatalogToolbar>
      <div className="record-catalog-grid">
        {matches.map((row) => {
          const type = materialType(row);
          return (
            <CatalogCard
              key={row.id}
              row={row}
              definitions={definitions}
              icon={
                type.value === 'text' ? AlignLeft : type.value === 'code' ? FileCode2 : FileText
              }
              label={type.label}
              preview={materialPreview(row)}
              metadata={[
                text(row.payload.provider) || text(row.payload.author),
                row.updated_at.slice(0, 10),
              ]
                .filter(Boolean)
                .join(' · ')}
              onOpen={onOpen}
            />
          );
        })}
      </div>
      {!matches.length && (
        <CatalogEmpty icon={FileText} filtered={!!(search || type || (!archived && state))} />
      )}
    </section>
  );
}
