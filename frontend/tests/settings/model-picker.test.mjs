import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';

const environment = { requests: [], cached: [], invalidated: [], notices: [] };
// 执行真实选择事件和成功/失败处理，只隔离 HTTP 与 React Query 调度。
const result = await build({
  entryPoints: [
    fileURLToPath(
      new URL('../../src/features/settings/components/ModelPicker.tsx', import.meta.url),
    ),
  ],
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
  jsx: 'automatic',
  plugins: [
    {
      name: 'boundaries',
      setup(builder) {
        const stubs = {
          '@tanstack/react-query': `
          export const useQueryClient = () => ({
            setQueryData: (...args) => environment.cached.push(args),
            invalidateQueries: (value) => environment.invalidated.push(value.queryKey),
          });
          export const useMutation = (options) => ({
            isPending: environment.pending,
            mutate: (id) => environment.completion = options.mutationFn(id)
              .then(options.onSuccess, options.onError),
          });`,
          '/api/client': `
          export const jsonBody = JSON.stringify;
          export async function api(path, options) {
            environment.requests.push([path, options]);
            if (environment.error) throw environment.error;
            return environment.response;
          }`,
          '/utils/toasts': 'export const toast = (...args) => environment.notices.push(args);',
          '/ui/Select': 'export const Select = () => null;',
        };
        builder.onResolve({ filter: /.*/ }, ({ path }) => {
          const key = Object.keys(stubs).find((item) => path === item || path.endsWith(item));
          if (key) return { path: key, namespace: 'boundary' };
        });
        builder.onLoad({ filter: /.*/, namespace: 'boundary' }, ({ path }) => ({
          contents: stubs[path],
          loader: 'js',
        }));
      },
    },
  ],
});
const compiled = { exports: {} };
new Function('require', 'module', 'exports', 'environment', result.outputFiles[0].text)(
  createRequire(import.meta.url),
  compiled,
  compiled.exports,
  environment,
);
const { ModelPicker } = compiled.exports;
const preference = {
  active_profile_id: 'second',
  model_profiles: [
    { id: 'first', name: '主模型', model: 'first-model' },
    { id: 'second', name: '备用', model: 'second-model' },
  ],
};
function reset() {
  Object.assign(environment, {
    requests: [],
    cached: [],
    invalidated: [],
    notices: [],
    error: undefined,
    response: preference,
    pending: false,
  });
}

test('切换只提交个人模型 ID，成功刷新选择及上下文，运行中提示下一轮生效', async () => {
  reset();
  const view = ModelPicker({ preference, busy: true });
  const select = view.props.children[1];
  assert.equal(select.props.value, 'second');
  assert.match(select.props.children[1].props.children.join(''), /second-model.*备用/);
  select.props.onValueChange('first');
  await environment.completion;
  assert.deepEqual(environment.requests, [
    ['/model-preference', { method: 'PUT', body: '{"profile_id":"first"}' }],
  ]);
  assert.deepEqual(environment.cached, [[['model-preference'], preference]]);
  assert.deepEqual(environment.invalidated, [['context']]);
  assert.match(environment.notices[0][0], /下一轮/);
});

test('切换失败重新读取个人选择，等待期间禁用选择器', async () => {
  reset();
  environment.pending = true;
  environment.error = new Error('模型配置不存在');
  const select = ModelPicker({ preference, busy: false }).props.children[1];
  assert.equal(select.props.disabled, true);
  select.props.onValueChange('missing');
  await environment.completion;
  assert.deepEqual(environment.cached, []);
  assert.deepEqual(environment.invalidated, [['model-preference']]);
  assert.equal(environment.notices[0][0], '模型配置不存在');
});
