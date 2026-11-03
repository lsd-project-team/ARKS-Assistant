import type { DiagramNode } from './ReaderFrame';

/** 只保留原交付的 SVG 与样式。脚本不进入阅读 iframe，图形语义和布局保持原样。 */
export function diagramDocument(source: string, theme: 'light' | 'dark', chrome: string) {
  const parsed = new DOMParser().parseFromString(source, 'text/html');
  const svg = parsed.querySelector<SVGSVGElement>('svg[viewBox]');
  if (!svg) throw new Error('图谱中缺少 SVG');
  // 图内含可操作节点，使用 group 让辅助技术能继续遍历其中的按钮。
  svg.setAttribute('role', 'group');
  const bounds = svg
    .getAttribute('viewBox')!
    .trim()
    .split(/[\s,]+/)
    .map(Number);
  if (bounds.length !== 4 || !bounds.every(Number.isFinite) || bounds[2] <= 0 || bounds[3] <= 0)
    throw new Error('图谱尺寸无效');
  svg.querySelectorAll('script, foreignObject, iframe, a').forEach((element) => {
    if (element.tagName.toLowerCase() === 'a') element.replaceWith(...element.childNodes);
    else element.remove();
  });
  for (const element of [svg, ...svg.querySelectorAll('*')]) {
    for (const attr of [...element.attributes]) {
      if (
        /^on/i.test(attr.name) ||
        (/^(?:href|xlink:href)$/i.test(attr.name) && !attr.value.startsWith('#'))
      )
        element.removeAttribute(attr.name);
    }
  }
  const nodes: DiagramNode[] = [...svg.querySelectorAll<SVGGElement>('[data-node-id]')].map(
    (node) => ({
      id: node.dataset.nodeId!,
      label:
        node.dataset.nodeLabel || node.querySelector('text')?.textContent || node.dataset.nodeId!,
      description: node.dataset.nodeSublabel,
      context: node.dataset.nodeContext,
      branches: [],
    }),
  );
  for (const node of nodes) {
    const edges = [...svg.querySelectorAll<SVGGElement>('[data-edge-from]')].filter(
      (edge) => edge.dataset.edgeFrom === node.id,
    );
    node.branches = edges.flatMap((edge, i) => {
      const destination = nodes.find((item) => item.id === edge.dataset.edgeTo);
      return destination
        ? [
            {
              id: edge.dataset.edgeId || `${node.id}-${i}`,
              target: destination.id,
              label: `${edge.dataset.edgeLabel ? `${edge.dataset.edgeLabel} → ` : '→ '}${destination.label}`,
            },
          ]
        : [];
    });
    // 原 SVG 的跨线和命中层可能重复携带同一关系，说明区只列一次。
    node.branches = node.branches.filter(
      (branch, index, all) =>
        all.findIndex((item) => item.target === branch.target && item.label === branch.label) ===
        index,
    );
  }
  const styles = [...parsed.head.querySelectorAll('style')]
    .map((style) => style.textContent)
    .join('\n');
  const authoredPreset = parsed.documentElement.dataset.preset ?? svg.dataset.preset ?? 'classic';
  const preset = ['classic', 'signal-flow', 'blueprint', 'editorial'].includes(authoredPreset)
    ? authoredPreset
    : 'classic';
  return {
    bounds,
    nodes,
    html: `<!doctype html><html lang="zh-CN" data-theme="${theme}" data-preset="${preset}" data-appearance="${theme === 'dark' ? 'dark' : 'white'}"><head><meta charset="utf-8"><style>${styles}\n${chrome}
    html,body { margin:0!important;padding:0!important;width:100%!important;height:100%!important;min-width:0!important;min-height:0!important;overflow:hidden!important;background:var(--bg)!important; }
    body > svg { display:block!important;width:100%!important;height:100%!important;min-width:0!important;min-height:0!important;max-width:none!important;max-height:none!important;margin:0!important;touch-action:none; }
    svg [data-node-id] { cursor:pointer; }
    svg [data-node-id][aria-pressed="true"] > rect, svg [data-node-id][aria-pressed="true"] > path, svg [data-node-id][aria-pressed="true"] > polygon { stroke:#168979!important;stroke-width:2.5px!important;filter:drop-shadow(0 0 3px #16897950); }
    .source-evidence-beacon { display:none!important; }
    * { animation:none!important;transition:none!important; }
  </style></head><body>${svg.outerHTML}</body></html>`,
  };
}
