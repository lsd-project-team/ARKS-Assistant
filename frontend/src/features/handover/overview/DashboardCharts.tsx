import { useState, type CSSProperties, type KeyboardEvent } from 'react';
import type { ChartDatum, ChartTone } from './overviewData';

export const chartColor = (tone: ChartTone) => 'var(--dashboard-' + tone + ')';
const circleLength = 2 * Math.PI * 64;

function ChartTooltip({ item, total, unit }: { item?: ChartDatum; total?: number; unit: string }) {
  if (!item) return null;
  return (
    <div className="dashboard-chart-tooltip" role="tooltip">
      <span>
        <i style={{ background: chartColor(item.tone) }} />
        {item.label}
      </span>
      <strong>
        {item.value} {unit}
        <small>{total ? ' · 占 ' + Math.round((item.value / total) * 100) + '%' : ''}</small>
      </strong>
      <small>点击查看对应记录</small>
    </div>
  );
}

export function InteractiveRing({
  data,
  selected,
  onSelect,
  label,
  unit,
  totalLabel,
  summary,
}: {
  data: ChartDatum[];
  selected: string;
  onSelect: (id: string) => void;
  label: string;
  unit: string;
  totalLabel: string;
  summary?: { value: string; label: string };
}) {
  const [hovered, setHovered] = useState<string>();
  const total = data.reduce((sum, item) => sum + item.value, 0);
  const highlighted = hovered || (selected !== 'all' ? selected : undefined);
  const active = data.find((item) => item.id === highlighted);
  let offset = 0;
  const choose = (id: string) => onSelect(selected === id ? 'all' : id);
  function activate(event: KeyboardEvent<SVGCircleElement>, id: string) {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    choose(id);
  }
  return (
    <figure className="dashboard-interactive-chart dashboard-ring-chart" aria-label={label}>
      <div className="dashboard-ring">
        <svg viewBox="0 0 164 164" aria-label={label}>
          <circle className="dashboard-ring-track" cx="82" cy="82" r="64" />
          {data.map((item) => {
            const length = total ? (item.value / total) * circleLength : 0;
            const start = offset;
            offset += length;
            if (!item.value) return null;
            return (
              <circle
                key={item.id}
                className="dashboard-ring-segment"
                cx="82"
                cy="82"
                r="64"
                fill="none"
                stroke={chartColor(item.tone)}
                strokeWidth={highlighted === item.id ? 15 : 11}
                strokeDasharray={
                  Math.max(0, length - (data.filter((row) => row.value).length > 1 ? 5 : 0)) +
                  ' ' +
                  circleLength
                }
                strokeDashoffset={-start}
                transform="rotate(-90 82 82)"
                opacity={highlighted && highlighted !== item.id ? 0.28 : 1}
                role="button"
                tabIndex={0}
                aria-pressed={selected === item.id}
                aria-label={item.label + ' ' + item.value + ' ' + unit + '，点击筛选'}
                onPointerEnter={() => setHovered(item.id)}
                onPointerLeave={() => setHovered(undefined)}
                onFocus={() => setHovered(item.id)}
                onBlur={() => setHovered(undefined)}
                onClick={() => choose(item.id)}
                onKeyDown={(event) => activate(event, item.id)}
              />
            );
          })}
        </svg>
        <button
          className="dashboard-ring-center"
          aria-label={'查看全部' + totalLabel}
          onClick={() => onSelect('all')}
        >
          <strong style={active ? { color: chartColor(active.tone) } : undefined}>
            {active ? active.value : summary?.value || total}
          </strong>
          <span>{active ? active.label : summary?.label || totalLabel}</span>
          {active && total > 0 && <small>{Math.round((active.value / total) * 100)}%</small>}
        </button>
      </div>
      <figcaption className="dashboard-chart-legend">
        {data.map((item) => (
          <button
            key={item.id}
            aria-pressed={selected === item.id}
            data-highlighted={highlighted === item.id}
            onClick={() => choose(item.id)}
            onPointerEnter={() => setHovered(item.id)}
            onPointerLeave={() => setHovered(undefined)}
            onFocus={() => setHovered(item.id)}
            onBlur={() => setHovered(undefined)}
          >
            <i style={{ background: chartColor(item.tone) }} />
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </button>
        ))}
      </figcaption>
      <ChartTooltip item={data.find((item) => item.id === hovered)} total={total} unit={unit} />
    </figure>
  );
}

export function PackageBars({
  data,
  onOpen,
}: {
  data: ChartDatum[];
  onOpen: (id: string) => void;
}) {
  const [hovered, setHovered] = useState<string>();
  const maximum = Math.max(1, ...data.map((item) => item.value));
  return (
    <figure
      className="dashboard-interactive-chart dashboard-package-chart"
      aria-label="交接包固定版本收录记录数"
    >
      <figcaption>收录记录数</figcaption>
      {data.map((item) => (
        <button
          key={item.id}
          className="dashboard-package-bar"
          onClick={() => onOpen(item.id)}
          aria-label={'打开交接包：' + item.label + '，收录 ' + item.value + ' 条记录'}
          onPointerEnter={() => setHovered(item.id)}
          onPointerLeave={() => setHovered(undefined)}
          onFocus={() => setHovered(item.id)}
          onBlur={() => setHovered(undefined)}
        >
          <span>
            <strong>{item.label}</strong>
            <b>
              {item.value}
              <small> 条</small>
            </b>
          </span>
          <span className="dashboard-bar-track">
            <span
              style={{
                width: (item.value / maximum) * 100 + '%',
                background: chartColor(item.tone),
              }}
            />
          </span>
        </button>
      ))}
      <ChartTooltip item={data.find((item) => item.id === hovered)} unit="条记录" />
    </figure>
  );
}

export function OperationBars({
  data,
  selected,
  onSelect,
}: {
  data: ChartDatum[];
  selected: string;
  onSelect: (id: string) => void;
}) {
  const [hovered, setHovered] = useState<string>();
  const maximum = Math.max(1, ...data.map((item) => item.value));
  const step = Math.max(
    1,
    10 ** Math.floor(Math.log10(maximum)) *
      Math.ceil(maximum / 10 ** Math.floor(Math.log10(maximum)) / 4),
  );
  const ceiling = step * 4;
  const total = data.reduce((sum, item) => sum + item.value, 0);
  const highlighted = hovered || (selected !== 'all' ? selected : undefined);
  return (
    <figure
      className="dashboard-interactive-chart dashboard-operations-chart"
      aria-label="近期交接操作分布"
    >
      <div className="dashboard-column-chart">
        <div className="dashboard-chart-axis" aria-hidden="true">
          {[4, 3, 2, 1, 0].map((tick) => (
            <span key={tick}>{tick * step}</span>
          ))}
        </div>
        <div
          className="dashboard-chart-columns"
          style={{ '--dashboard-columns': data.length } as CSSProperties}
        >
          {data.map((item) => (
            <button
              key={item.id}
              className="dashboard-chart-column"
              aria-label={item.label + ' ' + item.value + ' 次，点击筛选日志'}
              aria-pressed={selected === item.id}
              data-muted={!!highlighted && highlighted !== item.id}
              onClick={() => onSelect(selected === item.id ? 'all' : item.id)}
              onPointerEnter={() => setHovered(item.id)}
              onPointerLeave={() => setHovered(undefined)}
              onFocus={() => setHovered(item.id)}
              onBlur={() => setHovered(undefined)}
            >
              <span className="dashboard-column-track">
                <span
                  className="dashboard-column"
                  style={{
                    height: (item.value / ceiling) * 100 + '%',
                    background: chartColor(item.tone),
                  }}
                >
                  <b>{item.value}</b>
                </span>
              </span>
              <span className="dashboard-column-label">{item.label}</span>
            </button>
          ))}
        </div>
      </div>
      <ChartTooltip item={data.find((item) => item.id === hovered)} total={total} unit="次操作" />
    </figure>
  );
}
