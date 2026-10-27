import { useEffect, useRef, useState } from 'react';
import { useAppearance } from '../../settings/lib/appearance';
import type { CoordinateArtifact } from '../data/coordinateDiagrams';
import { createReadingDiagram } from './archifyReadingPage';
import diagramChrome from '../diagramChrome.css?inline';
import latinFont from '@fontsource-variable/geist/index.css?inline';
import chineseFont from '@fontsource-variable/noto-sans-sc/index.css?inline';

export function ReadingDiagram({
  source,
  narrow,
  title,
  readingMinWidth = 640,
  readingFontSize = 18,
}: {
  source: CoordinateArtifact;
  narrow?: CoordinateArtifact;
  title: string;
  readingMinWidth?: number;
  readingFontSize?: number;
}) {
  const container = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState<number | null>(null);
  const [page, setPage] = useState<ReturnType<typeof createReadingDiagram> | null>(null);
  const [failed, setFailed] = useState(false);
  const appearance = useAppearance((state) => state.mode);
  // 按图的可读宽度切换排布，避免宽图整体缩小后文字难辨。
  const selected = narrow && width !== null && width < readingMinWidth ? narrow : source;
  // 横纵图使用同一阅读字号，切换排布时仍保持文字清晰。
  const fontSize = readingFontSize;
  const naturalWidth = page ? (page.width * fontSize) / 18 : 0;
  const url = `/archify/${selected.path}?review=${selected.sha256.slice(0, 16)}`;

  useEffect(() => {
    const element = container.current;
    if (!element) return;
    const measure = () => {
      const style = getComputedStyle(element);
      setWidth(
        element.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight),
      );
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (width === null) return;
    const abort = new AbortController();
    setPage(null);
    setFailed(false);
    void fetch(url, { signal: abort.signal })
      .then((response) => {
        if (!response.ok) throw new Error('图谱加载失败');
        return response.text();
      })
      .then((html) => {
        if (!abort.signal.aborted)
          setPage(
            createReadingDiagram(
              html,
              appearance,
              `${latinFont}\n${chineseFont}\n${diagramChrome}`,
              fontSize,
            ),
          );
      })
      .catch(() => {
        if (!abort.signal.aborted) setFailed(true);
      });
    return () => abort.abort();
  }, [url, appearance, fontSize, width === null]);

  return (
    <div ref={container} className="g0-reading-surface" data-archify-source={selected.path}>
      {page ? (
        <iframe
          title={`${title} 阅读图`}
          srcDoc={page.html}
          sandbox="allow-same-origin"
          style={{
            maxWidth: naturalWidth,
            // 向上取整并留出两像素，避免分数像素造成 iframe 内出现细小滚动条。
            height:
              Math.ceil(
                (Math.min(width ?? naturalWidth, naturalWidth) * page.height) / page.width,
              ) + 2,
          }}
        />
      ) : (
        <p className="g0-diagram-loading" role="status">
          {failed ? '图谱暂时无法加载，可打开完整图谱阅读。' : '正在加载图谱…'}
        </p>
      )}
    </div>
  );
}
