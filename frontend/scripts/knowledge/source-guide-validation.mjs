import { createHash } from 'node:crypto';
import { readFile, realpath } from 'node:fs/promises';
import { isAbsolute, relative, resolve } from 'node:path';

function requireValue(condition, message) {
  if (!condition) throw new Error(message);
}

function decodeSource(bytes) {
  if (bytes[0] === 0xff && bytes[1] === 0xfe)
    return new TextDecoder('utf-16le', { fatal: true }).decode(bytes);
  if (bytes[0] === 0xfe && bytes[1] === 0xff)
    return new TextDecoder('utf-16be', { fatal: true }).decode(bytes);
  requireValue(!bytes.includes(0), '源码依据不能是二进制文件');
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(bytes);
  } catch {
    return new TextDecoder('gb18030', { fatal: true }).decode(bytes);
  }
}

// 只读取主项目源码；变化必须重新人工复核，检查不能自动接受新版本。
export async function validateSourceGuides({ guides, evidence, trunkRoot, topics, diagrams }) {
  const ids = new Set();
  const usedRefs = new Set();
  const pages = new Set();
  let claims = 0;
  let flows = 0;
  let steps = 0;
  const uniqueId = (id) => {
    requireValue(
      typeof id === 'string' && id.length > 0 && !ids.has(id),
      `重复或缺失的说明 ID：${id}`,
    );
    ids.add(id);
  };
  const claim = (item) => {
    requireValue(typeof item.text === 'string' && item.text.trim(), '源码说明不能为空');
    requireValue(Array.isArray(item.refs) && item.refs.length, `说明缺少源码依据：${item.text}`);
    requireValue(new Set(item.refs).size === item.refs.length, '说明重复引用同一依据');
    for (const id of item.refs) {
      requireValue(Object.hasOwn(evidence.ranges, id), `源码依据不存在：${id}`);
      usedRefs.add(id);
    }
    claims++;
  };
  requireValue(guides.length > 0, '尚无人工核对的源码说明');
  for (const guide of guides) {
    uniqueId(guide.id);
    requireValue(topics.includes(guide.topic), `功能专题不存在：${guide.topic}`);
    for (const page of [guide.topic, ...guide.diagrams]) {
      requireValue(!pages.has(page), `页面绑定了重复说明：${page}`);
      pages.add(page);
    }
    for (const id of guide.diagrams) requireValue(diagrams.includes(id), `图谱不存在：${id}`);
    requireValue(guide.flows.length > 0 && guide.boundaries.length > 0, '说明缺少流程或复核范围');
    for (const [page, flowId] of Object.entries(guide.initialFlows ?? {})) {
      requireValue(
        page === guide.topic || guide.diagrams.includes(page),
        `默认阅读页面未绑定：${page}`,
      );
      requireValue(
        guide.flows.some((flow) => flow.id === flowId),
        `默认阅读流程不存在：${flowId}`,
      );
    }
    for (const flow of guide.flows) {
      uniqueId(flow.id);
      claim(flow);
      requireValue(flow.steps.length > 0, `流程缺少节点：${flow.id}`);
      requireValue(
        flow.sequential === undefined || typeof flow.sequential === 'boolean',
        `流程顺序类型无效：${flow.id}`,
      );
      flows++;
      for (const step of flow.steps) {
        uniqueId(`${flow.id}/${step.id}`);
        claim(step);
        steps++;
        for (const outcome of step.outcomes) {
          requireValue(outcome.label?.trim(), `分支缺少名称：${step.id}`);
          claim(outcome);
        }
      }
    }
    guide.boundaries.forEach(claim);
  }
  const root = await realpath(trunkRoot);
  const files = new Map();
  for (const [id, source] of Object.entries(evidence.sources)) {
    requireValue(!isAbsolute(source.path), `源码路径必须位于 trunk：${source.path}`);
    const target = await realpath(resolve(root, source.path));
    const within = relative(root, target);
    requireValue(
      within && !within.startsWith('..') && !isAbsolute(within),
      `源码路径越界：${source.path}`,
    );
    requireValue(/^[a-f0-9]{64}$/.test(source.sha256), `源码指纹无效：${source.path}`);
    const bytes = await readFile(target);
    requireValue(
      createHash('sha256').update(bytes).digest('hex') === source.sha256,
      `源码已变化，需重新阅读并复核说明：${source.path}`,
    );
    const content = decodeSource(bytes);
    const lines = content ? content.split(/\r\n|\r|\n/) : [];
    // 文件末尾换行不额外算一行，与当前源码 API 的 line_count 保持一致。
    if (/(\r\n|\r|\n)$/.test(content)) lines.pop();
    files.set(id, lines);
  }
  const usedFiles = new Set();
  for (const [id, ref] of Object.entries(evidence.ranges)) {
    requireValue(usedRefs.has(id), `未使用的源码依据：${id}`);
    const lines = files.get(ref.file);
    requireValue(lines, `依据引用的文件不存在：${id}`);
    requireValue(
      Number.isSafeInteger(ref.start) &&
        Number.isSafeInteger(ref.end) &&
        ref.start > 0 &&
        ref.end >= ref.start &&
        ref.end <= lines.length,
      `依据行号无效：${id}`,
    );
    requireValue(ref.method?.trim(), `依据缺少方法名称：${id}`);
    requireValue(
      ref.code === lines.slice(ref.start - 1, ref.end).join('\n'),
      `依据片段与当前源码不符：${id}`,
    );
    usedFiles.add(ref.file);
  }
  requireValue(usedFiles.size === files.size, '存在没有被引用的源码文件');
  return { guides: guides.length, flows, steps, claims, files: files.size, ranges: usedRefs.size };
}
