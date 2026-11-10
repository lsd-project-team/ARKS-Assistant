import { fromMarkdown } from 'mdast-util-from-markdown';
import type { RootContent } from 'mdast';

export interface ManualHeading {
  id: string;
  title: string;
  offset: number;
  section: number;
}
export interface ManualSection {
  id: string;
  title: string;
  start: number;
  content: string;
}
const nodeText = (node: RootContent | { value?: string; children?: unknown[] }): string =>
  ('value' in node ? node.value : '') ||
  ('children' in node ? (node.children as RootContent[]).map(nodeText).join('') : '');

export function headingSlug(text: string) {
  return (
    text
      .toLowerCase()
      .replace(/[^\p{L}\p{N}\s_-]/gu, '')
      .trim()
      .replace(/\s+/g, '-') || 'section'
  );
}

export function splitManual(content: string) {
  const tree = fromMarkdown(content);
  const headings: ManualHeading[] = [];
  const sections: ManualSection[] = [
    { id: 'overview', title: '概览与范围', start: 0, content: '' },
  ];
  const seen = new Map<string, number>();
  const definitions: string[] = [];
  for (const node of tree.children) {
    if (node.type === 'definition')
      definitions.push(content.slice(node.position!.start.offset, node.position!.end.offset));
    if (node.type !== 'heading') continue;
    const title = nodeText(node);
    const slug = headingSlug(title);
    const count = seen.get(slug) || 0;
    seen.set(slug, count + 1);
    const id = count ? `${slug}-${count}` : slug;
    const offset = node.position!.start.offset!;
    // 只按真正的二级标题分页，代码块里的 ## 和表格内容不会被误拆。
    if (node.depth === 2) sections.push({ id, title, start: offset, content: '' });
    headings.push({ id, title, offset, section: sections.length - 1 });
  }
  sections.forEach((section, index) => {
    section.content = content.slice(section.start, sections[index + 1]?.start ?? content.length);
    // 分章后仍保留文末的引用式链接定义，不改变原始 Markdown。
    if (definitions.length) section.content += `\n\n${definitions.join('\n')}`;
  });
  return { sections, headings };
}

export function sectionForAnchor(document: ReturnType<typeof splitManual>, anchor: string) {
  const index = document.sections.findIndex((section) => section.id === anchor);
  if (index >= 0) return index;
  return document.headings.find((heading) => heading.id === anchor)?.section ?? 0;
}
