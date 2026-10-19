// 登录页只公开其真实静态依赖；业务分包和历史哈希文件默认需要会话。
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const loginModule = '/src/features/auth/login/LoginPage.tsx';
export const loginImages = ['brand/arks-assistant-icon.png', 'brand/arks-login-mark.png'];

export function publicChunks(bundle) {
  const chunks = Object.values(bundle).filter((item) => item.type === 'chunk');
  const entries = chunks.filter((item) => item.isEntry);
  const login = chunks.find((item) =>
    item.facadeModuleId?.replaceAll('\\', '/').endsWith(loginModule),
  );
  if (entries.length !== 1 || !login) throw new Error('登录页构建入口不完整，不能发布资源白名单');
  const result = new Set();
  function visit(name) {
    if (result.has(name)) return;
    const chunk = bundle[name];
    if (!chunk || chunk.type !== 'chunk') throw new Error('公开分包引用了未知脚本');
    if (
      Object.keys(chunk.modules).some((id) =>
        id.replaceAll('\\', '/').toLowerCase().includes('/src/features/knowledge/'),
      )
    )
      throw new Error('业务知识进入公开登录依赖，拒绝发布');
    result.add(name);
    // 不追踪 dynamicImports；只有明确选中的登录页动态入口可进入公开集合。
    chunk.imports.forEach(visit);
  }
  [...entries, login].forEach((chunk) => visit(chunk.fileName));
  return result;
}

export function publicFiles(manifest, chunks) {
  const files = new Set(['index.html', ...loginImages]);
  for (const name of chunks) {
    const entry = Object.values(manifest).find((item) => item.file === name);
    if (!entry) throw new Error('公开分包缺少Vite清单，拒绝发布');
    files.add(name);
    for (const path of [...(entry.css || []), ...(entry.assets || [])]) files.add(path);
  }
  for (const path of files) {
    if (
      !/^[a-zA-Z0-9_@./-]+$/.test(path) ||
      path.split('/').some((part) => !part || part === '..' || part === '.') ||
      !(path === 'index.html' || loginImages.includes(path) || path.startsWith('assets/'))
    )
      throw new Error('公开资源路径不受支持');
    if (/\.[cm]?js(?:\.map)?$/i.test(path) && !chunks.has(path))
      throw new Error('资源清单包含未审查脚本');
  }
  return files;
}

export async function writePublicManifest(output, manifest, chunks) {
  const files = {};
  for (const name of [...publicFiles(manifest, chunks)].sort()) {
    files[name] = createHash('sha256')
      .update(await readFile(resolve(output, name)))
      .digest('hex');
  }
  await writeFile(
    resolve(output, 'public-assets.json'),
    JSON.stringify({ schema_version: 1, files }) + '\n',
  );
  return files;
}

export function publicAssets() {
  let output;
  let reviewed;
  return {
    name: 'arks-public-assets',
    enforce: 'post',
    configResolved(config) {
      output = resolve(config.root, config.build.outDir);
    },
    generateBundle(_options, bundle) {
      reviewed = publicChunks(bundle);
    },
    async writeBundle() {
      const manifest = JSON.parse(await readFile(resolve(output, '.vite/manifest.json'), 'utf8'));
      await writePublicManifest(output, manifest, reviewed);
    },
  };
}
