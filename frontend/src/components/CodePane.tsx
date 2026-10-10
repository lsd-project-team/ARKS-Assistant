import { useEffect, useRef, useState } from 'react';
import Editor, { type OnMount, loader } from '@monaco-editor/react';
import * as monaco from 'monaco-editor/esm/vs/editor/editor.api';
import 'monaco-editor/esm/vs/basic-languages/csharp/csharp.contribution';
import 'monaco-editor/esm/vs/basic-languages/xml/xml.contribution';
import 'monaco-editor/esm/vs/language/json/monaco.contribution';
import EditorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';
import JsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker';
import { useQuery } from '@tanstack/react-query';
import {
  FileCode2,
  X,
  MessageSquarePlus,
  LockKeyhole,
  ChevronRight,
  RefreshCw,
} from 'lucide-react';
import { api, query } from '../lib/api';
import { useWorkspace } from '../lib/store';
import type { SourceFile } from '../types';
import { Button, ErrorText } from './ui';

// worker 和编辑器均来自本地构建，避免 Windows 离线时依赖 CDN。
(self as typeof self & { MonacoEnvironment: unknown }).MonacoEnvironment = {
  getWorker: (_module: string, label: string) =>
    label === 'json' ? new JsonWorker() : new EditorWorker(),
};
loader.config({ monaco });
const languageFor = (path: string) =>
  path.endsWith('.cs')
    ? 'csharp'
    : /\.(csproj|resx|config|xml)$/.test(path)
      ? 'xml'
      : path.endsWith('.json')
        ? 'json'
        : 'plaintext';

export function CodePane() {
  const { paths, activePath, openFile, closeFile, addSelection, jump } = useWorkspace();
  const editor = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const [hasSelection, setHasSelection] = useState(false);
  const source = useQuery({
    queryKey: ['source', activePath],
    queryFn: () => api<SourceFile>(`/file?path=${query(activePath)}`),
    enabled: !!activePath,
  });
  const onMount: OnMount = (instance) => {
    editor.current = instance;
    instance.onDidChangeCursorSelection((event) => setHasSelection(!event.selection.isEmpty()));
    instance.revealLineInCenter(jump.line);
    instance.setPosition({ lineNumber: jump.line, column: 1 });
  };
  useEffect(() => {
    if (source.data && editor.current) {
      editor.current.revealLineInCenter(jump.line);
      editor.current.setPosition({ lineNumber: jump.line, column: 1 });
    }
  }, [jump, source.data]);
  function attachSelection() {
    const selection = editor.current?.getSelection();
    const model = editor.current?.getModel();
    if (!selection || selection.isEmpty() || !model || !source.data) return;
    addSelection({
      path: activePath,
      start_line: selection.startLineNumber,
      end_line: selection.endLineNumber,
      start_column: selection.startColumn,
      end_column: selection.endColumn,
      content: model.getValueInRange(selection),
      version: source.data.version,
    });
  }
  return (
    <section className="code-pane">
      <div className="code-tabs">
        {paths.map((path) => (
          <div key={path} className={`code-tab ${path === activePath ? 'active' : ''}`}>
            <button title={path} onClick={() => openFile(path)}>
              <FileCode2 size={14} />
              <span>{path.split('/').at(-1)}</span>
            </button>
            <button aria-label={`关闭${path.split('/').at(-1)}`} onClick={() => closeFile(path)}>
              <X size={12} />
            </button>
          </div>
        ))}
        {!paths.length && <span className="empty-tab">源码浏览器</span>}
      </div>
      {activePath && (
        <div className="code-breadcrumb">
          <span>trunk</span>
          {activePath.split('/').map((segment, index) => (
            <span key={index}>
              <ChevronRight size={12} />
              {segment}
            </span>
          ))}
          <button
            title="重新读取文件"
            aria-label="重新读取文件"
            onClick={() => void source.refetch()}
          >
            <RefreshCw size={13} />
          </button>
        </div>
      )}
      <div className="editor-container">
        <ErrorText error={source.error} />
        {source.data ? (
          <Editor
            key={activePath}
            path={activePath}
            language={languageFor(activePath)}
            value={source.data.content}
            theme="vs"
            onMount={onMount}
            loading={<span className="muted padded">正在加载编辑器…</span>}
            options={{
              readOnly: true,
              domReadOnly: true,
              minimap: { enabled: false },
              fontFamily: 'Cascadia Code, Consolas, monospace',
              fontSize: 13,
              lineHeight: 22,
              padding: { top: 18 },
              scrollBeyondLastLine: false,
              automaticLayout: true,
              renderLineHighlight: 'gutter',
              selectionHighlight: true,
              folding: true,
              smoothScrolling: true,
              stickyScroll: { enabled: false },
            }}
          />
        ) : (
          <div className="editor-empty">
            <div className="empty-code-icon">
              <FileCode2 size={30} strokeWidth={1.3} />
            </div>
            <h2>从源码开始</h2>
            <p>在左侧打开文件，选中代码后加入对话。</p>
            <div className="empty-hint">
              <span>浏览文件</span>
              <ChevronRight size={12} />
              <span>选中代码</span>
              <ChevronRight size={12} />
              <span>向 Agent 提问</span>
            </div>
          </div>
        )}
        {hasSelection && source.data && (
          <Button className="selection-action" onClick={attachSelection}>
            <MessageSquarePlus size={14} />
            将选区加入对话
          </Button>
        )}
      </div>
      <div className="code-status">
        <span>
          <LockKeyhole size={11} />
          源码只读
        </span>
        <span>
          {source.data?.encoding || 'UTF-8'}
          {source.data && ` · ${source.data.line_count} 行`}
        </span>
      </div>
    </section>
  );
}
