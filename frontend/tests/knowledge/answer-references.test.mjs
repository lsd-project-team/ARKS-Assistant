import test from 'node:test';
import assert from 'node:assert/strict';
import {
  answerKnowledgeCitations,
  answerReferences,
} from '../../src/features/knowledge/lib/answerReferences.ts';

const handover = {
  kind: 'handover_material',
  id: 'handover-a',
  title: 'M8 DAF信息收集.docx',
  version: 1,
  citation: 'handover-source:handover-a/1#L1-L20',
};
const issue = {
  kind: 'debug_issue',
  id: 'issue-a',
  title: '中转台取片异常',
  version: 2,
  citation: 'debug-issue:issue-a/2',
  resolution_status: 'open',
  compatibility: { status: 'needs_confirmation', missing: ['设备版本'] },
};
const available = [handover, issue];

test('问候、资料标题与纯文本地址不把候选资料算作本轮参考', () => {
  for (const answer of [
    '',
    '你好！有什么需要帮忙的吗？',
    '可以查询 M8 DAF信息收集.docx 和中转台取片异常。',
    '地址：debug-issue:issue-a/2',
    '地址：handover-source:handover-a/1#L1-L20',
  ])
    assert.deepEqual(answerReferences(answer, available), [], answer);
});

test('只显示实际引用的资料，保留风险和适用条件信息', () => {
  assert.deepEqual(answerReferences('参考[取片记录](debug-issue:issue-a/2)。', available), [issue]);
});

test('允许引用已带入片段内的子范围，打开位置使用实际引用的行号', () => {
  assert.deepEqual(answerReferences('[资料](handover-source:handover-a/1#L8)。', available), [
    { ...handover, citation: 'handover-source:handover-a/1#L8' },
  ]);
});

test('按引用顺序排列，同一资料版本的多个片段只计一次', () => {
  assert.deepEqual(
    answerReferences(
      '[记录](debug-issue:issue-a/2)\n[资料一](handover-source:handover-a/1#L11)\n' +
        '[资料二](handover-source:handover-a/1#L15-L20)\n[记录](debug-issue:issue-a/2)',
      [...available, handover],
    ),
    [issue, { ...handover, citation: 'handover-source:handover-a/1#L11' }],
  );
});

test('同一资料的不同已记录版本独立列出，未知版本不显示', () => {
  const previous = { ...issue, version: 1, citation: 'debug-issue:issue-a/1' };
  assert.deepEqual(
    answerReferences(
      '[旧版](debug-issue:issue-a/1) [新版](debug-issue:issue-a/2) [未知](debug-issue:issue-a/3)',
      [...available, previous],
    ),
    [previous, issue],
  );
});

for (const target of [
  'material:project-a/manual/3#L12',
  'handover-source:unknown/1#L8',
  'handover-source:handover-a/2#L8',
  'handover-source:handover-a/1#L21',
  'handover-source:handover-a/1#L8-L2',
  'debug-issue:unknown/2',
  'debug-issue:issue-a/9007199254740992',
  'debug-issue:issue-a/0',
  'debug-issue:issue-a/2#L1',
  'source:Program.cs#L18',
  'https://example.com/issue-a/2',
]) {
  test(`不把不匹配或非法引用列为已参考资料：${target}`, () => {
    assert.deepEqual(answerReferences(`[链接](${target})`, available), []);
  });
}

test('代码块、行内代码、图片、转义示例和未使用的链接定义不算引用', () => {
  const answer = [
    '```md\n[记录](debug-issue:issue-a/2)\n```',
    '`[记录](debug-issue:issue-a/2)`',
    '![图片](debug-issue:issue-a/2)',
    String.raw`\[记录](debug-issue:issue-a/2)`,
    '[unused]: debug-issue:issue-a/2',
    '<a href="debug-issue:issue-a/2">记录</a>',
  ].join('\n\n');
  assert.deepEqual(answerReferences(answer, available), []);
});

test('支持参考式链接及显式自动链接，匹配大小写不同的参考名称', () => {
  assert.deepEqual(
    answerReferences(
      '[取片记录][Record]\n\n[record]: debug-issue:issue-a/2\n\n' +
        '<handover-source:handover-a/1#L1-L2>',
      available,
    ),
    [issue, { ...handover, citation: 'handover-source:handover-a/1#L1-L2' }],
  );
});

test('同名参考定义以首条为准，与 Markdown 显示一致', () => {
  assert.deepEqual(
    answerReferences(
      '[记录][ref]\n\n[ref]: debug-issue:issue-a/2\n\n[ref]: handover-source:handover-a/1#L1',
      available,
    ),
    [issue],
  );
});

test('流式半截链接不显示，完成链接才显示，替换回答后不残留旧引用', () => {
  assert.deepEqual(answerReferences('[取片记录](debug-issue:issue-a/2', available), []);
  assert.deepEqual(answerReferences('[取片记录](debug-issue:issue-a/2)', available), [issue]);
  assert.deepEqual(answerReferences('你好！', available), []);
});

test('引用行号恰好处于带入范围边界时可用；空候选不会推测资料', () => {
  assert.deepEqual(answerReferences('[说明](handover-source:handover-a/1#L1-L20)', available), [
    handover,
  ]);
  assert.deepEqual(answerReferences('[记录](debug-issue:issue-a/2)', []), []);
});

test('候选元数据与其引用地址身份不一致时不接受', () => {
  assert.deepEqual(
    answerReferences('[记录](debug-issue:issue-a/2)', [
      { ...issue, citation: 'debug-issue:other/2' },
      { ...issue, version: 1 },
      { ...issue, id: 'other' },
      { ...issue, kind: 'handover_material' },
    ]),
    [],
  );
});

test('仅提取知识资料协议，不将源码或外部网址视为资料引用', () => {
  assert.deepEqual(
    answerKnowledgeCitations('[代码](source:Program.cs#L20) [网站](https://example.com)'),
    [],
  );
});
