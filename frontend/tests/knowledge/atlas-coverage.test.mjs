import test from 'node:test';
import assert from 'node:assert/strict';
import { validateAtlasCoverage } from '../../scripts/knowledge/atlas-coverage-validation.mjs';

function fixture() {
  return {
    plan: '#### 04 产品坐标\n\n- 04.01 对象与父级。\n- 04.02 实例展开。\n',
    coverage: {
      topics: [
        {
          id: '04',
          title: '产品坐标',
          requirements: [
            {
              id: '04.01',
              text: '对象与父级。',
              status: 'reviewed',
              bindings: [{ topic: 'product', flow: 'parents', steps: ['chain'] }],
            },
            { id: '04.02', text: '实例展开。', status: 'pending', bindings: [] },
          ],
        },
      ],
    },
    guides: [
      {
        topic: 'product',
        flows: [{ id: 'parents', steps: [{ id: 'chain', refs: ['evidence'] }] }],
      },
    ],
  };
}

test('清单保留全部条目，只有逐项绑定的内容计入复核', () => {
  assert.deepEqual(validateAtlasCoverage(fixture()), {
    topics: 1,
    requirements: 2,
    reviewed: 1,
    pending: 1,
  });
});

test('不能删掉未完成条目、重复编号或改写要求来缩减范围', () => {
  for (const mutation of [
    (input) => input.coverage.topics[0].requirements.pop(),
    (input) => {
      input.coverage.topics[0].requirements[1].id = '04.01';
    },
    (input) => {
      input.coverage.topics[0].requirements[1].text = '缩减后的要求';
    },
  ]) {
    const input = fixture();
    mutation(input);
    assert.throws(() => validateAtlasCoverage(input), /规划条目不一致/);
  }
});

test('不存在的节点或空依据不能作为已复核证明', () => {
  for (const mutation of [
    (input) => {
      input.coverage.topics[0].requirements[0].bindings[0].steps = ['missing'];
    },
    (input) => {
      input.coverage.topics[0].requirements[0].bindings = [];
    },
    (input) => {
      input.guides[0].flows[0].steps[0].refs = [];
    },
  ]) {
    const input = fixture();
    mutation(input);
    assert.throws(() => validateAtlasCoverage(input), /已复核项/);
  }
});
