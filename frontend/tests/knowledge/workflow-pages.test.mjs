import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { presentationTopics } from '../../src/features/knowledge/data/presentation.ts';
import { archifyData } from '../../src/features/knowledge/data/archifyData.ts';
import { readingGraphPaths } from '../../src/features/knowledge/data/readingDestinations.ts';
import { routeFromHash } from '../../src/features/knowledge/routes.ts';
import { sourceGuides } from '../../src/features/knowledge/sourceGuides.ts';
import { manuals } from '../../src/features/knowledge/data/manualCatalog.ts';

const result = await build({
  stdin: {
    contents:
      "export * from './src/features/knowledge/KnowledgePages.tsx'; export { coordinateVisual } from './src/features/knowledge/coordinates/CoordinateReader.tsx'; export { functionalVisual } from './src/features/knowledge/atlas/AtlasReader.tsx';",
    resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
    loader: 'tsx',
  },
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
  jsx: 'automatic',
  metafile: true,
  loader: { '.css': 'empty' },
  plugins: [
    {
      name: 'inline-css',
      setup(build) {
        build.onResolve({ filter: /\.css\?inline$/ }, ({ path }) => ({
          path,
          namespace: 'css-text',
        }));
        build.onLoad({ filter: /.*/, namespace: 'css-text' }, () => ({
          contents: 'export default "";',
          loader: 'js',
        }));
      },
    },
  ],
});
const module = { exports: {} };
new Function('require', 'module', 'exports', result.outputFiles[0].text)(
  createRequire(import.meta.url),
  module,
  module.exports,
);
const { DiagramDetail, GraphAtlas, coordinateVisual, functionalVisual } = module.exports;
const render = (component, props) =>
  renderToStaticMarkup(createElement(component, { navigate() {}, ...props }));
const renderLegacyReading = (id) => {
  const route = routeFromHash('#topic/' + id);
  assert.ok(['graph', 'catalog'].includes(route.kind));
  return render(DiagramDetail, { id: route.slug ?? route.id, theme: 'light' });
};

test('46张导入图保留图解并返回图谱目录，旧章节链接继续可读', () => {
  for (const entry of manuals) {
    const html = render(DiagramDetail, { id: entry.id, theme: 'light' });
    assert.ok(html.includes(entry.title), entry.id);
    assert.match(html, /data-diagram-source="[^"]*manuals\//);
    assert.doesNotMatch(html, /详细说明|reader-document|role="tab/);
    const legacy = render(DiagramDetail, {
      id: entry.id,
      section: entry.detailAnchor,
      theme: 'light',
    });
    assert.match(legacy, /data-diagram-source=/);
    assert.doesNotMatch(legacy, /详细说明|reader-document|role="tab/);
    assert.match(html, /全部图谱/);
    assert.doesNotMatch(html, /专题|#topic\//);
  }
});

test('23个旧专题的说明和全部阅读环节迁入对应图谱，移除专题入口', () => {
  for (const topic of presentationTopics) {
    const html = renderLegacyReading(topic.id);
    assert.ok(html.includes(topic.summary), topic.id);
    assert.ok(html.includes(topic.purpose), topic.id);
    for (const note of [...topic.conditions, ...topic.exceptions])
      assert.ok(html.includes(renderToStaticMarkup(createElement('li', null, note))), topic.id);
    for (const flow of sourceGuides.find((guide) => guide.topic === topic.id)?.flows ?? [])
      assert.ok(html.includes(flow.title), topic.id + '/' + flow.id);
    assert.doesNotMatch(html, /全部专题|阅读专题|返回业务专题|href="#topic\//);
    assert.doesNotMatch(
      html,
      /源码模块结构|关联源码模块|源码依据|查看依据|查看协作依据|source-evidence|source-module|<pre/,
    );
  }
  assert.ok(
    Object.keys(result.metafile.inputs).every(
      (path) =>
        !/source-evidence\.json|EngineeringViews|engineeringData|ManualDocument|ManualMermaid|ReaderTabs/.test(
          path,
        ),
    ),
  );
});

test('生产流程保留原图、节点说明和协作条件，移除节点依据', () => {
  for (const graph of archifyData.graphs) {
    const html = render(DiagramDetail, {
      id: graph.slug,
      theme: 'light',
      focusedSignal: graph.nodes[0].signals[0] || 'unknown',
    });
    assert.match(html, /data-diagram-source=/);
    assert.match(html, /节点说明/);
    assert.doesNotMatch(html, /reader-document|role="tab/);
    assert.doesNotMatch(
      html,
      /源码依据|查看依据|查看协作依据|evidence-item|source-file|source-method|<pre/,
    );
  }
});

test('G0 从专题和图谱目录进入同一阅读页，使用 Archify 交付图', () => {
  const topic = renderLegacyReading('g0');
  const catalog = render(DiagramDetail, { id: 'g0-coordinate-system', theme: 'light' });
  assert.equal(catalog, topic);
  assert.match(topic, /data-archify-source="g0-archify\/device-overview\.html"/);
  assert.doesNotMatch(topic, /<svg[^>]+role="img"|g0-map-wide|g0-map-compact/);
  for (const label of [
    '坐标关系',
    '普通转换',
    '相机转换',
    '加载与保存',
    '标定与修正',
    '生产应用',
    '使用边界',
  ])
    assert.ok(topic.includes(label), label);
  assert.doesNotMatch(topic, /原图尚未生成|业务介绍|展开专题概览与协作条件/);
  assert.equal((topic.match(/<h1>/g) ?? []).length, 1);
});

test('G0 三张关系图都引用实际 Archify HTML，公式与数值例子继续留在节点内', () => {
  for (const [flow, step, source] of [
    ['g0-relations', 'reference', 'device-overview'],
    ['g0-relations', 'product', 'product-reading'],
    ['g0-camera', 'inputs', 'camera-overview'],
  ]) {
    const html = renderToStaticMarkup(coordinateVisual(flow, step));
    assert.ok(html.includes(`data-archify-source="g0-archify/${source}.html"`));
    assert.equal((html.match(/<figure/g) ?? []).length, 1);
    assert.match(html, /完整图谱/);
    assert.doesNotMatch(html, /图内可放大、拖动查看/);
  }
  assert.match(renderToStaticMarkup(coordinateVisual('g0-general', 'forward')), /cos θ/);
  assert.match(renderToStaticMarkup(coordinateVisual('g0-general', 'example')), /<table>/);
});

test('全部图谱包含可进入的 G0 内嵌阅读入口，既有独立图谱仍可展示', () => {
  const html = render(GraphAtlas, {});
  assert.doesNotMatch(html, /专题|card-topic|topic-card/);
  assert.equal((html.match(/查看图谱/g) ?? []).length, 121);
  assert.match(html, /设备、产品和相机中的位置怎样转换为同一个 G0 目标/);
  const entry = archifyData.flowchartCatalog.entries.find(
    (item) => item.id === 'g0-coordinate-system',
  );
  assert.equal(entry.inlineTopic, 'g0');
  assert.equal(
    archifyData.flowchartCatalog.counts.total,
    archifyData.flowchartCatalog.entries.length,
  );
  const startup = render(DiagramDetail, { id: 'startup-workflow', theme: 'light' });
  assert.match(startup, /data-diagram-source=/);
  assert.doesNotMatch(startup, /g0-reader/);
});

test('产品专题与目录共用整宽阅读页，并复用父链原图和定位更新交付', () => {
  const topic = renderLegacyReading('product-coordinates');
  const catalog = render(DiagramDetail, { id: 'product-coordinate-lifecycle', theme: 'light' });
  assert.equal(catalog, topic);
  for (const text of [
    '对象与父级',
    '实例展开与顺序',
    '定位参考点与角度',
    '结果写回与后续目标',
    '工位偏移与焊点补偿',
  ])
    assert.ok(topic.includes(text));
  assert.match(topic, /class="atlas-reader"/);
  assert.match(topic, /href="#catalog\/g0-coordinate-system"/);
  for (const [flow, step, source] of [
    ['product-hierarchy', 'chain', 'g0-archify/product-reading.html'],
    ['product-update', 'overview', 'functional-atlas/product-update.html'],
  ]) {
    const figure = renderToStaticMarkup(functionalVisual(flow, step));
    assert.ok(figure.includes(`data-archify-source="${source}"`));
    assert.equal((figure.match(/<figure/g) ?? []).length, 1);
  }
});

test('公共视觉默认先展示实际单点链路，保留六个环节和产品写回链接', () => {
  const topic = renderLegacyReading('public-vision');
  assert.equal(topic, render(DiagramDetail, { id: 'public-vision-process', theme: 'light' }));
  for (const text of [
    '模板与初始化',
    '采图与定位',
    '结果与距离检查',
    '产品各层怎样调用',
    '身份识别与墨点',
    '失败处理与修改模板',
  ])
    assert.ok(topic.includes(text));
  assert.ok(topic.includes('data-archify-source="functional-atlas/vision-point.html"'));
  assert.match(topic, /href="#catalog\/product-coordinate-lifecycle"/);
  assert.doesNotMatch(topic, /源码依据|source-evidence|<pre/);
});

test('相机标定专题绑定 S2 调度图，并提供保存与复核的对照表', () => {
  const topic = renderLegacyReading('camera-calibration');
  assert.equal(topic, render(DiagramDetail, { id: 'camera-calibration-process', theme: 'light' }));
  assert.ok(topic.includes('data-archify-source="functional-atlas/camera-calibration.html"'));
  for (const text of [
    '自动标定入口',
    '点胶与 Bond 采点',
    '上视坐标与位置',
    '晶圆相机与晶圆台',
    '焊头偏移与旋转',
    '保存与复核',
    '对中与自动对焦',
    '独立方法的差异',
  ])
    assert.ok(topic.includes(text));
  const table = renderToStaticMarkup(functionalVisual('cc-persistence', 'order'));
  assert.match(table, /<table>/);
  assert.match(table, /BMC 测高结果立即保存设备参数/);
  assert.match(table, /最终两角度复核/);
});

test('安全运动专题展示实际高度分支，并保留 XY 恢复原 Z 的差异', () => {
  const topic = renderLegacyReading('motion-safety');
  assert.equal(topic, render(DiagramDetail, { id: 'safe-motion-process', theme: 'light' }));
  assert.ok(topic.includes('data-archify-source="functional-atlas/safe-motion-branches.html"'));
  for (const text of [
    '目标与软限位',
    '安全高度来源',
    '二维三维四维',
    '生产区域切换',
    '碰撞圆与规划工具',
    '插补与驱动',
    '等待、异常与停止',
  ])
    assert.ok(topic.includes(text), text);
  assert.match(topic, /href="#graph\/failure-recovery-workflow"/);
  const table = renderToStaticMarkup(functionalVisual('sm-order', 'table'));
  assert.equal((table.match(/<tbody>[\s\S]*?<\/tbody>/)?.[0].match(/<tr>/g) ?? []).length, 5);
  assert.match(table, /安全 Z → XY → 恢复原 Z/);
  assert.match(table, /“含 T”只适用于 XYZT/);
});

test('工具校准专题共用阅读页，独立入口与七行保存边界均可阅读', () => {
  const topic = renderLegacyReading('tool-calibration');
  assert.equal(topic, render(DiagramDetail, { id: 'tool-calibration-process', theme: 'light' }));
  assert.ok(topic.includes('data-archify-source="functional-atlas/tool-calibration-entry.html"'));
  for (const title of [
    '入口与组合状态',
    '吸嘴中心示教',
    '吸嘴高度示教',
    '吸嘴自动校准',
    '单顶针与重教',
    '全部顶针旧接口',
    '取片偏移校准',
    '保存取消与工具',
  ])
    assert.ok(topic.includes(title), title);
  assert.match(topic, /href="#catalog\/camera-calibration-process"/);
  const table = renderToStaticMarkup(functionalVisual('tc-results', 'persistence'));
  assert.equal((table.match(/<tbody>[\s\S]*?<\/tbody>/)?.[0].match(/<tr>/g) ?? []).length, 7);
  assert.match(table, /收尾保存代码已注释/);
  assert.match(table, /Fail \/ Exception 也进入/);
  assert.match(table, /缺模板或定位失败早退后仍会调用保存/);
});

test('全局标定专题区分新区域与旧驱动链，并保留八条保存路径', () => {
  const topic = renderLegacyReading('global-calibration');
  assert.equal(topic, render(DiagramDetail, { id: 'global-calibration-process', theme: 'light' }));
  assert.ok(topic.includes('data-archify-source="functional-atlas/global-region-chain.html"'));
  for (const title of [
    '扫描点与范围',
    '扫描与温漂',
    '区域补偿',
    '点序与文件',
    '旧版单轴与模式',
    '旧版二维采集',
    '驱动生成与开关',
    'Bond 偏移标定',
    'BC 偏移关系',
    '暂停停止与保存',
  ])
    assert.ok(topic.includes(title), title);
  const driver = renderToStaticMarkup(functionalVisual('gc-driver', 'overview'));
  assert.ok(driver.includes('data-archify-source="functional-atlas/global-driver-mapping.html"'));
  assert.match(topic, /href="#catalog\/safe-motion-process"/);
  const table = renderToStaticMarkup(functionalVisual('gc-completion', 'persistence'));
  assert.equal((table.match(/<tbody>[\s\S]*?<\/tbody>/)?.[0].match(/<tr>/g) ?? []).length, 8);
  assert.match(table, /没有同样的尾部域保存/);
  assert.match(table, /替换之前先保存旧域/);
  assert.match(table, /域配置由保存按钮写入/);
});

test('光源专题共用目录入口，区分硬件、采集、缓存和视觉换算', () => {
  const topic = renderLegacyReading('lightness');
  assert.equal(topic, render(DiagramDetail, { id: 'lightness-process', theme: 'light' }));
  for (const title of [
    '相机与灯光',
    '手动调光与同步',
    '亮度采集与保存',
    '映射补全与缓存',
    '视觉中的正反向',
  ])
    assert.ok(topic.includes(title), title);
  assert.equal((topic.match(/<tbody>[\s\S]*?<\/tbody>/)?.[0].match(/<tr>/g) ?? []).length, 5);
  assert.match(topic, /下视环光（同名共用）/);
  const capture = renderToStaticMarkup(functionalVisual('lc-acquisition', 'overview'));
  const alarm = renderToStaticMarkup(functionalVisual('lc-application', 'overview'));
  assert.ok(capture.includes('data-archify-source="functional-atlas/lightness-calibration.html"'));
  assert.ok(alarm.includes('data-archify-source="functional-atlas/lightness-alarm-edit.html"'));
});

test('测高专题共用目录入口，读数和保存分表并保留两条实际结果链', () => {
  const topic = renderLegacyReading('height-measurement');
  assert.equal(topic, render(DiagramDetail, { id: 'height-measurement-process', theme: 'light' }));
  for (const title of [
    '入口与读数口径',
    'S1 探针与激光',
    'S2 焊头与激光',
    '物料多点与回写',
    '产品测高点示教',
    '固晶水平',
    'S1/S2 平面度',
    '多高度测量',
    '距离与标准工具',
    '结果与保存出口',
  ])
    assert.ok(topic.includes(title), title);
  assert.equal((topic.match(/<tbody>[\s\S]*?<\/tbody>/)?.[0].match(/<tr>/g) ?? []).length, 7);
  assert.match(topic, /原始|传感器读数/);
  const persistence = renderToStaticMarkup(functionalVisual('mh-results', 'persistence'));
  assert.equal((persistence.match(/<tbody>[\s\S]*?<\/tbody>/)?.[0].match(/<tr>/g) ?? []).length, 7);
  assert.match(persistence, /Save 先于点击处理中的新点列赋值/);
  assert.match(persistence, /Count &gt; 100/);
  for (const [flow, id] of [
    ['mh-product', 'height-s1-writeback'],
    ['mh-flatness', 'height-flat-batch'],
  ])
    assert.ok(
      renderToStaticMarkup(functionalVisual(flow, 'overview')).includes(
        'data-archify-source="functional-atlas/' + id + '.html"',
      ),
    );
  assert.match(topic, /href="#catalog\/global-calibration-process"/);
});

test('力控专题与目录共用阅读页，读数和保存分表并保留真实驱动及换算图', () => {
  const topic = renderLegacyReading('force-control');
  assert.equal(topic, render(DiagramDetail, { id: 'force-control-process', theme: 'light' }));
  for (const title of [
    '入口与读数',
    '启动与驱动分派',
    '固高大小力采样',
    'ETEL 采样差异',
    '目标与反馈换算',
    '设定、复位与清零',
    '生产取放与末次力',
    '平台、力与 LVDT 曲线',
    '力值检验与诊断',
    '保存与有效范围',
  ])
    assert.ok(topic.includes(title), title);
  assert.equal((topic.match(/<tbody>[\s\S]*?<\/tbody>/)?.[0].match(/<tr>/g) ?? []).length, 7);
  assert.match(topic, /未先除 32767/);
  assert.match(topic, /仅力模式且非 ETEL/);
  const persistence = renderToStaticMarkup(functionalVisual('fc-results', 'persistence'));
  assert.equal((persistence.match(/<tbody>[\s\S]*?<\/tbody>/)?.[0].match(/<tr>/g) ?? []).length, 8);
  assert.match(persistence, /单独刷新按钮未在同处 Save/);
  assert.match(persistence, /不是跨文件事务/);
  for (const [flow, id] of [
    ['fc-start', 'force-calibration-overview'],
    ['fc-conversion', 'force-input-overview'],
  ])
    assert.ok(
      renderToStaticMarkup(functionalVisual(flow, 'overview')).includes(
        'data-archify-source="functional-atlas/' + id + '.html"',
      ),
    );
  assert.match(topic, /href="#catalog\/height-measurement-process"/);
  assert.match(topic, /href="#catalog\/safe-motion-process"/);
});

test('工具库专题与目录共用阅读页，区分四种状态并绑定保存表和真实换嘴图', () => {
  const topic = renderLegacyReading('tool-bank');
  assert.equal(topic, render(DiagramDetail, { id: 'tool-bank-process', theme: 'light' }));
  assert.match(topic, /data-archify-source="functional-atlas\/tool-change-overview.html"/);
  const states = renderToStaticMarkup(functionalVisual('nb-identity', 'overview'));
  for (const state of ['工具实体', '工具槽位', '当前工具', '物理在位'])
    assert.ok(states.includes(state), state);
  assert.equal((states.match(/<tbody>[\s\S]*?<\/tbody>/)?.[0].match(/<tr>/g) ?? []).length, 4);
  const persistence = renderToStaticMarkup(functionalVisual('nb-results', 'persistence'));
  assert.equal((persistence.match(/<tbody>[\s\S]*?<\/tbody>/)?.[0].match(/<tr>/g) ?? []).length, 6);
  assert.match(persistence, /取消不统一回滚/);
  const change = renderToStaticMarkup(functionalVisual('nb-change', 'overview'));
  assert.match(change, /data-archify-source="functional-atlas\/tool-change-overview.html"/);
  assert.match(topic, /href="#catalog\/tool-calibration-process"/);
  assert.match(topic, /href="#catalog\/safe-motion-process"/);
});

test('维护专题默认展示清嘴图，目录共用并区分六个手动入口与八类保存', () => {
  const topic = renderLegacyReading('manual-maintenance');
  assert.equal(topic, render(DiagramDetail, { id: 'manual-maintenance-process', theme: 'light' }));
  assert.match(topic, /data-archify-source="functional-atlas\/nozzle-clean-overview.html"/);
  const entries = renderToStaticMarkup(functionalVisual('mn-manual', 'overview'));
  assert.equal((entries.match(/<tbody>[\s\S]*?<\/tbody>/)?.[0].match(/<tr>/g) ?? []).length, 6);
  assert.match(entries, /直接传出胶 true/);
  const saves = renderToStaticMarkup(functionalVisual('mn-results', 'persistence'));
  assert.equal((saves.match(/<tbody>[\s\S]*?<\/tbody>/)?.[0].match(/<tr>/g) ?? []).length, 8);
  assert.match(saves, /早于实际清洁/);
  assert.match(saves, /该方法自身未 Save/);
  for (const link of ['tool-bank', 'height-measurement', 'force-control', 'motion-safety'])
    assert.ok(topic.includes('href="#' + readingGraphPaths[link] + '"'), link);
});

test('耗材专题与目录共用扫描图，汇集和复位分表并链接更换与维护', () => {
  const topic = renderLegacyReading('consumables');
  assert.equal(topic, render(DiagramDetail, { id: 'consumables-process', theme: 'light' }));
  assert.match(topic, /data-archify-source="functional-atlas\/consumables-scan-overview.html"/);
  const sources = renderToStaticMarkup(functionalVisual('life-sources', 'overview'));
  assert.equal((sources.match(/<tbody>[\s\S]*?<\/tbody>/)?.[0].match(/<tr>/g) ?? []).length, 7);
  assert.match(sources, /翻转工具/);
  assert.match(sources, /未接入这条扫描与窗口/);
  const reset = renderToStaticMarkup(functionalVisual('life-reset', 'overview'));
  assert.equal((reset.match(/<tbody>[\s\S]*?<\/tbody>/)?.[0].match(/<tr>/g) ?? []).length, 4);
  assert.match(reset, /保留报警时间与IsAlarmed/);
  for (const link of ['tool-bank', 'manual-maintenance'])
    assert.ok(topic.includes('href="#' + readingGraphPaths[link] + '"'), link);
});

// 枚举整个公开目录，防止只统一示例而遗漏旧架构图、时序图或内嵌专题。
test('全部121张公开图谱采用整宽画布，无详细说明页签或文档入口', () => {
  const entries = archifyData.flowchartCatalog.entries.filter(
    (entry) => entry.type !== 'supplemental',
  );
  assert.equal(entries.length, 121);
  for (const entry of entries) {
    const html = render(DiagramDetail, { id: entry.id, theme: 'light' });
    assert.equal((html.match(/data-reader-layout="diagram"/g) ?? []).length, 1, entry.id);
    assert.equal((html.match(/aria-label="图谱工具"/g) ?? []).length, 1, entry.id);
    for (const control of [
      '清晰阅读',
      '查找图中节点',
      '适应画布',
      '全屏阅读',
      '导出 SVG',
      '节点说明',
    ])
      assert.ok(html.includes(control), entry.id + ': ' + control);
    assert.doesNotMatch(
      html,
      /使用图内缩放|交互图解|业务介绍|详细说明|role="tab|reader-document/,
      entry.id,
    );
  }
});
