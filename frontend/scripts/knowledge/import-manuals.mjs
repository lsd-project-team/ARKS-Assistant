// 首次传入交付目录；此后从已纳入版本管理的资源重建目录和搜索索引。
import { readFile, readdir, mkdir, writeFile } from 'node:fs/promises';
import { resolve, basename } from 'node:path';
import { createHash } from 'node:crypto';
import { projectRoot, knowledgePath } from './resources.mjs';

const target = knowledgePath('archify/manuals');
if (process.argv[2]) {
  const input = resolve(process.argv[2]);
  await mkdir(resolve(target, 'docs'), { recursive: true });
  for (const name of await readdir(resolve(input, 'zx2200 html文档')))
    if (name.endsWith('.html'))
      await writeFile(
        resolve(target, name),
        (await readFile(resolve(input, 'zx2200 html文档', name), 'utf8')).replace(/\r\n?/g, '\n'),
      );
  for (const name of await readdir(resolve(input, 'docs')))
    if (/^\d.*\.md$/.test(name))
      await writeFile(
        resolve(target, 'docs', name),
        (await readFile(resolve(input, 'docs', name), 'utf8')).replace(/\r\n?/g, '\n'),
      );
}

// Windows 编辑器可能再次写入 CRLF；计算摘要前统一正式资源的换行。
for (const folder of [target, resolve(target, 'docs')]) {
  for (const name of await readdir(folder)) {
    if (!/\.(?:html|md)$/.test(name)) continue;
    const path = resolve(folder, name);
    const text = await readFile(path, 'utf8');
    if (text.includes('\r')) await writeFile(path, text.replace(/\r\n?/g, '\n'));
  }
}

const topics = {
  '00': ['architecture'],
  '00-stop': ['recovery'],
  '01': ['startup'],
  '02': ['architecture', 'startup', 'recipe'],
  '03': ['architecture', 'persistence'],
  '04': ['recipe', 'maintenance'],
  '05': ['s2', 's1'],
  '06': ['s2', 'tool-bank'],
  '07': ['s2'],
  '08': ['wafer'],
  '09': ['wafer'],
  10: ['wafer'],
  11: ['height-measurement', 'motion-safety', 'persistence'],
  12: ['force-control', 'consumables', 'persistence'],
  13: ['global-calibration', 'camera-calibration', 'maintenance'],
  14: ['camera-calibration', 'tool-calibration', 'maintenance'],
  16: ['maintenance'],
  17: ['maintenance'],
  18: ['transport'],
  19: ['recipe', 'product-coordinates'],
  20: ['product-coordinates', 'recipe'],
  21: ['s1'],
  23: ['public-vision'],
  24: ['s1'],
  25: ['g0', 'motion-safety'],
  26: ['startup', 'maintenance'],
  27: ['architecture'],
  29: ['architecture'],
  30: ['architecture'],
  31: ['product-coordinates', 'recipe'],
  32: ['s2'],
  33: ['s2'],
  34: ['wafer'],
  35: ['wafer'],
  36: ['force-control', 'consumables', 'maintenance'],
  37: ['architecture', 'persistence'],
  38: ['startup', 'architecture'],
  39: ['transport'],
  40: ['s1'],
  41: ['camera-calibration', 'global-calibration', 'tool-calibration', 'maintenance'],
  42: ['maintenance'],
  43: ['recipe', 'product-coordinates'],
  44: ['architecture'],
  90: ['architecture'],
  91: ['recovery'],
  92: ['architecture'],
};
// 目录标题按阅读层次区分；文件名和历史链接保持不变。
const entryTitles = {
  31: '料单元系统·总览与主流程',
  32: '固晶系统·调度与动作节点总览',
  33: '固晶系统·界面与按钮流程细节',
  34: '晶圆系统·模型、实体与调度总览',
  35: '晶圆系统·界面与按钮流程细节',
  36: '支撑特性·全景与主流程',
  37: '基础设施·架构与依赖总览',
  38: '主框架·启动与调度总览',
  39: '物流搬运系统·全景与主流程',
  40: '点胶系统·全景与主流程',
  41: '标定系统·全景与主流程',
  42: '实验系统·全景与主流程',
  43: '料单元系统·按钮与交互细节',
  44: '本地化与工程杂项·工程说明',
};
const search = await readFile(resolve(target, 'search.html'), 'utf8');
const data = JSON.parse(search.match(/const DATA = (.*);/)[1]);
const digest = (value) => createHash('sha256').update(value).digest('hex');
const entries = [];
for (const item of data) {
  const key = item.id.includes('停机语义') ? '00-stop' : item.id.slice(0, 2);
  if (!topics[key]) throw new Error(`未归类的图解：${item.id}`);
  const file = `${item.id}.html`;
  const html = await readFile(resolve(target, file), 'utf8');
  const doc = key === '00-stop' ? '00-项目总览.md' : file.replace(/\.html$/, '.md');
  const hasDoc = (await readdir(resolve(target, 'docs'))).includes(doc);
  const documents = hasDoc
    ? [doc]
    : key === '90'
      ? [
          '02-机器模型与流程调度.md',
          '07-固晶系统调度与任务.md',
          '09-晶圆系统调度与服务.md',
          '18-物流搬运系统.md',
          '21-点胶系统.md',
        ]
      : key === '91'
        ? [
            '02-机器模型与流程调度.md',
            '04-基础设施界面层.md',
            '11-支撑特性一-测高运动与监控.md',
            '32-固晶系统全景与流程图（上）· 模型、动作节点与调度.md',
          ]
        : ['00-项目总览.md'];
  const documentHashes = {};
  for (const name of documents)
    documentHashes[name] = digest(await readFile(resolve(target, 'docs', name)));
  entries.push({
    id: `manual-${key}`,
    file,
    title: entryTitles[key] || item.id.replace(/^\d+-/, ''),
    summary: item.desc,
    detailAnchor:
      key === '00-stop'
        ? '54-停机语义本项目的停止到底怎么工作的-必读'
        : key === '91'
          ? '46-停止-急停-暂停-继续'
          : 'overview',
    type: item.type,
    topicIds: topics[key],
    documents,
    searchText: [
      item.title,
      item.desc,
      ...item.nodes.flatMap((n) => [n.label, n.sub]),
      ...item.cards.flatMap((c) => [c.title, ...(c.items || [])]),
    ].join(' '),
    htmlSha256: digest(html),
    documentHashes,
  });
}
const destination = resolve(projectRoot, 'frontend/src/features/knowledge/data/manualCatalog.json');
await writeFile(destination, JSON.stringify({ entries }, null, 2) + '\n');
console.log(
  `${basename(destination)}：${entries.length} 张图解，${new Set(entries.flatMap((x) => x.documents)).size} 篇说明。`,
);
