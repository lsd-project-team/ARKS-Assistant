import test from 'node:test';
import assert from 'node:assert/strict';
import { restoredMessageJump } from '../../src/features/chat/lib/chatNavigation.ts';
import { conversationGroup } from '../../src/features/chat/lib/conversationList.ts';

test('阅读历史恢复锚点，跟随最新时不加载旧页', () => {
  assert.equal(
    restoredMessageJump({ anchor: 'old-message', offset: 20, following: false }).id,
    'old-message',
  );
  assert.equal(restoredMessageJump({ anchor: 'last-message', offset: 0, following: true }).id, '');
  assert.equal(restoredMessageJump().id, '');
});

test('置顶先显示，同一天的会话保持服务端顺序', () => {
  const now = new Date(2026, 9, 10, 12);
  const rows = [
    { id: 'pin', title: '置顶', pinned_order: 0, updated_at: '2026-10-01T00:00:00' },
    { id: 'today', title: '今天', updated_at: '2026-10-10T10:00:00' },
    { id: 'yesterday', title: '昨天', updated_at: '2026-10-09T10:00:00' },
  ];
  assert.deepEqual(
    rows.map((row) => conversationGroup(row, now)),
    ['置顶', '今天', '昨天'],
  );
});
