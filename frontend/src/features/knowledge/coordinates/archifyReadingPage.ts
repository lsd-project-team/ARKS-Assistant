export type ReadingAppearance = 'white' | 'classic' | 'dark';

// 从 Archify 已交付的 HTML 提取原 SVG；保留节点、连线与 viewBox，阅读副本不执行查看器脚本。
export function createReadingDiagram(source: string, appearance: ReadingAppearance, chrome = '') {
  const svgStart = source.indexOf('<svg ');
  const svgEnd = source.indexOf('</svg>', svgStart);
  if (svgStart < 0 || svgEnd < 0) throw new Error('Archify 交付中缺少图形');
  const svg = source.slice(svgStart, svgEnd + 6);
  const viewBox = svg
    .match(/\bviewBox="([^"]+)"/)?.[1]
    .split(/\s+/)
    .map(Number);
  if (
    !viewBox ||
    viewBox.length !== 4 ||
    !viewBox.every(Number.isFinite) ||
    viewBox[2] <= 0 ||
    viewBox[3] <= 0
  )
    throw new Error('Archify 图形尺寸无效');
  const head = source.slice(0, source.indexOf('</head>'));
  const styles = [...head.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/g)]
    .map((match) => match[1])
    .join('\n');
  const readingSvg = svg
    .replace(/\s(?:tabindex|aria-pressed)="[^"]*"/g, '')
    .replace(/\srole="button"/g, '');
  const theme = appearance === 'dark' ? 'dark' : 'light';
  return {
    width: viewBox[2],
    height: viewBox[3],
    html: `<!doctype html><html lang="zh-CN" data-theme="${theme}" data-appearance="${appearance}"><head><meta charset="utf-8"><style>${styles}\n${chrome}
      html, body { margin: 0 !important; padding: 0 !important; min-height: 0 !important; height: auto !important; background: var(--bg); }
      svg[role="img"] { display: block !important; width: 100% !important; height: auto !important; min-width: 0 !important; min-height: 0 !important; max-width: none !important; max-height: none !important; margin: 0 !important; }
      svg .tree-label, svg [data-node-id] text.t-primary { font-size: 18px !important; font-weight: 500; }
      svg .tree-sublabel, svg [data-node-id] text.t-muted { font-size: 14px !important; }
      svg .source-evidence-beacon { display: none !important; }
      * { animation: none !important; transition: none !important; }
    </style></head><body>${readingSvg}</body></html>`,
  };
}
