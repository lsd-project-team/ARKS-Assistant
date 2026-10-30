import type { ChartBlock, MindmapBlock } from './types.ts';
import { validateChart, validateMindmap } from './visualValidation.ts';

export function chartOptions(block: ChartBlock) {
  validateChart(block);
  const common = {
    animation: false,
    aria: { enabled: true },
    tooltip: { trigger: block.chart_type === 'pie' ? 'item' : 'axis', renderMode: 'richText' },
    legend: { type: 'scroll', bottom: 0 },
  };
  if (block.chart_type === 'pie')
    return {
      ...common,
      series: [
        {
          type: 'pie',
          radius: ['25%', '65%'],
          name: block.series[0].name,
          data: block.labels.flatMap((name, i) =>
            block.series[0].values[i] === null ? [] : [{ name, value: block.series[0].values[i] }],
          ),
        },
      ],
    };
  return {
    ...common,
    grid: { left: 55, right: 24, top: 24, bottom: 70 },
    xAxis: { type: 'category', data: block.labels },
    yAxis: { type: 'value' },
    series: block.series.map((series) => ({
      id: series.id,
      name: series.name,
      type: block.chart_type,
      data: series.values,
    })),
  };
}

interface TreeNode {
  name: string;
  children?: TreeNode[];
}
export function mindmapOptions(block: MindmapBlock) {
  validateMindmap(block);
  const branch = (id: string): TreeNode => ({
    name: block.nodes.find((node) => node.id === id)!.label,
    children: block.nodes.filter((node) => node.parent_id === id).map((node) => branch(node.id)),
  });
  return {
    animation: false,
    aria: { enabled: true },
    tooltip: { renderMode: 'richText' },
    series: [
      {
        type: 'tree',
        data: [branch(block.nodes.find((node) => !node.parent_id)!.id)],
        top: 30,
        bottom: 30,
        left: 80,
        right: 140,
        roam: true,
        initialTreeDepth: -1,
        label: { position: 'left', width: 120, overflow: 'break' },
        leaves: { label: { position: 'right' } },
        expandAndCollapse: true,
      },
    ],
  };
}
