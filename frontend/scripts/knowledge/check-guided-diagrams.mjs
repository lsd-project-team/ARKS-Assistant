import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { guidedDiagrams } from '../../src/features/knowledge/guidedDiagrams.ts';
import { startupGuide } from '../../src/features/knowledge/reviews/startup.ts';
import { knowledgePath } from './resources.mjs';

for (const [flowId, diagram] of Object.entries(guidedDiagrams)) {
  const flow = startupGuide.flows.find((item) => item.id === flowId);
  if (!flow) throw new Error(`逐步阅读流程不存在：${flowId}`);
  const html = await readFile(knowledgePath(`archify/${diagram.path}`));
  if (createHash('sha256').update(html).digest('hex') !== diagram.sha256)
    throw new Error(`逐步阅读图已变化，需重新核对：${flowId}`);
  const specBytes = await readFile(
    knowledgePath(`archify/${diagram.path.replace('.html', '.archify.json')}`),
  );
  if (createHash('sha256').update(specBytes).digest('hex') !== diagram.specSha256)
    throw new Error(`逐步阅读规格已变化，需重新核对：${flowId}`);
  const specification = JSON.parse(specBytes.toString('utf8'));
  const steps = new Set(flow.steps.map((item) => item.id));
  const nodes = new Set(specification.nodes.map((item) => item.id));
  const covered = new Set();
  for (const [stepId, targets] of Object.entries(diagram.steps)) {
    if (!steps.delete(stepId) || !targets.length)
      throw new Error(`逐步阅读步骤绑定无效：${flowId}/${stepId}`);
    for (const id of targets) {
      if (!nodes.has(id) || !html.includes(`data-node-id="${id}"`))
        throw new Error(`逐步阅读节点不存在：${flowId}/${id}`);
      covered.add(id);
    }
  }
  if (steps.size || covered.size !== nodes.size)
    throw new Error(`逐步阅读遗漏步骤或图中分支：${flowId}`);
}
console.log(
  `逐步阅读检查通过：${Object.keys(guidedDiagrams).length} 张新版图与步骤、分支绑定一致。`,
);
