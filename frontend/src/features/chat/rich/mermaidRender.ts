import mermaid from 'mermaid';
import DOMPurify from 'dompurify';
import { validateMermaidContent } from './visualValidation.ts';

let serial = 0;
let queue: Promise<unknown> = Promise.resolve();
export function sanitizeDiagram(svg: string) {
  const fragment = DOMPurify.sanitize(svg, {
    USE_PROFILES: { svg: true, svgFilters: true },
    FORBID_TAGS: ['foreignObject', 'script', 'iframe', 'image', 'a'],
    FORBID_ATTR: ['href', 'xlink:href'],
    RETURN_DOM_FRAGMENT: true,
  });
  const root = fragment.querySelector('svg');
  if (!root) return '';
  const box = root
    .getAttribute('viewBox')
    ?.trim()
    .split(/[\s,]+/)
    .map(Number);
  if (box?.length === 4 && box.every(Number.isFinite) && box[2] > 0 && box[3] > 0) {
    // Mermaid 的百分比宽度用于内联 SVG；图片上下文需明确固有尺寸，避免小图被撑满正文。
    root.setAttribute('width', String(box[2]));
    root.setAttribute('height', String(box[3]));
    root.removeAttribute('style');
  }
  return root.outerHTML;
}

export function renderMermaid(content: string, dark: boolean): Promise<string> {
  // Mermaid 的配置和渲染队列是全局的；串行处理避免不同消息/主题相互覆盖。
  const task = queue
    .catch(() => {})
    .then(async () => {
      validateMermaidContent(content);
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: 'strict',
        theme: dark ? 'dark' : 'default',
        suppressErrorRendering: true,
        maxTextSize: 20000,
        maxEdges: 200,
        htmlLabels: false,
        flowchart: { htmlLabels: false },
        fontFamily: 'sans-serif',
      });
      const { svg } = await mermaid.render(`arks-mermaid-${++serial}`, content);
      return sanitizeDiagram(svg);
    });
  queue = task;
  return task;
}
