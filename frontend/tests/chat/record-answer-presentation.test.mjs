import test from 'node:test';
import assert from 'node:assert/strict';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { remarkRecordAnswer } from '../../src/features/chat/lib/recordAnswerPresentation.ts';

const citation = '[7月23—24日｜adv-3 温补方案贴片精度试验 · v4](debug-issue:trial/4)';
const displayNotice = '（3张原图随上述引用直接展示）';
function render(content) {
  return renderToStaticMarkup(
    createElement(ReactMarkdown, {
      children: content,
      remarkPlugins: [[remarkGfm, { singleTilde: false }], remarkRecordAnswer],
      // 与应用保持一致，测试固定版本业务引用的 Markdown 渲染。
      urlTransform: (url) => url,
    }),
  );
}

test('已有回复移除两句原图展示说明，来源引用紧接事实正文末尾', () => {
  const html = render(
    `室温 **25.2℃**，精度稳定在 **3μm 3Σ**，Y方向受影响有限。\n\n本次试验的原图如下：\n\n${citation}\n\n${displayNotice}`,
  );
  assert.equal((html.match(/<p>/g) || []).length, 1);
  assert.match(html, /Y方向受影响有限。 <a href="debug-issue:trial\/4">/);
  assert.match(html, /<strong>25.2℃<\/strong>/);
  assert.match(html, /温补方案贴片精度试验 · v4<\/a><\/p>$/);
  assert.doesNotMatch(html, /原图如下|随上述引用直接展示/);
});

test('独立来源标签合并到正文，新回复已有行内引用时保持排版', () => {
  const inline = render(`结果为−4～2μm。 ${citation}`);
  assert.equal(render(`结果为−4～2μm。\n\n来源：${citation}`), inline);
  assert.equal(render(`结果为−4～2μm。\n\n记录文字与全部原图：${citation}`), inline);
});

test('列表结束后来源接在最后一项文字后，不生成重复的引用段落', () => {
  const html = render(`- 室温23.2℃。\n- 精度−4～2μm。\n\n${citation}\n\n${displayNotice}`);
  assert.match(html, /精度−4～2μm。 <a href="debug-issue:trial\/4">/);
  assert.equal((html.match(/<li>/g) || []).length, 2);
  assert.doesNotMatch(html, /<p>|随上述引用直接展示/);
});

test('图片本身的业务说明、数字和原话不能作为展示提示删除', () => {
  const html = render(
    `原图如下：室温25.2℃，曲线在14:00下降2μm。\n\n记录附3张原图，其中两张重复。\n\n${citation}`,
  );
  assert.match(html, /原图如下：室温25.2℃，曲线在14:00下降2μm。/);
  assert.match(html, /记录附3张原图，其中两张重复。/);
});

test('没有真实记录链接时不清理文字，代码和引用块内的展示原话保持原样', () => {
  assert.match(render(displayNotice), /3张原图随上述引用直接展示/);
  assert.match(render(`\`${citation}\`\n\n${displayNotice}`), /3张原图随上述引用直接展示/);
  const html = render(
    `结果。 ${citation}\n\n> ${displayNotice}\n\n\`\`\`text\n${displayNotice}\n\`\`\``,
  );
  assert.equal((html.match(/3张原图随上述引用直接展示/g) || []).length, 2);
  assert.match(html, /<blockquote>/);
  assert.match(html, /<pre><code/);
});

test('多条记录的引用各自跟随前一段事实，保持版本和原先引用顺序', () => {
  const html = render(
    `第一条结果。\n\n${citation}\n\n第二条结果。\n\n[第二条 · v2](debug-issue:second/2)`,
  );
  assert.match(html, /第一条结果。 <a href="debug-issue:trial\/4">/);
  assert.match(html, /第二条结果。 <a href="debug-issue:second\/2">/);
  assert.ok(html.indexOf('debug-issue:trial/4') < html.indexOf('debug-issue:second/2'));
});

test('图表和代码后的来源保留独立引用，不把链接塞进数据单元格或代码', () => {
  const html = render(`| 精度 |\n| --- |\n| 3μm |\n\n${citation}`);
  assert.match(html, /<table>/);
  assert.match(html, /<\/table>\s*<p><a href="debug-issue:trial\/4">/);
});

test('工艺数值范围的单波浪号保持原样，显式双波浪号仍能表示删除线', () => {
  const html = render(
    `焊头力20~30g，顶针高度280~300。\n\n> 20~30g + 280~300\n\n~~旧设置~~ ${citation}`,
  );
  assert.match(html, /焊头力20~30g，顶针高度280~300。/);
  assert.match(html, /<blockquote>\s*<p>20~30g \+ 280~300<\/p>/);
  assert.equal((html.match(/<del>/g) || []).length, 1);
  assert.match(html, /<del>旧设置<\/del>/);
});
