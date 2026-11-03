import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { Minus, Plus, RotateCcw } from 'lucide-react';

const MIN_ZOOM = 0.25;
const MAX_ZOOM = 4;

export function MermaidViewport({ svg, title }: { svg: string; title: string }) {
  const viewport = useRef<HTMLDivElement>(null);
  const image = useRef<HTMLImageElement>(null);
  const targetZoom = useRef(1);
  const anchor = useRef<{ x: number; y: number; clientX: number; clientY: number }>(undefined);
  const [zoom, setZoom] = useState(1);
  const [size, setSize] = useState<{ width: number; height: number }>();

  const changeZoom = useCallback((value: number, clientX: number, clientY: number) => {
    const rect = image.current?.getBoundingClientRect();
    if (!rect?.width || !rect.height) return;
    const next = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, value));
    if (next === targetZoom.current) return;
    // 记录图片上的相对位置，缩放提交后让鼠标继续指向原来的图内位置。
    anchor.current = {
      x: (clientX - rect.left) / rect.width,
      y: (clientY - rect.top) / rect.height,
      clientX,
      clientY,
    };
    targetZoom.current = next;
    setZoom(next);
  }, []);

  useEffect(() => {
    const element = viewport.current;
    if (!element || !size) return;
    const wheel = (event: WheelEvent) => {
      if (!event.ctrlKey || !Number.isFinite(event.deltaY) || !event.deltaY) return;
      // React 的滚轮监听可能是 passive；原生非被动监听才能阻止浏览器整页缩放。
      event.preventDefault();
      event.stopPropagation();
      const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? element.clientHeight : 1;
      changeZoom(
        targetZoom.current * Math.exp(-event.deltaY * unit * 0.002),
        event.clientX,
        event.clientY,
      );
    };
    element.addEventListener('wheel', wheel, { passive: false });
    return () => element.removeEventListener('wheel', wheel);
  }, [size, changeZoom]);

  useLayoutEffect(() => {
    const point = anchor.current;
    const element = viewport.current;
    const rect = image.current?.getBoundingClientRect();
    if (!point || !element || !rect) return;
    element.scrollLeft += rect.left + point.x * rect.width - point.clientX;
    element.scrollTop += rect.top + point.y * rect.height - point.clientY;
    anchor.current = undefined;
  }, [zoom]);

  const zoomFromCenter = (factor: number) => {
    const rect = viewport.current?.getBoundingClientRect();
    if (rect)
      changeZoom(
        targetZoom.current * factor,
        rect.left + rect.width / 2,
        rect.top + rect.height / 2,
      );
  };

  return (
    <>
      <div className="rich-mermaid-tools">
        <span>Ctrl + 滚轮缩放</span>
        <div>
          <button
            type="button"
            aria-label="缩小流程图"
            disabled={zoom <= MIN_ZOOM}
            onClick={() => zoomFromCenter(1 / 1.2)}
          >
            <Minus size={14} />
          </button>
          <output aria-label="流程图缩放比例">{Math.round(zoom * 100)}%</output>
          <button
            type="button"
            aria-label="放大流程图"
            disabled={zoom >= MAX_ZOOM}
            onClick={() => zoomFromCenter(1.2)}
          >
            <Plus size={14} />
          </button>
          <button
            type="button"
            aria-label="重置流程图缩放"
            title="恢复 100%"
            onClick={() => {
              anchor.current = undefined;
              targetZoom.current = 1;
              setZoom(1);
              if (viewport.current) {
                viewport.current.scrollLeft = 0;
                viewport.current.scrollTop = 0;
              }
            }}
          >
            <RotateCcw size={14} />
          </button>
        </div>
      </div>
      <div
        className="rich-mermaid-viewport"
        ref={viewport}
        tabIndex={0}
        role="region"
        aria-label={`${title}，按住 Ctrl 并滚动滚轮缩放`}
      >
        {/* 清理后的 SVG 保持在图片上下文中，缩放只改变图片的布局尺寸。 */}
        <img
          ref={image}
          src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`}
          alt={title}
          draggable={false}
          style={size ? { width: size.width * zoom, height: size.height * zoom } : undefined}
          onLoad={(event) => {
            const { naturalWidth: width, naturalHeight: height } = event.currentTarget;
            if (width && height) setSize({ width, height });
          }}
        />
      </div>
    </>
  );
}
