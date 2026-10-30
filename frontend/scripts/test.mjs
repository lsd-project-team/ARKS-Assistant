// 显式递归发现测试，避免测试移入业务子目录后被顶层通配符漏掉。
import { readdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
async function discover(folder) {
  const entries = await readdir(folder, { withFileTypes: true });
  const groups = await Promise.all(
    entries.map((entry) => {
      const path = resolve(folder, entry.name);
      return entry.isDirectory() ? discover(path) : entry.name.endsWith('.test.mjs') ? [path] : [];
    }),
  );
  return groups.flat().sort();
}

const files = await discover(resolve(root, 'tests'));
if (!files.length) throw new Error('没有发现前端测试文件');
const result = spawnSync(process.execPath, ['--experimental-strip-types', '--test', ...files], {
  cwd: root,
  stdio: 'inherit',
});
if (result.error) throw result.error;
process.exit(result.status ?? 1);
