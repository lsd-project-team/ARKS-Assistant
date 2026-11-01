import { fromMarkdown } from 'mdast-util-from-markdown';
import type { SourceEvidence } from '../../../shared/types/api.ts';
import { citationEndLine } from '../../source_reader/lib/citationRange.ts';
import { resolveSourceEvidence } from './sourceEvidence.ts';
import type { AnswerSource } from './answerSources.ts';
import type { SourcePointer } from './types.ts';

export type CodeSourceGroup = {
  key: string;
  path: string;
  name: string;
  version?: string;
  sourceId?: string;
  sources: SourcePointer[];
};
type Node = { type: string; value?: string; children?: Node[] };
function labelText(node: Node): string {
  return node.value ?? node.children?.map(labelText).join('') ?? '';
}
export function codeRange(source: SourcePointer) {
  const end = source.end_line ?? source.start_line;
  return end === source.start_line ? `${source.start_line}` : `${source.start_line}–${end}`;
}
function markdownPointer(
  source: Extract<AnswerSource, { type: 'link' }>,
  evidence: SourceEvidence[],
): SourcePointer | undefined {
  const match = source.url.match(/^source:(.+)#L(\d+)(?:-L?(\d+))?$/);
  if (!match) return;
  let path: string;
  try {
    path = decodeURIComponent(match[1]);
  } catch {
    return;
  }
  const start = Number(match[2]);
  const end = citationEndLine(
    path,
    start,
    match[3],
    labelText(fromMarkdown(source.markdown)),
    evidence,
  );
  if (
    !path ||
    !Number.isSafeInteger(start) ||
    !Number.isSafeInteger(end) ||
    start < 1 ||
    end < start
  )
    return;
  return { path, start_line: start, end_line: end } satisfies SourcePointer;
}

export function groupCodeSources(
  sources: AnswerSource[],
  evidence: SourceEvidence[],
  defaultSourceId?: string,
) {
  const groups = new Map<string, CodeSourceGroup>();
  const others: AnswerSource[] = [];
  const invalid: { label: string; url: string }[] = [];
  for (const item of sources) {
    const isLink = item.type === 'link' && item.url.startsWith('source:');
    const pointer =
      item.type === 'source' ? item.source : isLink ? markdownPointer(item, evidence) : undefined;
    if (!pointer) {
      if (isLink) invalid.push({ label: labelText(fromMarkdown(item.markdown)), url: item.url });
      else others.push(item);
      continue;
    }
    // 只有实际证据唯一匹配时才补齐版本/目录，不能把同名文件或不同版本合成一组。
    const matched = resolveSourceEvidence(pointer, evidence, defaultSourceId).evidence;
    const version = pointer.version ?? matched?.version;
    const sourceId = pointer.source_workspace_id ?? matched?.source_workspace_id ?? defaultSourceId;
    const resolved = { ...pointer, version, source_workspace_id: sourceId };
    const key = JSON.stringify([pointer.path, version, sourceId]);
    let group = groups.get(key);
    if (!group) {
      group = {
        key,
        path: pointer.path,
        name: pointer.path.split(/[\\/]/).at(-1) || pointer.path,
        version,
        sourceId,
        sources: [],
      };
      groups.set(key, group);
    }
    if (
      !group.sources.some(
        (row) =>
          row.start_line === resolved.start_line &&
          (row.end_line ?? row.start_line) === (resolved.end_line ?? resolved.start_line),
      )
    )
      group.sources.push(resolved);
  }
  for (const group of groups.values())
    group.sources.sort(
      (a, b) =>
        a.start_line - b.start_line || (a.end_line ?? a.start_line) - (b.end_line ?? b.start_line),
    );
  return { groups: [...groups.values()], others, invalid };
}
