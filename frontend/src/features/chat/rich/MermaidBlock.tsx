import { useEffect, useState } from 'react';
import { CodeBlock } from '../../../shared/ui/markdown/CodeBlock';
import { useAppearance } from '../../settings/lib/appearance';
import type { MermaidBlock as MermaidData } from './types';
import { renderMermaid } from './mermaidRender';
import { MermaidViewport } from './MermaidViewport';

export function MermaidBlock({
  block,
  streaming = false,
}: {
  block: MermaidData;
  streaming?: boolean;
}) {
  const dark = useAppearance((state) => state.mode === 'dark');
  const [result, setResult] = useState<{
    content: string;
    dark: boolean;
    svg?: string;
    error?: string;
  }>();
  useEffect(() => {
    if (streaming) return;
    let active = true;
    void renderMermaid(block.content, dark).then(
      (svg) => {
        if (active) setResult({ content: block.content, dark, svg });
      },
      () => {
        if (active)
          setResult({
            content: block.content,
            dark,
            error: '流程图语法无效或渲染失败，已保留原始内容。',
          });
      },
    );
    return () => {
      active = false;
    };
  }, [block.content, dark, streaming]);
  const current = result?.content === block.content && result.dark === dark ? result : undefined;
  return (
    <figure className="rich-mermaid">
      {block.title && <figcaption>{block.title}</figcaption>}
      {current?.svg && !streaming ? (
        <MermaidViewport
          key={block.content}
          svg={current.svg}
          title={block.title || 'Mermaid 流程图'}
        />
      ) : (
        <p role="status">
          {streaming ? '流程图正在接收，完成后绘制…' : current?.error || '正在绘制流程图…'}
        </p>
      )}
      <details open={!!current?.error || undefined}>
        <summary>查看流程图源码</summary>
        <CodeBlock streaming={streaming} rawContent={block.content}>
          <code className="language-mermaid">{block.content}</code>
        </CodeBlock>
      </details>
    </figure>
  );
}
