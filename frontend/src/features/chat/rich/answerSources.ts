import { fromMarkdown } from 'mdast-util-from-markdown';
import { parseContent, type ContentSegment } from './parseContent.ts';
import type { ContentBlock, SourcePointer } from './types.ts';

type Node = {
  type: string;
  value?: string;
  alt?: string;
  url?: string;
  identifier?: string;
  children?: Node[];
  position?: { start: { offset?: number }; end: { offset?: number } };
};
export type AnswerSource =
  | { type: 'link'; url: string; markdown: string }
  | { type: 'text'; markdown: string; urls?: string[] }
  | { type: 'source'; source: SourcePointer };

const citationUrl = (url: string) => /^(?:debug-issue|handover-source|source):/.test(url);
const sourceLabel = /^(?:来源|参考资料|参考来源|参考文献|依据|sources?|references?)\s*[:：]\s*/i;
const sourceHeading = /^(?:来源|参考资料|参考来源|参考文献|sources?|references?)\s*[:：]?\s*$/i;
function bounds(node: Node): [number, number] | undefined {
  const start = node.position?.start.offset;
  const end = node.position?.end.offset;
  return start !== undefined && end !== undefined ? [start, end] : undefined;
}
function text(node: Node): string {
  return node.value ?? node.alt ?? node.children?.map(text).join('') ?? '';
}

function isCodeLocator(node: Node, url: string) {
  const target = url.match(/^source:(.+)#L(\d+)(?:-L?\d+)?$/);
  const label = text(node)
    .trim()
    .match(/^(.+?):L?(\d+)(?:\s*[-–—]\s*L?\d+)?$/);
  if (!target || !label || target[2] !== label[2]) return false;
  try {
    const path = decodeURIComponent(target[1]);
    return label[1] === path || label[1] === path.split(/[\\/]/).at(-1);
  } catch {
    return false;
  }
}

// 只改展示投影。按语法树处理链接，代码、图片、坏协议及持久化消息原文均不改写。
function separateMarkdown(content: string, add: (source: AnswerSource) => void) {
  const root = fromMarkdown(content) as Node;
  const definitions = new Map<string, string>();
  function visit(node: Node, apply: (node: Node) => void) {
    if (node.type === 'code' || node.type === 'inlineCode' || node.type === 'html') return;
    apply(node);
    node.children?.forEach((child) => visit(child, apply));
  }
  visit(root, (node) => {
    if (node.type === 'definition' && node.identifier && node.url)
      definitions.set(node.identifier, definitions.get(node.identifier) ?? node.url);
  });
  const edits: { start: number; end: number; replacement: string }[] = [];
  const headings: typeof edits = [];
  const urlOf = (node: Node) =>
    node.type === 'link'
      ? node.url
      : node.type === 'linkReference'
        ? definitions.get(node.identifier || '')
        : undefined;
  const labelOf = (node: Node) => {
    const children = node.children || [];
    const first = children[0] && bounds(children[0]);
    const last = children.at(-1) && bounds(children.at(-1)!);
    return first && last ? content.slice(first[0], last[1]) : text(node);
  };
  const footerLabel = (node: Node) => {
    let image = false;
    visit(node, (child) => {
      image ||= child.type === 'image' || child.type === 'imageReference';
    });
    return image ? (text(node) || '资料').replace(/[\[\]\\]/g, '\\$&') : labelOf(node);
  };
  const protectedLiteral = (node: Node): boolean => {
    if (node.type === 'link' || node.type === 'linkReference') return false;
    return (
      ['code', 'inlineCode', 'html'].includes(node.type) || !!node.children?.some(protectedLiteral)
    );
  };
  function scan(node: Node) {
    if (['code', 'inlineCode', 'html', 'definition'].includes(node.type)) return;
    const range = bounds(node);
    const plain = text(node);
    const literal = protectedLiteral(node);
    if (
      range &&
      !literal &&
      ['paragraph', 'heading'].includes(node.type) &&
      sourceHeading.test(plain.trim())
    ) {
      headings.push({ start: range[0], end: range[1], replacement: '' });
      return;
    }
    const labeled =
      !literal && ['paragraph', 'heading'].includes(node.type) && sourceLabel.test(plain.trim());
    const links: { node: Node; url: string }[] = [];
    let hasImage = false;
    visit(node, (child) => {
      if (child.type === 'image' || child.type === 'imageReference') hasImage = true;
      const url = urlOf(child);
      if (url && (citationUrl(url) || (labeled && /^https?:\/\//i.test(url))))
        links.push({ node: child, url });
    });
    const remainder = links
      .reduce((value, link) => value.replace(text(link.node), ''), plain)
      .replace(sourceLabel, '')
      .replace(/[\s、，,；;。()（）\[\]【】]+/g, '');
    if (
      range &&
      !hasImage &&
      ['paragraph', 'heading'].includes(node.type) &&
      ((links.length > 0 && !remainder) ||
        (labeled && (!/^依据/.test(plain.trim()) || links.length > 0)))
    ) {
      // 保留来源段落里的非链接说明；不在正文留下一个空的“来源：”。
      if (labeled && remainder) {
        let raw = content.slice(...range);
        const codeLinks = links.filter((link) => link.url.startsWith('source:'));
        for (const link of [...codeLinks].reverse()) {
          const location = bounds(link.node);
          if (location)
            raw = raw.slice(0, location[0] - range[0]) + raw.slice(location[1] - range[0]);
        }
        for (const { node: link, url } of codeLinks)
          add({
            type: 'link',
            url,
            markdown: `[${footerLabel(link)}](<${url.replaceAll('>', '%3E').replaceAll('<', '%3C')}>)`,
          });
        raw = raw.replace(/^#{1,6}\s*/, '').replace(sourceLabel, '');
        if (raw.trim())
          add({
            type: 'text',
            markdown: raw,
            urls: links.filter((link) => !link.url.startsWith('source:')).map((link) => link.url),
          });
      } else {
        links.forEach(({ node: link, url }) =>
          add({
            type: 'link',
            url,
            markdown: `[${footerLabel(link)}](<${url.replaceAll('>', '%3E').replaceAll('<', '%3C')}>)`,
          }),
        );
      }
      edits.push({ start: range[0], end: range[1], replacement: '' });
      return;
    }
    const url = urlOf(node);
    if (range && url && citationUrl(url)) {
      const label = labelOf(node);
      add({
        type: 'link',
        url,
        markdown: `[${footerLabel(node)}](<${url.replaceAll('>', '%3E').replaceAll('<', '%3C')}>)`,
      });
      if (isCodeLocator(node, url)) {
        // 纯文件/行号标签只在页尾展示；业务含义的链接文字仍留在原句中。
        let [start, end] = range;
        const before = content.slice(0, start).match(/([（(])[ \t]*$/);
        const after = content.slice(end).match(/^[ \t]*([）)])/);
        if (before && after && (before[1] === '（' ? after[1] === '）' : after[1] === ')')) {
          start -= before[0].length;
          end += after[0].length;
        }
        edits.push({ start, end, replacement: '' });
      } else edits.push({ start: range[0], end: range[1], replacement: label });
      return;
    }
    node.children?.forEach(scan);
  }
  scan(root);
  if (edits.length) edits.push(...headings);
  for (const edit of edits.sort((a, b) => b.start - a.start))
    content = content.slice(0, edit.start) + edit.replacement + content.slice(edit.end);
  return content;
}

export function separateAnswerSources(segments: ContentSegment[]) {
  const sources: AnswerSource[] = [];
  const seen = new Set<string>();
  function add(source: AnswerSource) {
    const key =
      source.type === 'link'
        ? `link:${source.url}`
        : source.type === 'source'
          ? JSON.stringify([
              'source',
              source.source.path,
              source.source.start_line,
              source.source.end_line ?? source.source.start_line,
              source.source.version,
              source.source.source_workspace_id,
            ])
          : JSON.stringify(source);
    if (!seen.has(key)) {
      seen.add(key);
      sources.push(source);
    }
  }
  const markdown = (content: string) => separateMarkdown(content, add);
  function blocks(values: ContentBlock[]): ContentBlock[] {
    return values.flatMap((block): ContentBlock[] => {
      switch (block.type) {
        case 'text':
        case 'markdown': {
          const content = markdown(block.content);
          return content.trim() ? [{ ...block, content }] : [];
        }
        case 'source_reference':
          block.sources.forEach((source) => add({ type: 'source', source }));
          return [];
        case 'code': {
          if (!block.source) return [block];
          add({ type: 'source', source: block.source });
          return [{ ...block, source: undefined }];
        }
        case 'overview_grid':
          return [
            {
              ...block,
              items: block.items.map((item) => {
                if (item.source) add({ type: 'source', source: item.source });
                return { ...item, description: markdown(item.description), source: undefined };
              }),
            },
          ];
        case 'step_flow':
          return [
            {
              ...block,
              steps: block.steps.map((step) => {
                const description = markdown(step.description);
                const details = step.details && markdown(step.details);
                step.sources?.forEach((source) => add({ type: 'source', source }));
                return { ...step, description, details, sources: [] };
              }),
            },
          ];
        case 'collapsible': {
          const children = blocks(block.blocks);
          return children.length ? [{ ...block, blocks: children }] : [];
        }
        default:
          return [block];
      }
    });
  }
  const body = segments.map((segment): ContentSegment => {
    if (segment.type === 'markdown') return { ...segment, content: markdown(segment.content) };
    if (segment.type === 'rich')
      return {
        ...segment,
        document: { ...segment.document, blocks: blocks(segment.document.blocks) },
      };
    return segment;
  });
  if (sources.length) {
    const emptyTitle = (value: string) =>
      /^(?:#{1,6}\s*)?(?:\*\*|__)?(?:来源|参考资料|参考来源|参考文献|sources?|references?)\s*[:：]?(?:\*\*|__)?\s*[:：]?\s*$/i.test(
        value.trim(),
      );
    const cleanBlocks = (values: ContentBlock[]): ContentBlock[] =>
      values.flatMap((block): ContentBlock[] => {
        if ((block.type === 'text' || block.type === 'markdown') && emptyTitle(block.content))
          return [];
        if (block.type === 'collapsible') {
          const children = cleanBlocks(block.blocks);
          return children.length ? [{ ...block, blocks: children }] : [];
        }
        return [block];
      });
    // 单独的“来源”标题可能与链接隔着富内容块，收集完成后清掉空标题。
    for (let index = 0; index < body.length; index++) {
      const segment = body[index];
      if (segment.type === 'markdown' && emptyTitle(segment.content))
        body[index] = { ...segment, content: '' };
      if (segment.type === 'rich')
        body[index] = {
          ...segment,
          document: { ...segment.document, blocks: cleanBlocks(segment.document.blocks) },
        };
    }
  }
  return { body, sources };
}

export function answerSourceLinks(content: string) {
  return separateAnswerSources(parseContent(content)).sources.flatMap((source) =>
    source.type === 'link' ? [source.url] : source.type === 'text' ? (source.urls ?? []) : [],
  );
}
