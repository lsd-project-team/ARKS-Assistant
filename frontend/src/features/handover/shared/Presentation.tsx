import type { ReactNode } from 'react';
import type { Tab } from './types';

export const pageDescriptions: Partial<Record<Tab, string>> = {
  overview: '查看交接现状，安排下一步工作。',
  materials: '上传并查看原始文件。',
  tasks: '记录工作项、负责人和进度，随时更新状态与备注。',
  issues: '记录问题处理、工作进展与经验，便于后续查阅和复用。',
  packages: '汇总交接内容，支持查阅与下载。',
  updates: '追踪内容变更与人工确认，及时复核受影响的记录。',
};

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
