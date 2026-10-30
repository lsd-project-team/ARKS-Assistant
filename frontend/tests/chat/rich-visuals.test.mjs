import test from 'node:test';
import assert from 'node:assert/strict';
import { parseDocument } from '../../src/features/chat/rich/schema.ts';
import { chartOptions, mindmapOptions } from '../../src/features/chat/rich/chartOptions.ts';
import { contentToMarkdown } from '../../src/features/chat/rich/contentToMarkdown.ts';
import { init, use } from 'echarts/core';
import { BarChart, LineChart, PieChart, TreeChart } from 'echarts/charts';
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
import { SVGRenderer } from 'echarts/renderers';

use([
  BarChart,
  LineChart,
  PieChart,
  TreeChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  SVGRenderer,
]);
const chart = {
  id: 'c',
  type: 'chart',
  chart_type: 'bar',
  title: '测试输入',
  labels: ['甲', '乙', '丙'],
  series: [{ id: 's', name: '原始数值', values: [0, 7, null] }],
};
const parse = (block, recover = false) =>
  parseDocument(JSON.stringify({ version: 1, blocks: [block] }), recover);
const svg = (option) => {
  const instance = init(null, null, { renderer: 'svg', ssr: true, width: 640, height: 400 });
  try {
    instance.setOption(option);
    return instance.renderToSVGString();
  } finally {
    instance.dispose();
  }
};

test('ECharts 实际绘制柱、线、饼图，零值与缺失值不被补造', () => {
  for (const type of ['bar', 'line', 'pie']) {
    const block = { ...chart, chart_type: type };
    assert.ok(parse(block).document);
    const option = chartOptions(block);
    assert.equal(option.tooltip.renderMode, 'richText');
    const markup = svg(option);
    assert.match(markup, /<svg/);
    assert.match(markup, /甲/);
    assert.equal(option.series.length, 1);
    if (type !== 'pie') assert.deepEqual(option.series[0].data, [0, 7, null]);
    else
      assert.deepEqual(option.series[0].data, [
        { name: '甲', value: 0 },
        { name: '乙', value: 7 },
      ]);
  }
});

test('图表拒绝错列、空值、非数值、无穷大、未知选项和负数饼图；相邻内容继续展示', () => {
  const invalid = [
    { ...chart, labels: [] },
    { ...chart, labels: ['甲'] },
    { ...chart, series: [] },
    { ...chart, series: [{ id: 's', name: 'n', values: [null, null, null] }] },
    { ...chart, series: [{ id: 's', name: 'n', values: ['7', 0, 1] }] },
    { ...chart, chart_type: 'pie', series: [{ id: 's', name: 'n', values: [-1, 0, 1] }] },
    { ...chart, option: { formatter: '() => alert(1)' } },
    { ...chart, labels: Array(501).fill('x') },
    { ...chart, chart_type: 'custom' },
  ];
  for (const block of invalid) {
    assert.ok(parse(block).error, JSON.stringify(block));
    const result = parseDocument(
      JSON.stringify({
        version: 1,
        blocks: [block, { id: 'next', type: 'text', content: '保留' }],
      }),
      true,
    );
    assert.equal(result.document.blocks[0].type, 'unsupported');
    assert.equal(result.document.blocks[1].content, '保留');
  }
  // JSON 不能表达 Infinity，直接传入配置转换器验证该边界。
  assert.throws(
    () => chartOptions({ ...chart, series: [{ id: 's', name: 'n', values: [Infinity, 0, 1] }] }),
    /有限数值/,
  );
});

test('思维导图校验单根、缺失父节点和循环，并实际绘制树及复制层级', () => {
  const map = {
    id: 'm',
    type: 'mindmap',
    title: '测试层级',
    nodes: [
      { id: 'root', label: '中心' },
      { id: 'a', label: '分支', parent_id: 'root' },
    ],
  };
  assert.ok(parse(map).document);
  assert.match(svg(mindmapOptions(map)), /中心/);
  const text = contentToMarkdown(
    '```rich-content\n' + JSON.stringify({ version: 1, blocks: [map, chart] }) + '\n```',
  );
  assert.match(text, /中心 → 分支/);
  assert.match(text, /\| 甲 \| 0 \|/);
  for (const nodes of [
    [],
    [
      { id: 'a', label: 'A' },
      { id: 'b', label: 'B' },
    ],
    [
      { id: 'r', label: 'R' },
      { id: 'a', label: 'A', parent_id: 'missing' },
    ],
    [
      { id: 'r', label: 'R' },
      { id: 'a', label: 'A', parent_id: 'b' },
      { id: 'b', label: 'B', parent_id: 'a' },
    ],
  ])
    assert.ok(parse({ ...map, nodes }).error);
});

test('文件只接受已有资料 ID，Mermaid 不接受配置覆盖或链接交互', () => {
  assert.ok(
    parse({ id: 'f', type: 'file', record_id: 'existing-record', name: '资料.pdf', version: 2 })
      .document,
  );
  assert.ok(parse({ id: 'f', type: 'file', record_id: '../private', name: 'bad' }).error);
  assert.ok(
    parse({ id: 'f', type: 'file', record_id: 'r', name: 'bad', url: 'javascript:bad()' }).error,
  );
  for (const content of [
    '%%{init: {"securityLevel":"loose"}}%%\nflowchart LR\nA-->B',
    '---\nconfig: {}\n---\nflowchart LR\nA-->B',
    'flowchart LR\nA-->B\nclick A "https://evil.test"',
  ])
    assert.ok(parse({ id: 'm', type: 'mermaid', content }).error);
});
