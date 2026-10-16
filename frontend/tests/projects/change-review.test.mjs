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
      "export { ChangeDelivery, writeChangeReview } from './src/features/projects/components/ChangeDelivery';",
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
      name: 'review-boundaries',
      setup(builder) {
        builder.onResolve(
          { filter: /\/api\/client$|\/hooks\/useProjectApi$|^@tanstack\/react-query$/ },
          ({ path }) => ({ path, namespace: 'review-boundary' }),
        );
        builder.onLoad({ filter: /.*/, namespace: 'review-boundary' }, ({ path }) => ({
          contents: path.endsWith('client')
            ? 'export const jsonBody=JSON.stringify;'
            : path.endsWith('useProjectApi')
              ? 'export const useProjectApi=()=>async()=>{throw new Error("SSR不能发送请求")};'
              : 'export const useQuery=()=>({data:{verifications:[],policy:{require_sandbox_delivery:false}}});',
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
const { ChangeDelivery, writeChangeReview } = module.exports;
const change = {
  id: 'copy/a',
  title: '修改入口',
  goal: '已查看的原验收',
  status: 'passed',
  change_version: 'a'.repeat(64),
  requirements_version: 'b'.repeat(64),
  acceptance_criteria: ['入口可用'],
  latest_verification: { status: 'passed', purpose: 'change', change_version: 'a'.repeat(64) },
};
function render(value) {
  return renderToStaticMarkup(
    createElement(ChangeDelivery, {
      projectId: 'project-a',
      change: value,
      profiles: [],
      disabled: false,
      sourceUnchanged: true,
      onChanged: () => {},
      onDownload: async () => {},
    }),
  );
}

test('审核请求固定为已展示的项目及修改和需求版本，不请求新版本代替用户确认', async () => {
  const calls = [];
  const api = async (path, options, projectId) => {
    calls.push({ path, options, projectId });
    return change;
  };
  assert.equal(await writeChangeReview(api, 'project-old', change, '已核对'), change);
  assert.deepEqual(calls, [
    {
      path: '/code-changes/copy%2Fa/review',
      projectId: 'project-old',
      options: {
        method: 'POST',
        body: JSON.stringify({
          change_version: change.change_version,
          requirements_version: change.requirements_version,
          notes: '已核对',
        }),
      },
    },
  ]);
});

test('缺需求版本不能发审核，后端版本冲突原样返回', async () => {
  let calls = 0;
  const api = async () => {
    calls++;
    throw new Error('需求约定已变化');
  };
  for (const field of ['change_version', 'requirements_version'])
    await assert.rejects(
      writeChangeReview(api, 'p', { ...change, [field]: undefined }, ''),
      /缺少版本/,
    );
  assert.equal(calls, 0);
  await assert.rejects(writeChangeReview(api, 'p', change, ''), /需求约定已变化/);
  assert.equal(calls, 1);
});

test('页面展示两个审核身份，旧需求或缺失需求审核不能下载交付包', () => {
  const review = {
    change_version: change.change_version,
    requirements_version: change.requirements_version,
    actor: 'reviewer',
  };
  const current = render({ ...change, review });
  assert.match(current, new RegExp(`当前需求版本：${change.requirements_version}`));
  assert.match(current, /当前版本已审核/);
  assert.doesNotMatch(current, /<button[^>]*disabled=""[^>]*>下载已审核交付包/);
  for (const requirements_version of [undefined, 'c'.repeat(64)]) {
    const html = render({ ...change, review: { ...review, requirements_version } });
    assert.doesNotMatch(html, /当前版本已审核/);
    assert.match(html, /<button[^>]*disabled=""[^>]*>下载已审核交付包/);
  }
  assert.match(render({ ...change, requirements_version: undefined }), /缺少需求版本/);
});
