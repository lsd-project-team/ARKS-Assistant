import { useId, useRef, useState } from 'react';
import { Maximize2, Minus, Plus, Scan } from 'lucide-react';
import type { DiagramBlock } from './types';
import { Modal } from '../../../shared/ui/ui';

// 只绘制校验后的节点和显式边；不解析或注入模型返回的 HTML/SVG。
export function FlowDiagram({ block }: { block: DiagramBlock }) {
  const [zoom, setZoom] = useState(1);
  const [full, setFull] = useState(false);
  const viewport = useRef<HTMLDivElement>(null);
  const marker = useId().replaceAll(':', '');
  const horizontal = block.layout === 'horizontal';
  const width = horizontal ? Math.max(320, block.nodes.length * 240) : 480;
  const height = horizontal ? 260 : Math.max(160, block.nodes.length * 104);
  const points = new Map(
    block.nodes.map((node, i) => [
      node.id,
      {
        x: horizontal ? i * 240 + 24 : 110,
        y: horizontal ? 100 : i * 104 + 24,
      },
    ]),
  );
  const diagram = (
    <>
      <div className="rich-diagram-toolbar">
        <span>{block.title}</span>
        <div>
          <button
            aria-label="缩小图形"
            disabled={zoom <= 0.4}
            onClick={() => setZoom((value) => Math.max(0.4, value - 0.2))}
          >
            <Minus size={15} />
          </button>
          <output aria-label="图形缩放比例">{Math.round(zoom * 100)}%</output>
          <button
            aria-label="放大图形"
            disabled={zoom >= 2}
            onClick={() => setZoom((value) => Math.min(2, value + 0.2))}
          >
            <Plus size={15} />
          </button>
          <button
            aria-label="适配图形宽度"
            onClick={() => setZoom(Math.min(1, (viewport.current?.clientWidth || width) / width))}
          >
            <Scan size={15} />
          </button>
          {!full && (
            <button aria-label="全屏查看图形" onClick={() => setFull(true)}>
              <Maximize2 size={15} />
            </button>
          )}
        </div>
      </div>
      <div
        className="rich-diagram-viewport"
        ref={viewport}
        tabIndex={0}
        role="region"
        aria-label={`${block.title}，可滚动`}
      >
        <svg
          width={width * zoom}
          height={height * zoom}
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label={block.title}
        >
          <defs>
            <marker id={marker} markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
              <path d="M0,0 L8,4 L0,8 z" fill="var(--text-muted)" />
            </marker>
          </defs>
          {block.edges.map((edge, i) => {
            const from = points.get(edge.from),
              to = points.get(edge.to);
            if (!from || !to) return null;
            const x1 = horizontal ? from.x + 192 : from.x + 96,
              y1 = horizontal ? from.y + 26 : from.y + 52;
            const x2 = horizontal ? to.x : to.x + 96,
              y2 = horizontal ? to.y + 26 : to.y;
            const bend = horizontal ? (x1 + x2) / 2 : 410 + (i % 3) * 14;
            const path = horizontal
              ? `M${x1},${y1} C${bend},${y1 - 52} ${bend},${y2 - 52} ${x2},${y2}`
              : `M${x1},${y1} C${bend},${y1} ${bend},${y2} ${x2},${y2}`;
            return (
              <g key={`${edge.from}:${edge.to}:${i}`}>
                <path
                  d={path}
                  fill="none"
                  stroke="var(--text-muted)"
                  strokeWidth="1.4"
                  markerEnd={`url(#${marker})`}
                />
                {edge.label && (
                  <text
                    x={horizontal ? bend : 345}
                    y={(y1 + y2) / 2 - 7}
                    className="rich-edge-label"
                  >
                    {edge.label.slice(0, 32)}
                  </text>
                )}
              </g>
            );
          })}
          {block.nodes.map((node) => {
            const point = points.get(node.id)!;
            return (
              <g key={node.id}>
                <title>{`${node.label}${node.description ? `：${node.description}` : ''}`}</title>
                <rect
                  x={point.x}
                  y={point.y}
                  width="192"
                  height="52"
                  rx="9"
                  fill="var(--surface-subtle)"
                  stroke="var(--border-strong)"
                />
                <text
                  x={point.x + 96}
                  y={point.y + 31}
                  textAnchor="middle"
                  className="rich-node-label"
                >
                  {node.label.length > 18 ? `${node.label.slice(0, 17)}…` : node.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <details className="rich-diagram-description">
        <summary>节点与连接说明</summary>
        <ul>
          {block.nodes.map((node) => (
            <li key={node.id}>
              <strong>{node.label}</strong>
              {node.description && `：${node.description}`}
            </li>
          ))}
        </ul>
        <ul>
          {block.edges.map((edge, i) => (
            <li key={i}>
              {block.nodes.find((n) => n.id === edge.from)?.label} →{' '}
              {block.nodes.find((n) => n.id === edge.to)?.label}
              {edge.label && `：${edge.label}`}
            </li>
          ))}
        </ul>
      </details>
    </>
  );
  return (
    <figure className="rich-diagram">
      {block.description && <figcaption>{block.description}</figcaption>}
      {full ? (
        <Modal
          open
          onClose={() => setFull(false)}
          title={block.title}
          className="rich-diagram-dialog"
        >
          <div className="dialog-body">{diagram}</div>
        </Modal>
      ) : (
        diagram
      )}
    </figure>
  );
}
