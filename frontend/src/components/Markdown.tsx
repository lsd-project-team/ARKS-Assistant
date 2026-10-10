import ReactMarkdown, { defaultUrlTransform } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useWorkspace } from '../lib/store';

export function Markdown({ content }: { content: string }) {
  const openFile = useWorkspace((state) => state.openFile);
  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        urlTransform={(url) => (url.startsWith('source:') ? url : defaultUrlTransform(url))}
        components={{
          a: ({ href, children }) => {
            const source = href?.match(/^source:(.+)#L(\d+)(?:-L?\d+)?$/);
            if (source)
              return (
                <button
                  className="source-link"
                  onClick={() => openFile(decodeURIComponent(source[1]), Number(source[2]))}
                >
                  {children}
                </button>
              );
            return (
              <a href={href} target="_blank" rel="noreferrer">
                {children}
              </a>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
