import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { build } from 'esbuild';

const result = await build({
  entryPoints: [
    fileURLToPath(
      new URL('../../src/features/settings/components/McpSettingsPanel.tsx', import.meta.url),
    ),
  ],
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
  jsx: 'automatic',
});
const compiled = { exports: {} };
new Function('require', 'module', 'exports', result.outputFiles[0].text)(
  createRequire(import.meta.url),
  compiled,
  compiled.exports,
);
const { McpSettingsPanel } = compiled.exports;
const server = {
  id: 'test-service',
  name: '测试知识服务',
  enabled: false,
  transport: 'streamable_http',
  url: 'https://test.invalid/mcp',
  command: '',
  args: [],
  headers: {},
  env: {},
};

function render(servers, probes = {}) {
  return renderToStaticMarkup(
    createElement(McpSettingsPanel, {
      settings: { mcp_servers: servers },
      probes,
      busy: false,
      onChange() {},
      onProbe() {},
      onAdvancedDirty() {},
    }),
  );
}

test('未配置 MCP 服务时可以打开设置，保留新增入口与高级配置', () => {
  const html = render([]);
  assert.match(html, /新增 MCP 服务/);
  assert.match(html, /高级 JSON 配置/);
  assert.doesNotMatch(html, /测试此服务/);
});

test('只展示与当前 MCP 配置匹配的检测结果', () => {
  const probe = {
    signature: JSON.stringify(server),
    result: { name: '已验证的服务', tools: [] },
  };
  assert.match(render([server], { [server.id]: probe }), /已验证的服务/);
  assert.doesNotMatch(
    render([{ ...server, url: 'https://changed.invalid/mcp' }], { [server.id]: probe }),
    /已验证的服务/,
  );
});
