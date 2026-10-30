import { useProjectApi } from '../../projects/hooks/useProjectApi';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, FileCode2 } from 'lucide-react';
import { query } from '../../../app/api/client';
import { useDebouncedValue } from '../../../shared/hooks/useDebouncedValue';
import { useSourceCitation } from '../hooks/useSourceCitation';
import { Modal, ErrorText } from '../../../shared/ui/ui';
import { Highlight } from '../../../shared/ui/markdown/Highlight';

interface SourceMatch {
  path: string;
  line: number;
  text: string;
}
export function WorkspaceSearch({ onClose }: { onClose: () => void }) {
  const api = useProjectApi();
  const [text, setText] = useState('');
  const [glob, setGlob] = useState('*');
  const settled = useDebouncedValue(text.trim());
  const settledGlob = useDebouncedValue(glob.trim() || '*');
  const locate = useSourceCitation();
  const results = useQuery({
    queryKey: ['workspace-search', settled, settledGlob],
    queryFn: () =>
      api<{ matches: SourceMatch[]; truncated: boolean }>(
        `/search?query=${query(settled)}&glob=${query(settledGlob)}`,
      ),
    enabled: !!settled,
  });
  const groups = new Map<string, SourceMatch[]>();
  for (const match of results.data?.matches || [])
    groups.set(match.path, [...(groups.get(match.path) || []), match]);
  return (
    <Modal
      open
      title="搜索源码"
      className="source-search-dialog"
      description="查找 trunk 内的文字，点击结果定位到对应行"
      onClose={onClose}
    >
      <div className="dialog-body workspace-search-body">
        <label className="search-box workspace-search-input">
          <Search size={15} />
          <input
            autoFocus
            aria-label="源码全文搜索"
            placeholder="在 trunk 中搜索文字…"
            maxLength={300}
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
        </label>
        <label className="workspace-search-filter">
          文件范围
          <input
            aria-label="搜索文件范围"
            value={glob}
            maxLength={120}
            onChange={(event) => setGlob(event.target.value)}
            placeholder="*.cs 或 Module/**"
          />
        </label>
        <ErrorText error={results.error} />
        {settled && (
          <p className="muted">
            {results.isFetching
              ? '正在搜索…'
              : `${results.data?.matches.length || 0} 处匹配，${groups.size} 个文件`}
            {results.data?.truncated && ' · 结果超过 100 处，请缩小文件范围或补充关键词'}
          </p>
        )}
        <div className="workspace-search-results">
          {[...groups].map(([path, matches]) => (
            <section key={path}>
              <strong>
                <FileCode2 size={13} />
                {path}
              </strong>
              {matches.map((match, index) => (
                <button
                  key={`${match.line}:${index}`}
                  title={`${path}:${match.line}`}
                  onClick={() =>
                    void locate(path, match.line).then((opened) => opened && onClose())
                  }
                >
                  <small>{match.line}</small>
                  <code>
                    <Highlight text={match.text} query={settled} />
                  </code>
                </button>
              ))}
            </section>
          ))}
          {!settled && (
            <p className="muted">支持中文和符号；搜索词按原文匹配，文件范围可填路径模式。</p>
          )}
        </div>
      </div>
    </Modal>
  );
}
