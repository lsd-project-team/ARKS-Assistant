import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { isAbsolute, join, relative, resolve } from 'node:path';
import { validateSourceGuides } from '../scripts/source-guide-validation.mjs';

async function fixture(t) {
  const folder = await mkdtemp(join(tmpdir(), 'trunk-source-review-'));
  t.after(() => {
    const within = relative(resolve(tmpdir()), resolve(folder));
    assert.ok(within && !within.startsWith('..') && !isAbsolute(within));
    return rm(folder, { recursive: true, force: true });
  });
  const trunkRoot = join(folder, 'trunk');
  await mkdir(trunkRoot);
  const code = '\ufeff// 中文\r\nbool Ready() => true;\r\n';
  await writeFile(join(trunkRoot, '入口.cs'), code);
  const claim = { text: '该方法直接返回 true。', refs: ['ready'] };
  return {
    trunkRoot,
    topics: ['startup'],
    diagrams: ['start'],
    guides: [
      {
        id: 'guide',
        topic: 'startup',
        diagrams: ['start'],
        flows: [
          {
            id: 'flow',
            title: '流程',
            ...claim,
            steps: [
              { id: 'step', title: '返回', ...claim, outcomes: [{ label: '结果', ...claim }] },
            ],
          },
        ],
        boundaries: [claim],
      },
    ],
    evidence: {
      sources: {
        entry: { path: '入口.cs', sha256: createHash('sha256').update(code).digest('hex') },
      },
      ranges: {
        ready: { file: 'entry', method: 'Ready', start: 2, end: 2, code: 'bool Ready() => true;' },
      },
    },
  };
}

test('主项目校验接受中文、BOM、CRLF，不要求历史项目目录', async (t) => {
  assert.deepEqual(await validateSourceGuides(await fixture(t)), {
    guides: 1,
    flows: 1,
    steps: 1,
    claims: 4,
    files: 1,
    ranges: 1,
  });
});
test('源码变化不能由旧片段继续通过校验，即使修改发生在引用范围外', async (t) => {
  const input = await fixture(t);
  await writeFile(join(input.trunkRoot, '入口.cs'), '// 文件改动\r\nbool Ready() => true;\r\n');
  await assert.rejects(validateSourceGuides(input), /源码已变化/);
});
test('指纹匹配时仍拒绝行号漂移或被改写的引用片段', async (t) => {
  const input = await fixture(t);
  input.evidence.ranges.ready.start = 1;
  input.evidence.ranges.ready.end = 1;
  await assert.rejects(validateSourceGuides(input), /片段与当前源码不符/);
  input.evidence.ranges.ready.start = 2;
  input.evidence.ranges.ready.end = 2;
  input.evidence.ranges.ready.code = 'bool Ready() => false;';
  await assert.rejects(validateSourceGuides(input), /片段与当前源码不符/);
});
test('说明和分支都必须绑定存在的源码依据', async (t) => {
  const input = await fixture(t);
  input.guides[0].flows[0].steps[0].outcomes[0] = { label: '结果', text: '无依据', refs: [] };
  await assert.rejects(validateSourceGuides(input), /缺少源码依据/);
  input.guides[0].flows[0].steps[0].outcomes[0].refs = ['missing'];
  await assert.rejects(validateSourceGuides(input), /依据不存在/);
});
test('文件末尾换行不能变成超出源码 API 行数的引用', async (t) => {
  const input = await fixture(t);
  Object.assign(input.evidence.ranges.ready, { start: 3, end: 3, code: '' });
  await assert.rejects(validateSourceGuides(input), /依据行号无效/);
});
test('引用不得越出主项目 trunk，页面不存在也拒绝通过', async (t) => {
  const input = await fixture(t);
  await writeFile(join(input.trunkRoot, '..', 'outside.cs'), '外部文件');
  input.evidence.sources.entry.path = '../outside.cs';
  await assert.rejects(validateSourceGuides(input), /源码路径越界/);
  input.evidence.sources.entry.path = '入口.cs';
  input.guides[0].diagrams = ['unknown'];
  await assert.rejects(validateSourceGuides(input), /图谱不存在/);
});

test('局部图的默认阅读环节必须属于已绑定页面和当前专题', async (t) => {
  const input = await fixture(t);
  input.guides[0].initialFlows = { start: 'flow' };
  await validateSourceGuides(input);
  input.guides[0].initialFlows = { start: 'other-topic-flow' };
  await assert.rejects(validateSourceGuides(input), /默认阅读流程不存在/);
  input.guides[0].initialFlows = { unbound: 'flow' };
  await assert.rejects(validateSourceGuides(input), /默认阅读页面未绑定/);
});
