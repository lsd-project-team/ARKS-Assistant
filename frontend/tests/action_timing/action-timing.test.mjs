import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { parseTimingHash, timingHash } from '../../src/features/action_timing/navigation.ts';
import { adminRoute } from '../../src/features/admin/navigation.ts';
import { scopedApiUrl } from '../../src/shared/api/apiRoutes.ts';

test('刷新和历史导航恢复耗时项目，交接导航继续独立工作', () => {
  const hash = timingHash('project-a');
  assert.deepEqual(parseTimingHash(`#${hash}`), {
    open: true,
    timingProjectId: 'project-a',
  });
  assert.equal(parseTimingHash('#handover/overview').open, false);
  assert.equal(parseTimingHash('#action-timing-other').open, false);
  assert.equal(adminRoute(`#${hash}`).page, 'action-timing');
  assert.equal(adminRoute(`#${hash}`).valid, true);
  assert.equal(adminRoute('#handover/materials').page, 'handover');
});

test('耗时项目使用独立地址，切换聊天项目不改变台账请求', () => {
  const ledger = '/action-timing/ledger?timing_project=device-a';
  for (const chat of ['chat-a', 'chat-b', 'independent']) {
    assert.equal(scopedApiUrl(ledger, chat), '/api' + ledger);
    assert.equal(scopedApiUrl('/action-timing/projects', chat), '/api/action-timing/projects');
    assert.equal(
      scopedApiUrl('/action-timing/ledger/export?timing_project=device-a', chat),
      '/api/action-timing/ledger/export?timing_project=device-a',
    );
  }
  assert.equal(parseTimingHash('#action-timing').timingProjectId, '');
  assert.equal(parseTimingHash('#action-timing?project=old-scope').timingProjectId, 'old-scope');
  assert.equal(timingHash('device-a'), 'action-timing?timing_project=device-a');
  assert.equal(scopedApiUrl('/threads', 'chat-a'), '/api/p/chat-a/threads');
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
  assert.ok(page.includes('动作耗时表'));
  assert.ok(page.includes('添加动作'));
  assert.ok(page.includes('ImportDialog'));
  assert.ok(page.includes('CategoryManager'));
  assert.ok(!page.includes('sourceTimingClient'));
});
