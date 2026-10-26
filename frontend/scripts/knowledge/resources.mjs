// 知识资源只有一个源目录，开发、校验和正式构建沿用相同的 URL 映射。
import { cp, readFile, readdir, writeFile } from 'node:fs/promises';
import { dirname, isAbsolute, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
export const knowledgeRoot = resolve(projectRoot, 'resources/knowledge');
const mounts = {
  archify: resolve(knowledgeRoot, 'flows'),
  'agent-knowledge.json': resolve(knowledgeRoot, 'generated/agent-knowledge.json'),
};

// 发布阅读用图谱时去掉历史源码绑定；原始图谱仍供构建校验使用。
export function readingDiagram(html) {
  return html
    .replace(/<script\b[^>]*id="archify-source-evidence-data"[^>]*>[\s\S]*?<\/script>/g, '')
    .replace(
      /<div class="card">\s*<div class="card-header">\s*<div class="card-dot[^"]*"><\/div>\s*<h3>(?:当前源码依据|源码依据与溯源)<\/h3><\/div>\s*<ul>[\s\S]*?<\/ul>\s*<\/div>/g,
      '',
    )
    .replace(/<li>\s*&bull;\s*依据[:：][\s\S]*?<\/li>/g, '')
    .replace(
      '</head>',
      '<style>.semantic-passport-evidence,.source-evidence-beacon{display:none!important}</style></head>',
    );
}

async function prepareDiagrams(folder) {
  for (const entry of await readdir(folder, { withFileTypes: true })) {
    const path = resolve(folder, entry.name);
    if (entry.isDirectory()) await prepareDiagrams(path);
    else if (entry.name.endsWith('.html'))
      await writeFile(path, readingDiagram(await readFile(path, 'utf8')));
  }
}

export function knowledgePath(url) {
  const decoded = decodeURIComponent(url.split('?')[0]).replace(/^\/+/, '');
  const [prefix, ...parts] = decoded.split('/');
  const root = mounts[prefix];
  if (!root) throw new Error(`未知知识资源地址：${url}`);
  if (prefix === 'agent-knowledge.json') {
    if (parts.length) throw new Error('知识资源路径越界');
    return root;
  }
  const target = resolve(root, ...parts);
  const within = relative(root, target);
  if (within.startsWith('..') || isAbsolute(within)) throw new Error('知识资源路径越界');
  return target;
}

const mime = {
  html: 'text/html; charset=utf-8',
  json: 'application/json; charset=utf-8',
  md: 'text/plain; charset=utf-8',
  css: 'text/css; charset=utf-8',
  js: 'text/javascript; charset=utf-8',
  svg: 'image/svg+xml',
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  webp: 'image/webp',
};

export function knowledgeMiddleware(request, response, next) {
  const prefix = request.url?.split(/[/?]/).find(Boolean);
  if (!Object.hasOwn(mounts, prefix)) return next();
  if (request.method !== 'GET' && request.method !== 'HEAD') return next();
  let path;
  try {
    path = knowledgePath(request.url);
  } catch {
    response.statusCode = 400;
    response.end('Invalid resource path');
    return;
  }
  readFile(path)
    .then((bytes) => {
      response.setHeader(
        'Content-Type',
        mime[path.split('.').at(-1)] || 'application/octet-stream',
      );
      const body = path.endsWith('.html') ? readingDiagram(bytes.toString('utf8')) : bytes;
      response.end(request.method === 'HEAD' ? undefined : body);
    })
    .catch(() => {
      response.statusCode = 404;
      response.end('Not found');
    });
}

export function knowledgeAssets() {
  let output;
  return {
    name: 'arks-knowledge-assets',
    configResolved(config) {
      output = resolve(config.root, config.build.outDir);
    },
    configureServer(server) {
      server.middlewares.use(knowledgeMiddleware);
    },
    configurePreviewServer(server) {
      server.middlewares.use(knowledgeMiddleware);
    },
    async writeBundle() {
      for (const [name, source] of Object.entries(mounts)) {
        await cp(source, resolve(output, name), { recursive: true });
      }
      await prepareDiagrams(resolve(output, 'archify'));
    },
  };
}
