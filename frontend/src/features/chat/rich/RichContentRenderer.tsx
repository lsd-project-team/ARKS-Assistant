import { memo, useMemo, type ComponentProps } from 'react';
import { Markdown } from '../../../app/components/Markdown';
import { CodeBlock } from '../../../shared/ui/markdown/CodeBlock';
import { CollapsibleSection, DataTable, OverviewGrid, StepFlow } from './ContentBlocks';
import { FlowDiagram } from './FlowDiagram';
import { createContentParser } from './parseContent';
import type { ContentBlock, SourcePointer } from './types';
import { remarkRecordAnswer } from '../lib/recordAnswerPresentation';
import { SourceReference } from './SourceReference';
import { BlockBoundary } from './BlockBoundary';

const answerPlugins = [remarkRecordAnswer];
type Context = Pick<ComponentProps<typeof Markdown>, 'runId' | 'sourceId'>;
const TextBlock = memo(function TextBlock({
  content,
  runId,
  sourceId,
  streaming,
}: Context & { content: string; streaming?: boolean }) {
  return (
    <Markdown
      content={content}
      runId={runId}
      sourceId={sourceId}
      remarkPlugins={answerPlugins}
      streaming={streaming}
    />
  );
});

const Block = memo(function Block({ block, runId, sourceId }: Context & { block: ContentBlock }) {
  const renderText = (content: string) => (
    <TextBlock content={content} runId={runId} sourceId={sourceId} />
  );
  const renderSource = (source: SourcePointer, key: string) => (
    <SourceReference key={key} source={source} runId={runId} sourceId={sourceId} />
  );
  switch (block.type) {
    case 'text':
      return renderText(block.content);
    case 'overview_grid':
      return <OverviewGrid block={block} renderText={renderText} renderSource={renderSource} />;
    case 'step_flow':
      return <StepFlow block={block} renderText={renderText} renderSource={renderSource} />;
    case 'source_reference':
      return (
        <div className="rich-sources">
          {block.sources.map((source, index) => renderSource(source, `${block.id}:${index}`))}
        </div>
      );
    case 'code':
      return (
        <div>
          <CodeBlock filename={block.filename} startLine={block.start_line}>
            <code className={block.language ? `language-${block.language}` : undefined}>
              {block.content}
            </code>
          </CodeBlock>
          {block.source && renderSource(block.source, block.id)}
        </div>
      );
    case 'table':
      return <DataTable block={block} />;
    case 'diagram':
      return <FlowDiagram block={block} />;
    case 'collapsible':
      return (
        <CollapsibleSection title={block.title} defaultOpen={block.default_open}>
          <Blocks blocks={block.blocks} runId={runId} sourceId={sourceId} />
        </CollapsibleSection>
      );
  }
});

function Blocks({ blocks, runId, sourceId }: Context & { blocks: ContentBlock[] }) {
  return (
    <div className="rich-content">
      {blocks.map((block) => (
        <BlockBoundary key={block.id} block={block}>
          <Block block={block} runId={runId} sourceId={sourceId} />
        </BlockBoundary>
      ))}
    </div>
  );
}

export function RichContentRenderer({
  content,
  runId,
  sourceId,
  streaming = false,
}: Context & { content: string; streaming?: boolean }) {
  const parse = useMemo(createContentParser, []);
  const segments = useMemo(() => parse(content, streaming), [content, streaming, parse]);
  return (
    <div className="rich-content">
      {segments.map((segment, index) => {
        switch (segment.type) {
          case 'markdown':
            return segment.content.trim() ? (
              <TextBlock
                key={segment.id}
                content={segment.content}
                streaming={streaming && index === segments.length - 1}
                runId={runId}
                sourceId={sourceId}
              />
            ) : null;
          case 'rich':
            return (
              <Blocks
                key={segment.id}
                blocks={segment.document.blocks}
                runId={runId}
                sourceId={sourceId}
              />
            );
          case 'pending':
            return (
              <div key={segment.id} className="rich-pending" role="status">
                正在组织内容…
              </div>
            );
          case 'fallback':
            return (
              <section key={segment.id} className="rich-fallback">
                <p role="status">{segment.error}，以下显示原始内容。</p>
                <CodeBlock>
                  <code>{segment.content}</code>
                </CodeBlock>
              </section>
            );
        }
      })}
    </div>
  );
}
