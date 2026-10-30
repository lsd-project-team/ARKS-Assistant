import { knowledgePath } from './resources.mjs';
import { access, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { archifyData } from '../../src/features/knowledge/data/archifyData.ts';
import { coordinateArtifacts } from '../../src/features/knowledge/data/coordinateDiagrams.ts';
import { functionalArtifacts } from '../../src/features/knowledge/data/functionalTopics.ts';
import './check-source-guides.mjs';

const missing = [];
let checked = 0;
async function check(path) {
  const relative = path.replace(/^docs[\\/]archify[\\/]/, 'archify/').replace(/^\//, '');
  const target = knowledgePath(relative);
  checked++;
  try {
    await access(target);
  } catch {
    missing.push(path);
  }
}
for (const entry of archifyData.flowchartCatalog.entries) {
  if (entry.html) await check(entry.html);
  if (!archifyData.diagramRecords[entry.id]) missing.push(`图谱记录：${entry.id}`);
}
// 源交付文件须保持 Archify 校验的字节；发布仍沿用现有源码依据隐藏规则。
for (const diagram of [...coordinateArtifacts, ...Object.values(functionalArtifacts)]) {
  for (const [path, sha256] of [
    [diagram.path, diagram.sha256],
    [diagram.path.replace(/\.html$/, '.json'), diagram.specificationSha256],
  ]) {
    const resourcePath = `archify/${path}`;
    await check(resourcePath);
    if (missing.includes(resourcePath)) continue;
    const bytes = await readFile(knowledgePath(resourcePath));
    if (createHash('sha256').update(bytes).digest('hex') !== sha256)
      throw new Error(`Archify 交付或规格已变化，需重新生成并核对：${path}`);
  }
}
if (missing.length) throw new Error(`缺失 ${missing.length} 项资料：\n${missing.join('\n')}`);
console.log(
  `资料检查通过：${archifyData.flowchartCatalog.entries.length} 项图谱/资料，共 ${checked} 项资源链接。`,
);
