import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile, rm, realpath } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, dirname, basename } from 'node:path';
import { createHash } from 'node:crypto';
import { build } from 'vite';
import {
  publicChunks,
  publicFiles,
  writePublicManifest,
  loginImages,
  publicAssets,
} from '../../scripts/build/public-assets.mjs';

function chunk(fileName, facadeModuleId, imports = [], extra = {}) {
  return {
    type: 'chunk',
    fileName,
    facadeModuleId,
    imports,
    dynamicImports: [],
    modules: { [facadeModuleId]: {} },
    ...extra,
  };
}

function fixture() {
  return {
    'assets/main.js': chunk('assets/main.js', '/app/index.html', ['assets/common.js'], {
      isEntry: true,
      dynamicImports: ['assets/workspace.js'],
    }),
    'assets/login.js': chunk('assets/login.js', '/app/src/features/auth/login/LoginPage.tsx', [
      'assets/common.js',
    ]),
    'assets/common.js': chunk('assets/common.js', '/app/src/shared/ui.ts'),
    'assets/workspace.js': chunk(
      'assets/workspace.js',
      '/app/src/features/knowledge/KnowledgeWorkspace.tsx',
    ),
  };
}

test('公开依赖只跟踪登录入口和静态依赖，不顺便公开工作区动态分包', () => {
  assert.deepEqual([...publicChunks(fixture())].sort(), [
    'assets/common.js',
    'assets/login.js',
    'assets/main.js',
  ]);
  for (const name of ['assets/main.js', 'assets/login.js', 'assets/common.js']) {
    const bundle = fixture();
    bundle[name].modules['D:\\app\\src\\features\\knowledge\\data\\archifyData.ts'] = {};
    assert.throws(() => publicChunks(bundle), /业务知识/);
    bundle[name].modules = { 'D:\\app\\SRC\\FEATURES\\KNOWLEDGE\\data.ts': {} };
    assert.throws(() => publicChunks(bundle), /业务知识/);
  }
});

test('真实Vite构建把业务动态分包留在会话后，并拒绝把业务数据导入登录入口', async (t) => {
  const directory = await mkdtemp(join(tmpdir(), 'arks-public-build-'));
  const parent = await realpath(tmpdir());
  assert.equal(dirname(await realpath(directory)), parent);
  t.after(async () => {
    assert.equal(dirname(await realpath(directory)), parent);
    assert.ok(basename(directory).startsWith('arks-public-build-'));
    await rm(directory, { recursive: true, force: true });
  });
  const sources = {
    'index.html': '<script type="module" src="/src/main.ts"></script>',
    'src/main.ts':
      "globalThis.loadLogin = () => import('./features/auth/login/LoginPage.tsx'); globalThis.loadKnowledge = () => import('./features/knowledge/secret.ts');",
    'src/features/auth/login/LoginPage.tsx': "export default 'login';",
    'src/features/knowledge/secret.ts': "globalThis.privateFixture = 'BUSINESS_RECORD_FIXTURE';",
    ...Object.fromEntries(loginImages.map((name) => ['public/' + name, 'image-fixture'])),
  };
  for (const [name, content] of Object.entries(sources)) {
    const file = join(directory, name);
    await mkdir(dirname(file), { recursive: true });
    await writeFile(file, content);
  }
  const options = {
    root: directory,
    configFile: false,
    logLevel: 'silent',
    plugins: [publicAssets()],
    build: { manifest: true, minify: false },
  };
  await build(options);
  const manifest = JSON.parse(await readFile(join(directory, 'dist/.vite/manifest.json'), 'utf8'));
  const secret = Object.values(manifest).find((item) => item.src?.endsWith('secret.ts'));
  const published = JSON.parse(await readFile(join(directory, 'dist/public-assets.json'), 'utf8'));
  assert.ok(secret?.file);
  assert.match(
    await readFile(join(directory, 'dist', secret.file), 'utf8'),
    /BUSINESS_RECORD_FIXTURE/,
  );
  assert.equal(published.files[secret.file], undefined);
  await writeFile(
    join(directory, 'src/main.ts'),
    "import './features/knowledge/secret.ts'; globalThis.loadLogin = () => import('./features/auth/login/LoginPage.tsx');",
  );
  await assert.rejects(build(options), /业务知识进入公开登录依赖/);
});

test('缺失入口或未知静态脚本依赖使构建失败', () => {
  const missing = fixture();
  delete missing['assets/login.js'];
  assert.throws(() => publicChunks(missing), /入口不完整/);
  const unknown = fixture();
  unknown['assets/login.js'].imports.push('unknown.js');
  assert.throws(() => publicChunks(unknown), /未知脚本/);
});

test('公开资源清单固定实际字节摘要，包含CSS字体并拒绝未审查脚本和越界路径', async (t) => {
  const directory = await mkdtemp(join(tmpdir(), 'arks-public-assets-'));
  t.after(async () => {
    assert.equal(dirname(await realpath(directory)), await realpath(tmpdir()));
    assert.ok(basename(directory).startsWith('arks-public-assets-'));
    await rm(directory, { recursive: true, force: true });
  });
  const chunks = publicChunks(fixture());
  const manifest = Object.fromEntries(
    [...chunks].map((file) => [
      file,
      { file, css: ['assets/login.css'], assets: ['assets/font.woff2'] },
    ]),
  );
  const names = ['index.html', ...loginImages, ...chunks, 'assets/login.css', 'assets/font.woff2'];
  for (const name of names) {
    const target = join(directory, name);
    await mkdir(join(target, '..'), { recursive: true });
    await writeFile(target, `fixture:${name}`);
  }
  const files = await writePublicManifest(directory, manifest, chunks);
  assert.equal(
    files['assets/font.woff2'],
    createHash('sha256').update('fixture:assets/font.woff2').digest('hex'),
  );
  assert.deepEqual(JSON.parse(await readFile(join(directory, 'public-assets.json'), 'utf8')), {
    schema_version: 1,
    files,
  });
  assert.equal(files['assets/workspace.js'], undefined);
  for (const path of [
    '../private',
    'assets/../private',
    '/etc/passwd',
    'engineering/secret.json',
    'assets/unknown.js',
    'assets/unknown.MJS',
    'assets/unknown.JS.map',
  ]) {
    const invalid = structuredClone(manifest);
    invalid['assets/main.js'].assets.push(path);
    assert.throws(() => publicFiles(invalid, chunks));
  }
});
