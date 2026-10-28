import test from 'node:test';
import assert from 'node:assert/strict';
import { scopedApiUrl } from '../../src/shared/api/apiRoutes.ts';

test('对话、源码和记忆始终带所属项目，没有当前项目时进入独立工作区', () => {
  for (const path of [
    '/threads',
    '/threads/id/runs',
    '/file?path=Program.cs',
    '/memories',
    '/source-options',
  ]) {
    assert.equal(scopedApiUrl(path, 'private-a'), `/api/p/private-a${path}`);
    assert.equal(scopedApiUrl(path, ''), `/api/p/independent${path}`);
    assert.equal(scopedApiUrl(path, 'independent'), `/api/p/independent${path}`);
  }
});

test('全局配置与管理路径不重复挂载到项目，匹配要求完整的路径段', () => {
  for (const path of [
    '/projects',
    '/sources/id/file',
    '/health',
    '/settings',
    '/model-preference',
    '/mcp/probe',
    '/backup',
    '/storage?scope=all',
    '/data/preview',
    '/handover/records/shared?version=2',
    '/auth/session',
    '/admin/questions',
    '/usage/heartbeat',
  ]) {
    assert.equal(scopedApiUrl(path, 'private-a'), `/api${path}`);
  }
  assert.equal(scopedApiUrl('/settings-extra', 'private-a'), '/api/p/private-a/settings-extra');
});
