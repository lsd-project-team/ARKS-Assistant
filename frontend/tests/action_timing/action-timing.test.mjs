import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { parseTimingHash, timingHash } from '../../src/features/action_timing/navigation.ts';
import {
  eventDuration,
  milliseconds,
  branchLabel,
} from '../../src/features/action_timing/format.ts';
import { adminRoute } from '../../src/features/admin/navigation.ts';

test('刷新和历史导航恢复所属项目及批次，交接导航继续独立工作', () => {
  const hash = timingHash('project-a', 'run-b');
  assert.deepEqual(parseTimingHash(`#${hash}`), {
    open: true,
    projectId: 'project-a',
    runId: 'run-b',
  });
  assert.equal(parseTimingHash('#handover/overview').open, false);
  assert.equal(parseTimingHash('#action-timing-other').open, false);
  assert.equal(adminRoute(`#${hash}`).page, 'action-timing');
  assert.equal(adminRoute(`#${hash}`).valid, true);
  assert.equal(adminRoute('#handover/materials').page, 'handover');
});

test('未完成和无样本不渲染为零，实际零耗时可显示', () => {
  assert.equal(milliseconds(null), '—');
  assert.equal(milliseconds(undefined), '—');
  assert.equal(milliseconds(NaN), '—');
  assert.equal(milliseconds(0), '0');
  assert.equal(eventDuration({ start_ms: 10, end_ms: null }), null);
  assert.equal(eventDuration({ start_ms: 10, end_ms: 22.5 }), 12.5);
  assert.notEqual(
    branchLabel('drycycle.uplook.one_point'),
    branchLabel('drycycle.uplook.two_point'),
  );
});

test('两个角色都有入口，工作区导航把统计放在交接下面', () => {
  const workspace = readFileSync(
    new URL('../../src/app/layouts/WorkspaceNavigation.tsx', import.meta.url),
    'utf8',
  );
  const admin = readFileSync(
    new URL('../../src/features/admin/AdminShell.tsx', import.meta.url),
    'utf8',
  );
  assert.ok(workspace.indexOf('title="交接工作台"') < workspace.indexOf('title="动作耗时统计"'));
  assert.ok(admin.includes("id: 'action-timing'"));
  const page = readFileSync(
    new URL('../../src/features/action_timing/ActionTimingPage.tsx', import.meta.url),
    'utf8',
  );
  assert.ok(page.includes('采集器测试数据'));
  assert.ok(page.includes('暂不计算成功耗时分布'));
});
