import { useMemo } from 'react';
import type { ChartBlock as ChartData } from './types';
import { chartOptions } from './chartOptions';
import { ChartSurface } from './ChartSurface';
import { DataTable } from './ContentBlocks';

export function ChartBlock({ block }: { block: ChartData }) {
  const option = useMemo(() => chartOptions(block), [block]);
  return (
    <figure className="rich-chart">
      {block.title && <figcaption>{block.title}</figcaption>}
      <ChartSurface option={option} label={block.title || '数据图表'} />
      <details>
        <summary>查看图表原始数据</summary>
        <DataTable
          block={{
            id: `${block.id}-data`,
            type: 'table',
            columns: [
              { id: 'label', label: '项目' },
              ...block.series.map((series) => ({ id: `series-${series.id}`, label: series.name })),
            ],
            rows: block.labels.map((label, i) => ({
              id: `row-${i}`,
              cells: [label, ...block.series.map((series) => series.values[i])],
            })),
          }}
        />
      </details>
    </figure>
  );
}
