import test from 'node:test';
import assert from 'node:assert/strict';
import { filterCatalogRecords } from '../../src/features/handover/shared/catalogRecords.ts';
import {
  materialType,
  materialPreview,
} from '../../src/features/handover/materials/materialRecords.ts';

function record(id, kind, payload = {}, state = 'draft') {
  return { id, kind, title: id, state, payload, updated_at: '2026-10-16T08:00:00Z' };
}

test('资料搜索组合名称和提供人，历史访谈可检索且不混入问题或交接包', () => {
  const rows = [
    record('ZX2200 手册', 'source', { provider: '贺强', content: '镜头切换' }),
    record('现场访谈', 'interview', { author: '贺强', transcript: 'ZX2200 镜头偏移' }),
    record('ZX2200 交付', 'package', { recipient: '贺强' }),
    record('ZX2200 镜头', 'debug_issue', { recorded_by: '贺强' }),
  ];
  const original = structuredClone(rows);
  assert.deepEqual(
    filterCatalogRecords(rows, ['source', 'interview'], '  zx2200   贺强\n镜头 ', '').map(
      (row) => row.id,
    ),
    ['ZX2200 手册', '现场访谈'],
  );
  assert.deepEqual(filterCatalogRecords(rows, ['source'], '不存在', ''), []);
  assert.deepEqual(rows, original);
});

test('交接包状态和接收对象共同筛选，排序不改输入，归档记录由调用范围决定', () => {
  const rows = [
    record('older', 'package', { recipient: '客服', scope: 'DAF' }, 'confirmed'),
    {
      ...record('newer', 'package', { recipient: '客服', scope: 'DAF' }, 'confirmed'),
      updated_at: '2026-10-17T08:00:00Z',
    },
    record('draft', 'package', { recipient: '客服', scope: 'DAF' }),
    record('archived', 'package', { recipient: '客服', scope: 'DAF' }, 'archived'),
    record('source', 'source', { provider: '客服', content: 'DAF' }, 'confirmed'),
  ];
  const original = structuredClone(rows);
  assert.deepEqual(
    filterCatalogRecords(rows, ['package'], '客服 daf', 'confirmed').map((row) => row.id),
    ['newer', 'older'],
  );
  assert.deepEqual(
    filterCatalogRecords(rows, ['package'], '', 'archived').map((row) => row.id),
    ['archived'],
  );
  assert.deepEqual(filterCatalogRecords(rows, ['package'], '', 'unknown'), []);
  assert.deepEqual(filterCatalogRecords([], ['package'], '', ''), []);
  assert.deepEqual(rows, original);
});

test('资料分类涵盖文件、文字和源码，旧访谈仍为文字资料而不改写类型', () => {
  for (const format of ['pdf', 'docx', 'txt', 'custom', ''])
    assert.equal(materialType(record('file', 'source', { format })).value, 'file');
  for (const format of ['source', 'zip', 'cs', 'CPP', 'c', 'h'])
    assert.equal(materialType(record('code', 'source', { format })).value, 'code');
  const interview = record('old', 'interview', { transcript: '原文' });
  assert.equal(materialType(interview).value, 'text');
  assert.equal(interview.kind, 'interview');
  assert.equal(materialType(record('text', 'source', { format: 'text' })).value, 'text');
});

test('资料预览优先正文，扫描文档保留解析说明，无正文不生成虚构说明', () => {
  const source = record('manual', 'source', {
    content: '原始正文',
    notes: '备注',
    parse_notes: '解析信息',
  });
  assert.equal(materialPreview(source), '原始正文');
  assert.equal(
    materialPreview(record('scan', 'source', { parse_notes: '共 71 页，需补充文字' })),
    '共 71 页，需补充文字',
  );
  assert.equal(materialPreview(record('old', 'interview', { transcript: '访谈原文' })), '访谈原文');
  assert.equal(materialPreview(record('empty', 'source')), '');
  const long = record('long', 'source', { content: '字'.repeat(1000) });
  assert.equal(materialPreview(long).length, 600);
  assert.equal(long.payload.content.length, 1000);
});
