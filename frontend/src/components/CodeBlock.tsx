import { Children, isValidElement, useState, type ReactNode } from 'react';
import { Copy, WrapText, ChevronDown, ChevronUp } from 'lucide-react';
import { toast } from '../lib/toasts';

function codeText(node: ReactNode): string {
  return Children.toArray(node)
    .map((child) => {
      if (typeof child === 'string' || typeof child === 'number') return String(child);
      return isValidElement<{ children?: ReactNode }>(child) ? codeText(child.props.children) : '';
    })
    .join('');
}

export function CodeBlock({ children }: { children: ReactNode }) {
  const [wrap, setWrap] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const element = Children.toArray(children).find((child) => isValidElement(child));
  const language = isValidElement<{ className?: string }>(element)
    ? element.props.className?.replace(/^language-/, '')
    : undefined;
  const content = codeText(children).replace(/\n$/, '');
  const long = content.split('\n').length > 18;
  async function copy() {
    try {
      await navigator.clipboard.writeText(content);
      toast('代码已复制');
    } catch {
      toast('复制失败，请手动选择代码复制', undefined, 'error');
    }
  }
  return (
    <div
      className={`answer-code ${wrap ? 'wrapped' : ''} ${long && !expanded ? 'collapsed-code' : ''}`}
    >
      <div className="answer-code-toolbar">
        <span>{language || '代码'}</span>
        <div>
          <button
            type="button"
            aria-label="代码自动换行"
            aria-pressed={wrap}
            title="自动换行"
            onClick={() => setWrap(!wrap)}
          >
            <WrapText size={13} />
          </button>
          <button type="button" aria-label="复制代码" title="复制代码" onClick={() => void copy()}>
            <Copy size={13} />
          </button>
        </div>
      </div>
      <pre>{children}</pre>
      {long && (
        <button type="button" className="code-expand" onClick={() => setExpanded(!expanded)}>
          {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}{' '}
          {expanded ? '收起代码' : `展开 ${content.split('\n').length} 行代码`}
        </button>
      )}
    </div>
  );
}
