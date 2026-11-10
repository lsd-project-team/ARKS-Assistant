import { renderDiagram } from '../../../shared/utils/mermaid.ts';
import { validateMermaidContent } from './visualValidation.ts';

export { sanitizeDiagram } from '../../../shared/utils/mermaid.ts';

export async function renderMermaid(content: string, dark: boolean): Promise<string> {
  // 聊天仍沿用原有白名单；静态文档的样式能力不扩展到模型输出。
  validateMermaidContent(content);
  return renderDiagram(content, dark);
}
