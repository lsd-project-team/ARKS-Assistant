import { draftFor, useWorkspace } from '../../app/state/store';
import { toast } from '../../shared/utils/toasts';
import { archifyData } from './data/archifyData';
import { diagramReadings } from './data/diagramReading';
import { displayDiagramTitle } from './data/presentation';
import type { ChatRoute } from './routes';

export async function discussKnowledge(route: ChatRoute): Promise<boolean> {
  const paragraphs: string[] = [];
  if (route.flow) {
    const graph = archifyData.graphs.find((item) => item.slug === route.flow);
    if (!graph) throw new Error('这个流程没有对应的资料');
    const reading = diagramReadings[graph.slug];
    paragraphs.push(
      `请结合当前项目源码讨论流程「${displayDiagramTitle(graph.slug, graph.title)}」。`,
      `用途：${reading.summary}`,
      `执行条件：${reading.condition}`,
      `异常与边界：${reading.exception}`,
      `流程节点：\n${graph.nodes.map((node) => `${node.label}：${node.detail}`).join('\n')}`,
    );
  }
  if (route.message) paragraphs.push(route.message);
  const state = useWorkspace.getState();
  const draft = draftFor(state);
  const content = [draft.content, paragraphs.join('\n\n')].filter(Boolean).join('\n\n');
  if (content.length > 30000) throw new Error('当前草稿过长，请精简后再加入流程资料');
  // 只加入流程说明，源码由对话按当前项目检索，不再附带历史快照选区。
  state.setDraft(content);
  state.setMobile('chat');
  toast('资料已加入当前对话草稿');
  return true;
}
