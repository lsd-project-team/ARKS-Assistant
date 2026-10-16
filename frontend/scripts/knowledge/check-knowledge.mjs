import { knowledgePath } from './resources.mjs';
import { readFile, access, readdir } from 'node:fs/promises';
import { archifyData } from '../../src/features/knowledge/data/archifyData.ts';
import './check-source-guides.mjs';

const manifest = JSON.parse(await readFile(knowledgePath('engineering/manifest.json'), 'utf8'));
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
for (const file of manifest.files) await check(`${manifest.base}/files/${file.id}.json`);
for (const module of manifest.modules) {
  const path = `${manifest.base}/modules/${module.id}.json`;
  await check(path);
  const detail = JSON.parse(await readFile(knowledgePath(path), 'utf8'));
  if (detail.review.document) await check(`archify/${detail.review.document}`);
  for (const method of detail.entryMethods)
    await check(`${manifest.base}/symbols/${method.id.slice(0, 2)}.json`);
}
await check(`${manifest.base}/search.json`);
await check(`${manifest.base}/evidence-baseline.json`);
const shards = await readdir(knowledgePath(`${manifest.base}/symbols`));
if (shards.length !== 256) throw new Error(`方法分片数量异常：${shards.length}`);
if (missing.length) throw new Error(`缺失 ${missing.length} 项资料：\n${missing.join('\n')}`);
console.log(
  `资料检查通过：${archifyData.flowchartCatalog.entries.length} 项图谱/资料，${manifest.modules.length} 个模块，${manifest.files.length} 个文件，${shards.length} 份方法分片，共 ${checked} 项资源链接。`,
);
