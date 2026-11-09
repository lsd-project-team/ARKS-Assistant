import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveSourceReference } from '../../src/features/chat/rich/sourceSearch.ts';

const source = { path: 'Dir/SignalPool.cs', start_line: 136, end_line: 152 };
const hit = { path: source.path, line: 136, text: 'public Signal Ready = new Signal();' };
const tool = (matches = [hit], extra = {}) => ({
  id: 'search',
  name: 'search_source',
  status: 'success',
  result: JSON.stringify({ matches, truncated: false }),
  ...extra,
});
const read = {
  ...source,
  start_line: 1,
  end_line: 300,
  version: 'v1',
  source_workspace_id: 'main',
  current_status: 'match',
};

test('真实搜索命中可作为当前源码引用，不把引用范围登记为完整已读或伪造版本', () => {
  for (const [path, start, end, line] of [
    [source.path, 136, 152, 136],
    ['Dir/Machine.Operate.cs', 136, 158, 158],
  ]) {
    const pointer = { path, start_line: start, end_line: end };
    const tools = [tool([{ path, line, text: 'Signal.ReSet();' }])];
    const before = JSON.stringify({ pointer, tools });
    const result = resolveSourceReference(pointer, [], tools, 'main');
    assert.equal(result.reason, undefined);
    assert.equal(result.kind, 'search');
    assert.deepEqual(result.evidence, {
      path,
      start_line: line,
      end_line: line,
      source_workspace_id: 'main',
    });
    assert.equal(result.evidence.version, undefined);
    assert.equal(JSON.stringify({ pointer, tools }), before);
  }
});

test('只接受本轮成功 search_source 的实际 matches，不把参数、其他工具或失败结果当成证据', () => {
  for (const invalid of [
    tool([], { arguments: { matches: [hit] } }),
    tool([hit], { name: 'find_source_files' }),
    tool([hit], { status: 'error' }),
    tool([hit], { status: undefined }),
    tool([hit], { execution_status: 'skipped' }),
    tool([hit], { result: JSON.stringify({ query: hit.path }) }),
  ])
    assert.ok(resolveSourceReference(source, [], [invalid], 'main').reason);
});

test('匹配完整路径和引用范围内的命中行，不猜同名文件或相邻范围', () => {
  for (const mismatched of [
    { ...hit, path: 'Other/SignalPool.cs' },
    { ...hit, path: 'SignalPool.cs' },
    { ...hit, line: 135 },
    { ...hit, line: 153 },
  ])
    assert.ok(resolveSourceReference(source, [], [tool([mismatched])], 'main').reason);
  assert.equal(
    resolveSourceReference(source, [], [tool([{ ...hit, line: 152 }])], 'main').reason,
    undefined,
  );
});

test('损坏或不完整搜索 JSON、错误字段和非法行号不会启用引用', () => {
  for (const result of [
    '{坏JSON',
    'null',
    '[]',
    '{"matches":{}}',
    '{"matches":[',
    JSON.stringify({
      matches: [
        null,
        1,
        {},
        { ...hit, line: '136' },
        { ...hit, line: 136.5 },
        { ...hit, line: -1 },
        { ...hit, line: Number.MAX_SAFE_INTEGER + 1 },
        { ...hit, text: 23 },
        { ...hit, text: ' ' },
      ],
    }),
  ])
    assert.ok(resolveSourceReference(source, [], [tool([], { result })], 'main').reason);
  for (const pointer of [
    { ...source, start_line: 0 },
    { ...source, end_line: 1 },
    { ...source, end_line: Infinity },
    { ...source, start_line: NaN },
  ])
    assert.ok(resolveSourceReference(pointer, [], [tool()], 'main').reason);
});

test('路径和来源身份必须一致，附加目录按显式身份定位', () => {
  for (const path of [
    '../SignalPool.cs',
    'Dir/../SignalPool.cs',
    '/Dir/SignalPool.cs',
    'C:\\Dir\\SignalPool.cs',
    'Dir\0/SignalPool.cs',
  ])
    assert.ok(
      resolveSourceReference({ ...source, path }, [], [tool([{ ...hit, path }])], 'main').reason,
    );
  assert.ok(
    resolveSourceReference({ ...source, source_workspace_id: 'other' }, [], [tool()], 'main')
      .reason,
  );
  assert.ok(
    resolveSourceReference({ ...source, source_workspace_id: 'other' }, [], [tool()]).reason,
  );
  const path = '@sources/library/Dir/SignalPool.cs';
  const tools = [tool([{ ...hit, path }])];
  assert.ok(
    resolveSourceReference({ ...source, path, source_workspace_id: 'other' }, [], tools, 'main')
      .reason,
  );
  const result = resolveSourceReference(
    { ...source, path, source_workspace_id: 'library' },
    [],
    tools,
    'main',
  );
  assert.equal(result.reason, undefined);
  assert.equal(result.evidence.source_workspace_id, 'library');
});

test('已读证据优先，搜索不能绕过显式版本、版本变化、不可读或多个版本/目录冲突', () => {
  const resolved = resolveSourceReference(source, [read], [tool()], 'main');
  assert.equal(resolved.kind, 'read');
  assert.equal(resolved.evidence, read);
  assert.equal(resolved.evidence.version, 'v1');
  assert.ok(resolveSourceReference({ ...source, version: 'v0' }, [], [tool()], 'main').reason);
  assert.ok(resolveSourceReference({ ...source, version: 'v0' }, [read], [tool()], 'main').reason);
  for (const status of ['changed', 'unavailable', undefined])
    assert.ok(
      resolveSourceReference(source, [{ ...read, current_status: status }], [tool()], 'main')
        .reason,
    );
  assert.ok(
    resolveSourceReference(source, [read, { ...read, version: 'v2' }], [tool()], 'main').reason,
  );
  assert.ok(
    resolveSourceReference(source, [read, { ...read, source_workspace_id: 'other' }], [tool()])
      .reason,
  );
  assert.ok(
    resolveSourceReference(
      source,
      [{ ...read, start_line: 1, end_line: 20, current_status: 'changed' }],
      [tool()],
      'main',
    ).reason,
  );
});

test('实际返回的截断搜索结果仍可定位，未返回的范围不推断为命中', () => {
  const tools = [tool([hit], { result: JSON.stringify({ matches: [hit], truncated: true }) })];
  assert.equal(resolveSourceReference(source, [], tools, 'main').reason, undefined);
  assert.ok(
    resolveSourceReference({ ...source, start_line: 200, end_line: 230 }, [], tools, 'main').reason,
  );
});
