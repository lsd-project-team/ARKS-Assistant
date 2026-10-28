import { useCallback, useEffect, useRef, useState } from 'react';
import type { PDFDocumentLoadingTask, PDFDocumentProxy, RenderTask } from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import { Button } from '../../../shared/ui/ui';
import { sessionFetch } from '../../auth/session';

function PdfPage({
  document,
  number,
  onError,
}: {
  document: PDFDocumentProxy;
  number: number;
  onError: () => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [rendered, setRendered] = useState(false);
  useEffect(() => {
    const element = container.current;
    if (!element) return;
    let disposed = false;
    let width = -1;
    let task: RenderTask | undefined;
    let generation = 0;
    setRendered(false);
    async function draw(nextWidth: number) {
      if (!nextWidth || width === nextWidth) return;
      width = nextWidth;
      const current = ++generation;
      const previous = task;
      previous?.cancel();
      try {
        if (previous) await previous.promise.catch(() => undefined);
        const page = await document.getPage(number);
        const target = canvas.current;
        if (!target || disposed || current !== generation) return;
        const original = page.getViewport({ scale: 1 });
        const viewport = page.getViewport({ scale: nextWidth / original.width });
        const ratio = Math.min(
          window.devicePixelRatio || 1,
          2,
          Math.sqrt(16000000 / (viewport.width * viewport.height)),
        );
        target.width = Math.max(1, Math.floor(viewport.width * ratio));
        target.height = Math.max(1, Math.floor(viewport.height * ratio));
        target.style.width = viewport.width + 'px';
        target.style.height = viewport.height + 'px';
        // 只绘制原 PDF 页面，不调用正文提取或修改原文件。
        task = page.render({ canvas: target, viewport, transform: [ratio, 0, 0, ratio, 0, 0] });
        await task.promise;
        if (!disposed && current === generation) setRendered(true);
      } catch (error) {
        if (
          !disposed &&
          current === generation &&
          (error as Error).name !== 'RenderingCancelledException'
        )
          onError();
      }
    }
    const observer = new ResizeObserver((entries) => {
      void draw(entries[0].contentRect.width);
    });
    observer.observe(element);
    void draw(element.clientWidth);
    return () => {
      disposed = true;
      generation++;
      observer.disconnect();
      task?.cancel();
    };
  }, [document, number, onError]);
  return (
    <div ref={container} className="material-pdf-page">
      {!rendered && <p role="status">正在显示页面…</p>}
      <canvas ref={canvas} role="img" aria-label={`PDF 第 ${number} 页`} />
    </div>
  );
}

export function PdfOriginal({ source }: { source: string }) {
  const [document, setDocument] = useState<PDFDocumentProxy>();
  const [number, setNumber] = useState(1);
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  const renderFailed = useCallback(() => setFailed(true), []);
  useEffect(() => {
    const controller = new AbortController();
    let disposed = false;
    let task: PDFDocumentLoadingTask | undefined;
    setDocument(undefined);
    setNumber(1);
    setFailed(false);
    async function open() {
      const [pdfjs, response] = await Promise.all([
        import('pdfjs-dist'),
        sessionFetch(source, { signal: controller.signal }),
      ]);
      if (!response.ok) throw new Error('原文件读取失败');
      const data = new Uint8Array(await response.arrayBuffer());
      if (disposed) return;
      pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;
      task = pdfjs.getDocument({
        data,
        cMapUrl: '/assets/pdfjs/cmaps/',
        standardFontDataUrl: '/assets/pdfjs/standard_fonts/',
        wasmUrl: '/assets/pdfjs/wasm/',
        iccUrl: '/assets/pdfjs/iccs/',
      });
      const loaded = await task.promise;
      if (!disposed) setDocument(loaded);
    }
    void open().catch(() => {
      if (!disposed) setFailed(true);
    });
    return () => {
      disposed = true;
      controller.abort();
      void task?.destroy();
    };
  }, [source, retry]);
  if (failed)
    return (
      <div className="material-original-fallback">
        <p>PDF 暂时无法预览，可重试或下载原文件查看。</p>
        <Button onClick={() => setRetry(retry + 1)}>重试预览</Button>
      </div>
    );
  if (!document) return <p role="status">正在打开原文件…</p>;
  return (
    <div className="material-pdf">
      <div className="material-pdf-toolbar" aria-label="PDF 翻页">
        <Button disabled={number === 1} onClick={() => setNumber(number - 1)}>
          上一页
        </Button>
        <span>
          {number} / {document.numPages}
        </span>
        <Button disabled={number === document.numPages} onClick={() => setNumber(number + 1)}>
          下一页
        </Button>
      </div>
      <div className="material-pdf-scroll">
        <PdfPage document={document} number={number} onError={renderFailed} />
      </div>
    </div>
  );
}
