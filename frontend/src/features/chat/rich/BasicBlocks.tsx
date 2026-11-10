import { CodeBlock } from '../../../shared/ui/markdown/CodeBlock';
import { ToolActivity } from '../components/ToolActivity';
import type {
  CodeContentBlock,
  SourceBlock,
  SourcePointer,
  ToolCallBlock,
  UnsupportedBlock,
} from './types';
import type { ReactNode } from 'react';

type SourceRenderer = (source: SourcePointer, key: string) => ReactNode;
export function SourceReferenceBlock({
  block,
  renderSource,
}: {
  block: SourceBlock;
  renderSource: SourceRenderer;
}) {
  return (
    <div className="rich-sources">
      {block.sources.map((source, i) => renderSource(source, `${block.id}:${i}`))}
    </div>
  );
}
export function CodeContent({
  block,
  renderSource,
}: {
  block: CodeContentBlock;
  renderSource: SourceRenderer;
}) {
  return (
    <div>
      <CodeBlock filename={block.filename} startLine={block.start_line} rawContent={block.content}>
        <code className={block.language ? `language-${block.language}` : undefined}>
          {block.content}
        </code>
      </CodeBlock>
      {block.source && renderSource(block.source, block.id)}
    </div>
  );
}
export function ToolCall({ block }: { block: ToolCallBlock }) {
  return <ToolActivity tools={[block.tool]} showSummary={false} />;
}
export function UnsupportedContent({ block }: { block: UnsupportedBlock }) {
  return (
    <section className="rich-fallback">
      <p role="status">{block.error}，以下显示原始内容。</p>
      <CodeBlock>
        <code>{JSON.stringify(block.raw, null, 2)}</code>
      </CodeBlock>
    </section>
  );
}
