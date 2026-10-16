import { useState } from 'react';
import { Archive, ArchiveRestore } from 'lucide-react';
import { Button } from '../components/ui';
import { RecordCard } from './RecordView';
import { PackageArchiveDialog } from './PackageArchiveDialog';
import type { Client } from './client';
import type { Definitions, HandoverRecord } from './types';
import './package-list.css';

export function PackageList({
  rows,
  definitions,
  client,
  actor,
  onActor,
  onOpen,
  onChanged,
}: {
  rows: HandoverRecord[];
  definitions: Definitions;
  client: Client;
  actor: string;
  onActor: (actor: string) => void;
  onOpen: (id: string) => void;
  onChanged: () => void;
}) {
  const [selected, setSelected] = useState<HandoverRecord>();
  const packages = rows.filter((row) => row.kind === 'package');
  return (
    <section className="handover-group">
      <header className="handover-group-heading">
        <div>
          <h3>
            交接包<span className="handover-count">{packages.length}</span>
          </h3>
          <p>保留生成时的记录版本，供查阅与下载。</p>
        </div>
      </header>
      <div className="handover-cards">
        {packages.map((row) => (
          <div className="package-list-item" key={row.id}>
            <RecordCard row={row} definitions={definitions} onOpen={onOpen} />
            {
              <Button
                className="package-list-archive"
                aria-label={`${row.state === 'archived' ? '恢复' : '归档'}交接包：${row.title}`}
                onClick={() => setSelected(row)}
              >
                {row.state === 'archived' ? <ArchiveRestore size={14} /> : <Archive size={14} />}
                {row.state === 'archived' ? '恢复' : '归档'}
              </Button>
            }
          </div>
        ))}
      </div>
      {!packages.length && <p className="handover-group-empty">暂无交接包。</p>}
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
