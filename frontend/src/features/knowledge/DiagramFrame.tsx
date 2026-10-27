import { useEffect, useState } from 'react';
import { archifyData } from './data/archifyData';
import { useAppearance } from '../settings/lib/appearance';
import diagramChrome from './diagramChrome.css?inline';
import diagramLatinFont from '@fontsource-variable/geist/index.css?inline';
import diagramChineseFont from '@fontsource-variable/noto-sans-sc/index.css?inline';

export function diagramHref(path: string, theme: string, revision?: string) {
  const file = path.replace(/^docs[\\/]archify[\\/]/, '').replace(/^archify\//, '');
  const version =
    revision ?? archifyData.flowchartCatalog.entries.find((item) => item.html === path)?.htmlSha256;
  return `/archify/${file}?theme=${theme}${version ? `&review=${version.slice(0, 16)}` : ''}`;
}

export function DiagramFrame({
  path,
  title,
  theme,
  revision,
  activeNode,
  hideNotes = false,
  onNode,
}: {
  path: string;
  title: string;
  theme: 'dark' | 'light';
  revision?: string;
  activeNode?: string;
  hideNotes?: boolean;
  onNode?: (id: string) => void;
}) {
  const [document, setDocument] = useState<Document | null>(null);
  const [initialTheme] = useState(theme);
  const [aspectRatio, setAspectRatio] = useState(1.8);
  const appearance = useAppearance((state) => state.mode);
  useEffect(() => {
    if (document) document.documentElement.dataset.appearance = appearance;
  }, [document, appearance]);
  useEffect(() => {
    if (!document) return;
    const style = document.createElement('style');
    // iframe 有独立字体环境；沿用主页面外观，不改节点语义颜色。
    style.textContent = `${diagramLatinFont}\n${diagramChineseFont}\n${diagramChrome}`;
    if (hideNotes) style.textContent += '\n.cards { display: none !important; }';
    document.head.appendChild(style);
    const guide = document.getElementById('btn-diagram-guide');
    const keepGuideOpen = (event: Event) => event.stopPropagation();
    guide?.addEventListener('click', keepGuideOpen);
    return () => {
      style.remove();
      guide?.removeEventListener('click', keepGuideOpen);
    };
  }, [document, hideNotes]);
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
      if (!node) return;
      if (activeNode) {
        // 内嵌图的节点由主页面解释，避免图内焦点与当前步骤形成两套选中状态。
        event.preventDefault();
        event.stopPropagation();
      }
      onNode(node.getAttribute('data-node-id')!);
    };
    const selectKeyboard = (event: KeyboardEvent) => {
      if (event.key === 'Enter' || event.key === ' ') select(event);
    };
    document.addEventListener('click', select, true);
    const keyboardEvent = activeNode ? 'keydown' : 'keyup';
    document.addEventListener(keyboardEvent, selectKeyboard, true);
    return () => {
      document.removeEventListener('click', select, true);
      document.removeEventListener(keyboardEvent, selectKeyboard, true);
    };
  }, [document, onNode, activeNode]);
  useEffect(() => {
    if (!document) return;
    const nodes = document.querySelectorAll<SVGGElement>('g[data-node-id]');
    // 逐步阅读只标记当前节点，保留全部分支；不触发会遮挡图面的护照浮层。
    nodes.forEach((node) => {
      node.classList.toggle('guided-node-active', node.dataset.nodeId === activeNode);
    });
    return () => nodes.forEach((node) => node.classList.remove('guided-node-active'));
  }, [document, activeNode]);
  return (
    <iframe
      title={`${title} 流程图`}
      src={`${diagramHref(path, initialTheme, revision)}${activeNode ? '&embed=1' : ''}`}
      style={activeNode ? { aspectRatio, height: 'auto' } : undefined}
      onLoad={(event) => {
        const content = event.currentTarget.contentDocument;
        setDocument(content);
        // 内嵌阅读只显示图面，按真实画布比例排版；完整工具保留在全屏阅读中。
        const box =
          content?.querySelector<SVGSVGElement>('.diagram-container svg')?.viewBox.baseVal;
        if (box?.width && box.height) setAspectRatio((box.width + 16) / (box.height + 20));
      }}
    />
  );
}
