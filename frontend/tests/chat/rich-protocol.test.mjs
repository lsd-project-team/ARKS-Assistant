import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { parseDocument, RICH_LIMITS } from '../../src/features/chat/rich/schema.ts';
import { parseContent } from '../../src/features/chat/rich/parseContent.ts';

const fixture = JSON.parse(
  await readFile(new URL('./fixtures/rich-content.json', import.meta.url), 'utf8'),
);
const fence = (value) => '```rich-content\n' + JSON.stringify(value) + '\n```';
test('八种内容块及历史 Markdown 保留顺序和原文', () => {
  assert.equal(parseDocument(JSON.stringify(fixture)).document.blocks.length, 8);
  const content = `前文\n\n${fence(fixture)}\n\n后文`;
  assert.deepEqual(
    parseContent(content).map((segment) => segment.type),
    ['markdown', 'rich', 'markdown'],
  );
  assert.equal(parseContent('旧历史\n\n- 原始列表')[0].content, '旧历史\n\n- 原始列表');
});
test('普通围栏、较长围栏里的协议示例不转换，CRLF 和波浪围栏可用', () => {
  assert.equal(parseContent('````markdown\n' + fence(fixture) + '\n````')[0].type, 'markdown');
  assert.equal(
    parseContent(fence(fixture).replaceAll('```', '~~~').replaceAll('\n', '\r\n'))[0].type,
    'rich',
  );
});
test('损坏、未知版本、未知组件与多余操作字段安全降级', () => {
  for (const content of ['```rich-content\n{坏JSON}\n```', fence({ version: 2, blocks: [] })]) {
    const [segment] = parseContent(content);
    assert.equal(segment.type, 'fallback');
    assert.equal(segment.content, content);
  }
});
test('未知和损坏块局部降级，相邻块及嵌套块保持正常且保留原文', () => {
  const raw = { id: 'bad', type: 'iframe', src: 'javascript:alert(1)' };
  const document = {
    version: 1,
    blocks: [
      { id: 'before', type: 'markdown', content: '前文' },
      raw,
      {
        id: 'after',
        type: 'collapsible',
        title: '详情',
        blocks: [
          { id: 'broken', type: 'text', onClick: 'delete()' },
          { id: 'good', type: 'text', content: '后文' },
        ],
      },
    ],
  };
  const [segment] = parseContent(fence(document));
  assert.equal(segment.type, 'rich');
  assert.equal(segment.document.blocks[0].type, 'markdown');
  assert.deepEqual(segment.document.blocks[1].raw, raw);
  assert.equal(segment.document.blocks[1].id, 'bad');
  assert.equal(segment.document.blocks[2].blocks[0].type, 'unsupported');
  assert.equal(segment.document.blocks[2].blocks[1].content, '后文');
  assert.ok(parseDocument(JSON.stringify(document)).error);
});
test('缺失字段、重复 ID、表格错列、未知节点、非法路径被拒绝', () => {
  const invalid = [
    { id: 'x', type: 'text' },
    {
      id: 'x',
      type: 'overview_grid',
      items: [
        { id: 'a', title: 'A', description: '' },
        { id: 'a', title: 'B', description: '' },
      ],
    },
    { id: 'x', type: 'table', columns: [{ id: 'a', label: 'A' }], rows: [{ id: 'r', cells: [] }] },
    {
      id: 'x',
      type: 'diagram',
      title: '图',
      nodes: [{ id: 'a', label: 'A' }],
      edges: [{ from: 'a', to: 'missing' }],
    },
    ...['../private', '/etc/passwd', 'C:/secret', 'a\\b', 'a/./b', 'a\u0000b'].map((path) => ({
      id: 'x',
      type: 'source_reference',
      sources: [{ path, start_line: 1 }],
    })),
  ];
  for (const block of invalid)
    assert.ok(parseDocument(JSON.stringify({ version: 1, blocks: [block] })).error);
  assert.ok(
    parseDocument(
      JSON.stringify({
        version: 1,
        blocks: [
          { id: 'x', type: 'text', content: '' },
          { id: 'x', type: 'text', content: '' },
        ],
      }),
    ).error,
  );
});
test('超限大小、条数与深层递归受限，零值不是缺失值', () => {
  assert.ok(parseDocument(' '.repeat(RICH_LIMITS.bytes + 1)).error);
  assert.ok(
    parseDocument(
      JSON.stringify({
        version: 1,
        blocks: Array.from({ length: 129 }, (_, i) => ({ id: `t${i}`, type: 'text', content: '' })),
      }),
    ).error,
  );
  let block = { id: 'text', type: 'text', content: '' };
  for (let i = 0; i < 6; i++)
    block = { id: `nest${i}`, type: 'collapsible', title: '嵌套', blocks: [block] };
  assert.ok(parseDocument(JSON.stringify({ version: 1, blocks: [block] })).error);
  assert.equal(parseDocument(JSON.stringify(fixture)).document.blocks[5].rows[0].cells[1], 0);
});
test('完整文档中的不可信文本只作为文字，未完整 JSON 没有可信组件', () => {
  const content = fence({
    version: 1,
    blocks: [
      { id: 'x', type: 'text', content: '<script>alert(1)</script> [危险](javascript:alert(1))' },
    ],
  });
  assert.equal(parseContent(content)[0].type, 'rich');
  assert.equal(parseContent(content.slice(0, -3), true)[0].type, 'pending');
  assert.equal(parseContent(content.slice(0, -3), false)[0].type, 'fallback');
});
