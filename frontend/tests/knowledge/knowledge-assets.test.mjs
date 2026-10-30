import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { once } from 'node:events';
import {
  knowledgePath,
  knowledgeMiddleware,
  readingDiagram,
} from '../../scripts/knowledge/resources.mjs';

test('知识资源解析保留公开地址，并拒绝越界路径', () => {
  assert.match(knowledgePath('/archify/example.html'), /flows[\\/]example\.html$/);
  for (const path of [
    '/archify/../private.json',
    '/archify/%2e%2e/private.json',
    '/unknown/file',
    '/engineering/manifest.json',
  ]) {
    assert.throws(() => knowledgePath(path));
  }
});

test('开发资源服务返回阅读图谱，旧索引不再提供，未知资源与业务请求分别处理', async (t) => {
  const server = createServer((request, response) =>
    knowledgeMiddleware(request, response, () => {
      response.statusCode = 418;
      response.end('business route');
    }),
  );
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(() => {
    server.closeAllConnections();
    return new Promise((done) => server.close(done));
  });
  const base = `http://127.0.0.1:${server.address().port}`;
  for (const path of ['/archify/machine-start-readiness-workflow.html']) {
    const response = await fetch(base + path);
    assert.equal(response.status, 200);
    assert.deepEqual(
      Buffer.from(await response.arrayBuffer()),
      Buffer.from(readingDiagram(await readFile(knowledgePath(path), 'utf8'))),
    );
  }
  assert.equal((await fetch(base + '/archify/nonexistent.html')).status, 404);
  assert.equal((await fetch(base + '/api/health')).status, 418);
  assert.equal((await fetch(base + '/engineering/manifest.json')).status, 418);
});

test('图谱发布移除源码绑定和依据卡片，保留相邻流程卡片与节点交互', () => {
  const card = (title, body) =>
    `<div class="card"><div class="card-header"><div class="card-dot cyan"></div><h3>${title}</h3></div><ul><li>${body}</li></ul></div>`;
  const html = `<head></head><script id="archify-source-evidence-data" type="application/json">{"old":"snapshot"}</script>${card('运行条件', '业务条件')}${card('当前源码依据', 'old.cs')}${card('异常处理', '业务异常')}<g data-node-id="start"></g>`;
  const published = readingDiagram(html);
  assert.doesNotMatch(published, /archify-source-evidence-data|old.cs|snapshot|当前源码依据/);
  assert.match(published, /运行条件.*业务条件/);
  assert.match(published, /异常处理.*业务异常/);
  assert.match(published, /data-node-id="start"/);
  assert.match(published, /\.semantic-passport-evidence.*display:none!important/);
});
