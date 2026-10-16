import test from 'node:test';
import assert from 'node:assert/strict';
import {
  codeFileDraftKey,
  readCodeFileDraft,
  writeCodeFileDraft,
} from '../../src/features/projects/lib/codeFileDraft.ts';

const scope = { accountId: 'account-a', projectId: 'project-a', changeId: 'change-a' };
const value = {
  file: {
    path: 'src/A.cs',
    content: '旧正文\r\n',
    version: 'a'.repeat(64),
    requirements_version: 'b'.repeat(64),
    exists: true,
  },
  draft: '尚未保存\n',
};
function storage() {
  const map = new Map();
  return {
    getItem: (key) => map.get(key) ?? null,
    setItem: (key, item) => map.set(key, item),
    removeItem: (key) => map.delete(key),
  };
}

test('切走项目再返回恢复原文件基线与草稿，账号和副本分别隔离', () => {
  const saved = storage();
  assert.equal(writeCodeFileDraft(saved, scope, value), true);
  for (const other of [
    { ...scope, accountId: 'account-b' },
    { ...scope, projectId: 'project-b' },
    { ...scope, changeId: 'change-b' },
  ])
    assert.equal(readCodeFileDraft(saved, other), undefined);
  assert.deepEqual(readCodeFileDraft(saved, scope), value);
  assert.match(codeFileDraftKey(scope), /^trunk-workspace:account:account-a:code-work:/);
});

test('保存或显式放弃后删除暂存，恢复时不替换成服务器新版本', () => {
  const saved = storage();
  writeCodeFileDraft(saved, scope, value);
  assert.equal(readCodeFileDraft(saved, scope).file.version, 'a'.repeat(64));
  writeCodeFileDraft(saved, scope, { file: value.file, draft: value.file.content });
  assert.equal(readCodeFileDraft(saved, scope), undefined);
});

test('新文件不存在sentinel随草稿保存，不与已存在空文件混淆', () => {
  const saved = storage();
  const fresh = {
    file: { path: 'new.cs', content: '', version: '', exists: false },
    draft: '新正文',
  };
  writeCodeFileDraft(saved, scope, fresh);
  assert.deepEqual(readCodeFileDraft(saved, scope), fresh);
  saved.setItem(
    codeFileDraftKey(scope),
    JSON.stringify({ schema: 1, ...scope, ...fresh, file: { ...fresh.file, exists: true } }),
  );
  assert.equal(readCodeFileDraft(saved, scope), undefined);
});

test('禁止存储、损坏正文或身份不匹配不会误恢复，也不会使编辑崩溃', () => {
  const broken = {
    getItem: () => {
      throw new Error('blocked');
    },
    setItem: () => {
      throw new Error('quota');
    },
    removeItem: () => {},
  };
  assert.equal(readCodeFileDraft(broken, scope), undefined);
  assert.equal(writeCodeFileDraft(broken, scope, value), false);
  assert.equal(writeCodeFileDraft(undefined, scope, value), false);
  assert.equal(writeCodeFileDraft(storage(), { ...scope, accountId: '' }, value), false);
  const saved = storage();
  saved.setItem(codeFileDraftKey(scope), 'broken JSON');
  assert.equal(readCodeFileDraft(saved, scope), undefined);
  saved.setItem(
    codeFileDraftKey(scope),
    JSON.stringify({ schema: 1, ...scope, ...value, accountId: 'other' }),
  );
  assert.equal(readCodeFileDraft(saved, scope), undefined);
});
