import { fromMarkdown } from 'mdast-util-from-markdown';
import type { KnowledgeReference } from '../../../shared/types/api';

type MarkdownNode = {
  type: string;
  url?: string;
  identifier?: string;
  children?: MarkdownNode[];
};

interface KnowledgeCitation {
  citation: string;
  kind: KnowledgeReference['kind'];
  id: string;
  version: number;
  projectId?: string;
  start?: number;
  end?: number;
}

function parseCitation(citation: string): KnowledgeCitation | undefined {
  const debug = citation.match(/^debug-issue:([\w-]+)\/(\d+)$/);
  const material = citation.match(/^material:([\w-]+)\/([\w-]+)\/(\d+)#L(\d+)(?:-L?(\d+))?$/);
  const handover = citation.match(/^handover-source:([\w-]+)\/(\d+)#L(\d+)(?:-L?(\d+))?$/);
  let parsed: KnowledgeCitation;
  if (debug) {
    parsed = { citation, kind: 'debug_issue', id: debug[1], version: Number(debug[2]) };
  } else if (material) {
    parsed = {
      citation,
      kind: 'material',
      projectId: material[1],
      id: material[2],
      version: Number(material[3]),
      start: Number(material[4]),
      end: Number(material[5] || material[4]),
    };
  } else if (handover) {
    parsed = {
      citation,
      kind: 'handover_material',
      id: handover[1],
      version: Number(handover[2]),
      start: Number(handover[3]),
      end: Number(handover[4] || handover[3]),
    };
  } else return;
  if (!Number.isSafeInteger(parsed.version) || parsed.version <= 0) return;
  if (
    parsed.start !== undefined &&
    (!Number.isSafeInteger(parsed.start) ||
      parsed.start <= 0 ||
      !Number.isSafeInteger(parsed.end) ||
      parsed.end! < parsed.start)
  )
    return;
  return parsed;
}

// 使用 Markdown 语法树区分真实链接与代码示例、纯文本，避免把提到资料误认为引用。
export function answerKnowledgeCitations(answer: string): KnowledgeCitation[] {
  const tree = fromMarkdown(answer);
  const definitions = new Map<string, string>();
  function visit(node: MarkdownNode, apply: (node: MarkdownNode) => void) {
    apply(node);
    node.children?.forEach((child) => visit(child, apply));
  }
  visit(tree, (node) => {
    if (node.type === 'definition' && node.identifier && node.url)
      definitions.set(node.identifier, definitions.get(node.identifier) ?? node.url);
  });
  const citations: KnowledgeCitation[] = [];
  visit(tree, (node) => {
    const url =
      node.type === 'link'
        ? node.url
        : node.type === 'linkReference'
          ? definitions.get(node.identifier || '')
          : undefined;
    const parsed = url && parseCitation(url);
    if (parsed) citations.push(parsed);
  });
  return citations;
}

export function answerReferences(answer: string, references: KnowledgeReference[]) {
  const available = references.map((row) => ({ row, source: parseCitation(row.citation) }));
  const used = new Map<string, KnowledgeReference>();
  for (const citation of answerKnowledgeCitations(answer)) {
    const match = available.find(
      ({ row, source }) =>
        source &&
        row.kind === citation.kind &&
        row.id === citation.id &&
        row.version === citation.version &&
        source.kind === citation.kind &&
        source.id === citation.id &&
        source.version === citation.version &&
        source.projectId === citation.projectId &&
        (citation.start === undefined ||
          (source.start! <= citation.start && source.end! >= citation.end!)),
    );
    if (!match) continue;
    // 同一资料版本可引用多个片段；列表按首次引用顺序只列一次，保留实际引用位置。
    const key = `${citation.kind}:${citation.projectId || ''}:${citation.id}:${citation.version}`;
    if (!used.has(key)) used.set(key, { ...match.row, citation: citation.citation });
  }
  return [...used.values()];
}
