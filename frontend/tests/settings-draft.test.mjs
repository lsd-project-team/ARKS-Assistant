import test from 'node:test';
import assert from 'node:assert/strict';
import {
  emptyModel,
  normalizeSettings,
  settingsPayload,
  validateSettings,
  parseMcpJson,
} from '../src/lib/settingsDraft.ts';
import { blankMemory, memorySignature, validateMemory } from '../src/lib/memoryDraft.ts';

const settings = () =>
  normalizeSettings({
    model: emptyModel(),
    mcp_servers: [],
    auto_memory: true,
    deepwiki_repo: '',
    version: 'version',
  });

test('旧配置归一化，写入切换时省略旧模型镜像和检测缓存', () => {
  const value = settings();
  value.model_profiles.push({
    id: 'second',
    name: '备用',
    config: { ...emptyModel(), model: '备用模型' },
    capabilities: { ok: true },
  });
  value.active_profile_id = 'second';
  const payload = settingsPayload(value);
  assert.equal(payload.active_profile_id, 'second');
  assert.equal(payload.model_profiles[1].config.model, '备用模型');
  assert.equal('model' in payload, false);
  assert.equal('version' in payload, false);
  assert.equal('capabilities' in payload.model_profiles[1], false);
  assert.equal(validateSettings(value).length, 0);
});

test('配置验证拦截错误地址、无效 ID、容量和不存在的当前模型', () => {
  const value = settings();
  value.model_profiles[0] = {
    id: 'bad id',
    name: '  ',
    config: {
      ...emptyModel(),
      base_url: 'https://name:secret@example.com',
      context_tokens: 2048,
      output_tokens: 2048,
      temperature: NaN,
    },
  };
  value.active_profile_id = 'missing';
  const errors = validateSettings(value).join(' ');
  assert.match(errors, /名称不能为空/);
  assert.match(errors, /ID 无效/);
  assert.match(errors, /地址/);
  assert.match(errors, /预留/);
  assert.match(errors, /温度/);
  assert.match(errors, /当前模型配置不存在/);
});

test('高级 MCP JSON 类型检查，并保留凭据掩码和未启用草稿', () => {
  const server = parseMcpJson(
    '[{"id":"wiki","name":"Wiki","enabled":false,"headers":{"Authorization":"••••••"}}]',
  )[0];
  assert.equal(server.transport, 'streamable_http');
  assert.deepEqual(server.args, []);
  assert.equal(server.headers.Authorization, '••••••');
  const value = { ...settings(), mcp_servers: [server] };
  assert.deepEqual(validateSettings(value), []);
  assert.throws(() => parseMcpJson('{}'), /对象数组/);
  assert.throws(() => parseMcpJson('[{"id":"x","name":"x","headers":null}]'), /键值对象/);
  assert.throws(() => parseMcpJson('[{"id":"x","name":"x","args":[1]}]'), /字符串数组/);
  assert.throws(() => parseMcpJson('[{"id":"x","name":"x","enabled":"false"}]'), /布尔值/);
  server.enabled = true;
  assert.match(validateSettings(value).join(' '), /填写 MCP 地址/);
  server.url = 'https://wiki.example/mcp';
  server.headers = { 'Bad Header': 'secret\nvalue' };
  assert.match(validateSettings(value).join(' '), /名称无效/);
  assert.match(validateSettings(value).join(' '), /不能包含换行/);
});

test('记忆草稿验证中文名称、空白内容和保护判断', () => {
  const draft = { ...blankMemory(), name: '项目结构.md', content: '按中文回复' };
  assert.deepEqual(validateMemory(draft), []);
  assert.notEqual(memorySignature(draft), memorySignature({ ...draft, content: '修改' }));
  assert.equal(memorySignature(draft), memorySignature({ ...draft, updated_at: 123 }));
  assert.match(validateMemory({ ...draft, name: '../secret.md' }).join(' '), /名称需为/);
  assert.match(validateMemory({ ...draft, content: ' \n ' }).join(' '), /内容不能为空/);
});
