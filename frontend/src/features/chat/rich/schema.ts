import type { RichDocument, SourcePointer } from './types.ts';

export const RICH_LIMITS = { bytes: 262144, blocks: 128, depth: 4 } as const;
type ObjectValue = Record<string, unknown>;
function object(value: unknown): ObjectValue {
  if (!value || typeof value !== 'object' || Array.isArray(value))
    throw new Error('内容必须是对象');
  return value as ObjectValue;
}
function keys(value: ObjectValue, allowed: string[]) {
  if (Object.keys(value).some((key) => !allowed.includes(key))) throw new Error('含不支持的字段');
}
function text(value: unknown, max = 20000): asserts value is string {
  if (typeof value !== 'string' || value.length > max) throw new Error('文字字段缺失或过长');
}
function optionalText(value: unknown, max = 20000) {
  if (value !== undefined) text(value, max);
}
function array(value: unknown, max: number): unknown[] {
  if (!Array.isArray(value) || value.length > max) throw new Error('列表缺失或超过限制');
  return value;
}
function integer(value: unknown) {
  if (!Number.isSafeInteger(value) || Number(value) < 1 || Number(value) > 10000000)
    throw new Error('行号无效');
}
function id(value: unknown): asserts value is string {
  if (typeof value !== 'string' || !/^[\w-]{1,80}$/.test(value)) throw new Error('ID 无效');
}
function unique(values: unknown[], validate: (value: ObjectValue) => void) {
  const seen = new Set<string>();
  for (const item of values) {
    const row = object(item);
    id(row.id);
    if (seen.has(row.id)) throw new Error('ID 重复');
    seen.add(row.id);
    validate(row);
  }
}

export function validateSource(value: unknown): SourcePointer {
  const source = object(value);
  keys(source, ['path', 'start_line', 'end_line', 'version', 'source_workspace_id']);
  text(source.path, 1024);
  if (
    !source.path ||
    /[\\:\u0000-\u001f\u007f]/.test(source.path) ||
    source.path.split('/').some((part) => !part || part === '.' || part === '..')
  )
    throw new Error('源码路径无效');
  integer(source.start_line);
  if (source.end_line !== undefined) {
    integer(source.end_line);
    if (Number(source.end_line) < Number(source.start_line)) throw new Error('源码范围无效');
  }
  optionalText(source.version, 128);
  if (source.source_workspace_id !== undefined) id(source.source_workspace_id);
  return source as unknown as SourcePointer;
}

// 校验与展示分离；白名单字段不允许模型传入路由、回调或动态组件。
export function validateDocument(value: unknown): RichDocument {
  const document = object(value);
  keys(document, ['version', 'blocks']);
  if (document.version !== 1) throw new Error('不支持的内容协议版本');
  let count = 0;
  const identifiers = new Set<string>();
  const blocks = (values: unknown, depth: number) => {
    if (depth > RICH_LIMITS.depth) throw new Error('内容嵌套过深');
    for (const value of array(values, RICH_LIMITS.blocks)) {
      const block = object(value);
      id(block.id);
      if (identifiers.has(block.id)) throw new Error('内容块 ID 重复');
      identifiers.add(block.id);
      if (++count > RICH_LIMITS.blocks) throw new Error('内容块过多');
      const allowed = (fields: string[]) => keys(block, ['id', 'type', ...fields]);
      optionalText(block.title, 300);
      switch (block.type) {
        case 'text':
          allowed(['content']);
          text(block.content);
          break;
        case 'overview_grid':
          allowed(['title', 'items']);
          unique(array(block.items, 64), (item) => {
            keys(item, ['id', 'title', 'description', 'icon', 'status', 'source']);
            text(item.title, 300);
            text(item.description, 4000);
            optionalText(item.status, 300);
            if (
              item.icon !== undefined &&
              !['code', 'layers', 'settings', 'workflow'].includes(String(item.icon))
            )
              throw new Error('未知图标');
            if (item.source !== undefined) validateSource(item.source);
          });
          break;
        case 'step_flow':
          allowed(['title', 'description', 'steps']);
          optionalText(block.description, 4000);
          unique(array(block.steps, 128), (step) => {
            keys(step, ['id', 'title', 'description', 'details', 'sources']);
            text(step.title, 300);
            text(step.description, 4000);
            optionalText(step.details);
            if (step.sources !== undefined) array(step.sources, 16).forEach(validateSource);
          });
          break;
        case 'source_reference':
          allowed(['sources']);
          array(block.sources, 64).forEach(validateSource);
          break;
        case 'code':
          allowed(['content', 'language', 'filename', 'start_line', 'source']);
          text(block.content, 60000);
          optionalText(block.language, 40);
          optionalText(block.filename, 1024);
          if (block.language !== undefined && !/^[\w#+.-]{1,40}$/.test(String(block.language)))
            throw new Error('代码语言无效');
          if (block.start_line !== undefined) integer(block.start_line);
          if (block.source !== undefined) validateSource(block.source);
          break;
        case 'table': {
          allowed(['title', 'columns', 'rows']);
          const columns = array(block.columns, 32);
          if (!columns.length) throw new Error('表格缺少列');
          unique(columns, (column) => {
            keys(column, ['id', 'label', 'align']);
            text(column.label, 300);
            if (
              column.align !== undefined &&
              !['left', 'right', 'center'].includes(String(column.align))
            )
              throw new Error('表格对齐无效');
          });
          unique(array(block.rows, 200), (row) => {
            keys(row, ['id', 'cells']);
            const cells = array(row.cells, 32);
            if (cells.length !== columns.length) throw new Error('表格列数不一致');
            for (const cell of cells)
              if (typeof cell === 'string') text(cell, 4000);
              else if (cell !== null && (typeof cell !== 'number' || !Number.isFinite(cell)))
                throw new Error('表格单元格无效');
          });
          break;
        }
        case 'diagram': {
          allowed(['title', 'description', 'layout', 'nodes', 'edges']);
          text(block.title, 300);
          optionalText(block.description, 4000);
          if (
            block.layout !== undefined &&
            !['vertical', 'horizontal'].includes(String(block.layout))
          )
            throw new Error('未知图形布局');
          const nodes = array(block.nodes, 60);
          if (!nodes.length) throw new Error('图形缺少节点');
          unique(nodes, (node) => {
            keys(node, ['id', 'label', 'description']);
            text(node.label, 300);
            optionalText(node.description, 4000);
          });
          const nodeIds = new Set(nodes.map((node) => object(node).id));
          for (const value of array(block.edges, 120)) {
            const edge = object(value);
            keys(edge, ['from', 'to', 'label']);
            if (!nodeIds.has(edge.from) || !nodeIds.has(edge.to))
              throw new Error('图形连接指向未知节点');
            optionalText(edge.label, 300);
          }
          break;
        }
        case 'collapsible':
          allowed(['title', 'default_open', 'blocks']);
          text(block.title, 300);
          if (block.default_open !== undefined && typeof block.default_open !== 'boolean')
            throw new Error('折叠状态无效');
          blocks(block.blocks, depth + 1);
          break;
        default:
          throw new Error(`未知内容块类型：${String(block.type).slice(0, 40)}`);
      }
    }
  };
  blocks(document.blocks, 0);
  return document as unknown as RichDocument;
}

export function parseDocument(
  json: string,
): { document: RichDocument; error?: never } | { document?: never; error: string } {
  try {
    if (
      json.length > RICH_LIMITS.bytes ||
      new TextEncoder().encode(json).length > RICH_LIMITS.bytes
    )
      throw new Error('结构化内容超过大小限制');
    return { document: validateDocument(JSON.parse(json)) };
  } catch (error) {
    return { error: error instanceof Error ? error.message : '内容格式无效' };
  }
}
