import { useEffect, useRef, useState } from 'react';
import { useReaderCanvas } from './ReaderFrame';
import { diagramDocument } from './diagramDocument';
import { useAppearance } from '../../settings/lib/appearance';
import diagramChrome from '../diagramChrome.css?inline';
import latinFont from '@fontsource-variable/geist/index.css?inline';
import chineseFont from '@fontsource-variable/noto-sans-sc/index.css?inline';

/** 统一接管画布相机和节点选择；交付页自身的工具栏与脚本不再嵌套。 */
export function DiagramViewport({
  path,
  revision,
  source,
  title,
}: {
  path?: string;
  revision?: string;
  source?: string;
  title: string;
}) {
  const bridge = useReaderCanvas();
  const bridgeRef = useRef(bridge);
  bridgeRef.current = bridge;
  const appearance = useAppearance((state) => state.mode);
  const [page, setPage] = useState<ReturnType<typeof diagramDocument>>();
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  const [loaded, setLoaded] = useState<Document | null>(null);
  const focusNode = useRef<(id: string, move: boolean) => void>(() => {});

  useEffect(() => {
    const controller = new AbortController();
    setPage(undefined);
    setLoaded(null);
    setFailed(false);
    bridgeRef.current?.register([]);
    void (
      source !== undefined
        ? Promise.resolve(source)
        : fetch(`${path}?review=${revision ?? ''}`, { signal: controller.signal }).then(
            (response) => {
              if (!response.ok) throw new Error('图谱加载失败');
              return response.text();
            },
          )
    )
      .then((html) => {
        if (controller.signal.aborted) return;
        const page = diagramDocument(
          html,
          appearance === 'dark' ? 'dark' : 'light',
          `${latinFont}\n${chineseFont}\n${diagramChrome}`,
        );
        // 保留应用的白色、经典及深色外观，语义节点颜色仍来自原交付图。
        page.html = page.html.replace('data-appearance="white"', `data-appearance="${appearance}"`);
        setPage(page);
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => controller.abort();
  }, [path, revision, source, appearance, retry]);

  useEffect(() => {
    if (!page || !loaded) return;
    const svg = loaded.querySelector<SVGSVGElement>('body > svg');
    const win = loaded.defaultView;
    if (!svg || !win) return;
    const [x, y, width, height] = page.bounds;
    const camera = { x: x + width / 2, y: y + height / 2, scale: 1 };
    let autoFit = true;
    let initialized = false;
    let drag: { x: number; y: number; cx: number; cy: number; moved: boolean } | undefined;
    let dragged = false;
    const paint = () => {
      const w = win.innerWidth / camera.scale,
        h = win.innerHeight / camera.scale;
      svg.setAttribute('viewBox', `${camera.x - w / 2} ${camera.y - h / 2} ${w} ${h}`);
      bridgeRef.current?.setScale(camera.scale);
    };
    const fit = () => {
      if (!win.innerWidth || !win.innerHeight) return;
      const fitted = Math.min((win.innerWidth - 24) / width, (win.innerHeight - 24) / height);
      camera.scale = Math.min(1, fitted);
      camera.x = x + width / 2;
      camera.y = y + height / 2;
      paint();
    };
    const zoom = (factor: number) => {
      autoFit = false;
      camera.scale = Math.min(4, Math.max(0.1, camera.scale * factor));
      paint();
    };
    const selectNode = (id: string, move: boolean) => {
      for (const element of svg.querySelectorAll<SVGGraphicsElement>('[data-node-id]')) {
        const selected = element.dataset.nodeId === id;
        element.setAttribute('aria-pressed', String(selected));
        if (!selected || !move) continue;
        const bounds = element.getBoundingClientRect();
        // 用屏幕坐标计算相机偏移，同时适配树图中的 translate 和缩放组。
        camera.x += (bounds.left + bounds.width / 2 - win.innerWidth / 2) / camera.scale;
        camera.y += (bounds.top + bounds.height / 2 - win.innerHeight / 2) / camera.scale;
        autoFit = false;
        paint();
      }
    };
    focusNode.current = selectNode;
    const pick = (event: Event) => {
      if (dragged) {
        dragged = false;
        return;
      }
      const node = (event.target as Element | null)?.closest('[data-node-id]');
      if (node) bridgeRef.current?.select(node.getAttribute('data-node-id')!);
    };
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        pick(event);
      }
    };
    const down = (event: PointerEvent) => {
      if (event.button !== 0) return;
      drag = { x: event.clientX, y: event.clientY, cx: camera.x, cy: camera.y, moved: false };
      dragged = false;
    };
    const move = (event: PointerEvent) => {
      if (!drag) return;
      const dx = event.clientX - drag.x,
        dy = event.clientY - drag.y;
      if (Math.hypot(dx, dy) < 4 && !drag.moved) return;
      if (!drag.moved) svg.setPointerCapture(event.pointerId);
      drag.moved = true;
      autoFit = false;
      camera.x = drag.cx - dx / camera.scale;
      camera.y = drag.cy - dy / camera.scale;
      paint();
    };
    const up = () => {
      dragged = Boolean(drag?.moved);
      drag = undefined;
    };
    const wheel = (event: WheelEvent) => {
      if (!event.ctrlKey && !event.metaKey) return;
      event.preventDefault();
      zoom(event.deltaY < 0 ? 1.1 : 1 / 1.1);
    };
    const exportSvg = () => {
      const clone = svg.cloneNode(true) as SVGSVGElement;
      clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
      clone.setAttribute('viewBox', page.bounds.join(' '));
      clone.setAttribute('width', String(width));
      clone.setAttribute('height', String(height));
      clone.dataset.theme = appearance === 'dark' ? 'dark' : 'light';
      clone.dataset.appearance = appearance;
      const style = loaded.createElementNS('http://www.w3.org/2000/svg', 'style');
      style.textContent = [...loaded.head.querySelectorAll('style')]
        .map((item) => item.textContent?.replace(/html(?=\[data-)/g, ':root'))
        .join('\n');
      clone.prepend(style);
      const url = URL.createObjectURL(
        new Blob([new XMLSerializer().serializeToString(clone)], {
          type: 'image/svg+xml;charset=utf-8',
        }),
      );
      const link = document.createElement('a');
      link.href = url;
      link.download = `${title.replace(/[\\/:*?"<>|]/g, '-')}.svg`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    };
    bridgeRef.current?.register(page.nodes, {
      fit: () => {
        autoFit = true;
        fit();
      },
      zoom,
      export: exportSvg,
    });
    const resize = new ResizeObserver(() => {
      if (!win.innerWidth || !win.innerHeight) return;
      if (!initialized) {
        initialized = true;
        fit();
      } else if (autoFit) fit();
      else paint();
    });
    resize.observe(loaded.documentElement);
    selectNode(bridgeRef.current?.selected ?? page.nodes[0]?.id, false);
    svg.addEventListener('click', pick);
    svg.addEventListener('keydown', keyboard);
    svg.addEventListener('pointerdown', down);
    svg.addEventListener('pointermove', move);
    svg.addEventListener('pointerup', up);
    svg.addEventListener('pointercancel', up);
    svg.addEventListener('wheel', wheel, { passive: false });
    return () => {
      resize.disconnect();
      focusNode.current = () => {};
      svg.removeEventListener('click', pick);
      svg.removeEventListener('keydown', keyboard);
      svg.removeEventListener('pointerdown', down);
      svg.removeEventListener('pointermove', move);
      svg.removeEventListener('pointerup', up);
      svg.removeEventListener('pointercancel', up);
      svg.removeEventListener('wheel', wheel);
    };
  }, [page, loaded, appearance, title]);

  const selected = bridge?.selected;
  const lastSelected = useRef<string | undefined>(undefined);
  useEffect(() => {
    if (!selected) return;
    focusNode.current(
      selected,
      lastSelected.current !== undefined && lastSelected.current !== selected,
    );
    lastSelected.current = selected;
  }, [selected, loaded]);
  return (
    <div className="reader-viewport" data-diagram-source={path}>
      {page ? (
        <iframe
          title={`${title} 流程图`}
          srcDoc={page.html}
          sandbox="allow-same-origin"
          onLoad={(event) => setLoaded(event.currentTarget.contentDocument)}
        />
      ) : (
        <div className="reader-loading" role={failed ? 'alert' : 'status'}>
          {failed ? (
            <>
              <p>图谱暂时无法加载。</p>
              <button type="button" className="button" onClick={() => setRetry(retry + 1)}>
                重新加载
              </button>
            </>
          ) : (
            '正在加载图谱…'
          )}
        </div>
      )}
    </div>
  );
}
