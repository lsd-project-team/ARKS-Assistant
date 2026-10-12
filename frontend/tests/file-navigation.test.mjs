import { test } from 'node:test';
import assert from 'node:assert/strict';
import { tabLabel } from '../src/lib/fileNavigation.ts';
import { markdownSourceRange, resolveMarkdownLink } from '../src/lib/markdownSelection.ts';

test('同名标签使用足够的父目录区分，而普通标签保持简短', () => {
  const paths = ['src/A/Views/Main.cs', 'src/B/Views/Main.cs', 'App.cs'];
  assert.equal(tabLabel(paths[0], paths), 'A/Views/Main.cs');
  assert.equal(tabLabel(paths[1], paths), 'B/Views/Main.cs');
  assert.equal(tabLabel('App.cs', paths), 'App.cs');
});

test('Markdown 预览引用来自原文，保留中文、CRLF 和格式边界', () => {
  const source = {
    path: 'README.md',
    content: '# 标题\r\n\r\n这是 **重要** 的内容。\r\n',
    version: 'snapshot',
  };
  const start = source.content.indexOf('这是');
  const precise = markdownSourceRange(source, start, source.content.length, '重要');
  assert.equal(precise.content, '重要');
  assert.equal(precise.start_line, 3);
  assert.equal(precise.start_column, 6);
  const formatted = markdownSourceRange(source, start, source.content.length, '这是 重要 的内容。');
  assert.equal(formatted.content, '这是 **重要** 的内容。\r\n');
  assert.equal(formatted.version, 'snapshot');
  const repeated = { ...source, content: '文本重复，文本再次出现。' };
  assert.equal(
    markdownSourceRange(repeated, 0, repeated.content.length, '文本').content,
    repeated.content,
  );
});

test('Markdown 内部链接可解析中文和父目录，越界与外部链接不会进入源码路径', () => {
  assert.deepEqual(resolveMarkdownLink('docs/README.md', '../src/%E4%B8%AD%E6%96%87.cs'), {
    path: 'src/中文.cs',
    hash: '',
  });
  assert.deepEqual(resolveMarkdownLink('docs/README.md', '#启动'), {
    path: 'docs/README.md',
    hash: '启动',
  });
  assert.equal(resolveMarkdownLink('docs/README.md', '../../secret'), null);
  assert.equal(resolveMarkdownLink('docs/README.md', 'https://example.com'), null);
  assert.equal(resolveMarkdownLink('docs/README.md', 'javascript:alert(1)'), null);
  assert.equal(resolveMarkdownLink('docs/README.md', '%ZZ.cs'), null);
});
