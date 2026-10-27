import { useEffect, useState } from 'react';
import { archifyData } from './data/archifyData';
import { useAppearance } from '../settings/lib/appearance';
import diagramChrome from './diagramChrome.css?inline';
import diagramLatinFont from '@fontsource-variable/geist/index.css?inline';
import diagramChineseFont from '@fontsource-variable/noto-sans-sc/index.css?inline';
const resourceHref = (href: string) => `/archify/${href.replace(/^docs[\\/]archify[\\/]/, '')}`;

export function OriginalDiagram({
  path,
  title,
  onNode,
  theme,
  compact = false,
  artifactRevision,
}: {
  path: string;
  title: string;
  onNode?: (id: string) => void;
  theme: 'dark' | 'light';
  compact?: boolean;
  artifactRevision?: string;
}) {
  const [document, setDocument] = useState<Document | null>(null);
  const [initialTheme] = useState(theme);
  const revision = (
    artifactRevision ??
    archifyData.flowchartCatalog.entries.find((entry) => entry.html === path)?.htmlSha256
  )?.slice(0, 16);
  const diagramURL = (color: string) =>
    `${resourceHref(path)}?theme=${color}${revision ? `&review=${revision}` : ''}`;
  const appearance = useAppearance((state) => state.mode);
  useEffect(() => {
    // 图谱预设控制节点样式，页面外观单独控制工具栏和阅读底色。
    if (document) document.documentElement.dataset.appearance = appearance;
  }, [document, appearance]);
  useEffect(() => {
    if (!document) return;
    const style = document.createElement('style');
    // iframe 有独立的字体上下文；同样引用本地字体，避免原图退回粗重的系统字形。
    style.textContent = `${diagramLatinFont}\n${diagramChineseFont}\n${diagramChrome}`;
    if (compact) {
      // 节点正文已有标题与说明，嵌入时只保留图和图内阅读工具。
      style.textContent += `
        body { padding: 0 !important; }
        .header, .toolbar, .reader-rail { display: none !important; }
        .container { margin: 0; padding: 0; max-width: none; width: 100%; }
        .diagram-container { margin: 0; border: 0; border-radius: 0; min-height: 580px; }
      `;
    }
    document.head.appendChild(style);
    let cancelled = false;
    // 窄栏沿用查看器的原生缩放与拖动，避免将整张图压成无法阅读的缩略图。
    if (compact) {
      void document.fonts.ready.then(async () => {
        if (cancelled || document.documentElement.clientWidth >= 600) return;
        const zoom = document.querySelector<HTMLButtonElement>('button[data-view="in"]');
        const nextFrame = () =>
          new Promise<void>((resolve) =>
            document.defaultView?.requestAnimationFrame(() => resolve()),
          );
        await nextFrame();
        for (let count = 0; count < 8 && !cancelled; count++) {
          const label = document.querySelector<SVGTextElement>(
            '.tree-label, .node-title, text[data-node-label]',
          );
          const matrix = label?.getScreenCTM();
          const fontSize = label && document.defaultView?.getComputedStyle(label).fontSize;
          if (!zoom || !matrix || !fontSize) break;
          if (parseFloat(fontSize) * Math.hypot(matrix.a, matrix.b) >= 10) break;
          zoom.click();
          await nextFrame();
        }
      });
    }
    const guide = document.getElementById('btn-diagram-guide');
    // 原图只比较按钮本身，图标点击会被误判为外部点击；保留按钮原有处理，再阻止冒泡。
    const keepGuideOpen = (event: Event) => event.stopPropagation();
    guide?.addEventListener('click', keepGuideOpen);
    return () => {
      cancelled = true;
      style.remove();
      guide?.removeEventListener('click', keepGuideOpen);
    };
  }, [document, compact]);
  useEffect(() => {
    if (!document || document.documentElement.dataset.theme === theme) return;
    const toggle = document.getElementById('btn-theme');
    if (toggle) toggle.click();
    else document.documentElement.dataset.theme = theme;
  }, [document, theme]);
  useEffect(() => {
    if (!document || !onNode) return;
    const select = (event: Event) => {
      const target = event.target as Element | null;
      const node = target?.closest?.('[data-node-id]');
      if (node) onNode(node.getAttribute('data-node-id')!);
    };
    const selectKeyboard = (event: KeyboardEvent) => {
      if (event.key === 'Enter' || event.key === ' ') select(event);
    };
    document.addEventListener('click', select, true);
    document.addEventListener('keyup', selectKeyboard, true);
    return () => {
      document.removeEventListener('click', select, true);
      document.removeEventListener('keyup', selectKeyboard, true);
    };
  }, [document, onNode]);
  const Container = compact ? 'figure' : 'section';
  return (
    <Container className={compact ? 'g0-archify' : 'section card panel original-diagram'}>
      <div className="panel-title">
        <div>
          <span className="eyebrow">{compact ? `Archify · ${title}` : '流程图'}</span>
          {!compact && (
            <p>使用图内缩放、查找与演示工具阅读。生产主流程可点击节点，查看下方环节说明。</p>
          )}
        </div>
        <a className="button" href={diagramURL(theme)} target="_blank" rel="noreferrer">
          全屏阅读 ↗
        </a>
      </div>
      {compact && <figcaption>图内可放大、拖动查看；全屏阅读可使用完整工具。</figcaption>}
      <iframe
        title={`${title} 流程图`}
        src={diagramURL(initialTheme)}
        onLoad={(event) => setDocument(event.currentTarget.contentDocument)}
      />
    </Container>
  );
}
