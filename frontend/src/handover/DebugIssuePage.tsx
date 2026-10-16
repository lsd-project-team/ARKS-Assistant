import { useState } from 'react';
import { Bug, Search } from 'lucide-react';
import { HandoverSelect } from './Controls';
import { debugStatus, filterDebugIssues } from './debugIssues';
import { ids, text, type HandoverRecord } from './types';
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
  const matches = filterDebugIssues(rows, search, status);
  return (
    <section className="debug-issue-page" aria-label="调试问题库">
      <div className="debug-issue-tools">
        <label className="debug-issue-search">
          <Search size={16} />
          <input
            aria-label="搜索调试问题"
            placeholder="搜索现象、报警码、原因或处理办法…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <HandoverSelect
          value={status}
          onValueChange={setStatus}
          label="调试问题状态"
          options={[
            { value: '', label: '全部状态' },
            { value: 'open', label: '未解决' },
            { value: 'resolved', label: '已解决' },
          ]}
        />
        <span className="handover-muted">{matches.length} 条记录</span>
      </div>
      <p className="debug-issue-tip">
        也可以在对话中输入 <code>/记录问题</code>，再粘贴调试过程，由 AI 整理录入。
      </p>
      <div className="debug-issue-grid">
        {matches.map((row) => (
          <button key={row.id} className="debug-issue-card" onClick={() => onOpen(row.id)}>
            <div className="debug-issue-card-top">
              <Bug size={17} />
              <span
                className={`debug-status ${row.payload.resolution_status === 'resolved' ? 'resolved' : ''}`}
              >
                {row.state === 'archived' ? '已归档' : debugStatus(row.payload)}
              </span>
            </div>
            <strong>{row.title}</strong>
            <p>{text(row.payload.problem)}</p>
            <div className="debug-issue-solution">
              <span>处理办法</span>
              {text(row.payload.solution) || '待补充'}
            </div>
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
              {text(row.payload.reported_by) || '未记录姓名'} · {row.updated_at.slice(0, 10)} ·{' '}
              {row.payload.origin === 'ai' ? 'AI 整理' : '手动录入'}
            </small>
          </button>
        ))}
      </div>
      {!matches.length && (
        <div className="handover-empty-state">
          <Bug size={26} />
          <strong>{search || status ? '没有匹配的调试问题' : '把调试中遇到的问题记录下来'}</strong>
          <p>
            {search || status
              ? '试试其他关键词或状态。'
              : '点击“记录调试问题”开始，或在对话中使用 /记录问题。'}
          </p>
        </div>
      )}
    </section>
  );
}
