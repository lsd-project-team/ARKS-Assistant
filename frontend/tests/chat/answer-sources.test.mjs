import test from 'node:test';
import assert from 'node:assert/strict';
import { parseContent } from '../../src/features/chat/rich/parseContent.ts';
import {
  separateAnswerSources,
  answerSourceLinks,
} from '../../src/features/chat/rich/answerSources.ts';
import { answerKnowledgeCitations } from '../../src/features/knowledge/lib/answerReferences.ts';

const citation = '[试验记录](debug-issue:trial/4)';
const split = (content, streaming = false) =>
  separateAnswerSources(parseContent(content, streaming));

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
