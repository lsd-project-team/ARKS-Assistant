import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import { CodeView, type CodeViewHandle, type CodeViewReactOptions } from '@pierre/diffs/react';
import type { CodeViewItem } from '@pierre/diffs';
import { MessageSquarePlus } from 'lucide-react';
import { SOURCE_THEME } from '../lib/editorTheme';
import {
  indexSource,
  readSourceSelection,
  sourcePointAtOffset,
  sourceSelection,
} from '../lib/sourceSelection';
import { useWorkspace } from '../lib/store';
import type { Selection, SourceFile } from '../types';
import { Button } from './ui';
import { SourceSearch } from './SourceSearch';

const readingCSS = `
  [data-file] { --diffs-bg: #fff; --diffs-bg-hover-override: #f7f7f7; }
  [data-code] { scrollbar-gutter: auto; }
  ::selection { background: #dfebff; }
`;

export function SourceViewer({ source, wordWrap }: { source: SourceFile; wordWrap: boolean }) {
  const viewer = useRef<CodeViewHandle<undefined, undefined>>(null);
  const container = useRef<HTMLDivElement>(null);
  const scrollFrame = useRef<number | undefined>(undefined);
  const pendingJump = useRef<{ line: number; align: 'start' | 'center' } | undefined>(undefined);
  const [selected, setSelected] = useState<Selection | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const jump = useWorkspace((state) => state.jump);
  const fontSize = useWorkspace((state) => state.sourceFontSize);
  const lineHeight = useWorkspace((state) => state.sourceLineHeight);
  const addSelection = useWorkspace((state) => state.addSelection);
  const savePosition = useWorkspace((state) => state.savePosition);
  const index = useMemo(() => indexSource(source.content), [source.content]);
  const saveReadingPosition = useCallback(() => {
    if (scrollFrame.current !== undefined) cancelAnimationFrame(scrollFrame.current);
    // 虚拟列表先处理滚动，再更新行节点；渲染后读取可见行，避免保存旧节点的行号。
    scrollFrame.current = requestAnimationFrame(() => {
      const element = container.current;
      const root = element?.querySelector('diffs-container')?.shadowRoot;
      if (!element || !root) return;
      const top = element.getBoundingClientRect().top;
      const target = pendingJump.current;
      if (target) {
        const row = root.querySelector<HTMLElement>(
          `[data-line="${target.line}"][data-line-index]`,
        );
        if (!row) return;
        // 折行后的高度在高亮渲染后才准确，按实际行节点修正初始估算的跳转位置。
        const bounds = row.getBoundingClientRect();
        const desired =
          target.align === 'start' ? top + 8 : top + (element.clientHeight - bounds.height) / 2;
        element.scrollTo({ top: element.scrollTop + bounds.top - desired, behavior: 'instant' });
        pendingJump.current = undefined;
      }
      const line = Array.from(
        root.querySelectorAll<HTMLElement>('[data-line][data-line-index]'),
      ).find((row) => row.getBoundingClientRect().bottom > top + 8.5);
      if (line) savePosition(source.path, Number(line.dataset.line));
    });
  }, [savePosition, source.path]);
  useEffect(
    () => () => {
      if (scrollFrame.current !== undefined) cancelAnimationFrame(scrollFrame.current);
    },
    [],
  );
  const selectMatch = useCallback(
    (start: number, end: number) => {
      const first = sourcePointAtOffset(index, start);
      const last = sourcePointAtOffset(index, end);
      viewer.current?.scrollTo({
        type: 'line',
        id: source.path,
        lineNumber: first.line,
        align: 'center',
        behavior: 'instant',
      });
      viewer.current?.setSelectedLines({
        id: source.path,
        range: { start: first.line, end: last.line },
      });
      setSelected(sourceSelection(source, index, first, last));
    },
    [index, source],
  );
  const items = useMemo<CodeViewItem<undefined>[]>(
    () => [
      {
        id: source.path,
        type: 'file',
        file: {
          name: source.path,
          contents: source.content,
          cacheKey: `${source.path}:${source.version}`,
          ...(/\.(csproj|resx|config|props|targets)$/i.test(source.path)
            ? { lang: 'xml' as const }
            : {}),
        },
      },
    ],
    [source],
  );
  const options = useMemo<CodeViewReactOptions<undefined, undefined>>(
    () => ({
      theme: SOURCE_THEME,
      themeType: 'light',
      overflow: wordWrap ? 'wrap' : 'scroll',
      disableFileHeader: true,
      enableLineSelection: true,
      lineHoverHighlight: 'both',
      unsafeCSS: readingCSS,
      itemMetrics: { lineHeight: fontSize * lineHeight, spacing: 0 },
      layout: { gap: 0, paddingTop: 8, paddingBottom: 16 },
      onPostRender: (_node, _instance, phase) => {
        if (phase !== 'unmount') saveReadingPosition();
      },
    }),
    [wordWrap, saveReadingPosition, fontSize, lineHeight],
  );

  useEffect(() => {
    setSelected(null);
    pendingJump.current = {
      line: Math.max(1, Math.min(jump.line, source.line_count || 1)),
      align: jump.align,
    };
    viewer.current?.clearSelectedLines();
    if (jump.endLine)
      viewer.current?.setSelectedLines({
        id: source.path,
        range: { start: jump.line, end: jump.endLine },
      });
    viewer.current?.scrollTo({
      type: 'line',
      id: source.path,
      lineNumber: Math.max(1, Math.min(jump.line, source.line_count || 1)),
      align: jump.align,
      behavior: 'instant',
    });
  }, [jump, source]);

  useEffect(() => {
    const readSelection = () => {
      const root = container.current?.querySelector('diffs-container')?.shadowRoot;
      if (!root) return;
      const selection = readSourceSelection(root, source, index);
      if (selection) setSelected(selection);
    };
    document.addEventListener('selectionchange', readSelection);
    return () => document.removeEventListener('selectionchange', readSelection);
  }, [index, source]);

  return (
    <>
      <div
        className="source-reading-surface"
        role="region"
        tabIndex={0}
        aria-label={`${source.path.split('/').at(-1)} 源码，只读`}
        onPointerDown={(event) => {
          setSelected(null);
          const inGutter = event.nativeEvent
            .composedPath()
            .some((node) => node instanceof Element && node.hasAttribute('data-column-number'));
          if (!inGutter) viewer.current?.clearSelectedLines();
        }}
        onKeyDown={(event) => {
          if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'f') {
            event.preventDefault();
            document.getSelection()?.removeAllRanges();
            setSearchOpen(true);
            return;
          }
          if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== 'a') return;
          event.preventDefault();
          document.getSelection()?.removeAllRanges();
          const end = Math.max(1, source.line_count);
          viewer.current?.setSelectedLines({ id: source.path, range: { start: 1, end } });
          setSelected(
            sourceSelection(
              source,
              index,
              { line: 1, column: 1 },
              { line: end, column: (index.lines[end - 1]?.length ?? 0) + 1 },
            ),
          );
        }}
        onCopy={(event) => {
          const root = container.current?.querySelector('diffs-container')?.shadowRoot;
          const selection = (root && readSourceSelection(root, source, index)) || selected;
          if (!selection) return;
          // 从原文复制，避免行号、虚拟占位节点或折行进入剪贴板。
          event.clipboardData.setData('text/plain', selection.content);
          event.preventDefault();
        }}
      >
        <CodeView
          ref={viewer}
          containerRef={container}
          className="source-code-view"
          style={
            {
              '--diffs-font-size': `${fontSize}px`,
              '--diffs-line-height': `${fontSize * lineHeight}px`,
            } as CSSProperties
          }
          items={items}
          options={options}
          onSelectedLinesChange={(selection) => {
            if (!selection) return;
            const start = Math.min(selection.range.start, selection.range.end);
            const end = Math.max(selection.range.start, selection.range.end);
            setSelected(
              sourceSelection(
                source,
                index,
                { line: start, column: 1 },
                { line: end, column: (index.lines[end - 1]?.length ?? 0) + 1 },
              ),
            );
          }}
          onScroll={saveReadingPosition}
        />
        {searchOpen && (
          <SourceSearch
            content={source.content}
            onMatch={selectMatch}
            onClose={() => {
              setSearchOpen(false);
              container.current?.focus();
            }}
          />
        )}
      </div>
      {selected && (
        <Button
          className="selection-action"
          onPointerDown={(event) => event.preventDefault()}
          onClick={() => addSelection(selected)}
        >
          <MessageSquarePlus size={14} />
          将选区加入对话
        </Button>
      )}
    </>
  );
}
