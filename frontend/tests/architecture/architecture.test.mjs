import test from 'node:test';
import assert from 'node:assert/strict';
import { readdir, readFile } from 'node:fs/promises';
import { dirname, resolve, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../src');
async function files(folder) {
  const entries = await readdir(folder, { withFileTypes: true });
  return (
    await Promise.all(
      entries.map((entry) =>
        entry.isDirectory() ? files(resolve(folder, entry.name)) : [resolve(folder, entry.name)],
      ),
    )
  ).flat();
}

test('公共前端能力不依赖应用装配或具体业务模块', async () => {
  const invalid = [];
  for (const path of await files(resolve(root, 'shared'))) {
    if (!/\.tsx?$/.test(path)) continue;
    const source = await readFile(path, 'utf8');
    for (const match of source.matchAll(/(?:from\s*|import\s*\()(['"])(\.[^'"]+)\1/g)) {
      const target = relative(root, resolve(dirname(path), match[2])).replaceAll('\\', '/');
      if (/^(app|features)\//.test(target)) invalid.push([relative(root, path), target]);
    }
  }
  assert.deepEqual(invalid, []);
});
