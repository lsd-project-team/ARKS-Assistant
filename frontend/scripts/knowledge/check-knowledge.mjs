import { knowledgePath } from './resources.mjs';
import { access } from 'node:fs/promises';
import { archifyData } from '../../src/features/knowledge/data/archifyData.ts';
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
if (missing.length) throw new Error(`缺失 ${missing.length} 项资料：\n${missing.join('\n')}`);
console.log(
  `资料检查通过：${archifyData.flowchartCatalog.entries.length} 项图谱/资料，共 ${checked} 项资源链接。`,
);
