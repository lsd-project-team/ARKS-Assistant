import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { JSDOM } from 'jsdom';
import { fromMarkdown } from 'mdast-util-from-markdown';
import { manuals } from '../../src/features/knowledge/data/manualCatalog.ts';
import { presentationTopics } from '../../src/features/knowledge/data/presentation.ts';
import { knowledgePath } from './resources.mjs';
import { splitManual } from '../../src/features/knowledge/manuals/manualContent.ts';

const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');
const root = knowledgePath('archify/manuals');
const used = new Set();
let links = 0;
for (const entry of manuals) {
  const html = await readFile(`${root}/${entry.file}`, 'utf8');
  assert.equal(digest(html), entry.htmlSha256, `图解变更后请重建目录：${entry.id}`);
  assert.ok(
    entry.topicIds.length &&
      entry.topicIds.every((id) => presentationTopics.some((topic) => topic.id === id)),
    `业务归类：${entry.id}`,
  );
  for (const link of html.matchAll(/<a\b[^>]*\bhref="([^"]*)"/g)) {
    const href = link[1];
    if (!href || /^(?:https?:|data:|#)/.test(href)) continue;
    assert.ok(
      (await readdir(root)).includes(decodeURIComponent(href.split('#')[0])),
      `失效链接：${entry.file}/${href}`,
    );
    links++;
  }
  for (const script of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g))
    if (!/type="application\/json"/.test(script[1])) new Function(script[2]);
  for (const name of entry.documents) {
    const text = await readFile(`${root}/docs/${name}`, 'utf8');
    assert.equal(digest(text), entry.documentHashes[name], `说明变更后请重建目录：${name}`);
    if (name === entry.documents[0] && entry.detailAnchor !== 'overview') {
      const document = splitManual(text);
      assert.ok(
        document.headings.some((heading) => heading.id === entry.detailAnchor),
        `默认章节失效：${entry.id}`,
      );
    }
    used.add(name);
  }
}
assert.equal(manuals.length, 46);
assert.equal(used.size, 42);
assert.deepEqual(
  [...used].sort(),
  (await readdir(`${root}/docs`)).filter((name) => name.endsWith('.md')).sort(),
);
const alarm = await readFile(`${root}/91-报警与停机.html`, 'utf8');
assert.doesNotMatch(alarm, /最多要等一个 20 ms|不管从哪来，最后都是|改回 Run 才继续/);
assert.ok(alarm.includes('20 ms 是暂停时的轮询间隔'));

// 真实 Mermaid 解析器核对全部说明图的语法；不把解析通过当作浏览器排版验收。
const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.window = dom.window;
globalThis.document = dom.window.document;
const { default: mermaid } = await import('mermaid');
mermaid.initialize({
  startOnLoad: false,
  securityLevel: 'strict',
  maxTextSize: 60000,
  maxEdges: 1000,
});
const failures = [];
let diagrams = 0;
for (const name of used) {
  const text = await readFile(`${root}/docs/${name}`, 'utf8');
  for (const node of fromMarkdown(text).children) {
    if (node.type !== 'code' || node.lang !== 'mermaid') continue;
    diagrams++;
    try {
      await mermaid.parse(node.value);
    } catch (error) {
      failures.push(`${name}:${node.position.start.line} ${String(error.message).slice(0, 240)}`);
    }
  }
}
dom.window.close();
if (failures.length)
  throw new Error(`${failures.length}/${diagrams} 张详细流程图语法失败：\n${failures.join('\n')}`);
console.log(
  `模块资料检查通过：${manuals.length} 张交互图、${used.size} 篇说明、${diagrams} 张 Mermaid 图、${links} 个图内链接。`,
);
