import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  findSourceMatches,
  indexSource,
  sourcePointAtOffset,
  sourceSelection,
} from '../../src/features/source_reader/lib/sourceSelection.ts';

function file(content) {
  return { path: 'Example.cs', content, version: 'test-version', line_count: 3 };
}

test('跨行引用保留 CRLF、Tab、中文和准确的起止列号', () => {
  const source = file('\tvar 名称 = "值";\r\n\tRun(名称);\r\n');
  const selection = sourceSelection(
    source,
    indexSource(source.content),
    { line: 1, column: 2 },
    { line: 2, column: 7 },
  );
  assert.deepEqual(selection, {
    path: 'Example.cs',
    version: 'test-version',
    start_line: 1,
    start_column: 2,
    end_line: 2,
    end_column: 7,
    content: 'var 名称 = "值";\r\n\tRun(名',
  });
});

test('反向选区与正向选区得到相同引用，代理对按 UTF-16 列计数', () => {
  const source = file('a😀b\nsecond');
  const index = indexSource(source.content);
  const first = { line: 1, column: 2 };
  const last = { line: 1, column: 4 };
  assert.equal(sourceSelection(source, index, first, last).content, '😀');
  assert.deepEqual(
    sourceSelection(source, index, first, last),
    sourceSelection(source, index, last, first),
  );
});

test('混合行尾、空行和文件末尾仍保持源码偏移', () => {
  const source = file('one\r\n\ntwo\rlast');
  const index = indexSource(source.content);
  assert.deepEqual(index.starts, [0, 5, 6, 10]);
  assert.equal(
    sourceSelection(source, index, { line: 2, column: 1 }, { line: 4, column: 5 }).content,
    '\ntwo\rlast',
  );
});

test('空选区和越界坐标不能生成源码引用', () => {
  const source = file('line');
  const index = indexSource(source.content);
  const first = { line: 1, column: 1 };
  for (const last of [
    first,
    { line: 0, column: 1 },
    { line: 2, column: 1 },
    { line: 1, column: 8 },
  ]) {
    assert.equal(sourceSelection(source, index, first, last), null);
  }
});

test('文件内查找按原文偏移匹配，符号是字面量并支持大小写', () => {
  const content = 'Call(x);\r\ncall(x);\nCALL(y);';
  const matches = findSourceMatches(content, 'Call(x)');
  assert.deepEqual(matches, [
    { start: 0, end: 7 },
    { start: 10, end: 17 },
  ]);
  const index = indexSource(content);
  assert.deepEqual(sourcePointAtOffset(index, matches[1].start), { line: 2, column: 1 });
  assert.deepEqual(sourcePointAtOffset(index, matches[1].end), { line: 2, column: 8 });
  assert.deepEqual(findSourceMatches(content, ''), []);
  assert.deepEqual(findSourceMatches(content, '.*'), []);
});
