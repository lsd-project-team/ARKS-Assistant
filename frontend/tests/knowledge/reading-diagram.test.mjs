import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createReadingDiagram } from '../../src/features/knowledge/coordinates/archifyReadingPage.ts';

const resources = new URL('../../../resources/knowledge/flows/g0-archify/', import.meta.url);
const json = async (name) => JSON.parse(await readFile(new URL(`${name}.json`, resources), 'utf8'));

test('阅读副本保留 Archify 全部节点、连线与自然尺寸，移除脚本和无效交互', async () => {
  for (const name of [
    'device-tree',
    'product-tree',
    'camera-workflow',
    'device-reading',
    'camera-reading',
    'device-overview',
    'product-reading',
    'camera-overview',
  ]) {
    const spec = await json(name);
    const source = await readFile(new URL(`${name}.html`, resources), 'utf8');
    const page = createReadingDiagram(source, 'classic');
    const sourceViewBox = source
      .match(/<svg[^>]*viewBox="([^"]+)"/)[1]
      .split(/\s+/)
      .map(Number);
    assert.deepEqual([page.width, page.height], sourceViewBox.slice(2));
    for (const node of spec.nodes ?? spec.components) {
      assert.ok(page.html.includes(`data-node-id="${node.id}"`), `${name}: ${node.id}`);
      assert.ok(page.html.includes(node.label), `${name}: ${node.label}`);
    }
    assert.equal(
      (page.html.match(/\bdata-edge-from=/g) ?? []).length,
      (source.match(/\bdata-edge-from=/g) ?? []).length,
    );
    const body = page.html.slice(page.html.indexOf('<body>'));
    assert.equal(/<script\b|tabindex=|role="button"/.test(body), false);
    assert.match(page.html, /height: auto !important/);
    assert.match(createReadingDiagram(source, 'dark').html, /data-theme="dark"/);
  }
});

test('桌面坐标图保留全部关系，减少长竖图并在窄屏保留纵向版本', async () => {
  const semantics = (spec) => {
    const nodes = spec.nodes ?? spec.components;
    const edges =
      spec.connections ??
      nodes.filter((node) => node.parent).map((node) => ({ from: node.parent, to: node.id }));
    return {
      nodes: nodes.map(({ id, label, sublabel, sources }) => ({ id, label, sublabel, sources })),
      edges: edges.map(({ from, to, label }) => ({ from, to, label })),
    };
  };
  for (const [original, desktop] of [
    ['device-tree', 'device-overview'],
    ['product-tree', 'product-reading'],
    ['camera-reading', 'camera-overview'],
  ]) {
    assert.deepEqual(semantics(await json(desktop)), semantics(await json(original)));
    const source = await readFile(new URL(`${desktop}.html`, resources), 'utf8');
    const page = createReadingDiagram(source, 'classic');
    assert.ok(page.width >= 900 && page.width <= 1100, desktop);
    assert.ok(page.height <= 430, desktop);
  }
});

test('纵向阅读图与原图拥有相同节点和方向关系，不省略相机或输入', async () => {
  for (const [original, reading] of [
    ['device-tree', 'device-reading'],
    ['camera-workflow', 'camera-reading'],
  ]) {
    const full = await json(original);
    const narrow = await json(reading);
    assert.deepEqual(
      narrow.components.map((node) => node.id).sort(),
      full.nodes.map((node) => node.id).sort(),
    );
    const edges =
      full.edges ??
      full.nodes.filter((node) => node.parent).map((node) => ({ from: node.parent, to: node.id }));
    const pairs = (items) => items.map((edge) => `${edge.from}>${edge.to}`).sort();
    assert.deepEqual(pairs(narrow.connections), pairs(edges));
  }
});

test('无法确定图形尺寸时不输出裁切或空白阅读图', () => {
  for (const html of [
    '',
    '<svg></svg>',
    '<svg viewBox="0 0 0 100"></svg>',
    '<svg viewBox="0 0 NaN 100"></svg>',
  ]) {
    assert.throws(() => createReadingDiagram(html, 'white'));
  }
});

test('产品定位图在阅读副本中保留限内写回与超限异常的方向', async () => {
  const source = await readFile(
    new URL(
      '../../../resources/knowledge/flows/functional-atlas/product-update.html',
      import.meta.url,
    ),
    'utf8',
  );
  const page = createReadingDiagram(source, 'classic');
  for (const [from, to, label] of [
    ['gate', 'write', '通过'],
    ['gate', 'error', '超限'],
  ]) {
    assert.ok(
      page.html.includes(
        `data-edge-from="${from}" data-edge-to="${to}" data-edge-label="${label}"`,
      ),
    );
  }
  assert.equal((page.html.match(/<g\b[^>]*data-node-id=/g) ?? []).length, 7);
  assert.doesNotMatch(page.html, /<script\b/);
  assert.match(page.html, /\[data-edge-id\] text \{ font-size: 14px/);
});

test('公共视觉图保留自动结果、人工回传与退出，不能把失败统一连到成功', async () => {
  const source = await readFile(
    new URL(
      '../../../resources/knowledge/flows/functional-atlas/vision-point.html',
      import.meta.url,
    ),
    'utf8',
  );
  const page = createReadingDiagram(source, 'classic');
  for (const [from, to, label] of [
    ['result', 'alarm', '空值'],
    ['alarm', 'convert', 'OK'],
    ['alarm', 'exit', '非 OK'],
  ])
    assert.ok(
      page.html.includes(
        `data-edge-from="${from}" data-edge-to="${to}" data-edge-label="${label}"`,
      ),
    );
  assert.equal((page.html.match(/<g\b[^>]*data-node-id=/g) ?? []).length, 7);
  assert.doesNotMatch(page.html, /data-edge-from="exit" data-edge-to="save"/);
});

test('标定图保留可跳过的同标记步骤及真实 S2 调度顺序', async () => {
  const source = await readFile(
    new URL(
      '../../../resources/knowledge/flows/functional-atlas/camera-calibration.html',
      import.meta.url,
    ),
    'utf8',
  );
  const page = createReadingDiagram(source, 'classic');
  const path = ['prepare', 'bond', 'offset', 'optional', 'position', 'wafer', 'results'];
  for (let index = 0; index < path.length - 1; index++)
    assert.ok(
      page.html.includes(`data-edge-from="${path[index]}" data-edge-to="${path[index + 1]}"`),
    );
  assert.equal((page.html.match(/<g\b[^>]*data-node-id=/g) ?? []).length, 7);
  assert.match(page.html, /确认执行，取消跳过/);
});

test('安全移动图先经限位和单步门控，再分成三种顺序而非顺序执行全部路径', async () => {
  const source = await readFile(
    new URL(
      '../../../resources/knowledge/flows/functional-atlas/safe-motion-branches.html',
      import.meta.url,
    ),
    'utf8',
  );
  const page = createReadingDiagram(source, 'classic');
  for (const [from, to] of [
    ['target', 'prepare'],
    ['prepare', 'single'],
    ['single', 'branch'],
    ['branch', 'xy-first'],
    ['branch', 'z-first'],
    ['branch', 'lift-first'],
  ])
    assert.ok(page.html.includes(`data-edge-from="${from}" data-edge-to="${to}"`));
  assert.equal((page.html.match(/<g\b[^>]*data-node-id=/g) ?? []).length, 7);
  assert.doesNotMatch(page.html, /data-edge-from="xy-first" data-edge-to="z-first"/);
  assert.match(page.html, /拒绝则直接返回/);
});

test('安全移动窄图保留原图的全部节点、含义和分支，仅缩紧排布', async () => {
  const folder = new URL('../../../resources/knowledge/flows/functional-atlas/', import.meta.url);
  const full = JSON.parse(await readFile(new URL('safe-motion-branches.json', folder), 'utf8'));
  const narrow = JSON.parse(await readFile(new URL('safe-motion-reading.json', folder), 'utf8'));
  const meaning = ({ pos, size, ...node }) => node;
  assert.deepEqual(narrow.components.map(meaning), full.components.map(meaning));
  assert.deepEqual(narrow.connections, full.connections);
  const source = await readFile(new URL('safe-motion-reading.html', folder), 'utf8');
  const page = createReadingDiagram(source, 'classic');
  assert.ok(page.width < 430);
  for (const node of full.components) assert.ok(page.html.includes(`data-node-id="${node.id}"`));
});

test('工具校准入口图保留三个并列按钮，不把未启用组合串成执行链', async () => {
  const source = await readFile(
    new URL(
      '../../../resources/knowledge/flows/functional-atlas/tool-calibration-entry.html',
      import.meta.url,
    ),
    'utf8',
  );
  const page = createReadingDiagram(source, 'classic');
  for (const target of ['nozzle', 'ejection', 'pick'])
    assert.ok(page.html.includes(`data-edge-from="page" data-edge-to="${target}"`));
  assert.equal((page.html.match(/<g\b[^>]*data-node-id=/g) ?? []).length, 4);
  assert.match(page.html, /一键组合未启用/);
  assert.doesNotMatch(page.html, /data-edge-from="nozzle" data-edge-to="ejection"/);
  assert.doesNotMatch(page.html, /data-edge-from="ejection" data-edge-to="pick"/);
});

test('全局区域主链保留粗略完成与四点构造门控，驱动图保留分派而非顺次下载两种驱动', async () => {
  const folder = new URL('../../../resources/knowledge/flows/functional-atlas/', import.meta.url);
  const main = createReadingDiagram(
    await readFile(new URL('global-region-chain.html', folder), 'utf8'),
    'classic',
  );
  assert.equal((main.html.match(/<g\b[^>]*data-node-id=/g) ?? []).length, 7);
  assert.match(main.html, /粗略完成门控/);
  assert.match(main.html, /零值标量少于3个/);
  assert.match(main.html, /构造至少4个点/);
  assert.ok(
    main.html.includes('data-edge-from="gate" data-edge-to="region" data-edge-label="通过"'),
  );
  const driver = createReadingDiagram(
    await readFile(new URL('global-driver-mapping.html', folder), 'utf8'),
    'classic',
  );
  for (const target of ['etel-file', 'gt-table'])
    assert.ok(driver.html.includes(`data-edge-from="driver" data-edge-to="${target}"`));
  assert.equal((driver.html.match(/<g\b[^>]*data-node-id=/g) ?? []).length, 6);
  assert.doesNotMatch(driver.html, /data-edge-from="etel-enable" data-edge-to="gt-table"/);
  assert.match(driver.html, /GTAxis；bool 未门控/);
});

test('亮度图保留全部返回才保存，以及报警编辑先正向后反向的条件和顺序', async () => {
  const folder = new URL('../../../resources/knowledge/flows/functional-atlas/', import.meta.url);
  const capture = createReadingDiagram(
    await readFile(new URL('lightness-calibration.html', folder), 'utf8'),
    'classic',
  );
  assert.equal((capture.html.match(/<g\b[^>]*data-node-id=/g) ?? []).length, 7);
  assert.match(capture.html, /Done 发起后台任务/);
  assert.match(capture.html, /每组五个 Bond 点/);
  assert.match(capture.html, /每点八次匹配/);
  assert.ok(
    capture.html.includes(
      'data-edge-from="pairs" data-edge-to="save" data-edge-label="全部正常返回"',
    ),
  );
  const alarm = createReadingDiagram(
    await readFile(new URL('lightness-alarm-edit.html', folder), 'utf8'),
    'classic',
  );
  assert.equal((alarm.html.match(/<g\b[^>]*data-node-id=/g) ?? []).length, 6);
  for (const [from, to] of [
    ['entry', 'forward'],
    ['forward', 'editor'],
    ['editor', 'reverse'],
    ['reverse', 'save'],
    ['save', 'resume'],
  ])
    assert.ok(alarm.html.includes('data-edge-from="' + from + '" data-edge-to="' + to + '"'));
  assert.match(alarm.html, /有 PRHardware；点胶/);
  assert.match(alarm.html, /关闭后仍为点胶/);
  assert.doesNotMatch(alarm.html, /data-edge-from="editor" data-edge-to="save"/);
});

test('测高回写图保留先收集再校验，平面度图只以非空列表进入极差', async () => {
  const folder = new URL('../../../resources/knowledge/flows/functional-atlas/', import.meta.url);
  const writeback = createReadingDiagram(
    await readFile(new URL('height-s1-writeback.html', folder), 'utf8'),
    'classic',
  );
  assert.equal((writeback.html.match(/<g\b[^>]*data-node-id=/g) ?? []).length, 8);
  for (const [from, to] of [
    ['measure', 'append'],
    ['append', 'check'],
    ['check', 'average'],
    ['average', 'result'],
    ['result', 'complete'],
  ])
    assert.ok(writeback.html.includes('data-edge-from="' + from + '" data-edge-to="' + to + '"'));
  assert.match(writeback.html, /失败项在列表中保留/);
  assert.match(writeback.html, /未检出 NaN 时/);
  const flat = createReadingDiagram(
    await readFile(new URL('height-flat-batch.html', folder), 'utf8'),
    'classic',
  );
  assert.equal((flat.html.match(/<g\b[^>]*data-node-id=/g) ?? []).length, 6);
  assert.ok(flat.html.includes('data-edge-from="nonempty" data-edge-to="range"'));
  assert.match(flat.html, /仅检查列表非空/);
  assert.match(flat.html, /未核对点数齐全/);
});

test('力控分派保留两路 finally，目标力换算保留大小力初值差异和多点前提', async () => {
  const folder = new URL('../../../resources/knowledge/flows/functional-atlas/', import.meta.url);
  const dispatch = createReadingDiagram(
    await readFile(new URL('force-calibration-dispatch.html', folder), 'utf8'),
    'classic',
  );
  for (const [from, to] of [
    ['dispatch', 'gt-prepare'],
    ['dispatch', 'etel-prepare'],
    ['gt-finally', 'save'],
    ['etel-finally', 'save'],
    ['save', 'safe'],
  ])
    assert.ok(dispatch.html.includes(`data-edge-from="${from}" data-edge-to="${to}"`));
  assert.match(dispatch.html, /停止\/异常仍写局部表/);
  assert.match(dispatch.html, /单角结果未加入表/);
  assert.match(dispatch.html, /仅在 Save 返回后/);
  assert.doesNotMatch(dispatch.html, /data-edge-from="gt-samples" data-edge-to="etel-samples"/);
  const conversion = createReadingDiagram(
    await readFile(new URL('force-input-conversion.html', folder), 'utf8'),
    'classic',
  );
  for (const branch of ['small', 'large']) {
    assert.ok(conversion.html.includes(`data-edge-from="range" data-edge-to="${branch}"`));
    assert.ok(conversion.html.includes(`data-edge-from="${branch}" data-edge-to="samples"`));
  }
  assert.match(conversion.html, /正常多点路径/);
  assert.match(conversion.html, /小力用传入初值/);
  assert.match(conversion.html, /大力用角度初值/);
});

test('力控宽屏图与纵图保留相同节点和分支，桌面画布可完整展开', async () => {
  const folder = new URL('../../../resources/knowledge/flows/functional-atlas/', import.meta.url);
  for (const [compact, wide] of [
    ['force-calibration-dispatch', 'force-calibration-overview'],
    ['force-input-conversion', 'force-input-overview'],
  ]) {
    const original = JSON.parse(await readFile(new URL(compact + '.json', folder), 'utf8'));
    const desktop = JSON.parse(await readFile(new URL(wide + '.json', folder), 'utf8'));
    const meaning = ({ pos, size, ...node }) => node;
    assert.deepEqual(desktop.components.map(meaning), original.components.map(meaning));
    assert.deepEqual(desktop.connections, original.connections);
    const page = createReadingDiagram(
      await readFile(new URL(wide + '.html', folder), 'utf8'),
      'classic',
    );
    assert.ok(page.width >= 800 && page.width <= 900, wide);
    assert.ok(page.height <= 650, wide);
  }
});

test('换嘴主链保留同名早退、先还后取及直接取嘴，纵图不丢分支', async () => {
  const folder = new URL('../../../resources/knowledge/flows/functional-atlas/', import.meta.url);
  const load = async (id) => JSON.parse(await readFile(new URL(id + '.json', folder), 'utf8'));
  const wide = await load('tool-change-overview');
  const narrow = await load('tool-change-reading');
  const meaning = ({ pos, size, ...node }) => node;
  assert.deepEqual(wide.components.map(meaning), narrow.components.map(meaning));
  assert.deepEqual(wide.connections, narrow.connections);
  const edges = wide.connections.map(({ from, to }) => `${from}>${to}`);
  for (const edge of [
    'name>same',
    'name>change',
    'change>manual',
    'change>check',
    'check>put',
    'check>take',
    'put>take',
    'take>home',
    'home>success',
  ])
    assert.ok(edges.includes(edge), edge);
  assert.ok(!edges.some((edge) => edge.startsWith('same>') || edge.startsWith('manual>')));
  for (const id of ['tool-change-overview', 'tool-change-reading']) {
    const page = createReadingDiagram(
      await readFile(new URL(id + '.html', folder), 'utf8'),
      'classic',
    );
    assert.equal((page.html.match(/<g\b[^>]*data-node-id=/g) ?? []).length, 9);
    assert.match(page.html, /未用回位结果门控/);
    assert.match(page.html, /冲突或终止→false/);
    assert.match(page.html, /可经人工忽略到达/);
  }
});

test('清嘴图保留关闭不计数、未到间隔加一及先清洁再清零，纵图不改触发顺序', async () => {
  const folder = new URL('../../../resources/knowledge/flows/functional-atlas/', import.meta.url);
  const wide = JSON.parse(await readFile(new URL('nozzle-clean-overview.json', folder), 'utf8'));
  const narrow = JSON.parse(await readFile(new URL('nozzle-clean-reading.json', folder), 'utf8'));
  const meaning = ({ pos, size, ...node }) => node;
  assert.deepEqual(wide.components.map(meaning), narrow.components.map(meaning));
  assert.deepEqual(wide.connections, narrow.connections);
  const edges = wide.connections.map(({ from, to }) => `${from}>${to}`);
  for (const edge of [
    'check>skip',
    'check>interval',
    'interval>clean',
    'interval>increment',
    'clean>reset',
    'reset>increment',
    'increment>resume',
  ])
    assert.ok(edges.includes(edge), edge);
  assert.ok(!edges.some((edge) => edge.startsWith('skip>')));
  for (const id of ['nozzle-clean-overview', 'nozzle-clean-reading']) {
    const page = createReadingDiagram(
      await readFile(new URL(id + '.html', folder), 'utf8'),
      'classic',
    );
    assert.equal((page.html.match(/<g\b[^>]*data-node-id=/g) ?? []).length, 8);
    assert.match(page.html, /随后才判断DryCycle/);
    assert.match(page.html, /区域Count先占用/);
  }
});

test('耗材扫描保留到期优先、冷却回落提醒及忽略与停止的不同清零边界', async () => {
  const folder = new URL('../../../resources/knowledge/flows/functional-atlas/', import.meta.url);
  const load = async (id) => JSON.parse(await readFile(new URL(id + '.json', folder), 'utf8'));
  const wide = await load('consumables-scan-overview');
  const narrow = await load('consumables-scan-reading');
  const meaning = ({ pos, size, ...node }) => node;
  assert.deepEqual(wide.components.map(meaning), narrow.components.map(meaning));
  assert.deepEqual(wide.connections, narrow.connections);
  const edges = wide.connections.map(({ from, to }) => from + '>' + to);
  for (const edge of [
    'list>gate',
    'gate>expired',
    'gate>remind-gate',
    'expired>ignore',
    'expired>stop',
    'remind-gate>remind',
    'remind-gate>skip',
  ])
    assert.ok(edges.includes(edge), edge);
  for (const missing of ['gate>skip', 'ignore>stop', 'expired>remind'])
    assert.ok(!edges.includes(missing), missing);
  for (const id of ['consumables-scan-overview', 'consumables-scan-reading']) {
    const page = createReadingDiagram(
      await readFile(new URL(id + '.html', folder), 'utf8'),
      'classic',
    );
    assert.equal((page.html.match(/<g\b[^>]*data-node-id=/g) ?? []).length, 8);
    assert.match(page.html, /先写已提醒与时间/);
    assert.match(page.html, /不等待更换确认/);
    assert.match(page.html, /继续遍历；不清零/);
  }
});
