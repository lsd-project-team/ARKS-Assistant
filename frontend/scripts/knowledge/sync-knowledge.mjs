import { knowledgePath, projectRoot } from './resources.mjs';
import { cp, mkdir, readFile, writeFile, stat } from 'node:fs/promises';
import { resolve } from 'node:path';
import { archifyData } from '../../src/features/knowledge/data/archifyData.ts';

const frontend = resolve(projectRoot, 'frontend');
const legacy = resolve(process.argv[2] || resolve(frontend, '../其他模块/archify-ui'));
const destination = resolve(projectRoot, 'resources/knowledge');
const manifest = JSON.parse(
  await readFile(resolve(legacy, 'public/engineering/manifest.json'), 'utf8'),
);
if (!/^[a-f0-9]{20}$/.test(manifest.version)) throw new Error('源码索引版本格式无效');
await mkdir(destination, { recursive: true });
// 独立保存资料与当前索引，运行新版本不再依赖旧版服务或数据库。
await cp(resolve(legacy, 'public/archify'), knowledgePath('archify/'), { recursive: true });
await cp(
  resolve(legacy, `public/engineering/versions/${manifest.version}`),
  knowledgePath(`engineering/versions/${manifest.version}`),
  { recursive: true },
);
await writeFile(knowledgePath('engineering/manifest.json'), JSON.stringify(manifest));
const reviewed = {
  ...JSON.parse(
    await readFile(resolve(legacy, 'public/archify/module-review-evidence.json'), 'utf8'),
  ),
  ...archifyData.refs,
};
const filesByPath = new Map(manifest.files.map((file) => [file.path.replaceAll('\\', '/'), file]));
const codeCache = new Map();
const refs = {};
for (const [id, ref] of Object.entries(reviewed)) {
  const file = filesByPath.get(ref.path.replaceAll('\\', '/'));
  if (!file) {
    refs[id] = { sha256: ref.sha256, current: false };
    continue;
  }
  if (!codeCache.has(file.id))
    codeCache.set(
      file.id,
      JSON.parse(await readFile(knowledgePath(`${manifest.base}/files/${file.id}.json`), 'utf8')),
    );
  const code = codeCache.get(file.id).code;
  const excerpt = code
    .split(/\r\n|\r|\n/)
    .slice(ref.start - 1, ref.end)
    .map((line, index) => `${ref.start + index}: ${line}`)
    .join('\n');
  refs[id] = {
    fileId: file.id,
    sha256: ref.sha256,
    current:
      file.exists &&
      file.sha256 === ref.sha256 &&
      ref.code.replaceAll('\r', '') === excerpt &&
      file.assemblies.every(
        (assembly) =>
          manifest.projects.find((project) => project.assembly === assembly)?.current !== false,
      ),
  };
}
const modules = {};
for (const module of manifest.modules) {
  const detail = JSON.parse(
    await readFile(knowledgePath(`${manifest.base}/modules/${module.id}.json`), 'utf8'),
  );
  modules[module.id] = detail.review.evidenceIds;
}
await writeFile(
  knowledgePath(`${manifest.base}/evidence-baseline.json`),
  JSON.stringify({ refs, modules }),
);
await stat(knowledgePath(`${manifest.base}/search.json`));
console.log(
  `资料已同步：${manifest.modules.length} 个模块，${manifest.counts.files} 个源码文件，版本 ${manifest.version}`,
);
