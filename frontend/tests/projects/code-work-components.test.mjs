import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const environment = {
  role: 'user',
  data: {},
  profileQuery: undefined,
  api: async () => ({ profiles: [] }),
};
const bundled = await build({
  stdin: {
    contents:
      "export { CodeChangesPanel } from './src/features/projects/components/CodeChangesPanel'; export { ProjectReadingPanel } from './src/features/projects/components/ProjectReadingPanel'; export { ProjectVerificationProfiles, ProjectVerificationProfileList } from './src/features/projects/components/ProjectVerificationProfiles'; export { ConfigurationPage } from './src/features/admin/ConfigurationPage'; export { ChangeFileEditor } from './src/features/projects/components/ChangeFileEditor';",
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
      name: 'code-work-boundaries',
      setup(builder) {
        const stubs = {
          query:
            'export const useQuery = (options) => environment.query(options); export const useQueryClient = () => ({ invalidateQueries: async () => {}, setQueryData: () => {} });',
          api: 'export const jsonBody = JSON.stringify; export const apiUrl = (path, id) => `/api/p/${id}${path}`; export const api = (...args) => environment.api(...args);',
          project:
            'export const useProjectApi = () => async () => { throw new Error("渲染测试不应发送请求"); };',
          auth: 'export const useAuth = () => ({ session: { user: { role: environment.role, id: "account-a" } } });',
          settings: 'export const SettingsDialog = () => null;',
          editor: 'export const ProjectEditor = () => null;',
          documents: 'export const ProjectDocuments = () => null;',
          admin: 'export const adminApi = async () => ({}); export const dateTime = String;',
          store:
            'export const useWorkspace = (selector) => selector({projectId: "project-a"}); useWorkspace.getState = () => ({switchProject: () => {}});',
        };
        builder.onResolve({ filter: /.*/ }, ({ path, importer }) => {
          const name =
            path === '@tanstack/react-query'
              ? 'query'
              : path.endsWith('/api/client')
                ? 'api'
                : path.endsWith('/hooks/useProjectApi')
                  ? 'project'
                  : path.endsWith('/auth/AuthContext')
                    ? 'auth'
                    : path.endsWith('/settings/components/SettingsDialog')
                      ? 'settings'
                      : path.endsWith('/projects/components/ProjectEditor')
                        ? 'editor'
                        : path.endsWith('/projects/components/ProjectDocuments')
                          ? 'documents'
                          : path.endsWith('/state/store')
                            ? 'store'
                            : path === './client' && importer.endsWith('ConfigurationPage.tsx')
                              ? 'admin'
                              : '';
          if (name) return { path: name, namespace: 'code-work-boundary' };
        });
        builder.onLoad({ filter: /.*/, namespace: 'code-work-boundary' }, ({ path }) => ({
          contents: stubs[path],
          loader: 'js',
        }));
      },
    },
  ],
});
const bundledModule = { exports: {} };
new Function('require', 'module', 'exports', 'environment', bundled.outputFiles[0].text)(
  createRequire(import.meta.url),
  bundledModule,
  bundledModule.exports,
  environment,
);
const {
  CodeChangesPanel,
  ProjectReadingPanel,
  ProjectVerificationProfiles,
  ProjectVerificationProfileList,
  ConfigurationPage,
  ChangeFileEditor,
} = bundledModule.exports;

function setup({ change, profiles = [], diff, job, documents = [], role = 'user' } = {}) {
  environment.role = role;
  environment.query = ({ queryKey, queryFn }) => {
    if (queryKey[0] === 'projects')
      return {
        data: { projects: [{ id: 'project-a', name: '项目A', state: 'active' }] },
        error: null,
      };
    if (queryKey[0] === 'project')
      return { data: { id: 'project-a', name: '项目A', state: 'active' }, error: null };
    if (queryKey[0] === 'admin-events') return { data: [], error: null };
    if (queryKey[0] === 'code-change-profiles-admin') environment.profileQuery = queryFn;
    const key =
      queryKey[0] === 'code-change-profiles' || queryKey[0] === 'code-change-profiles-admin'
        ? 'profiles'
        : queryKey[0] === 'code-changes'
          ? queryKey.length === 2
            ? 'changes'
            : queryKey.includes('diff')
              ? 'diff'
              : 'change'
          : queryKey.length === 2
            ? 'jobs'
            : queryKey.includes('documents')
              ? 'documents'
              : 'job';
    const data = {
      profiles: { profiles },
      changes: { changes: change ? [change] : [] },
      change,
      diff: diff || { diff: '', files: [], conflicts: [], source_unchanged: true },
      jobs: { jobs: job ? [job] : [], latest: job || null },
      job,
      documents: { documents },
    }[key];
    return { data, isPending: false, error: null, refetch: async () => {} };
  };
}
const base = {
  id: 'change-a',
  title: '修改A',
  goal: '修复问题',
  status: 'ready',
  files_changed: 0,
  latest_verification: null,
};
const verification = {
  id: 'verify-a',
  status: 'passed',
  profile_id: 'test',
  argv: ['python', '-m', 'pytest'],
  exit_code: 0,
  output: '测试通过',
  truncated: false,
  started_at: '2026-10-16T10:00:00Z',
  change_version: 'hash-a',
  stale: false,
};
const renderChanges = (readOnly = false) =>
  renderToStaticMarkup(createElement(CodeChangesPanel, { projectId: 'project-a', readOnly }));

test('未配置命令时显示明确空状态，普通用户没有管理员命令表单', () => {
  setup({ change: base });
  const html = renderChanges();
  assert.match(html, /尚未配置验证命令/);
  assert.doesNotMatch(html, /验证命令参数 JSON 数组/);
  assert.match(html, /<button[^>]*disabled=""[^>]*>执行所选验证<\/button>/);
});

test('过期的通过结果仍可看日志，但不提供成功经验保存入口', () => {
  setup({
    change: {
      ...base,
      status: 'editing',
      latest_verification: { ...verification, stale: true, truncated: true },
    },
  });
  const html = renderChanges();
  assert.match(html, /修改后已失效/);
  assert.match(html, /当前显示已截断/);
  assert.match(html, /下载完整日志/);
  assert.doesNotMatch(html, /记录调试经验/);
});

test('有效通过开放用户事实表单，失败记录不开放，命令结果不声称设备验收', () => {
  setup({ change: { ...base, status: 'passed', latest_verification: verification } });
  const passed = renderChanges();
  assert.match(passed, /记录调试经验/);
  assert.match(passed, /我确认该问题已解决/);
  assert.match(passed, /不等同于设备验收/);
  assert.match(passed, /实际验证结果<textarea[^>]*required=""/);
  assert.doesNotMatch(passed, /<textarea[^>]*>测试通过<\/textarea>/);
  setup({
    change: {
      ...base,
      status: 'failed',
      latest_verification: { ...verification, status: 'failed', exit_code: 1 },
    },
  });
  assert.doesNotMatch(renderChanges(), /记录调试经验/);
});

test('丢弃副本保留状态信息但不再展示编辑和验证入口', () => {
  setup({ change: { ...base, status: 'discarded' } });
  const html = renderChanges();
  assert.match(html, /隔离副本已丢弃/);
  assert.doesNotMatch(html, /副本文件路径|执行所选验证|下载补丁/);
});

test('运行中可取消，已归档项目禁用取消和命令配置保存', () => {
  setup({
    change: {
      ...base,
      status: 'verifying',
      latest_verification: { ...verification, status: 'running' },
    },
    role: 'admin',
  });
  assert.match(renderChanges(), /<button class="button">取消运行<\/button>/);
  const archived = renderChanges(true);
  assert.match(archived, /<button[^>]*disabled=""[^>]*>取消运行<\/button>/);
  assert.match(archived, /<button[^>]*disabled=""[^>]*>保存命令配置<\/button>/);
});

test('阅读页面保留读取、分析、评审独立统计，展示证据版本与未知项', () => {
  const job = {
    id: 'read-a',
    title: '项目阅读',
    status: 'partial',
    snapshot_version: 3,
    updated_at: 'now',
    counts: {
      files: 8,
      indexed: 8,
      read: 7,
      analyzed: 5,
      reviewed: 1,
      pending: 2,
      failed: 1,
      excluded: 4,
      stale: 1,
    },
    modules: [
      {
        name: '模块A',
        total: 8,
        read: 7,
        analyzed: 5,
        reviewed: 1,
        pending: 2,
        failed: 1,
        stale: 1,
      },
    ],
  };
  setup({
    job,
    documents: [
      {
        id: 'doc-a',
        path: 'src/A.cs',
        module: '模块A',
        version: 2,
        source_version: 'source-hash',
        start_line: 4,
        end_line: 20,
        status: 'analyzed',
        summary: '入口处理',
        unknowns: ['设备时序需要验证'],
      },
    ],
  });
  const html = renderToStaticMarkup(
    createElement(ProjectReadingPanel, { projectId: 'project-a', readOnly: false }),
  );
  assert.match(html, /已读取<\/dt><dd>7/);
  assert.match(html, /已分析<\/dt><dd>5/);
  assert.match(html, /已评审<\/dt><dd>1/);
  assert.match(html, /继续阅读/);
  assert.match(html, /设备时序需要验证/);
  assert.match(html, /source-hash/);
  assert.match(html, /确认本版成果/);
  assert.match(html, /64 个分块/);
  assert.match(html, /供应商额度/);
});

test('源码冲突阻止验证和经验入口，但允许导出旧基线补丁保留成果', () => {
  setup({
    change: { ...base, status: 'passed', files_changed: 1, latest_verification: verification },
    diff: { diff: 'saved patch', files: [], conflicts: ['src/A.cs'], source_unchanged: false },
  });
  const html = renderChanges();
  assert.match(html, /历史命令验证通过（原始源码已变化）/);
  assert.match(html, /应用时需人工合并/);
  assert.match(html, /<button class="button">下载补丁<\/button>/);
  assert.doesNotMatch(html, /记录调试经验/);
});

test('管理员系统配置的命令入口先选择项目，显式查询不沿用前台项目', async () => {
  setup({
    role: 'admin',
    profiles: [
      { id: 'test-a', name: '单元测试', argv: ['python', '-m', 'pytest'], timeout_seconds: 120 },
    ],
  });
  const chooser = renderToStaticMarkup(
    createElement(ProjectVerificationProfiles, {
      projects: [{ id: 'project-b', name: '项目B', state: 'active' }],
    }),
  );
  assert.match(chooser, /选择验证命令所属项目/);
  assert.match(chooser, /先选择一个项目/);
  assert.doesNotMatch(chooser, /保存命令配置/);
  const html = renderToStaticMarkup(
    createElement(ProjectVerificationProfileList, { projectId: 'project-b', readOnly: false }),
  );
  assert.match(html, /单元测试/);
  assert.match(html, /保存命令配置/);
  assert.match(html, /副本不限制进程系统权限/);
  const calls = [];
  environment.api = async (path, options, projectId = 'wrong-workspace') => {
    calls.push({ path, projectId });
    return { profiles: [] };
  };
  const boundQuery = environment.profileQuery;
  await Promise.resolve();
  await boundQuery({ signal: undefined });
  assert.deepEqual(calls, [{ path: '/code-changes/profiles', projectId: 'project-b' }]);
});

test('管理员系统配置实际挂载项目验证命令入口，数据维护页不混入该功能', () => {
  setup({ role: 'admin' });
  const html = renderToStaticMarkup(createElement(ConfigurationPage, { dataOnly: false }));
  assert.match(html, /项目验证命令/);
  assert.match(html, /选择验证命令所属项目/);
  assert.doesNotMatch(
    renderToStaticMarkup(createElement(ConfigurationPage, { dataOnly: true })),
    /项目验证命令/,
  );
});

test('重新进入副本恢复草稿及原版本，另一个项目不会恢复该正文', async () => {
  const { writeCodeFileDraft } = await import('../../src/features/projects/lib/codeFileDraft.ts');
  const saved = new Map();
  const storage = {
    getItem: (key) => saved.get(key) ?? null,
    setItem: (key, value) => saved.set(key, value),
    removeItem: (key) => saved.delete(key),
  };
  const previous = globalThis.window;
  globalThis.window = { sessionStorage: storage };
  try {
    setup();
    writeCodeFileDraft(
      storage,
      { accountId: 'account-a', projectId: 'project-a', changeId: 'change-a' },
      {
        file: { path: 'A.cs', content: '原正文', version: 'f'.repeat(64), exists: true },
        draft: '待保存草稿',
      },
    );
    const props = {
      changeId: 'change-a',
      projectId: 'project-a',
      selectedPath: '',
      disabled: false,
      onSaved: () => {},
      onDirtyChange: () => {},
    };
    const html = renderToStaticMarkup(createElement(ChangeFileEditor, props));
    assert.match(html, /待保存草稿/);
    assert.match(html, /f{64}/);
    assert.match(html, /已恢复本账号/);
    assert.match(html, /正文 UTF-8 SHA-256/);
    assert.doesNotMatch(
      renderToStaticMarkup(createElement(ChangeFileEditor, { ...props, projectId: 'project-b' })),
      /待保存草稿/,
    );
  } finally {
    if (previous === undefined) delete globalThis.window;
    else globalThis.window = previous;
  }
});
