import test from 'node:test';
import assert from 'node:assert/strict';
import { parseContent } from '../../src/features/chat/rich/parseContent.ts';
import {
  separateAnswerSources,
  answerSourceLinks,
} from '../../src/features/chat/rich/answerSources.ts';
import { answerKnowledgeCitations } from '../../src/features/knowledge/lib/answerReferences.ts';
import { fromMarkdown } from 'mdast-util-from-markdown';

const citation = '[试验记录](debug-issue:trial/4)';
const split = (content, streaming = false) =>
  separateAnswerSources(parseContent(content, streaming));

for (const ordered of [false, true]) {
  test(`${ordered ? '有序' : '无序'}纯引用列表迁移后没有空项，相邻正文完整保留`, () => {
    const items = Array.from(
      { length: 5 },
      (_, i) =>
        `${ordered ? `${i + 1}.` : '-'} [File${i}.cs:12-24](source:Dir/File${i}.cs#L12-L24)`,
    ).join('\n');
    const { body, sources } = split(`前文。\n\n来源：\n${items}\n\n后文。`);
    assert.equal(sources.length, 5);
    assert.deepEqual(
      fromMarkdown(body[0].content).children.map((node) => node.type),
      ['paragraph', 'paragraph'],
    );
    assert.match(body[0].content, /前文。/);
    assert.match(body[0].content, /后文。/);
  });
}

test('正文与引用混排时仅移走纯引用项，保留正文及行内链接含义', () => {
  const content = `- 正常准备。\n- ${citation}\n- 参考${citation}继续处理。\n- 结束。`;
  const { body, sources } = split(content);
  assert.equal(sources.length, 1);
  const list = fromMarkdown(body[0].content).children[0];
  assert.equal(list.children.length, 3);
  assert.equal(list.spread, false);
  assert.match(body[0].content, /- 正常准备。\n\n?- 参考试验记录继续处理。\n- 结束。/);
});

test('CRLF来源列表清理不会把正常正文列表拆开或改成松散列表', () => {
  const content = `- 第一步\r\n- ${citation}\r\n- 第二步\r\n\r\n后续正文。`;
  const { body, sources } = split(content);
  assert.equal(sources.length, 1);
  assert.equal(body[0].content, '- 第一步\r\n- 第二步\r\n\r\n后续正文。');
  assert.equal(fromMarkdown(body[0].content).children[0].spread, false);
});

test('嵌套引用列表和空引用父项一并清理，父项正文与后续列表不丢失', () => {
  const content = `- 保留父项\n  - ${citation}\n  - 来源：\n    - [File.cs:2](source:Dir/File.cs#L2)\n- 下一步。\n\n后文。`;
  const { body, sources } = split(content);
  const nodes = fromMarkdown(body[0].content).children;
  assert.equal(sources.length, 2);
  assert.equal(nodes[0].children.length, 2);
  assert.equal(nodes[0].children[0].children.length, 1);
  assert.match(body[0].content, /保留父项/);
  assert.match(body[0].content, /下一步。/);
  assert.match(body[0].content, /后文。/);
});

test('不清理原有空项，保留任务、图片、代码和普通外链列表', () => {
  const content = `-\n- [x] 已完成\n- ![图](https://example.com/a.png)\n- \`示例\`\n- [官网](https://example.com)\n- ${citation}`;
  const { body, sources } = split(content);
  assert.equal(sources.length, 1);
  const list = fromMarkdown(body[0].content).children[0];
  assert.equal(list.children.length, 5);
  assert.equal(list.children[0].children.length, 0);
  for (const value of ['[x] 已完成', '![图]', '`示例`', '[官网](https://example.com)'])
    assert.ok(body[0].content.includes(value));
});

test('正文项附带独立引用段落以及引用式链接，不留下空嵌套容器', () => {
  const content =
    '- 保留正文。\n\n  [File.cs:2][code]\n\n- > [经验](debug-issue:trial/4)\n\n尾段。\n\n[code]: source:Dir/File.cs#L2';
  const { body, sources } = split(content);
  const nodes = fromMarkdown(body[0].content).children;
  assert.equal(sources.length, 2);
  assert.equal(nodes[0].children.length, 1);
  assert.equal(nodes[0].children[0].children.length, 1);
  assert.match(body[0].content, /保留正文。/);
  assert.match(body[0].content, /尾段。/);
});

test('来源段移出正文，后续图片、说明、警告和表格保留原顺序', () => {
  const content = `结论。\n\n来源：${citation}\n\n![示意](https://example.com/a.png)\n\n后续说明。\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n源码核对提示：仍需核对。`;
  const { body, sources } = split(content);
  assert.equal(sources.length, 1);
  assert.equal(sources[0].url, 'debug-issue:trial/4');
  assert.ok(!body[0].content.includes('来源：'));
  assert.ok(body[0].content.includes('![示意]'));
  assert.ok(body[0].content.includes('| 1 | 2 |'));
  assert.ok(body[0].content.endsWith('源码核对提示：仍需核对。'));
  assert.ok(content.includes(`来源：${citation}`));
});

test('行内链接保留文字含义，真实引用去重，引用式链接与普通外链兼容', () => {
  const content = `可参考${citation}，参见[记录][ref]。\n\n${citation}\n\n[普通外链](https://example.com)\n\n[ref]: debug-issue:trial/4`;
  const { body, sources } = split(content);
  assert.equal(sources.length, 1);
  assert.match(body[0].content, /可参考试验记录，参见记录。/);
  assert.match(body[0].content, /\[普通外链\]\(https:\/\/example.com\)/);
});

test('正文的纯代码定位标签及空括号移至最后，业务文字与代码样例保留', () => {
  const content =
    '必须等待（[Engine.cs:12–24](source:Dir/Engine.cs#L12-L24)）。\n\n' +
    '再检查 ([Engine.cs:30](source:Dir/Engine.cs#L30))。\n\n' +
    '[取片入口](source:Dir/Engine.cs#L40)负责取片。\n\n' +
    '`[Engine.cs:12](source:Dir/Engine.cs#L12)`';
  const { body, sources } = split(content);
  assert.match(body[0].content, /必须等待。/);
  assert.match(body[0].content, /再检查 。/);
  assert.match(body[0].content, /取片入口负责取片。/);
  assert.match(body[0].content, /`\[Engine.cs:12\]\(source:Dir\/Engine.cs#L12\)`/);
  assert.equal(sources.length, 3);
});

test('来源段中的外链会移至最后，代码和链接样例不当成真实来源', () => {
  const sample = `\`\`\`md\n来源：${citation}\n\`\`\`\n\n\`${citation}\`\n\n来源：[资料](https://example.com/doc)`;
  const { body, sources } = split(sample);
  assert.equal(sources.length, 1);
  assert.equal(sources[0].url, 'https://example.com/doc');
  assert.ok(body[0].content.includes(`来源：${citation}`));
  assert.ok(body[0].content.includes(`\`${citation}\``));
});

test('富内容内的来源、步骤引用、代码来源和嵌套折叠一并收集，源码版本不丢失', () => {
  const pointer = {
    path: 'Program.cs',
    start_line: 2,
    end_line: 3,
    version: 'v2',
    source_workspace_id: 's',
  };
  const document = {
    version: 1,
    blocks: [
      { type: 'text', id: 'text', content: `正文\n\n来源：${citation}` },
      { type: 'text', id: 'title', content: '### 来源' },
      {
        type: 'step_flow',
        id: 'steps',
        steps: [{ id: 'a', title: '执行', description: '正常动作', sources: [pointer] }],
      },
      { type: 'code', id: 'code', content: '  return 0;\n', language: 'cs', source: pointer },
      {
        type: 'collapsible',
        id: 'more',
        title: '补充',
        blocks: [{ type: 'source_reference', id: 'src', sources: [pointer] }],
      },
      { type: 'mermaid', id: 'graph', content: 'flowchart TD\n a[开始] --> b[结束]' },
    ],
  };
  const original = JSON.stringify(document);
  const { body, sources } = split('```rich-content\n' + original + '\n```');
  assert.equal(sources.length, 2);
  assert.ok(!body[0].document.blocks.some((b) => b.id === 'title'));
  assert.deepEqual(sources[1].source, pointer);
  assert.equal(body[0].document.blocks.find((b) => b.id === 'code').content, '  return 0;\n');
  assert.equal(body[0].document.blocks.find((b) => b.id === 'code').source, undefined);
  assert.ok(body[0].document.blocks.some((b) => b.id === 'graph'));
  assert.equal(JSON.stringify(document), original);
  assert.deepEqual(
    answerKnowledgeCitations('```rich-content\n' + original + '\n```').map((c) => c.citation),
    ['debug-issue:trial/4'],
  );
});

test('坏协议或流式未闭合协议不扫描其中JSON字符串，替换后的来源不沿用旧数据', () => {
  const raw = '```rich-content\n{"broken":"' + citation + '"';
  assert.equal(split(raw, true).sources.length, 0);
  assert.equal(split(raw).sources.length, 0);
  assert.deepEqual(answerSourceLinks(`来源：${citation}`), ['debug-issue:trial/4']);
  assert.deepEqual(answerSourceLinks('重写后的回答。'), []);
});

test('独立来源标题不残留，事实依据段不误当来源，引用图片不复制到页尾', () => {
  const { body, sources } = split(`正文。\n\n依据：两次读数相差1mm。\n\n## 来源\n\n${citation}`);
  assert.match(body[0].content, /依据：两次读数相差1mm。/);
  assert.doesNotMatch(body[0].content, /## 来源/);
  assert.equal(sources.length, 1);
  const image = split('[![原图](https://example.com/a.png)](debug-issue:trial/4)');
  assert.match(image.body[0].content, /!\[原图\]/);
  assert.doesNotMatch(image.sources[0].markdown, /!\[/);
  const literal = split('`来源：[代码样例](debug-issue:example/1)`');
  assert.equal(literal.sources.length, 0);
  assert.equal(literal.body[0].content, '`来源：[代码样例](debug-issue:example/1)`');
  const annotated =
    '```rich-content\n' +
    JSON.stringify({
      version: 1,
      blocks: [{ type: 'text', id: 's', content: `来源：${citation}（历史试验）` }],
    }) +
    '\n```';
  assert.deepEqual(
    answerKnowledgeCitations(annotated).map((c) => c.citation),
    ['debug-issue:trial/4'],
  );
});
