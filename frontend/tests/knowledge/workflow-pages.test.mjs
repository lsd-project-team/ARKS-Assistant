import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { presentationTopics } from '../../src/features/knowledge/data/presentation.ts';
import { archifyData } from '../../src/features/knowledge/data/archifyData.ts';

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
const { TopicDetail, DiagramDetail, GraphAtlas, coordinateVisual, functionalVisual } =
  module.exports;
const render = (component, props) =>
  renderToStaticMarkup(createElement(component, { navigate() {}, ...props }));

test('全部专题保留流程内容，不再显示源码模块、依据、路径和快照选区', () => {
  for (const topic of presentationTopics) {
    const html = render(TopicDetail, { id: topic.id });
    assert.ok(html.includes(topic.title));
    assert.match(html, /建议阅读顺序/);
    assert.doesNotMatch(
      html,
      /源码模块结构|关联源码模块|源码依据|查看依据|查看协作依据|source-evidence|source-module|<pre/,
    );
  }
  assert.ok(
    Object.keys(result.metafile.inputs).every(
      (path) => !/source-evidence\.json|EngineeringViews|engineeringData/.test(path),
    ),
  );
});

test('生产流程保留原图、节点说明和协作条件，移除节点依据', () => {
  for (const graph of archifyData.graphs) {
    const html = render(DiagramDetail, { id: graph.slug, theme: 'light' });
    assert.match(html, /<iframe/);
    assert.match(html, /深入阅读节点与模块协作/);
    assert.ok(html.includes(graph.nodes[0].label));
    assert.doesNotMatch(
      html,
      /源码依据|查看依据|查看协作依据|evidence-item|source-file|source-method|<pre/,
    );
  }
});

test('G0 从专题和图谱目录进入同一阅读页，使用 Archify 交付图', () => {
  const topic = render(TopicDetail, { id: 'g0' });
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
  assert.match(startup, /<iframe/);
  assert.doesNotMatch(startup, /g0-reader/);
});

test('产品专题与目录共用整宽阅读页，并复用父链原图和定位更新交付', () => {
  const topic = render(TopicDetail, { id: 'product-coordinates' });
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
  assert.match(topic, /href="#topic\/g0"/);
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
  const topic = render(TopicDetail, { id: 'public-vision' });
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
  assert.match(topic, /href="#topic\/product-coordinates"/);
  assert.doesNotMatch(topic, /源码依据|source-evidence|<pre/);
});

test('相机标定专题绑定 S2 调度图，并提供保存与复核的对照表', () => {
  const topic = render(TopicDetail, { id: 'camera-calibration' });
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
  const topic = render(TopicDetail, { id: 'motion-safety' });
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
  assert.match(topic, /href="#topic\/recovery"/);
  const table = renderToStaticMarkup(functionalVisual('sm-order', 'table'));
  assert.equal((table.match(/<tbody>[\s\S]*?<\/tbody>/)?.[0].match(/<tr>/g) ?? []).length, 5);
  assert.match(table, /安全 Z → XY → 恢复原 Z/);
  assert.match(table, /“含 T”只适用于 XYZT/);
});

test('工具校准专题共用阅读页，独立入口与七行保存边界均可阅读', () => {
  const topic = render(TopicDetail, { id: 'tool-calibration' });
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
  assert.match(topic, /href="#topic\/camera-calibration"/);
  const table = renderToStaticMarkup(functionalVisual('tc-results', 'persistence'));
  assert.equal((table.match(/<tbody>[\s\S]*?<\/tbody>/)?.[0].match(/<tr>/g) ?? []).length, 7);
  assert.match(table, /收尾保存代码已注释/);
  assert.match(table, /Fail \/ Exception 也进入/);
  assert.match(table, /缺模板或定位失败早退后仍会调用保存/);
});

test('全局标定专题区分新区域与旧驱动链，并保留八条保存路径', () => {
  const topic = render(TopicDetail, { id: 'global-calibration' });
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
  assert.match(topic, /href="#topic\/motion-safety"/);
  const table = renderToStaticMarkup(functionalVisual('gc-completion', 'persistence'));
  assert.equal((table.match(/<tbody>[\s\S]*?<\/tbody>/)?.[0].match(/<tr>/g) ?? []).length, 8);
  assert.match(table, /没有同样的尾部域保存/);
  assert.match(table, /替换之前先保存旧域/);
  assert.match(table, /域配置由保存按钮写入/);
});

test('光源专题共用目录入口，区分硬件、采集、缓存和视觉换算', () => {
  const topic = render(TopicDetail, { id: 'lightness' });
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
  const topic = render(TopicDetail, { id: 'height-measurement' });
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
  assert.match(topic, /href="#topic\/global-calibration"/);
});

test('力控专题与目录共用阅读页，读数和保存分表并保留真实驱动及换算图', () => {
  const topic = render(TopicDetail, { id: 'force-control' });
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
  assert.match(topic, /href="#topic\/height-measurement"/);
  assert.match(topic, /href="#topic\/motion-safety"/);
});

test('工具库专题与目录共用阅读页，区分四种状态并绑定保存表和真实换嘴图', () => {
  const topic = render(TopicDetail, { id: 'tool-bank' });
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
  assert.match(topic, /href="#topic\/tool-calibration"/);
  assert.match(topic, /href="#topic\/motion-safety"/);
});

test('维护专题默认展示清嘴图，目录共用并区分六个手动入口与八类保存', () => {
  const topic = render(TopicDetail, { id: 'manual-maintenance' });
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
    assert.ok(topic.includes('href="#topic/' + link + '"'), link);
});
