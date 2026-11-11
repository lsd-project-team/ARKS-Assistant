import test from 'node:test';
import assert from 'node:assert/strict';
import {
  splitManual,
  sectionForAnchor,
} from '../../src/features/knowledge/manuals/manualContent.ts';
import { manuals } from '../../src/features/knowledge/data/manualCatalog.ts';
import { presentationTopics } from '../../src/features/knowledge/data/presentation.ts';
import { archifyData } from '../../src/features/knowledge/data/archifyData.ts';
import { routeFromHash, routeHash } from '../../src/features/knowledge/routes.ts';

test('长文只按二级标题分章，代码里的标题不产生章节且正文完整保留', () => {
  const content =
    '# 总览\n\n前言\n\n## 执行条件\n\n```cs\n## 这不是标题\n```\n\n### 安全门\n条件\n\n## 失败处理\n保留原文';
  const result = splitManual(content);
  assert.deepEqual(
    result.sections.map((item) => item.title),
    ['概览与范围', '执行条件', '失败处理'],
  );
  assert.equal(result.sections.map((item) => item.content).join(''), content);
  assert.equal(sectionForAnchor(result, '安全门'), 1);
  assert.equal(sectionForAnchor(result, '不存在'), 0);
});

test('同名章节与内联代码标题保持稳定链接，分章后引用式链接仍能解析', () => {
  const result = splitManual(
    '# 标题\n\n## 条件 `A`\n[说明][ref]\n\n## 条件 `A`\n详情\n\n[ref]: 02-机器模型与流程调度.md',
  );
  assert.deepEqual(
    result.sections.map((item) => item.id),
    ['overview', '条件-a', '条件-a-1'],
  );
  assert.equal(sectionForAnchor(result, '条件-a-1'), 2);
  assert.match(result.sections[1].content, /\[ref\]: 02-机器模型/);
});

test('文档章节路由可刷新恢复，包含中文及特殊符号的章节不会变成其他参数', () => {
  const route = { kind: 'catalog', id: 'manual-32', section: '64-节点与信号-&-恢复' };
  assert.deepEqual(routeFromHash('#' + routeHash(route)), route);
  assert.deepEqual(routeFromHash('#catalog/manual-32'), { kind: 'catalog', id: 'manual-32' });
});

test('全部交付图保留目录入口和42篇正文资源，内部关联可供继续阅读', () => {
  assert.equal(manuals.length, 46);
  assert.equal(new Set(manuals.flatMap((entry) => entry.documents)).size, 42);
  assert.equal(new Set(manuals.map((entry) => entry.id)).size, 46);
  for (const entry of manuals) {
    assert.ok(archifyData.flowchartCatalog.entries.some((item) => item.id === entry.id));
    for (const topic of entry.topicIds)
      assert.ok(
        presentationTopics.find((item) => item.id === topic)?.diagrams.includes(entry.id),
        `${entry.id}/${topic}`,
      );
  }
});

test('模块图解目录标题区分总览、调度和按钮细节入口', () => {
  const titles = Object.fromEntries(
    manuals
      .filter((entry) => /^manual-(3[1-9]|4[0-4])$/.test(entry.id))
      .map((entry) => [entry.id, entry.title]),
  );
  assert.equal(titles['manual-31'], '料单元系统·总览与主流程');
  assert.equal(titles['manual-43'], '料单元系统·按钮与交互细节');
  assert.equal(titles['manual-32'], '固晶系统·调度与动作节点总览');
  assert.equal(titles['manual-33'], '固晶系统·界面与按钮流程细节');
  assert.equal(titles['manual-34'], '晶圆系统·模型、实体与调度总览');
  assert.equal(titles['manual-35'], '晶圆系统·界面与按钮流程细节');
});
