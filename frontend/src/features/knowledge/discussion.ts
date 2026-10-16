import { api, query } from '../../app/api/client';
import { draftFor, useWorkspace } from '../../app/state/store';
import { toast } from '../../shared/utils/toasts';
import type { Selection, SourceFile as WorkspaceSource } from '../../shared/types/api';
import { archifyData } from './data/archifyData';
import { diagramReadings } from './data/diagramReading';
import { displayDiagramTitle } from './data/presentation';
import { fetchJSON } from './engineeringData';
import type { EngineeringManifest, SourceSymbol } from './engineeringTypes';
import { workspacePath, type ChatRoute } from './routes';
import { knowledgeSelection } from './sourceContext';

interface SourceRange {
  fileId: string;
  start: number;
  end: number;
}
export async function discussKnowledge(route: ChatRoute): Promise<boolean> {
  const { threadId: targetThread, projectId } = useWorkspace.getState();
  const manifest = await fetchJSON<EngineeringManifest>('/engineering/manifest.json');
  const ranges: SourceRange[] = [];
  const paragraphs: string[] = [];
  if (route.flow) {
    const graph = archifyData.graphs.find((item) => item.slug === route.flow);
    if (!graph) throw new Error('这个流程没有对应的资料');
    const reading = diagramReadings[graph.slug];
    paragraphs.push(
      `请结合源码讨论流程「${displayDiagramTitle(graph.slug, graph.title)}」。`,
      `资料索引版本：${manifest.version}`,
      `用途：${reading.summary}`,
      `执行条件：${reading.condition}`,
      `异常与边界：${reading.exception}`,
      `流程节点：\n${graph.nodes.map((node) => `${node.label}：${node.detail}`).join('\n')}`,
    );
    for (const node of graph.nodes)
      ranges.push(...(manifest.nodeBindings[`${graph.slug}/${node.id}`] ?? []));
  }
  if (route.method) {
    const shard = await fetchJSON<Record<string, SourceSymbol>>(
      `${manifest.base}/symbols/${route.method.slice(0, 2)}.json`,
    );
    const method = shard[route.method];
    if (!method) throw new Error('方法资料不存在');
    paragraphs.push(
      `请结合源码解释方法「${method.label}」的用途、执行条件、调用关系与异常边界。`,
      `资料索引版本：${manifest.version}。调用关系来自静态分析，运行时分派仍需确认。`,
      `调用方：${
        method.incoming
          .slice(0, 12)
          .map((call) => call.target?.label ?? '未解析')
          .join('；') || '未记录'
      }`,
      `调用目标：${
        method.outgoing
          .slice(0, 12)
          .map((call) => call.target?.label ?? '未解析')
          .join('；') || '未记录'
      }`,
    );
    ranges.push(...method.declarations);
  }
  if (route.sourceFile && !route.method) {
    ranges.push({
      fileId: route.sourceFile,
      start: route.start ?? 1,
      end: route.end ?? route.start ?? 1,
    });
    paragraphs.push(
      `请结合这段源码解释它的职责、上下文和需要注意的条件。资料索引版本：${manifest.version}。`,
    );
  }
  if (route.message) paragraphs.push(route.message);
  const selections: Selection[] = [];
  const unique = ranges
    .filter(
      (range, index) =>
        ranges.findIndex((item) => item.fileId === range.fileId && item.start === range.start) ===
        index,
    )
    .slice(0, 3);
  await Promise.all(
    unique.map(async (range) => {
      const file = manifest.files.find((item) => item.id === range.fileId);
      if (!file) return;
      const path = workspacePath(file.path);
      try {
        const source = await api<WorkspaceSource>(
          `/file?path=${query(path)}`,
          undefined,
          projectId,
        );
        if (source.version !== file.sha256) {
          paragraphs.push(
            `资料对应 ${path}:L${range.start}–${range.end}，但当前文件已变化。旧行号和调用依据需要重新确认。`,
          );
          return;
        }
        const selected = knowledgeSelection(source, range.start, range.end);
        if (!selected) return;
        selections.push(selected);
        paragraphs.push(
          `源码依据：${path}:L${selected.start_line}–${selected.end_line}${selected.end_line < range.end ? `（完整范围至 L${range.end}）` : ''}`,
        );
      } catch {
        paragraphs.push(
          `资料中的 ${path}:L${range.start}–${range.end} 当前无法读取，请先确认文件位置。`,
        );
      }
    }),
  );
  const state = useWorkspace.getState();
  // 异步读取期间可能切换会话，不能把资料写进另一个会话的草稿。
  if (state.threadId !== targetThread || state.projectId !== projectId) {
    toast('当前会话已切换，请重新点击讨论入口', undefined, 'error');
    return false;
  }
  const draft = draftFor(state);
  const content = [draft.content, paragraphs.join('\n\n')].filter(Boolean).join('\n\n');
  if (content.length > 30000) throw new Error('当前草稿过长，请精简后再加入流程资料');
  state.setDraft(content);
  const available = Math.max(0, 8 - draft.selections.length);
  selections.slice(0, available).forEach(state.addSelection);
  state.setMobile('chat');
  toast(
    `资料已加入当前对话草稿${selections.length > available ? '；选区已满，其他依据保留为文字路径' : ''}`,
  );
  return true;
}

export async function openKnowledgeSource(
  path: string,
  start = 1,
  end = start,
  expectedVersion?: string,
): Promise<boolean> {
  const projectId = useWorkspace.getState().projectId;
  const normalized = workspacePath(path);
  const source = await api<WorkspaceSource>(
    `/file?path=${query(normalized)}`,
    undefined,
    projectId,
  );
  const manifest = expectedVersion
    ? undefined
    : await fetchJSON<EngineeringManifest>('/engineering/manifest.json');
  const expected =
    expectedVersion ??
    manifest?.files.find((file) => workspacePath(file.path) === normalized)?.sha256;
  if (useWorkspace.getState().projectId !== projectId) return false;
  if (!expected || source.version !== expected) {
    useWorkspace.getState().openFile(normalized, undefined, 'pinned');
    toast('已打开当前源码；文件与旧资料不一致，原行号需要重新定位', undefined, 'error');
    return true;
  }
  if (start < 1 || end < start || end > source.line_count) {
    useWorkspace.getState().openFile(normalized, undefined, 'pinned');
    toast(
      `已打开当前源码；原引用 L${start}–${end} 超出当前文件的 ${source.line_count} 行范围`,
      undefined,
      'error',
    );
    return true;
  }
  useWorkspace.getState().openFile(normalized, start, 'pinned', end);
  return true;
}
