// 导出已有人工复核资料给 Agent；不修改中文说明或接受新的源码指纹。
import { writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { sourceGuides, sourceEvidence } from '../../src/features/knowledge/sourceGuides.ts';

const documents = [];
for (const guide of sourceGuides) {
  const add = (id, title, claim) => {
    documents.push({
      id: `${guide.id}:${id}`,
      title: `${guide.title} / ${title}`,
      topic: guide.topic,
      text: claim.text,
      references: claim.refs.map((id) => {
        const range = sourceEvidence.ranges[id];
        if (!range) throw new Error(`资料引用不存在：${id}`);
        return { id, ...range, ...sourceEvidence.sources[range.file] };
      }),
    });
  };
  for (const flow of guide.flows) {
    add(flow.id, flow.title, flow);
    for (const step of flow.steps) {
      add(`${flow.id}:${step.id}`, `${flow.title} / ${step.title}`, step);
      step.outcomes.forEach((outcome, index) =>
        add(`${flow.id}:${step.id}:${index}`, `${step.title} / ${outcome.label}`, outcome),
      );
    }
  }
  guide.boundaries.forEach((claim, index) => add(`boundary:${index}`, '复核边界', claim));
}
const payload = { schema_version: 1, documents };
const target = fileURLToPath(
  new URL('../../../resources/knowledge/generated/agent-knowledge.json', import.meta.url),
);
await writeFile(target, JSON.stringify(payload, null, 2) + '\n', 'utf8');
console.log(`已导出 ${documents.length} 条人工复核资料供 Agent 检索`);
