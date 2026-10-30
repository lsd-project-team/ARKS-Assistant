import { FileText, Search } from 'lucide-react';
import { useState } from 'react';
import { localTime } from '../shared/format';
import type { HandoverRecord } from '../shared/types';
import { materialFiles, materialName } from './materialRecords';
import './materials.css';

export function MaterialFileList({
  rows,
  onOpen,
}: {
  rows: HandoverRecord[];
  onOpen: (id: string) => void;
}) {
  return (
    <ul className="material-file-list">
      {rows.map((row) => (
        <li key={row.id}>
          <button
            className="material-file"
            aria-label={`查看原文件：${materialName(row)}`}
            onClick={() => onOpen(row.id)}
          >
            <FileText size={22} />
            <strong>{materialName(row)}</strong>
            <span className="material-uploader" aria-label="上传人">
              {row.created_by || '—'}
            </span>
            <time dateTime={row.created_at}>{localTime(row.created_at)}</time>
          </button>
        </li>
      ))}
    </ul>
  );
}

export function MaterialsPage({
  rows,
  onOpen,
}: {
  rows: HandoverRecord[];
  onOpen: (id: string) => void;
}) {
  const [search, setSearch] = useState('');
  const matches = materialFiles(rows, search);
  return (
    <section aria-label="资料文件">
      <div className="material-file-tools">
        <label className="material-file-search">
          <Search size={16} />
          <input
            aria-label="搜索资料"
            placeholder="搜索文件名或上传人…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <span>{matches.length} 份资料</span>
      </div>
      {matches.length ? (
        <MaterialFileList rows={matches} onOpen={onOpen} />
      ) : (
        <div className="material-file-empty">
          <FileText size={28} />
          <p>{search ? '没有匹配的资料' : '暂无资料'}</p>
        </div>
      )}
    </section>
  );
}
