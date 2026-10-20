import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolveSourceEvidence } from '../../src/features/chat/rich/sourceEvidence.ts';
import { contentToMarkdown } from '../../src/features/chat/rich/contentToMarkdown.ts';

const source = { path: 'Engine.cs', start_line: 10, end_line: 15 };
const evidence = {
  path: 'Engine.cs',
  start_line: 1,
  end_line: 30,
  version: 'v1',
  source_workspace_id: 'src-a',
  current_status: 'match',
};
test('源码只用完整路径、覆盖范围、来源和版本匹配，绝不按同名文件猜测', () => {
  assert.equal(resolveSourceEvidence(source, [evidence], 'src-a').evidence, evidence);
  for (const pointer of [
    { ...source, path: 'other/Engine.cs' },
    { ...source, end_line: 31 },
    { ...source, version: 'v0' },
    { ...source, source_workspace_id: 'src-b' },
  ])
    assert.ok(resolveSourceEvidence(pointer, [evidence], 'src-a').reason);
  assert.ok(resolveSourceEvidence(source, []).reason);
});
test('跨目录同名源码、变化版本、未知状态与来源矛盾不产生定位成功', () => {
  assert.match(
    resolveSourceEvidence(source, [evidence, { ...evidence, source_workspace_id: 'src-b' }]).reason,
    /多个/,
  );
  assert.match(
    resolveSourceEvidence(source, [{ ...evidence, current_status: 'changed' }]).reason,
    /变化/,
  );
  assert.match(
    resolveSourceEvidence(source, [{ ...evidence, current_status: 'unavailable' }]).reason,
    /不可读取/,
  );
  assert.match(
    resolveSourceEvidence(
      { ...source, path: '@sources/src-a/Engine.cs', source_workspace_id: 'src-b' },
      [],
    ).reason,
    /身份不一致/,
  );
  assert.equal(
    resolveSourceEvidence({ ...source, version: 'v1' }, [evidence, { ...evidence, version: 'v2' }])
      .evidence,
    evidence,
  );
});
test('复制结构化回答保留语义、步骤、代码、表格和引用，旧文本逐字保留', async () => {
  const fixture = await readFile(new URL('./fixtures/rich-content.json', import.meta.url), 'utf8');
  const answer = '# 回答\n\n```rich-content\n' + fixture + '\n```\n\n末尾';
  const copied = contentToMarkdown(answer);
  for (const content of [
    '# 回答',
    '功能入口',
    '1. **检查条件**',
    '失败时返回',
    'Program.cs#L2-L2',
    '```csharp',
    '空闲 | 0',
    '入口 → 工作方法',
    '这里保留细节',
    '末尾',
  ])
    assert.ok(copied.includes(content), content);
  assert.doesNotMatch(copied, /rich-content|"version"/);
  assert.equal(contentToMarkdown('旧文本\r\n\r\n- 原文'), '旧文本\r\n\r\n- 原文');
  assert.equal(
    contentToMarkdown('```rich-content\n{坏JSON}\n```'),
    '```rich-content\n{坏JSON}\n```',
  );
});
