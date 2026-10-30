import { useState } from 'react';
import { NotebookPen, Search } from 'lucide-react';
import { HandoverSelect } from '../shared/Controls';
import {
  debugRecordType,
  debugRecordTypes,
  debugStatus,
  debugVisiblePayload,
  filterDebugIssues,
} from './debugIssues';
import { ids, text, type HandoverRecord } from '../shared/types';
import './debug-issues.css';

export function DebugIssuePage({
  rows,
  onOpen,
}: {
  rows: HandoverRecord[];
  onOpen: (id: string) => void;
}) {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [recordType, setRecordType] = useState('');
  const matches = filterDebugIssues(rows, search, status, recordType).map((row) => ({
    ...row,
    payload: debugVisiblePayload(row.payload),
  }));
  return (
    <section className="debug-issue-page" aria-label="问题与经验记录">
      <div className="debug-issue-tools">
        <label className="debug-issue-search">
          <Search size={16} />
          <input
            aria-label="搜索问题与经验"
            placeholder="搜索问题、答案或关键词…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <HandoverSelect
          value={recordType}
          onValueChange={setRecordType}
          label="记录类型"
          options={[{ value: '', label: '全部类型' }, ...debugRecordTypes]}
        />
        <HandoverSelect
          value={status}
          onValueChange={setStatus}
          label="记录状态"
          options={[
            { value: '', label: '全部状态' },
            { value: 'open', label: '未解决' },
            { value: 'resolved', label: '已解决' },
            { value: 'recorded', label: '已记录' },
          ]}
        />
        <span className="handover-muted">{matches.length} 条记录</span>
      </div>
      <div className="debug-issue-grid">
        {matches.map((row) => (
          <button key={row.id} className="debug-issue-card" onClick={() => onOpen(row.id)}>
            <div className="debug-issue-card-top">
              <NotebookPen size={17} />
              <span>{debugRecordType(row.payload).label}</span>
              <span
                className={`debug-status ${row.payload.resolution_status === 'recorded' ? 'recorded' : row.payload.resolution_status === 'resolved' ? 'resolved' : ''}`}
              >
                {debugStatus(row.payload)}
              </span>
            </div>
            <strong>{text(row.payload.question) || row.title}</strong>
            {text(row.payload.answer) && (
              <div className="debug-issue-solution">
                <span>答案</span>
                {text(row.payload.answer)}
              </div>
            )}
            {!!ids(row.payload.keywords).length && (
              <div className="debug-issue-tags">
                {ids(row.payload.keywords)
                  .slice(0, 6)
                  .map((tag, index) => (
                    <span key={`${tag}:${index}`}>{tag}</span>
                  ))}
              </div>
            )}
          </button>
        ))}
      </div>
      {!matches.length && (
        <div className="handover-empty-state">
          <NotebookPen size={26} />
          <strong>{search || status || recordType ? '没有匹配的记录' : '暂无记录'}</strong>
        </div>
      )}
    </section>
  );
}
