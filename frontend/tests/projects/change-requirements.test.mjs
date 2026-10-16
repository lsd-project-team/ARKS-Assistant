import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const bundled = await build({
  stdin: {
    contents:
      "export { ChangeRequirements, writeChangeRequirements } from './src/features/projects/components/ChangeRequirements';",
    resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
    loader: 'tsx',
  },
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
  jsx: 'automatic',
  plugins: [
    {
      name: 'requirements-api',
      setup(builder) {
        builder.onResolve({ filter: /\/api\/client$|\/hooks\/useProjectApi$/ }, ({ path }) => ({
          path: path.endsWith('useProjectApi') ? 'project' : 'api',
          namespace: 'requirements-boundary',
        }));
        builder.onLoad({ filter: /.*/, namespace: 'requirements-boundary' }, ({ path }) => ({
          contents:
            path === 'api'
              ? 'export const jsonBody=JSON.stringify;'
              : 'export const useProjectApi=()=>async()=>{throw new Error("SSR不能发出请求")};',
          loader: 'js',
        }));
      },
    },
  ],
});
const module = { exports: {} };
new Function('require', 'module', 'exports', bundled.outputFiles[0].text)(
  createRequire(import.meta.url),
  module,
  module.exports,
);
const { ChangeRequirements, writeChangeRequirements } = module.exports;
const base = {
  id: 'copy-a',
  title: '旧的修改',
  goal: '补齐现有副本验收',
  status: 'editing',
  files_changed: 1,
  change_version: 'a'.repeat(64),
  requirements_version: 'b'.repeat(64),
};
const draft = {
  title: ' 增加校验 ',
  goal: ' 返回值符合要求 ',
  criteria: '正常结果通过\n异常路径有诊断',
  constraints: '原件只读',
  paths: 'src/**\ntests\\**',
};

function render(change = base, disabled = false) {
  return renderToStaticMarkup(
    createElement(ChangeRequirements, {
      projectId: 'project-a',
      change,
      disabled,
      onSaved: () => {},
    }),
  );
}

test('旧副本可补充验收且展示重新验证提示，原需求作为表单初值', () => {
  const html = render();
  assert.match(html, /编辑需求约定/);
  assert.match(html, /旧的修改/);
  assert.match(html, /补齐现有副本验收/);
  assert.match(html, /保存后旧验证和审核失效/);
  assert.match(html, /<button[^>]*type="submit"[^>]*>保存需求约定/);
  assert.doesNotMatch(html, /<button[^>]*disabled=""[^>]*>保存需求约定/);
  assert.match(
    render({
      ...base,
      acceptance_criteria: ['已约定结果'],
      constraints: '禁止外部副作用',
      allowed_paths: ['src/**'],
    }),
    /已约定结果.*禁止外部副作用.*src\/\*\*/s,
  );
});

test('归档或忙碌和文件草稿未保存可禁用，验证中/已丢弃/缺版本不能保存', () => {
  assert.match(render(base, true), /<button[^>]*disabled=""[^>]*>保存需求约定/);
  for (const status of ['verifying', 'discarded'])
    assert.match(render({ ...base, status }), /<button[^>]*disabled=""[^>]*>保存需求约定/);
  const html = render({ ...base, requirements_version: undefined });
  assert.match(html, /缺少版本信息/);
  assert.match(html, /<button[^>]*disabled=""[^>]*>保存需求约定/);
});

test('保存固定发起项目、修改版本和需求版本，复用范围校验与独立字段', async () => {
  const calls = [];
  const response = { ...base, status: 'editing', latest_verification: undefined, review: null };
  const api = async (path, options, projectId) => {
    calls.push({ path, options, projectId });
    return response;
  };
  assert.equal(
    await writeChangeRequirements(api, 'project-old', { ...base, id: 'copy/a' }, draft),
    response,
  );
  assert.deepEqual(calls, [
    {
      path: '/code-changes/copy%2Fa/requirements',
      options: {
        method: 'PUT',
        body: JSON.stringify({
          title: '增加校验',
          goal: '返回值符合要求',
          acceptance_criteria: ['正常结果通过', '异常路径有诊断'],
          constraints: '原件只读',
          allowed_paths: ['src/**', 'tests/**'],
          change_version: base.change_version,
          requirements_version: base.requirements_version,
        }),
      },
      projectId: 'project-old',
    },
  ]);
});

test('缺版本、空白目标和越界路径拒绝发送，后端冲突保留为错误', async () => {
  let calls = 0;
  const api = async () => {
    calls++;
    throw new Error('需求版本冲突，请刷新');
  };
  await assert.rejects(
    writeChangeRequirements(api, 'p', { ...base, change_version: undefined }, draft),
    /缺少版本/,
  );
  await assert.rejects(
    writeChangeRequirements(api, 'p', base, { ...draft, goal: ' ' }),
    /名称和目标/,
  );
  await assert.rejects(
    writeChangeRequirements(api, 'p', base, { ...draft, paths: '../**' }),
    /相对路径/,
  );
  assert.equal(calls, 0);
  await assert.rejects(writeChangeRequirements(api, 'p', base, draft), /需求版本冲突/);
  assert.equal(calls, 1);
});
