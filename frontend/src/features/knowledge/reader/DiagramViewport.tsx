import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { useReaderCanvas } from './ReaderFrame';
import { diagramDocument } from './diagramDocument';
import { fitCamera, boundCamera, zoomCamera, cameraViewBox, diagramHeight } from './diagramCamera';
import { clarifyNodeText } from './diagramText';
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
  const container = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState(440);
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
    if (!page || !container.current) return;
    const element = container.current;
    const measure = () => {
      if (element.clientWidth > 0) setHeight(diagramHeight(page.bounds, element.clientWidth));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [page]);

  useEffect(() => {
    if (!page || !loaded) return;
    const svg = loaded.querySelector<SVGSVGElement>('body > svg');
    const win = loaded.defaultView;
    if (!svg || !win) return;
    let bounds = page.bounds;
    const viewport = () => {
      const rect = svg.getBoundingClientRect();
      return { width: rect.width, height: rect.height };
    };
    const camera = fitCamera(bounds, viewport());
    let autoFit = true;
    let active = true;
    let drag: { x: number; y: number; cx: number; cy: number; moved: boolean } | undefined;
    let dragged = false;
    const paint = () => {
      Object.assign(camera, boundCamera(camera, bounds, viewport()));
      svg.setAttribute('viewBox', cameraViewBox(camera, viewport()).join(' '));
      bridgeRef.current?.setScale(camera.scale);
    };
    const fit = () => {
      const size = viewport();
      if (!size.width || !size.height) return;
      Object.assign(camera, fitCamera(bounds, size));
      paint();
    };
    const zoom = (factor: number, anchor?: { x: number; y: number }) => {
      autoFit = false;
      Object.assign(camera, zoomCamera(camera, bounds, viewport(), factor, anchor));
      paint();
    };
    const selectNode = (id: string, move: boolean) => {
      for (const element of svg.querySelectorAll<SVGGraphicsElement>('[data-node-id]')) {
        const selected = element.dataset.nodeId === id;
        element.setAttribute('aria-pressed', String(selected));
        if (!selected || !move) continue;
        const box = element.getBoundingClientRect();
        const size = viewport();
        // 全图状态只高亮，不移动相机；放大后只补足越出视口的部分。
        const shift = (start: number, end: number, pixels: number) =>
          end - start > pixels - 32
            ? (start + end - pixels) / 2
            : start < 16
              ? start - 16
              : end > pixels - 16
                ? end - pixels + 16
                : 0;
        const next = boundCamera(
          {
            ...camera,
            x: camera.x + shift(box.left, box.right, size.width) / camera.scale,
            y: camera.y + shift(box.top, box.bottom, size.height) / camera.scale,
          },
          bounds,
          size,
        );
        if (next.x === camera.x && next.y === camera.y) continue;
        autoFit = false;
        Object.assign(camera, next);
        paint();
      }
    };
    const layout = () => {
      if (!active) return;
      // 百分比装饰层依赖 viewBox；每次测量从原始坐标系开始，避免它随缩放反复变大。
      svg.setAttribute('viewBox', page.bounds.join(' '));
      clarifyNodeText(svg);
      const box = svg.getBBox();
      const [x, y, width, height] = page.bounds;
      const left = Math.min(x, box.x),
        top = Math.min(y, box.y);
      bounds = [
        left,
        top,
        Math.max(x + width, box.x + box.width) - left,
        Math.max(y + height, box.y + box.height) - top,
      ];
      if (container.current?.clientWidth)
        setHeight(diagramHeight(bounds, container.current.clientWidth));
      if (autoFit) fit();
      else paint();
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
      if (!drag) return;
      dragged = drag.moved;
      drag = undefined;
    };
    const wheel = (event: WheelEvent) => {
      if (!event.ctrlKey && !event.metaKey) return;
      event.preventDefault();
      zoom(event.deltaY < 0 ? 1.1 : 1 / 1.1, { x: event.clientX, y: event.clientY });
    };
    const exportSvg = () => {
      const clone = svg.cloneNode(true) as SVGSVGElement;
      clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
      clone.setAttribute('viewBox', bounds.join(' '));
      clone.setAttribute('width', String(bounds[2]));
      clone.setAttribute('height', String(bounds[3]));
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
      readable: () => {
        const sizes = [
          ...svg.querySelectorAll<SVGTextElement>(
            '[data-node-id] text.t-primary,[data-node-id] text.tree-label,[data-node-id] text[data-detail="context"],[data-node-id] text.tree-sublabel',
          ),
        ]
          .map((text) => parseFloat(win.getComputedStyle(text).fontSize))
          .filter((size) => size > 0);
        const target = Math.max(
          fitCamera(bounds, viewport()).scale,
          14 / (sizes.length ? Math.min(...sizes) : 14),
        );
        zoom(target / camera.scale);
        const id = bridgeRef.current?.selected;
        if (id) selectNode(id, true);
      },
      export: exportSvg,
    });
    const resize = new ResizeObserver(() => {
      const size = viewport();
      if (!size.width || !size.height) return;
      if (autoFit) fit();
      else paint();
    });
    resize.observe(loaded.documentElement);
    layout();
    void loaded.fonts.ready.then(layout);
    selectNode(bridgeRef.current?.selected ?? page.nodes[0]?.id, false);
    svg.addEventListener('click', pick);
    svg.addEventListener('keydown', keyboard);
    svg.addEventListener('pointerdown', down);
    svg.addEventListener('pointermove', move);
    svg.addEventListener('pointerup', up);
    svg.addEventListener('pointercancel', up);
    svg.addEventListener('lostpointercapture', up);
    win.addEventListener('blur', up);
    svg.addEventListener('wheel', wheel, { passive: false });
    return () => {
      active = false;
      resize.disconnect();
      focusNode.current = () => {};
      svg.removeEventListener('click', pick);
      svg.removeEventListener('keydown', keyboard);
      svg.removeEventListener('pointerdown', down);
      svg.removeEventListener('pointermove', move);
      svg.removeEventListener('pointerup', up);
      svg.removeEventListener('pointercancel', up);
      svg.removeEventListener('lostpointercapture', up);
      win.removeEventListener('blur', up);
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
    <div
      ref={container}
      className="reader-viewport"
      data-diagram-source={path}
      style={{ '--diagram-height': `${height}px` } as CSSProperties}
    >
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
