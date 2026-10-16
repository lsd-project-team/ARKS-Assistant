import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { once } from 'node:events';
import { knowledgePath, knowledgeMiddleware } from '../../scripts/knowledge/resources.mjs';

test('知识资源解析保留公开地址，并拒绝越界路径', () => {
  assert.match(knowledgePath('/archify/example.html'), /flows[\\/]example\.html$/);
  assert.match(knowledgePath('/engineering/manifest.json'), /modules[\\/]manifest\.json$/);
  for (const path of [
    '/archify/../private.json',
    '/archify/%2e%2e/private.json',
    '/unknown/file',
  ]) {
    assert.throws(() => knowledgePath(path));
  }
});

test('开发资源服务返回原始图谱和索引，未知资源与业务请求分别处理', async (t) => {
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
  for (const path of [
    '/archify/machine-start-readiness-workflow.html',
    '/engineering/manifest.json',
  ]) {
    const response = await fetch(base + path);
    assert.equal(response.status, 200);
    assert.deepEqual(
      Buffer.from(await response.arrayBuffer()),
      await readFile(knowledgePath(path)),
    );
  }
  assert.equal((await fetch(base + '/archify/nonexistent.html')).status, 404);
  assert.equal((await fetch(base + '/api/health')).status, 418);
});
