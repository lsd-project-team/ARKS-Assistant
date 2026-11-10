import { useEffect, useRef, useState } from 'react';
import { init, use, type EChartsCoreOption } from 'echarts/core';
import { BarChart, LineChart, PieChart, TreeChart } from 'echarts/charts';
import {
  AriaComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components';
import { SVGRenderer } from 'echarts/renderers';
import { useAppearance } from '../../settings/lib/appearance';

use([
  BarChart,
  LineChart,
  PieChart,
  TreeChart,
  AriaComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  SVGRenderer,
]);

export function ChartSurface({ option, label }: { option: EChartsCoreOption; label: string }) {
  const element = useRef<HTMLDivElement>(null);
  const mode = useAppearance((state) => state.mode);
  const [error, setError] = useState(false);
  useEffect(() => {
    if (!element.current) return;
    setError(false);
    let chart: ReturnType<typeof init> | undefined;
    let observer: ResizeObserver | undefined;
    const resize = () => chart?.resize();
    try {
      chart = init(element.current, mode === 'dark' ? 'dark' : undefined, { renderer: 'svg' });
      chart.setOption({ ...option, backgroundColor: 'transparent' });
      if (typeof ResizeObserver !== 'undefined') {
        observer = new ResizeObserver(resize);
        observer.observe(element.current);
      }
      window.addEventListener('resize', resize);
    } catch {
      setError(true);
    }
    return () => {
      observer?.disconnect();
      window.removeEventListener('resize', resize);
      chart?.dispose();
    };
  }, [option, mode]);
  return (
    <>
      <div ref={element} className="rich-chart-canvas" role="img" aria-label={label} />
      {error && <p role="status">图形暂时无法绘制，请查看下方原始数据。</p>}
    </>
  );
}
