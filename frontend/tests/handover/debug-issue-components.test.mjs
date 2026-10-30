import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const bundled = await build({
  stdin: {
    contents: `export { DebugIssuePage } from './src/features/handover/debug_issues/DebugIssuePage';
      export { DebugIssueDetail } from './src/features/handover/debug_issues/DebugIssueDetail';`,
    resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
    loader: 'tsx',
  },
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
  jsx: 'automatic',
  loader: { '.css': 'empty' },
  plugins: [
    {
      name: 'debug-display-boundaries',
      setup(builder) {
        builder.onResolve({ filter: /\/(AuthContext|HandoverModal)$/ }, ({ path }) => ({
          path: path.endsWith('/AuthContext') ? 'auth' : 'modal',
          namespace: 'debug-boundary',
        }));
        builder.onLoad({ filter: /.*/, namespace: 'debug-boundary' }, ({ path }) => ({
          resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
          contents:
            path === 'auth'
              ? 'export const useAuth = () => ({session: {user: {display_name: "测试用户"}}});'
              : 'import {createElement} from "react"; export const HandoverModal = (props) => createElement("article", null, props.title, props.children);',
        }));
      },
    },
  ],
});
const bundledModule = { exports: {} };
new Function('require', 'module', 'exports', bundled.outputFiles[0].text)(
  createRequire(import.meta.url),
  bundledModule,
  bundledModule.exports,
);
const { DebugIssuePage, DebugIssueDetail } = bundledModule.exports;

test('当前列表与固定版本详情隐藏来源信息，仍显示记录人、日期和完整业务原文', () => {
  const row = {
    id: 'test-issue',
    kind: 'debug_issue',
    title: '力控经验',
    state: 'draft',
    version: 3,
    updated_at: '2026-10-28',
    payload: {
      origin: 'import',
      record_type: 'experience',
      resolution_status: 'recorded',
      problem: '正文完整保留',
      solution: '处理过程保留',
      recorded_by: '原作者',
      recorded_at: '10月27日',
      keywords: ['EXP-099', '力控'],
      notes: '来源编号：EXP-099\n原始来源：交接原件.xlsx\n实际结果保留',
      original_text: JSON.stringify({
        id: 'EXP-099',
        source: '交接原件.xlsx',
        answer: '原始回答保留',
        status: '待验证',
      }),
    },
  };
  const page = renderToStaticMarkup(createElement(DebugIssuePage, { rows: [row], onOpen() {} }));
  const detail = renderToStaticMarkup(
    createElement(DebugIssueDetail, {
      row,
      version: 3,
      client: {},
      onEdit() {},
      onChanged() {},
      onOpen() {},
      onClose() {},
    }),
  );
  for (const markup of [page, detail]) {
    for (const value of [
      'EXP-099',
      '交接原件.xlsx',
      '来源编号',
      '原始来源',
      '手动录入',
      'AI 整理',
      'v3',
      '记录ID',
      '归档状态',
      '原图数',
      '详情起始行',
    ]) {
      assert.ok(!markup.includes(value), value);
    }
    for (const value of ['正文完整保留', '处理过程保留', '原作者', '10月27日', '力控']) {
      assert.ok(markup.includes(value), value);
    }
  }
  for (const value of ['实际结果保留', '原始回答保留', '待验证', '查看最新记录']) {
    assert.ok(detail.includes(value), value);
  }
  const primary = detail.split('<details')[0];
  for (const label of ['标题', '适用条件', '内容说明', '处理方法', '结果记录', '注意事项']) {
    assert.ok(primary.includes(`<dt>${label}</dt>`), label);
  }
  assert.ok(!primary.includes('<dt>关键词</dt>'));
  const archived = renderToStaticMarkup(
    createElement(DebugIssuePage, {
      rows: [{ ...row, state: 'archived' }],
      onOpen() {},
    }),
  );
  assert.ok(archived.includes('已记录'));
  assert.ok(!archived.includes('已归档'));
});
