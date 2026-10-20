import { parseContent } from './parseContent.ts';
import type { ContentBlock, SourcePointer } from './types.ts';

function sourceText(source: SourcePointer) {
  const label = `${source.path}:${source.start_line}–${source.end_line || source.start_line}`
    .replaceAll('[', '\\[')
    .replaceAll(']', '\\]');
  return `[${label}](source:${encodeURI(source.path).replaceAll('(', '%28').replaceAll(')', '%29')}#L${source.start_line}-L${source.end_line || source.start_line})`;
}
function blocksToMarkdown(blocks: ContentBlock[]): string {
  return blocks
    .map((block) => {
      const title = 'title' in block && block.title ? `### ${block.title}\n\n` : '';
      switch (block.type) {
        case 'text':
          return block.content;
        case 'overview_grid':
          return (
            title +
            block.items
              .map(
                (item) =>
                  `- **${item.title}**：${item.description}${item.status ? ` · ${item.status}` : ''}${item.source ? ` ${sourceText(item.source)}` : ''}`,
              )
              .join('\n')
          );
        case 'step_flow':
          return (
            title +
            (block.description ? `${block.description}\n\n` : '') +
            block.steps
              .map(
                (step, i) =>
                  `${i + 1}. **${step.title}**：${step.description}${step.details ? `\n\n   ${step.details}` : ''}${step.sources?.length ? `\n   ${step.sources.map(sourceText).join(' ')}` : ''}`,
              )
              .join('\n\n')
          );
        case 'source_reference':
          return block.sources.map(sourceText).join(' ');
        case 'code': {
          const longest = Math.max(
            2,
            ...Array.from(block.content.matchAll(/`+/g), (match) => match[0].length),
          );
          const fence = '`'.repeat(longest + 1);
          return `${block.filename ? `${block.filename}\n\n` : ''}${fence}${block.language || ''}\n${block.content}\n${fence}${block.source ? `\n\n${sourceText(block.source)}` : ''}`;
        }
        case 'table': {
          const cell = (value: string | number | null) =>
            String(value ?? '—')
              .replaceAll('|', '\\|')
              .replaceAll('\n', '<br>');
          return (
            title +
            `| ${block.columns.map((c) => cell(c.label)).join(' | ')} |\n| ${block.columns.map((c) => (c.align === 'right' ? '---:' : c.align === 'center' ? ':---:' : '---')).join(' | ')} |\n` +
            block.rows.map((row) => `| ${row.cells.map(cell).join(' | ')} |`).join('\n')
          );
        }
        case 'diagram':
          return (
            title +
            (block.description || '') +
            '\n\n' +
            block.nodes
              .map((node) => `- ${node.label}${node.description ? `：${node.description}` : ''}`)
              .join('\n') +
            '\n\n' +
            block.edges
              .map(
                (edge) =>
                  `${block.nodes.find((n) => n.id === edge.from)?.label} → ${block.nodes.find((n) => n.id === edge.to)?.label}${edge.label ? `：${edge.label}` : ''}`,
              )
              .join('\n')
          );
        case 'collapsible':
          return title + blocksToMarkdown(block.blocks);
      }
    })
    .join('\n\n');
}

export function contentToMarkdown(content: string): string {
  return parseContent(content)
    .map((segment) =>
      segment.type === 'rich' ? blocksToMarkdown(segment.document.blocks) : segment.content,
    )
    .join('');
}
