import { useMemo } from 'react';
import type { MindmapBlock as MindmapData } from './types';
import { mindmapOptions } from './chartOptions';
import { ChartSurface } from './ChartSurface';

export function MindmapBlock({ block }: { block: MindmapData }) {
  const option = useMemo(() => mindmapOptions(block), [block]);
  return (
    <figure className="rich-chart rich-mindmap">
      <figcaption>
        {block.title || '思维导图'}
        <small>可拖动、缩放，点击节点折叠</small>
      </figcaption>
      <ChartSurface option={option} label={block.title || '思维导图'} />
      <details>
        <summary>查看节点与层级</summary>
        <ul>
          {block.nodes.map((node) => (
            <li key={node.id}>
              {node.parent_id
                ? `${block.nodes.find((parent) => parent.id === node.parent_id)?.label} → `
                : ''}
              {node.label}
            </li>
          ))}
        </ul>
      </details>
    </figure>
  );
}
