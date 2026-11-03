import { useEffect, useRef, useState } from 'react';
import { useAppearance } from '../../settings/lib/appearance';
import { CodeBlock } from '../../../shared/ui/markdown/CodeBlock';

export default function ManualMermaid({ content }: { content: string }) {
  const container = useRef<HTMLElement>(null);
  const dark = useAppearance((state) => state.mode === 'dark');
  const [visible, setVisible] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [result, setResult] = useState<{
    content: string;
    dark: boolean;
    svg?: string;
    error?: string;
  }>();
  useEffect(() => {
    if (!container.current || !('IntersectionObserver' in window)) {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: '400px' },
    );
    observer.observe(container.current);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (!visible) return;
    let active = true;
    // 文档可使用静态配色，配置覆盖和链接事件仍不执行。
    const draw = async () => {
      if (content.length > 60000 || /%%\s*\{|^\s*click\s/im.test(content))
        throw new Error('图表包含不支持的配置或交互');
      const { renderDiagram } = await import('../../../shared/utils/mermaid');
      return renderDiagram(content, dark, true);
    };
    void draw().then(
      (svg) => {
        if (active) setResult({ content, dark, svg });
      },
      () => {
        if (active) setResult({ content, dark, error: '此图暂时无法绘制，原始图表内容已保留。' });
      },
    );
    return () => {
      active = false;
    };
  }, [visible, content, dark]);
  const current = result?.content === content && result.dark === dark ? result : undefined;
  return (
    <figure className="manual-mermaid" ref={container}>
      {current?.svg ? (
        <>
          <div className="manual-diagram-controls" role="group" aria-label="详细流程图缩放">
            <button onClick={() => setZoom(Math.max(0.5, zoom - 0.25))} aria-label="缩小详细流程图">
              −
            </button>
            <button onClick={() => setZoom(1)} aria-label="重置详细流程图">
              {Math.round(zoom * 100)}%
            </button>
            <button onClick={() => setZoom(Math.min(3, zoom + 0.25))} aria-label="放大详细流程图">
              ＋
            </button>
          </div>
          <div className="manual-diagram-viewport" tabIndex={0}>
            <img
              alt="详细说明流程图"
              src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(current.svg)}`}
              style={
                zoom === 1 ? { maxWidth: '100%' } : { width: `${zoom * 100}%`, maxWidth: 'none' }
              }
            />
          </div>
        </>
      ) : (
        <p role="status">
          {current?.error || (visible ? '正在绘制流程图…' : '流程图将在阅读到此处时绘制')}
        </p>
      )}
      <details open={!!current?.error || undefined}>
        <summary>查看图表原文</summary>
        <CodeBlock rawContent={content}>
          <code className="language-mermaid">{content}</code>
        </CodeBlock>
      </details>
    </figure>
  );
}
