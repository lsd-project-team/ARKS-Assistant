import { Archive, ArchiveRestore, Package } from 'lucide-react';
import { useState } from 'react';
import { Button } from '../../../shared/ui/ui';
import type { Client } from '../shared/client';
import { filterCatalogRecords } from '../shared/catalogRecords';
import { CatalogCard, CatalogEmpty, CatalogToolbar } from '../shared/RecordCatalog';
import { text, type Definitions, type HandoverRecord } from '../shared/types';
import './package-list.css';
import { PackageArchiveDialog } from './PackageArchiveDialog';
import { packageGroups } from './packageContents';

export function PackageList({
  rows,
  definitions,
  archived,
  client,
  actor,
  onActor,
  onOpen,
  onChanged,
}: {
  rows: HandoverRecord[];
  definitions: Definitions;
  archived: boolean;
  client: Client;
  actor: string;
  onActor: (actor: string) => void;
  onOpen: (id: string) => void;
  onChanged: () => void;
}) {
  const [selected, setSelected] = useState<HandoverRecord>();
  const [search, setSearch] = useState('');
  const [state, setState] = useState('');
  const packages = filterCatalogRecords(rows, ['package'], search, archived ? '' : state);
  return (
    <section aria-label="交接包记录">
      <CatalogToolbar
        search={search}
        onSearch={setSearch}
        label="搜索交接包"
        placeholder="搜索交接包名称、接收对象或内容…"
        state={state}
        onState={setState}
        archived={archived}
        definitions={definitions}
        count={packages.length}
        unit="份交接包"
      />
      <div className="record-catalog-grid">
        {packages.map((row) => (
          <CatalogCard
            key={row.id}
            row={row}
            definitions={definitions}
            icon={Package}
            label="交接包"
            preview={text(row.payload.scope) || text(row.payload.notes) || text(row.payload.gaps)}
            metadata={[
              `${packageGroups(row.payload, []).reduce((sum, group) => sum + group.items.length, 0)} 条记录`,
              text(row.payload.recipient) && `接收：${text(row.payload.recipient)}`,
              row.created_at.slice(0, 10),
            ]
              .filter(Boolean)
              .join(' · ')}
            onOpen={onOpen}
            actions={
              <Button
                className="package-list-archive"
                aria-label={`${row.state === 'archived' ? '恢复' : '归档'}交接包：${row.title}`}
                onClick={() => setSelected(row)}
              >
                {row.state === 'archived' ? <ArchiveRestore size={14} /> : <Archive size={14} />}
                {row.state === 'archived' ? '恢复' : '归档'}
              </Button>
            }
          />
        ))}
      </div>
      {!packages.length && (
        <CatalogEmpty icon={Package} filtered={!!(search || (!archived && state))} />
      )}
      {selected && (
        <PackageArchiveDialog
          key={selected.id}
          row={selected}
          client={client}
          actor={actor}
          onActor={onActor}
          onClose={() => setSelected(undefined)}
          onChanged={onChanged}
        />
      )}
    </section>
  );
}
