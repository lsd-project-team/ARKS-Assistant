import test from 'node:test';
import assert from 'node:assert/strict';
import {
  executorPayload,
  executionLabel,
  requirementsPayload,
  deliveryVersionCurrent,
  reviewMissing,
  bytesLabel,
} from '../../src/features/projects/lib/codeReadiness.ts';
import { changeCanRecordExperience } from '../../src/features/projects/lib/codeWorkRules.ts';

const container = {
  kind: 'container',
  platform: 'linux',
  image: `sdk@sha256:${'a'.repeat(64)}`,
  context: 'default',
};
test('容器要求固定镜像digest，不把标签或空镜像视为已准备', () => {
  assert.deepEqual(executorPayload(container), container);
  for (const image of ['', 'sdk:latest', 'sdk:8', 'sha256:short', `sdk@sha256:${'g'.repeat(64)}`])
    assert.throws(() => executorPayload({ ...container, image }), /固定 SHA-256/);
  assert.equal(
    executorPayload({ ...container, image: `sha256:${'b'.repeat(64)}`, context: '' }).context,
    'default',
  );
});
test('可信宿主必须显式kind且始终标记非沙箱，不沿用容器镜像', () => {
  const host = executorPayload({ ...container, kind: 'trusted_host', platform: 'windows' });
  assert.equal(host.image, '');
  assert.match(executionLabel(host), /windows.*非沙箱/);
  assert.match(executionLabel(undefined), /未提供/);
  assert.match(executionLabel({ ...container, platform: 'windows' }), /执行支持待接入/);
});
test('修改验收信息保留独立条目并拒绝越界glob', () => {
  assert.deepEqual(
    requirementsPayload('返回值正确\n\n异常路径通过', '不调用设备', 'src/**\ntests\\**'),
    {
      acceptance_criteria: ['返回值正确', '异常路径通过'],
      constraints: '不调用设备',
      allowed_paths: ['src/**', 'tests/**'],
    },
  );
  for (const path of ['../**', '/etc/**', 'C:\\data\\**', 'src/../**', 'src\0/**'])
    assert.throws(() => requirementsPayload('', '', path), /相对路径/);
});
const change = {
  status: 'passed',
  change_version: 'current',
  acceptance_criteria: ['实际标准'],
  latest_verification: {
    status: 'passed',
    purpose: 'change',
    change_version: 'current',
    profile_id: 'test',
    stale: false,
  },
};
test('基线通过和过期修改不能冒充当前修改验收', () => {
  assert.deepEqual(reviewMissing(change), []);
  for (const latest_verification of [
    { ...change.latest_verification, purpose: 'baseline' },
    { ...change.latest_verification, stale: true },
    { ...change.latest_verification, change_version: 'old' },
    { ...change.latest_verification, status: 'failed' },
  ])
    assert.match(reviewMissing({ ...change, latest_verification }).join(), /当前修改版本尚未通过/);
  assert.match(reviewMissing({ ...change, acceptance_criteria: [] }).join(), /验收标准/);
  assert.equal(
    changeCanRecordExperience({
      ...change,
      latest_verification: { ...change.latest_verification, purpose: 'baseline' },
    }),
    false,
  );
});
test('要求基线时核对同一配置的有效原版本结果', () => {
  const profile = { id: 'test', baseline_required: true };
  assert.match(reviewMissing(change, profile).join(), /有效原版本基线/);
  assert.deepEqual(
    reviewMissing(change, profile, [
      { purpose: 'baseline', status: 'passed', profile_id: 'test', stale: false },
    ]),
    [],
  );
  assert.match(
    reviewMissing(change, profile, [
      { purpose: 'baseline', status: 'passed', profile_id: 'other' },
    ]).join(),
    /基线/,
  );
});
test('审核精确绑定当前版本，旧版本与缺失版本不能交付', () => {
  assert.equal(deliveryVersionCurrent({ ...change, review: { change_version: 'current' } }), true);
  assert.equal(deliveryVersionCurrent({ ...change, review: { change_version: 'old' } }), false);
  assert.equal(deliveryVersionCurrent({ review: { change_version: undefined } }), false);
  assert.equal(bytesLabel(1048576), '1.0 MB');
});
