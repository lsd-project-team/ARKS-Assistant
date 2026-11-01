import test from 'node:test';
import assert from 'node:assert/strict';
import { groupCodeSources } from '../../src/features/chat/rich/codeSources.ts';
import { separateAnswerSources } from '../../src/features/chat/rich/answerSources.ts';
import { parseContent } from '../../src/features/chat/rich/parseContent.ts';

const source = {
  path: 'Dir/Engine.cs',
  start_line: 12,
  end_line: 24,
  version: 'v1',
  source_workspace_id: 's',
};
const evidence = [{ ...source, start_line: 1, end_line: 100, current_status: 'match' }];
const link = (url, label = 'Engine.cs:12–24') => ({
  type: 'link',
  url,
  markdown: `[${label}](<${url}>)`,
});

test('按真实路径、版本和目录归组，合并两种协议的相同范围且不合并不同范围', () => {
  const input = [
    { type: 'source', source },
    link('source:Dir%2FEngine.cs#L12-L24'),
    link('source:Dir/Engine.cs#L30-L32'),
  ];
  const before = JSON.stringify(input);
  const { groups, others } = groupCodeSources(input, evidence);
  assert.equal(groups.length, 1);
  assert.equal(groups[0].name, 'Engine.cs');
  assert.equal(groups[0].path, 'Dir/Engine.cs');
  assert.deepEqual(
    groups[0].sources.map((row) => [row.start_line, row.end_line]),
    [
      [12, 24],
      [30, 32],
    ],
  );
  assert.equal(others.length, 0);
  assert.equal(JSON.stringify(input), before);
});

test('同名文件、不同版本和目录不能合并，未知版本不能强行绑定某个版本', () => {
  const sources = [
    source,
    { ...source, version: 'v2' },
    { ...source, source_workspace_id: 'other' },
    { ...source, path: 'Other/Engine.cs' },
  ].map((source) => ({ type: 'source', source }));
  const result = groupCodeSources(
    [...sources, link('source:Dir/Engine.cs#L12-L24')],
    [evidence[0], { ...evidence[0], version: 'v2' }],
  );
  assert.equal(result.groups.length, 5);
  assert.equal(result.groups.at(-1).version, undefined);
});

test('短锚点仅在实际读取范围支持时恢复展示的终点，坏编码或行号不能走旧链接入口', () => {
  assert.equal(
    groupCodeSources([link('source:Dir/Engine.cs#L12')], evidence).groups[0].sources[0].end_line,
    24,
  );
  assert.equal(
    groupCodeSources([link('source:Dir/Engine.cs#L12')], []).groups[0].sources[0].end_line,
    12,
  );
  const result = groupCodeSources(
    [link('source:Dir%ZZ/Engine.cs#L12'), link('source:Dir/Engine.cs#L30-L2')],
    evidence,
  );
  assert.equal(result.groups.length, 0);
  assert.equal(result.invalid.length, 2);
  assert.equal(result.others.length, 0);
});

test('文本经验来源保持不变，附带说明中的代码引用也进入文件分组', () => {
  const content = '来源：[代码](source:Dir/Engine.cs#L12-L24)（已读取）';
  const projected = separateAnswerSources(parseContent(content));
  const knowledge = link('debug-issue:case/4', '经验');
  const result = groupCodeSources([...projected.sources, knowledge], evidence);
  assert.equal(result.groups.length, 1);
  assert.ok(result.others.some((row) => row.type === 'text' && row.markdown.includes('已读取')));
  assert.ok(result.others.includes(knowledge));
  assert.ok(!result.others.some((row) => row.markdown?.includes('source:')));
});
