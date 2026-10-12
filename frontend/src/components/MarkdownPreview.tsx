import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check, MessageSquarePlus } from 'lucide-react';
import { useWorkspace } from '../lib/store';
import { readMarkdownSelection, resolveMarkdownLink } from '../lib/markdownSelection';
import type { Selection, SourceFile } from '../types';
import { Button } from './ui';

interface PreviewNode {
  type: string;
  tagName?: string;
  value?: string;
  properties?: Record<string, unknown>;
  children?: PreviewNode[];
  position?: { start: { line: number; offset?: number }; end: { offset?: number } };
}
function previewPositions() {
  return (tree: PreviewNode) => {
    const headings = new Map<string, number>();
    const text = (node: PreviewNode): string =>
      node.value || node.children?.map(text).join('') || '';
    const visit = (node: PreviewNode) => {
      if (node.type === 'element' && node.position) {
        node.properties = {
          ...node.properties,
          'data-source-start': node.position.start.offset,
          'data-source-end': node.position.end.offset,
          'data-source-line': node.position.start.line,
        };
        if (/^h[1-6]$/.test(node.tagName || '')) {
          const slug = text(node)
            .toLowerCase()
            .replace(/[^\p{L}\p{N}\s_-]/gu, '')
            .trim()
            .replace(/\s+/g, '-');
          const count = headings.get(slug) || 0;
          headings.set(slug, count + 1);
          node.properties.id = count ? `${slug}-${count}` : slug;
        }
      }
      node.children?.forEach(visit);
    };
    visit(tree);
  };
}

function PreviewCodeBlock({
  children,
  language,
}: {
  children?: React.ReactNode;
  language?: string;
}) {
  const block = useRef<HTMLPreElement>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!copied) return;
    const timeout = setTimeout(() => setCopied(false), 2000);
    return () => clearTimeout(timeout);
  }, [copied]);
  return (
    <div className="preview-code-block">
      {language && <span className="preview-code-language">{language}</span>}
      <button
        aria-label="复制代码块"
        title={copied ? '已复制' : '复制代码'}
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(block.current?.textContent || '');
            setCopied(true);
            setError('');
          } catch {
            setError('复制失败，请手动选择代码复制');
          }
        }}
      >
        {copied ? <Check size={14} /> : <Copy size={14} />}
      </button>
      <pre ref={block}>{children}</pre>
      {error && (
        <span role="status" className="muted">
          {error}
        </span>
      )}
    </div>
  );
}

export function MarkdownPreview({ source }: { source: SourceFile }) {
  const container = useRef<HTMLDivElement>(null);
  const [selected, setSelected] = useState<Selection | null>(null);
  const { addSelection, openFile } = useWorkspace();
  useEffect(() => {
    const element = container.current;
    if (!element) return;
    const line = useWorkspace.getState().positions[source.path] ?? 1;
    const blocks = Array.from(element.querySelectorAll<HTMLElement>('[data-source-line]'));
    const target = blocks.find((block) => Number(block.dataset.sourceLine) >= line);
    if (line > 1) target?.scrollIntoView({ block: 'start' });
    const read = () => setSelected(readMarkdownSelection(element, source));
    document.addEventListener('selectionchange', read);
    return () => document.removeEventListener('selectionchange', read);
  }, [source]);
  return (
    <>
      <div
        ref={container}
        className="markdown-preview"
        role="region"
        aria-label={`${source.path.split('/').at(-1)} 文档预览，只读`}
        onPointerDown={() => setSelected(null)}
        onScroll={() => {
          const element = container.current;
          if (!element) return;
          const top = element.getBoundingClientRect().top;
          const first = Array.from(
            element.querySelectorAll<HTMLElement>('[data-source-line]'),
          ).find((block) => block.getBoundingClientRect().bottom > top);
          if (first)
            useWorkspace.getState().savePosition(source.path, Number(first.dataset.sourceLine));
        }}
      >
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[previewPositions]}
          components={{
            pre: ({ children, node }) => {
              const code = node?.children.find(
                (child) => child.type === 'element' && child.tagName === 'code',
              );
              const classes = code?.type === 'element' ? code.properties.className : [];
              const language = Array.isArray(classes)
                ? String(
                    classes.find((name) => String(name).startsWith('language-')) || '',
                  ).replace(/^language-/, '')
                : '';
              return (
                <div
                  data-source-start={node?.position?.start.offset}
                  data-source-end={node?.position?.end.offset}
                  data-source-line={node?.position?.start.line}
                >
                  <PreviewCodeBlock language={language}>{children}</PreviewCodeBlock>
                </div>
              );
            },
            a: ({ href, children, node: _node, ...props }) => {
              const local = href ? resolveMarkdownLink(source.path, href) : null;
              if (!local)
                return (
                  <a {...props} href={href} target="_blank" rel="noreferrer">
                    {children}
                  </a>
                );
              return (
                <a
                  {...props}
                  href={href}
                  onClick={(event) => {
                    event.preventDefault();
                    if (local.path === source.path && local.hash) {
                      let id: string;
                      try {
                        id = decodeURIComponent(local.hash);
                      } catch {
                        return;
                      }
                      container.current
                        ?.querySelector<HTMLElement>(`#${CSS.escape(id)}`)
                        ?.scrollIntoView({ block: 'start', behavior: 'smooth' });
                    } else openFile(local.path);
                  }}
                >
                  {children}
                </a>
              );
            },
          }}
        >
          {source.content}
        </ReactMarkdown>
      </div>
      {selected && (
        <Button
          className="selection-action"
          onPointerDown={(event) => event.preventDefault()}
          onClick={() => {
            addSelection(selected);
            setSelected(null);
          }}
        >
          <MessageSquarePlus size={14} />
          将选区加入对话{' '}
          <span className="selection-lines">
            L{selected.start_line}
            {selected.end_line !== selected.start_line ? `–${selected.end_line}` : ''}
          </span>
        </Button>
      )}
    </>
  );
}
