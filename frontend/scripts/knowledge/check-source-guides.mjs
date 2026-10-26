import { knowledgePath, projectRoot } from './resources.mjs';
import { resolve } from 'node:path';
import { readFile } from 'node:fs/promises';
import { sourceGuides } from '../../src/features/knowledge/sourceGuides.ts';
import sourceEvidence from './source-evidence.json' with { type: 'json' };
import { archifyData } from '../../src/features/knowledge/data/archifyData.ts';
import { presentationTopics } from '../../src/features/knowledge/data/presentation.ts';
import { validateSourceGuides } from './source-guide-validation.mjs';

const trunkRoot = resolve(projectRoot, 'trunk');
const counts = await validateSourceGuides({
  guides: sourceGuides,
  evidence: sourceEvidence,
  trunkRoot,
  topics: presentationTopics.map((item) => item.id),
  diagrams: archifyData.flowchartCatalog.entries.map((item) => item.id),
});
const { createHash } = await import('node:crypto');
for (const diagram of Object.values(sourceEvidence.diagrams)) {
  if (!/^archify\/[a-z0-9-]+\.html$/.test(diagram.path)) throw new Error('复核图谱路径无效');
  const bytes = await readFile(knowledgePath(diagram.path));
  if (createHash('sha256').update(bytes).digest('hex') !== diagram.sha256)
    throw new Error(`复核图谱已变化，需同步复核内容与版本：${diagram.path}`);
}
// 这三条关系按 PrepareMachineReadyToStart 与 Start 的源码顺序人工核对。
// 同时检查路径和标签端点，防止原图与右侧说明出现相反调用顺序。
const startupDiagram = await readFile(
  knowledgePath('archify/machine-start-readiness-workflow.html'),
  'utf8',
);
for (const [from, to] of [
  ['prepare', 'init'],
  ['init', 'environment'],
  ['environment', 'working'],
]) {
  for (const element of ['path', 'g']) {
    if (
      !new RegExp(`<${element}[^>]*data-edge-from="${from}"[^>]*data-edge-to="${to}"`).test(
        startupDiagram,
      )
    )
      throw new Error(`启动原图的调用顺序不符：${from} → ${to} (${element})`);
  }
}
// 人工重绘的局部图同时核对可见节点、SVG 路径、标签和目录规格。
// 文件指纹防止未经复核的修改；端点检查防止文字正确而箭头仍指向旧分支。
for (const id of [
  's1-defect-outcome-workflow',
  's1-rework-context-workflow',
  's2-task-entry-boundary-workflow',
  'relative-bond-order-workflow',
  's2-action-boundary-workflow',
  'wafer-search-gate-workflow',
  'wafer-change-retry-workflow',
  'wafer-vision-outcome-workflow',
]) {
  const directory = knowledgePath('archify/');
  const specBytes = await readFile(resolve(directory, `${id}.archify.json`));
  const spec = JSON.parse(specBytes.toString('utf8'));
  const html = await readFile(resolve(directory, `${id}.html`), 'utf8');
  const entry = archifyData.flowchartCatalog.entries.find((item) => item.id === id);
  if (createHash('sha256').update(specBytes).digest('hex') !== entry.specSha256)
    throw new Error(`图谱规格版本不符：${id}`);
  if (spec.nodes.length !== entry.nodeCount || spec.edges.length !== entry.relationCount)
    throw new Error(`图谱目录数量不符：${id}`);
  const visibleNodes = [...html.matchAll(/<g\b[^>]*data-node-id="([^"]+)"[^>]*>/g)];
  const paths = [...html.matchAll(/<path\b[^>]*data-edge-id="([^"]+)"[^>]*>/g)];
  if (visibleNodes.length !== spec.nodes.length || paths.length !== spec.edges.length)
    throw new Error(`原图节点或分支数量不符：${id}`);
  for (const node of spec.nodes) {
    const tag = visibleNodes.find((match) => match[1] === node.id)?.[0] ?? '';
    if (
      !tag.includes(`data-node-label="${node.label}"`) ||
      !tag.includes(`data-node-sublabel="${node.sublabel}"`)
    )
      throw new Error(`原图节点文字不符：${id}/${node.id}`);
  }
  for (const edge of spec.edges) {
    for (const element of ['path', 'g']) {
      const tags = [
        ...html.matchAll(new RegExp(`<${element}\\b[^>]*data-edge-id="${edge.id}"[^>]*>`, 'g')),
      ];
      if (
        tags.length !== 1 ||
        !['from', 'to', 'label'].every((key) =>
          tags[0][0].includes(`data-edge-${key}="${edge[key]}"`),
        )
      )
        throw new Error(`原图分支端点或标签不符：${id}/${edge.id} (${element})`);
    }
  }
}
console.log(
  `源码说明检查通过：${counts.guides} 个专题，${counts.flows} 条流程，${counts.steps} 个节点，${counts.claims} 条说明；${counts.files} 个文件、${counts.ranges} 段依据均与 trunk 一致。`,
);
