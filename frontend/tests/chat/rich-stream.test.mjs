import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createAnswerBuffer,
  subscribeRunEvents,
} from '../../src/features/chat/lib/streamEvents.ts';
import { createContentParser, parseContent } from '../../src/features/chat/rich/parseContent.ts';

const block =
  '```rich-content\n{"version":1,"blocks":[{"id":"s","type":"step_flow","steps":[{"id":"a","title":"动作","description":"内容"}]}]}\n```';
test('任意 token 边界不会提前提交交互块，完整块提交后身份保持稳定', () => {
  const parse = createContentParser();
  for (let i = 1; i < block.length - 1; i++)
    assert.ok(parse(block.slice(0, i), true).every((segment) => segment.type !== 'rich'));
  // Markdown 围栏至少三个字符才闭合，完成后追加正文不重建已确认块。
  const complete = parse(block, true);
  assert.equal(complete[0].type, 'rich');
  assert.equal(parse(block + '\n\n新增文字', true)[0], complete[0]);
  assert.equal(parse(block + '\n\n新增文字', false)[0], complete[0]);
  assert.equal(parse('替换后的答案', true)[0].content, '替换后的答案');
});
test('取消/失败后的不完整块保留原文，历史恢复得到相同的已确认块', () => {
  const partial = block + '\n\n```rich-content\n{"version":1,';
  assert.deepEqual(
    parseContent(partial, true).map((s) => s.type),
    ['rich', 'markdown', 'pending'],
  );
  const stopped = parseContent(partial, false);
  assert.deepEqual(
    stopped.map((s) => s.type),
    ['rich', 'markdown', 'fallback'],
  );
  assert.ok(stopped[2].content.includes('"version":1,'));
  assert.deepEqual(parseContent(JSON.parse(JSON.stringify(partial))), stopped);
});
test('token 批量刷新、最终替换、停止与卸载均不串用旧数据', () => {
  const scheduled = new Map();
  let serial = 0,
    answer = '',
    updates = 0;
  const buffer = createAnswerBuffer(
    (text) => {
      answer += text;
      updates++;
    },
    (text) => {
      answer = text;
      updates++;
    },
    (callback) => {
      scheduled.set(++serial, callback);
      return serial;
    },
    (id) => scheduled.delete(id),
  );
  buffer.token('前');
  buffer.token('文');
  assert.equal(scheduled.size, 1);
  assert.equal(answer, '');
  [...scheduled.values()][0]();
  assert.equal(answer, '前文');
  assert.equal(updates, 1);
  buffer.token('旧片段');
  buffer.replace('核对后的回答');
  assert.equal(scheduled.size, 0);
  assert.equal(answer, '核对后的回答');
  buffer.token('末尾');
  buffer.finish();
  assert.equal(answer, '核对后的回答末尾');
  buffer.token('不应追加');
  buffer.finish('');
  assert.equal(answer, '');
  buffer.token('已切换会话');
  buffer.dispose();
  assert.equal(scheduled.size, 0);
});
test('真实事件订阅器去重重放、拒绝倒序与坏数据，清理后不处理旧事件', () => {
  const source = new EventTarget();
  let malformed = 0;
  const seen = [];
  const events = subscribeRunEvents(source, () => malformed++);
  events.listen('token', (payload) => seen.push(payload.text));
  const emit = (id, data) =>
    source.dispatchEvent(new MessageEvent('token', { lastEventId: String(id), data }));
  emit(1, '{"text":"a"}');
  emit(1, '{"text":"重复"}');
  emit(3, '{"text":"c"}');
  emit(2, '{"text":"倒序"}');
  emit(4, '{坏JSON');
  emit(5, '[]');
  emit(6, '{"text":"后续可用"}');
  assert.deepEqual(seen, ['a', 'c', '后续可用']);
  assert.equal(malformed, 2);
  events.dispose();
  emit(7, '{"text":"不能串入新会话"}');
  assert.equal(seen.length, 3);
});
