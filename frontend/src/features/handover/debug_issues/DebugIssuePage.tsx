import { useState } from 'react';
import { NotebookPen, Search } from 'lucide-react';
import { HandoverSelect } from '../shared/Controls';
import { debugRecordType, debugRecordTypes, debugStatus, filterDebugIssues } from './debugIssues';
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
  const matches = filterDebugIssues(rows, search, status, recordType);
  return (
    <section className="debug-issue-page" aria-label="问题与经验记录">
      <div className="debug-issue-tools">
        <label className="debug-issue-search">
          <Search size={16} />
          <input
            aria-label="搜索问题与经验"
            placeholder="搜索事项、记录人、日期或处理办法…"
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
      <p className="debug-issue-tip">
        也可以在对话中输入 <code>/记录问题</code>，再粘贴问题、经验或工作进展，由 AI 整理录入。
      </p>
      <div className="debug-issue-grid">
        {matches.map((row) => (
          <button key={row.id} className="debug-issue-card" onClick={() => onOpen(row.id)}>
            <div className="debug-issue-card-top">
              <NotebookPen size={17} />
              <span>{debugRecordType(row.payload).label}</span>
              <span
                className={`debug-status ${row.payload.resolution_status === 'recorded' ? 'recorded' : row.payload.resolution_status === 'resolved' ? 'resolved' : ''}`}
              >
                {row.state === 'archived' ? '已归档' : debugStatus(row.payload)}
              </span>
            </div>
            <strong>{row.title}</strong>
            <p>{text(row.payload.problem)}</p>
            {text(row.payload.solution) && (
              <div className="debug-issue-solution">
                <span>处理办法</span>
                {text(row.payload.solution)}
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
            <small>
              {text(row.payload.recorded_by) || text(row.payload.reported_by) || '未记录姓名'} ·{' '}
              {text(row.payload.recorded_at) ||
                text(row.payload.occurred_on) ||
                row.updated_at.slice(0, 10)}{' '}
              · {row.payload.origin === 'ai' ? 'AI 整理' : '手动录入'}
            </small>
          </button>
        ))}
      </div>
      {!matches.length && (
        <div className="handover-empty-state">
          <NotebookPen size={26} />
          <strong>
            {search || status || recordType ? '没有匹配的记录' : '记录工作中遇到的问题与经验'}
          </strong>
          <p>
            {search || status || recordType
              ? '试试其他关键词、类型或状态。'
              : '点击“添加记录”开始，或在对话中使用 /记录问题。'}
          </p>
        </div>
      )}
    </section>
  );
}
