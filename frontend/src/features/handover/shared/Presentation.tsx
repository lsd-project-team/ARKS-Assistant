import type { ReactNode } from 'react';

export function PageHeading({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children?: ReactNode;
}) {
  return (
    <header
      className={`handover-page-heading${description ? '' : ' handover-page-heading-compact'}`}
    >
      <div>
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {children && <div className="handover-actions">{children}</div>}
    </header>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="handover-empty-state">
      <strong>{title}</strong>
      {children && <p>{children}</p>}
    </div>
  );
}
