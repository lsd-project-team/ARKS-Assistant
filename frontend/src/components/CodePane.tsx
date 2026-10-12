import { useProjectApi } from '../hooks/useProjectApi';
import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileCode2, LockKeyhole, ChevronRight, X } from 'lucide-react';
import { query } from '../lib/api';
import { useWorkspace } from '../lib/store';
import type { SourceFile } from '../types';
import { ErrorText } from './ui';
import { SourceViewer } from './SourceViewer';
import { MarkdownPreview } from './MarkdownPreview';
import { FileToolbar } from './FileToolbar';
import { FileTabs } from './FileTabs';

export function CodePane({ onSearch }: { onSearch: () => void }) {
  const api = useProjectApi();
  const { activePath, wordWrap, sourceModes, navigateHistory, setLayout } = useWorkspace();
  const markdown = /\.(md|markdown)$/i.test(activePath);
  const showSource = !markdown || !!sourceModes[activePath];
  const source = useQuery({
    queryKey: ['source', activePath],
    queryFn: () => api<SourceFile>(`/file?path=${query(activePath)}`),
    enabled: !!activePath,
  });
  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      const editing = (event.target as HTMLElement)?.closest(
        'input, textarea, [contenteditable="true"], [role="dialog"]',
      );
      if (editing || !event.altKey || !['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
      event.preventDefault();
      navigateHistory(event.key === 'ArrowLeft' ? -1 : 1);
    };
    window.addEventListener('keydown', shortcut);
    return () => window.removeEventListener('keydown', shortcut);
  }, [navigateHistory]);
  return (
    <section className="code-pane" aria-label="源码显示区">
      <div className="code-heading">
        <FileTabs />
        <button
          className="close-code-pane"
          aria-label="关闭源码显示区"
          title="关闭源码显示区"
          onClick={() => setLayout({ codeOpen: false })}
        >
          <X size={16} />
        </button>
      </div>
      <FileToolbar
        markdown={markdown}
        showSource={showSource}
        onSearch={onSearch}
        onRefresh={() => {
          useWorkspace.getState().restoreReadingPosition();
          void source.refetch();
        }}
        loading={source.isFetching}
        lineCount={source.data?.line_count || 0}
      />
      <div
        className="editor-container"
        id="source-reading-panel"
        role="tabpanel"
        aria-label={activePath || '文件阅读区'}
      >
        <ErrorText error={source.error} />
        {source.data ? (
          showSource ? (
            <SourceViewer
              key={`${activePath}:${source.data.version}`}
              source={source.data}
              wordWrap={wordWrap}
            />
          ) : (
            <MarkdownPreview key={`${activePath}:${source.data.version}`} source={source.data} />
          )
        ) : activePath ? (
          <div className="editor-empty">
            <p>
              {source.isPending ? '正在读取文件…' : '暂时无法打开这个文件，请重试或选择其他文件。'}
            </p>
          </div>
        ) : (
          <div className="editor-empty">
            <div className="empty-code-icon">
              <FileCode2 size={30} strokeWidth={1.3} />
            </div>
            <h2>从源码开始</h2>
            <p>从右侧文件树打开文件，选中代码后加入左侧问答。</p>
            <div className="empty-hint">
              <span>浏览文件</span>
              <ChevronRight size={12} />
              <span>选中代码</span>
              <ChevronRight size={12} />
              <span>向 Agent 提问</span>
            </div>
          </div>
        )}
      </div>
      <div className="code-status">
        <span>
          <LockKeyhole size={11} />
          {markdown && !showSource ? '文档预览 · 只读' : '源码只读'}
        </span>
        <span>
          {source.data?.encoding || 'UTF-8'}
          {source.data && ` · ${source.data.line_count} 行`}
        </span>
      </div>
    </section>
  );
}
