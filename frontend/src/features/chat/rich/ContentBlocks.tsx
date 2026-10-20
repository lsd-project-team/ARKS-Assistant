import { type ReactNode } from 'react';
import { Code2, Layers, Settings2, Workflow } from 'lucide-react';
import type { OverviewBlock, StepFlowBlock, TableBlock, SourcePointer } from './types';

export type RenderText = (content: string) => ReactNode;
export type RenderSource = (source: SourcePointer, key: string) => ReactNode;
const icons = { code: Code2, layers: Layers, settings: Settings2, workflow: Workflow };

export function OverviewGrid({
  block,
  renderText,
  renderSource,
}: {
  block: OverviewBlock;
  renderText: RenderText;
  renderSource: RenderSource;
}) {
  if (!block.items.length) return null;
  return (
    <section className="rich-overview" aria-label={block.title || '功能概览'}>
      {block.title && <h3>{block.title}</h3>}
      <ul className="rich-overview-grid">
        {block.items.map((item) => {
          const Icon = item.icon ? icons[item.icon] : undefined;
          return (
            <li key={item.id} className="rich-overview-item">
              {Icon && (
                <span className="rich-overview-icon">
                  <Icon size={21} aria-hidden="true" />
                </span>
              )}
              <div>
                <h4>{item.title}</h4>
                {renderText(item.description)}
                {item.status && <small className="rich-status">{item.status}</small>}
                {item.source && renderSource(item.source, item.id)}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export function StepFlow({
  block,
  renderText,
  renderSource,
}: {
  block: StepFlowBlock;
  renderText: RenderText;
  renderSource: RenderSource;
}) {
  if (!block.steps.length) return null;
  return (
    <section className="rich-step-flow" aria-label={block.title || '执行步骤'}>
      {block.title && <h3>{block.title}</h3>}
      {block.description && <p className="rich-description">{block.description}</p>}
      <ol className="rich-steps">
        {block.steps.map((step, index) => (
          <li key={step.id}>
            <span className="rich-step-number" aria-hidden="true">
              {index + 1}
            </span>
            <div className="rich-step-body">
              <h4>{step.title}</h4>
              {renderText(step.description)}
              {!!step.sources?.length && (
                <div className="rich-sources">
                  {step.sources.map((source, i) => renderSource(source, `${step.id}:${i}`))}
                </div>
              )}
              {step.details && (
                <CollapsibleSection title="详细说明">{renderText(step.details)}</CollapsibleSection>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

export function DataTable({ block }: { block: TableBlock }) {
  if (!block.columns.length) return null;
  return (
    <div
      className="rich-table-scroll"
      role="region"
      aria-label={block.title || '数据表格'}
      tabIndex={0}
    >
      <table className="rich-table">
        {block.title && <caption>{block.title}</caption>}
        <thead>
          <tr>
            {block.columns.map((column) => (
              <th scope="col" key={column.id} style={{ textAlign: column.align }}>
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {block.rows.map((row) => (
            <tr key={row.id}>
              {block.columns.map((column, i) => (
                <td key={column.id} style={{ textAlign: column.align }}>
                  {row.cells[i] ?? '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {!block.rows.length && <p className="rich-description">暂无数据</p>}
    </div>
  );
}

export function CollapsibleSection({
  title,
  defaultOpen = false,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  return (
    <details className="rich-collapsible" open={defaultOpen || undefined}>
      <summary>{title}</summary>
      <div className="rich-collapsible-body">{children}</div>
    </details>
  );
}
