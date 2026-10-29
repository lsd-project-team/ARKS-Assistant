import test from 'node:test';
import assert from 'node:assert/strict';
import {
  changeCanEdit,
  changeCanVerify,
  changeCanRecordExperience,
  normalizeChangePath,
  filePatchRequest,
  parseCommandArgv,
  codeWorkError,
  contentHash,
} from '../../src/features/projects/lib/codeWorkRules.ts';
import { boundProjectApi } from '../../src/features/projects/lib/projectRequest.ts';
import { scopedApiUrl } from '../../src/shared/api/apiRoutes.ts';

test('运行中与丢弃的副本禁止编辑和再启动验证，未保存内容也阻止验证', () => {
  for (const status of ['verifying', 'discarded']) {
    assert.equal(changeCanEdit({ status }), false);
    assert.equal(changeCanVerify({ status }, 'configured'), false);
  }
  assert.equal(changeCanVerify({ status: 'editing' }, 'configured'), true);
  assert.equal(changeCanVerify({ status: 'editing' }, ''), false);
  assert.equal(changeCanVerify({ status: 'editing' }, 'configured', true), false);
});

test('只有与当前修改关联的有效通过结果才开放经验保存', () => {
  const passed = {
    status: 'passed',
    latest_verification: { status: 'passed', change_version: 'hash-a', stale: false },
  };
  assert.equal(changeCanRecordExperience(passed), true);
  assert.equal(changeCanRecordExperience(passed, true), false);
  assert.equal(changeCanRecordExperience({ ...passed, status: 'editing' }), false);
  assert.equal(
    changeCanRecordExperience({
      ...passed,
      latest_verification: { ...passed.latest_verification, stale: true },
    }),
    false,
  );
  assert.equal(
    changeCanRecordExperience({
      ...passed,
      latest_verification: { ...passed.latest_verification, status: 'failed' },
    }),
    false,
  );
  assert.equal(
    changeCanRecordExperience({ ...passed, latest_verification: { status: 'passed' } }),
    false,
  );
  assert.equal(changeCanRecordExperience({ ...passed, latest_verification: null }), false);
});

test('副本路径接受目录相对路径，拒绝越界、绝对路径与空片段', () => {
  assert.equal(normalizeChangePath(' src\\中文.cs '), 'src/中文.cs');
  for (const path of [
    '',
    '../x',
    'src/../x',
    './x',
    '/etc/passwd',
    'C:\\x',
    'C:x',
    '\\\\server\\x',
    'a//b',
    'a/./b',
    'a\0b',
  ])
    assert.throws(() => normalizeChangePath(path), /相对文件路径/, path);
});

test('保存补丁固定读取时的路径、完整旧正文和版本，保留换行和空文件', () => {
  const file = {
    path: 'src/A.cs',
    content: 'a\r\nb\r\n',
    version: 'read-hash',
    requirements_version: 'req-hash',
  };
  assert.deepEqual(filePatchRequest(file, 'a\r\nc\r\n'), {
    path: 'src/A.cs',
    before: 'a\r\nb\r\n',
    after: 'a\r\nc\r\n',
    version: 'read-hash',
    requirements_version: 'req-hash',
  });
  assert.equal(file.content, 'a\r\nb\r\n');
  assert.deepEqual(
    filePatchRequest(
      { path: 'empty.txt', content: '', version: 'empty-hash', requirements_version: 'req-hash' },
      'new',
    ),
    {
      path: 'empty.txt',
      before: '',
      after: 'new',
      version: 'empty-hash',
      requirements_version: 'req-hash',
    },
  );
  assert.throws(() => filePatchRequest({ ...file, version: '' }, 'x'), /重新读取/);
  assert.deepEqual(
    filePatchRequest(
      {
        path: 'new.txt',
        content: '',
        version: '',
        exists: false,
        requirements_version: 'req-hash',
      },
      'new',
    ),
    { path: 'new.txt', before: '', after: 'new', version: '', requirements_version: 'req-hash' },
  );
  assert.throws(
    () =>
      filePatchRequest({ path: 'new.txt', content: '旧正文', version: '', exists: false }, 'new'),
    /重新读取/,
  );
  assert.throws(
    () => filePatchRequest({ ...file, requirements_version: undefined }, 'new'),
    /缺少需求版本/,
  );
});

test('管理员命令配置保留每个原始参数，不拆分、不拼接shell命令', () => {
  assert.deepEqual(parseCommandArgv('["python", "-m", "pytest", "path with spaces", " "]'), [
    'python',
    '-m',
    'pytest',
    'path with spaces',
    ' ',
  ]);
  for (const value of [
    'python -m pytest',
    '"python"',
    '{}',
    '[]',
    '[""]',
    '["  ", "x"]',
    '["python", 3]',
    '["python", null]',
    '["python", ""]',
    '["a\\u0000b"]',
  ])
    assert.throws(() => parseCommandArgv(value), /JSON|非空/);
  assert.throws(
    () => parseCommandArgv(JSON.stringify(Array.from({ length: 101 }, () => 'x'))),
    /最多 100/,
  );
  assert.throws(() => parseCommandArgv(JSON.stringify(['python', 'a'.repeat(20001)])), /非空/);
});

test('409冲突提示保留草稿并要求核对，不掩盖后端具体原因', () => {
  const reason = Object.assign(new Error('基线文件已改变'), { status: 409 });
  assert.match(codeWorkError(reason).message, /版本冲突.*基线文件已改变.*编辑内容已保留/);
  const forbidden = Object.assign(new Error('没有配置权限'), { status: 403 });
  assert.equal(codeWorkError(forbidden), forbidden);
  for (const message of ['验证程序不存在', '请填写实际验证结果', '验证参数不能为空']) {
    const ordinary = Object.assign(new Error(message), { status: 409 });
    assert.equal(codeWorkError(ordinary), ordinary);
  }
});

test('正文hash基于实际UTF-8字节，改行尾也改变hash', async () => {
  assert.equal(
    await contentHash(''),
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  );
  assert.equal(
    await contentHash('abc'),
    'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
  );
  assert.notEqual(await contentHash('a\n'), await contentHash('a\r\n'));
});

test('阅读、修改与命令配置请求在等待和切换项目时保持所属项目', async () => {
  const calls = [];
  const original = boundProjectApi('project-a', async (path, options, projectId) => {
    await Promise.resolve();
    calls.push({ url: scopedApiUrl(path, projectId), method: options?.method || 'GET' });
    return {};
  });
  await Promise.all([
    original('/code-changes/id/verify', { method: 'POST' }),
    original('/code-changes/id/file?path=src%2FA.cs'),
    original('/code-changes/profiles', { method: 'POST' }),
    original('/code-changes/id/experience', { method: 'POST' }),
  ]);
  assert.deepEqual(
    calls.map((call) => call.url),
    [
      '/api/p/project-a/code-changes/id/verify',
      '/api/p/project-a/code-changes/id/file?path=src%2FA.cs',
      '/api/p/project-a/code-changes/profiles',
      '/api/p/project-a/code-changes/id/experience',
    ],
  );
});
