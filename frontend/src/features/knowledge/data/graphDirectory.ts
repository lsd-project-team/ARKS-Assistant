import { archifyData } from './archifyData.ts';
import { diagramReadings, isSupportingEntry } from './diagramReading.ts';
import { displayDiagramTitle, presentationTopics, topicForDiagram } from './presentation.ts';
import { manualById } from './manualCatalog.ts';
import { graphMemberIds, graphOwner } from './graphCollections.ts';

export const publicGraphs = archifyData.flowchartCatalog.entries.filter(
  (entry) => !isSupportingEntry(entry),
);
const entriesById = new Map(publicGraphs.map((entry) => [entry.id, entry]));
export const graphEntry = (id: string) => entriesById.get(id);
export const graphDirectory = publicGraphs.filter((entry) => graphOwner(entry.id) === entry.id);
export const graphMembers = (id: string) =>
  graphMemberIds(id).flatMap((id) => {
    const entry = graphEntry(id);
    return entry ? [entry] : [];
  });

const searchText = new Map(
  publicGraphs.map((entry) => [
    entry.id,
    [
      displayDiagramTitle(entry.id, entry.title),
      entry.title,
      entry.id,
      diagramReadings[entry.id]?.summary,
      topicForDiagram(entry.id)?.title,
      manualById(entry.id)?.searchText,
    ]
      .join(' ')
      .toLowerCase(),
  ]),
);

export function searchGraphDirectory(query = '', type = 'all', level = 'all') {
  const term = query.trim().toLowerCase();
  return graphDirectory.flatMap((entry) => {
    if (level !== 'all' && (level === 'main') !== Boolean(entry.chapter)) return [];
    // 名称和类型须在同一张图上命中；目录只返回所属主入口，并记住实际命中的子图。
    const candidates = graphMembers(entry.id).filter(
      (member) =>
        (type === 'all' || member.type === type) && searchText.get(member.id)!.includes(term),
    );
    const match =
      candidates.find(
        (member) =>
          term === member.id.toLowerCase() ||
          term === displayDiagramTitle(member.id, member.title).toLowerCase(),
      ) ?? candidates[0];
    return match ? [{ entry, match }] : [];
  });
}

export function relatedGraphs(id: string) {
  const owner = graphOwner(id);
  const members = new Set(graphMemberIds(owner));
  const related = new Set(
    presentationTopics
      .filter((topic) => topic.diagrams.some((diagram) => members.has(diagram)))
      .flatMap((topic) => topic.diagrams.map(graphOwner)),
  );
  return graphDirectory.filter((entry) => entry.id !== owner && related.has(entry.id));
}
