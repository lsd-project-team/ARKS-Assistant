import type { ChartBlock, MindmapBlock } from './types.ts';

type Row = Record<string, unknown>;
function row(value: unknown): Row {
  if (!value || typeof value !== 'object' || Array.isArray(value))
    throw new Error('图形数据必须是对象');
  return value as Row;
}
function fields(value: Row, allowed: string[]) {
  if (Object.keys(value).some((key) => !allowed.includes(key)))
    throw new Error('图形含不支持的字段');
}
function text(value: unknown, max = 300): asserts value is string {
  if (typeof value !== 'string' || value.length > max) throw new Error('图形文字无效或过长');
}
function list(value: unknown, max: number): unknown[] {
  if (!Array.isArray(value) || !value.length || value.length > max)
    throw new Error('图形数据为空或超过限制');
  return value;
}
function identifier(value: unknown): asserts value is string {
  if (typeof value !== 'string' || !/^[\w-]{1,80}$/.test(value)) throw new Error('图形 ID 无效');
}

export function validateChart(value: unknown): asserts value is ChartBlock {
  const block = row(value);
  fields(block, ['id', 'type', 'title', 'chart_type', 'labels', 'series']);
  if (!['bar', 'line', 'pie'].includes(String(block.chart_type))) throw new Error('图表类型无效');
  const labels = list(block.labels, 500);
  labels.forEach((label) => text(label));
  const series = list(block.series, 12);
  if (block.chart_type === 'pie' && series.length !== 1) throw new Error('饼图仅支持一个数据系列');
  const seen = new Set<string>();
  let hasValue = false;
  for (const value of series) {
    const item = row(value);
    fields(item, ['id', 'name', 'values']);
    identifier(item.id);
    if (seen.has(item.id)) throw new Error('图表系列 ID 重复');
    seen.add(item.id);
    text(item.name);
    const values = list(item.values, 500);
    if (values.length !== labels.length) throw new Error('图表标签与数值数量不一致');
    for (const number of values) {
      if (number === null) continue;
      if (typeof number !== 'number' || !Number.isFinite(number))
        throw new Error('图表需要有限数值');
      if (block.chart_type === 'pie' && number < 0) throw new Error('饼图不能使用负值');
      hasValue = true;
    }
  }
  if (!hasValue) throw new Error('图表没有有效数值');
}

export function validateMindmap(value: unknown): asserts value is MindmapBlock {
  const block = row(value);
  fields(block, ['id', 'type', 'title', 'nodes']);
  const nodes = list(block.nodes, 60).map(row);
  const byId = new Map<string, Row>();
  for (const node of nodes) {
    fields(node, ['id', 'label', 'parent_id']);
    identifier(node.id);
    text(node.label);
    if (node.parent_id !== undefined) identifier(node.parent_id);
    if (byId.has(node.id)) throw new Error('思维导图节点 ID 重复');
    byId.set(node.id, node);
  }
  if (nodes.filter((node) => node.parent_id === undefined).length !== 1)
    throw new Error('思维导图需要唯一根节点');
  for (const node of nodes) {
    const visited = new Set<string>();
    let current: Row | undefined = node;
    while (current) {
      const id = String(current.id);
      if (visited.has(id)) throw new Error('思维导图存在循环');
      visited.add(id);
      if (current.parent_id === undefined) break;
      current = byId.get(String(current.parent_id));
      if (!current) throw new Error('思维导图父节点不存在');
    }
  }
}

export function validateMermaidContent(content: string) {
  if (!content.trim() || content.length > 20000) throw new Error('流程图内容为空或超过限制');
  // 配置由应用控制，禁止模型覆盖安全选项、注入自定义样式或链接事件。
  if (
    content.trimStart().startsWith('---') ||
    /%%\s*\{|^\s*(?:click|style|classDef)\s/im.test(content)
  )
    throw new Error('流程图包含不支持的配置、样式或交互指令');
}
