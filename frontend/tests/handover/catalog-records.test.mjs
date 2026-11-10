import test from 'node:test';
import assert from 'node:assert/strict';
import { filterCatalogRecords } from '../../src/features/handover/shared/catalogRecords.ts';
import {
  materialFiles,
  materialName,
} from '../../src/features/handover/materials/materialRecords.ts';

function record(id, kind, payload = {}, state = 'draft') {
  return {
    id,
    kind,
    title: id,
    state,
    payload,
    created_at: '2026-10-16T08:00:00Z',
    updated_at: '2026-10-16T08:00:00Z',
  };
}

test('资料搜索组合名称和提供人，原文可检索且不混入问题或交接包', () => {
  const rows = [
    record('ZX2200 手册', 'source', { provider: '贺强', content: '镜头切换' }),
    record('现场笔记', 'source', { provider: '贺强', content: 'ZX2200 镜头偏移' }),
    record('ZX2200 交付', 'package', { recipient: '贺强' }),
    record('ZX2200 镜头', 'debug_issue', { recorded_by: '贺强' }),
  ];
  const original = structuredClone(rows);
  assert.deepEqual(
    filterCatalogRecords(rows, ['source'], '  zx2200   贺强\n镜头 ', '').map((row) => row.id),
    ['ZX2200 手册', '现场笔记'],
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

test('原文件按名称与实际上传人搜索，不搜索隐藏正文；按上传时间排序且不改输入', () => {
  const older = {
    ...record('旧标题', 'source', { content: '隐藏正文', provider: '原作者' }),
    created_by: '上传甲',
    original_file: { name: '手册.PDF', previewable: true },
  };
  const newer = {
    ...record('新文件', 'source'),
    created_at: '2026-10-17T08:00:00Z',
    created_by: '上传乙',
  };
  const legacy = record('文本资料', 'source', { content: '旧正文' });
  const rows = [
    older,
    newer,
    legacy,
    record('已移出', 'source', {}, 'archived'),
    record('任务', 'task'),
  ];
  const original = structuredClone(rows);
  assert.equal(materialName(older), '手册.PDF');
  assert.deepEqual(
    materialFiles(rows, ' 手册   上传甲 ').map((row) => row.id),
    ['旧标题'],
  );
  assert.deepEqual(materialFiles(rows, '隐藏正文'), []);
  assert.deepEqual(materialFiles(rows, '原作者'), []);
  assert.deepEqual(
    materialFiles(rows).map((row) => row.id),
    ['新文件', '旧标题', '文本资料'],
  );
  assert.deepEqual(rows, original);
});
