import test from 'node:test';
import assert from 'node:assert/strict';
import { conversationSearchPageSize, searchConversations } from '../src/lib/conversationSearch.ts';

const defaults = {
  filter: '',
  offset: 0,
  projectId: 'project-a',
  all: true,
  signal: new AbortController().signal,
};

test('归档和回收站的空搜索、关键词及后续页始终使用各自范围', async () => {
  for (const view of ['archived', 'deleted']) {
    for (const filter of ['', '相同关键词']) {
      const calls = [];
      const request = async (path, options, projectId) => {
        calls.push({ url: new URL(path, 'http://local.test'), options, projectId });
        return Array.from({ length: conversationSearchPageSize }, (_, id) => ({ id }));
      };
      const result = await searchConversations(request, { ...defaults, view, filter, offset: 50 });
      assert.equal(calls.length, 1);
      assert.equal(calls[0].url.pathname, '/projects/search-threads');
      assert.equal(calls[0].url.searchParams.get('view'), view);
      assert.equal(calls[0].url.searchParams.get('query'), filter);
      assert.equal(calls[0].url.searchParams.get('offset'), '50');
      assert.equal(calls[0].url.searchParams.has('project_id'), false);
      assert.equal(calls[0].options.signal, defaults.signal);
      assert.equal(result.hasMore, true);
    }
  }
});

test('当前项目筛选只能缩小归档或回收站范围，空结果不再请求其他状态', async () => {
  for (const view of ['archived', 'deleted']) {
    const urls = [];
    const request = async (path) => {
      urls.push(new URL(path, 'http://local.test'));
      return [];
    };
    const result = await searchConversations(request, { ...defaults, view, all: false });
    assert.equal(urls.length, 1);
    assert.equal(urls[0].searchParams.get('view'), view);
    assert.equal(urls[0].searchParams.get('project_id'), defaults.projectId);
    assert.deepEqual(result, { rows: [], hasMore: false });
  }
});

test('最近页保留原搜索行为，归档和删除查询不会混入最近查询', async () => {
  for (const filter of ['', '关键词']) {
    const calls = [];
    const result = await searchConversations(
      async (path) => {
        const url = new URL(path, 'http://local.test');
        calls.push(url);
        return [{ id: url.searchParams.get('state') }];
      },
      { ...defaults, view: 'active', all: false, filter },
    );
    assert.deepEqual(
      result.rows.map((row) => row.id),
      filter ? ['active', 'archived'] : ['active'],
    );
    assert.ok(calls.every((url) => url.pathname === '/threads' && !url.searchParams.has('view')));
    assert.equal(result.hasMore, false);
  }
});
