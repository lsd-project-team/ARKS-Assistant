import { test } from 'node:test';
import assert from 'node:assert/strict';
import { exactCommand, matchingCommands } from '../../src/features/chat/lib/composerCommands.ts';

test('斜杠前缀筛选命令，独立命令允许空白和大小写', () => {
  assert.deepEqual(
    matchingCommands('/').map((item) => item.id),
    ['context', 'compact', '记录问题'],
  );
  assert.deepEqual(
    matchingCommands('/com').map((item) => item.id),
    ['compact'],
  );
  assert.equal(exactCommand('  /CONTEXT  '), 'context');
  assert.equal(exactCommand('/compact'), 'compact');
  assert.equal(exactCommand('/记录问题'), '记录问题');
  assert.deepEqual(
    matchingCommands('/记').map((item) => item.id),
    ['记录问题'],
  );
  assert.equal(exactCommand('/c'), undefined);
});

test('含正文、代码或路径的输入不会误当成上下文命令', () => {
  for (const content of [
    '/compact 请解释这个命令',
    '/context\n问题',
    '代码中 /compact 的含义',
    '/project/file.cs',
    '/unknown',
    '/记录问题 取片真空报警，检查后仍未解决',
  ]) {
    assert.equal(exactCommand(content), undefined);
    assert.deepEqual(matchingCommands(content), []);
  }
});
