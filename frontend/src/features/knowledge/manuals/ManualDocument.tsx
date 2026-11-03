import {
  Children,
  isValidElement,
  lazy,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Root } from 'mdast';
import { CodeBlock } from '../../../shared/ui/markdown/CodeBlock';
import { manualDocumentResource, manualForDocument, type ManualEntry } from '../data/manualCatalog';
import { routeHash, type Route } from '../routes';
import { sectionForAnchor, splitManual } from './manualContent';

const ManualMermaid = lazy(() => import('./ManualMermaid'));

function DocumentPre({ children }: { children?: React.ReactNode }) {
  const code = Children.toArray(children).find(isValidElement);
  if (
    isValidElement<{ className?: string; children?: React.ReactNode }>(code) &&
    code.props.className === 'language-mermaid'
  ) {
    const content = Children.toArray(code.props.children).join('');
    return (
      <Suspense fallback={<p role="status">正在加载流程图…</p>}>
        <ManualMermaid content={content} />
      </Suspense>
    );
  }
  return <CodeBlock>{children}</CodeBlock>;
}

export default function ManualDocument({
  entry,
  anchor,
  navigate,
}: {
  entry: ManualEntry;
  anchor: string;
  navigate: (route: Route) => void;
}) {
  const file = entry.documents[0];
  const [loaded, setLoaded] = useState<{ file: string; content?: string; error?: string }>();
  const [retry, setRetry] = useState(0);
  const [query, setQuery] = useState('');
  const article = useRef<HTMLElement>(null);
  const content = loaded?.file === file ? loaded.content : undefined;
  const document = useMemo(
    () => (content === undefined ? undefined : splitManual(content)),
    [content],
  );
  const sectionIndex = document ? sectionForAnchor(document, anchor) : 0;
  const section = document?.sections[sectionIndex];
  useEffect(() => {
    const controller = new AbortController();
    void fetch(
      `${manualDocumentResource(file)}?review=${entry.documentHashes[file]?.slice(0, 16) ?? ''}`,
      { signal: controller.signal },
    )
      .then(async (response) => {
        if (!response.ok) throw new Error(String(response.status));
        return response.text();
      })
      .then((text) => {
        if (!controller.signal.aborted) setLoaded({ file, content: text });
      })
      .catch(() => {
        if (!controller.signal.aborted) setLoaded({ file, error: '详细说明加载失败，请重试。' });
      });
    return () => controller.abort();
  }, [file, entry, retry]);
  useEffect(() => {
    if (!section || !article.current) return;
    const target = [...article.current.querySelectorAll<HTMLElement>('[data-manual-heading]')].find(
      (element) => element.dataset.manualHeading === anchor,
    );
    (target ?? article.current).scrollIntoView({ block: 'start' });
  }, [section, anchor]);
  const headingIds = useMemo(
    () => () => (tree: Root) => {
      for (const node of tree.children) {
        if (node.type !== 'heading') continue;
        const offset = (node.position?.start.offset ?? 0) + (section?.start ?? 0);
        const heading = document?.headings.find((item) => item.offset === offset);
        if (heading)
          node.data = {
            ...node.data,
            hProperties: { id: `manual-heading-${heading.id}`, 'data-manual-heading': heading.id },
          };
      }
    },
    [document, section],
  );
  const components: Components = {
    pre: DocumentPre,
    table: ({ children }) => (
      <div className="manual-table-scroll" tabIndex={0}>
        <table>{children}</table>
      </div>
    ),
    a: ({ href, children }) => {
      if (!href) return <span>{children}</span>;
      if (/^https?:\/\//i.test(href))
        return (
          <a href={href} target="_blank" rel="noreferrer">
            {children}
          </a>
        );
      try {
        const [path, fragment] = href.split('#');
        const destination = path
          ? manualForDocument(decodeURIComponent(path).split(/[\\/]/).pop()!)
          : entry;
        if (!destination) return <span>{children}</span>;
        const next: Route = {
          kind: 'catalog',
          id: destination.id,
          section: fragment ? decodeURIComponent(fragment) : 'overview',
        };
        return (
          <a
            href={`#${routeHash(next)}`}
            onClick={(event) => {
              event.preventDefault();
              navigate(next);
            }}
          >
            {children}
          </a>
        );
      } catch {
        return <span>{children}</span>;
      }
    },
  };
  const chooseSection = (id: string) => navigate({ kind: 'catalog', id: entry.id, section: id });
  return (
    <section className="manual-document" aria-label="详细说明阅读器">
      {entry.documents.length > 1 && (
        <div className="manual-related-docs" role="group" aria-label="选择详细说明">
          {entry.documents.map((name) => (
            <button
              key={name}
              onClick={() => {
                const target = manualForDocument(name);
                if (target) navigate({ kind: 'catalog', id: target.id, section: 'overview' });
              }}
            >
              {name.replace(/^\d+-|\.md$/g, '')}
            </button>
          ))}
        </div>
      )}
      {loaded?.file === file && loaded.error ? (
        <div className="empty-state compact">
          <p role="alert">{loaded.error}</p>
          <button className="button" onClick={() => setRetry(retry + 1)}>
            重试
          </button>
        </div>
      ) : !document || !section ? (
        <p role="status">正在加载详细说明…</p>
      ) : (
        <div className="manual-document-layout">
          <nav className="manual-chapters" aria-label="详细说明章节">
            <label>
              搜索详细说明
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="搜索条件、按钮、异常…"
              />
            </label>
            {document.sections
              .filter(
                (item) =>
                  !query.trim() || item.content.toLowerCase().includes(query.trim().toLowerCase()),
              )
              .map((item) => (
                <button
                  key={item.id}
                  aria-current={section.id === item.id ? 'page' : undefined}
                  onClick={() => chooseSection(item.id)}
                >
                  {item.title}
                </button>
              ))}
            {query &&
              !document.sections.some((item) =>
                item.content.toLowerCase().includes(query.trim().toLowerCase()),
              ) && <p>没有匹配章节</p>}
          </nav>
          <div className="manual-chapter-main">
            <article className="manual-markdown" ref={article}>
              <ReactMarkdown remarkPlugins={[remarkGfm, headingIds]} components={components}>
                {section.content}
              </ReactMarkdown>
            </article>
            <div className="manual-pagination">
              <button
                className="button"
                disabled={sectionIndex === 0}
                onClick={() => chooseSection(document.sections[sectionIndex - 1].id)}
              >
                ← 上一章
              </button>
              <span>
                {sectionIndex + 1} / {document.sections.length}
              </span>
              <button
                className="button"
                disabled={sectionIndex === document.sections.length - 1}
                onClick={() => chooseSection(document.sections[sectionIndex + 1].id)}
              >
                下一章 →
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
