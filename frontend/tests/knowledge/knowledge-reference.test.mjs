import test from 'node:test';
import assert from 'node:assert/strict';
import {
  handoverDocumentText,
  handoverReference,
  isKnowledgeReference,
} from '../../src/features/knowledge/lib/knowledgeReference.ts';

test('用户端与管理端都保留三类内部引用，不允许其他协议充当资料引用', () => {
  for (const href of ['source:Program.cs#L1', 'debug-issue:issue/2', 'handover-source:source/3#L2'])
    assert.equal(isKnowledgeReference(href), true);
  for (const href of [
    'javascript:alert(1)',
    'data:text/html,private',
    'https://example.com',
    'xsource:other',
    'material:p/m/2#L1',
  ])
    assert.equal(isKnowledgeReference(href), false);
});

test('历史交接引用保留记录、版本和行号，拒绝不完整或越界范围', () => {
  assert.deepEqual(handoverReference('debug-issue:issue-id/2'), {
    kind: 'debug-issue',
    id: 'issue-id',
    version: 2,
    start: 1,
    end: 1,
  });
  assert.deepEqual(handoverReference('handover-source:source-id/3#L2-L5'), {
    kind: 'handover-source',
    id: 'source-id',
    version: 3,
    start: 2,
    end: 5,
  });
  for (const href of [
    'handover-source:id/2',
    'debug-issue:id/0',
    'handover-source:id/2#L5-L1',
    'debug-issue:../2',
    'handover-source:id/2#L0',
    'debug-issue:id/9007199254740992',
  ])
    assert.equal(handoverReference(href), undefined);
});

test('普通资料保留原文与行号，旧访谈资料按既有正文结构读取', () => {
  assert.equal(
    handoverDocumentText({ kind: 'source', payload: { content: '第一行\n第二行' } }),
    '第一行\n第二行',
  );
  assert.equal(
    handoverDocumentText({
      kind: 'interview',
      payload: { topic: '调试记录', transcript: '现场描述' },
    }),
    '主题：调试记录\n访谈原文：现场描述',
  );
});
