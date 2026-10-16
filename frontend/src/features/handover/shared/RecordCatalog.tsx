import { Search, type LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';
import { HandoverSelect } from './Controls';
import { Status } from './RecordCard';
import type { Definitions, HandoverRecord } from './types';
import './record-catalog.css';

export function CatalogToolbar({
  search,
  onSearch,
  label,
  placeholder,
  state,
  onState,
  archived,
  definitions,
  count,
  unit,
  children,
}: {
  search: string;
  onSearch: (value: string) => void;
  label: string;
  placeholder: string;
  state: string;
  onState: (value: string) => void;
  archived: boolean;
  definitions: Definitions;
  count: number;
  unit: string;
  children?: ReactNode;
}) {
  return (
    <div className="record-catalog-tools">
      <label className="record-catalog-search">
        <Search size={16} />
        <input
          aria-label={label}
          placeholder={placeholder}
          value={search}
          onChange={(event) => onSearch(event.target.value)}
        />
      </label>
      {children}
      <HandoverSelect
        label="记录状态"
        value={archived ? 'archived' : state}
        onValueChange={onState}
        disabled={archived}
        options={
          archived
            ? [{ value: 'archived', label: definitions.states.archived || '已归档' }]
            : [
                { value: '', label: '全部状态' },
                ...Object.entries(definitions.states)
                  .filter(([value]) => value !== 'archived')
                  .map(([value, label]) => ({ value, label })),
              ]
        }
      />
      <span className="record-catalog-count">
        {count} {unit}
      </span>
    </div>
  );
}

export function CatalogCard({
  row,
  definitions,
  icon: Icon,
  label,
  preview,
  metadata,
  onOpen,
  actions,
}: {
  row: HandoverRecord;
  definitions: Definitions;
  icon: LucideIcon;
  label: string;
  preview: string;
  metadata: ReactNode;
  onOpen: (id: string) => void;
  actions?: ReactNode;
}) {
  return (
    <article className="record-catalog-card">
      <button
        className="record-catalog-open"
        aria-label={`查看记录：${row.title}`}
        onClick={() => onOpen(row.id)}
      >
        <div className="record-catalog-card-top">
          <Icon size={17} />
          <span>
            {label} · v{row.version}
          </span>
          <Status row={row} definitions={definitions} />
        </div>
        <strong>{row.title}</strong>
        {preview && <p>{preview}</p>}
        <small>{metadata}</small>
      </button>
      {actions && <div className="record-catalog-actions">{actions}</div>}
    </article>
  );
}

export function CatalogEmpty({ icon: Icon, filtered }: { icon: LucideIcon; filtered: boolean }) {
  return (
    <div className="record-catalog-empty">
      <Icon size={26} />
      <strong>{filtered ? '没有匹配的记录' : '暂无记录'}</strong>
    </div>
  );
}
