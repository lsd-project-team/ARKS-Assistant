import mermaid from 'mermaid';
import DOMPurify from 'dompurify';
import { validateMermaidContent } from './visualValidation.ts';

let serial = 0;
let queue: Promise<unknown> = Promise.resolve();
export function sanitizeDiagram(svg: string) {
  return DOMPurify.sanitize(svg, {
    USE_PROFILES: { svg: true, svgFilters: true },
    FORBID_TAGS: ['foreignObject', 'script', 'iframe', 'image', 'a'],
    FORBID_ATTR: ['href', 'xlink:href'],
  });
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
