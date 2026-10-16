import type { ReactNode } from 'react';
import { RecordCard } from './RecordCard';
import type { Definitions, HandoverRecord, Kind, Tab } from './types';

export const pageDescriptions: Record<Tab, string> = {
  overview: '查看交接现状，安排下一步工作。',
  materials: '集中保存文档、文字记录和项目资料，审核 AI 提取结果。',
  tasks: '记录工作项、负责人和进度，随时更新状态与备注。',
  issues: '保存调试现象、排查过程与处理办法，供后续遇到相似问题时查阅。',
  packages: '汇总固定版本的交接内容，供查阅与下载。',
  updates: '追踪内容变更与人工确认，及时复核受影响的记录。',
};

export const kindDescriptions: Partial<Record<Kind, string>> = {
  source: '保存文档、源码或项目资料的原始版本。',
  interview: '记录原作者的说明、问答及后续更正。',
  candidate: '逐条核对 AI 提取的内容与来源，再合并为交接记录。',
  decision: '交代设计意图、备选方案与取舍依据。',
  constraint: '明确设备、工艺与安全边界，以及停止条件。',
  baseline: '固定代码版本、固件、SDK、配方、标定与构建环境。',
  framework: '梳理入口、模块职责、分层与关键流程。',
  training: '说明运行条件、操作时序、异常恢复与培训结果。',
  issue: '集中跟进疑问、阻塞与尚未确认的条件。',
  package: '保留生成时的记录版本，供接收人查阅与下载。',
};

export function PageHeading({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <header className="handover-page-heading">
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
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

export function RecordGroup({
  kind,
  rows,
  definitions,
  onOpen,
  includedKinds,
}: {
  kind: Kind;
  rows: HandoverRecord[];
  definitions: Definitions;
  onOpen: (id: string) => void;
  includedKinds?: Kind[];
}) {
  // 历史访谈沿用原类型与版本，在资料组展示，不改写旧记录和引用。
  const records = rows.filter((row) =>
    includedKinds ? includedKinds.includes(row.kind) : row.kind === kind,
  );
  return (
    <section className="handover-group">
      <header className="handover-group-heading">
        <div>
          <h3>
            {definitions.kinds[kind]}
            <span className="handover-count">{records.length}</span>
          </h3>
          <p>{kindDescriptions[kind]}</p>
        </div>
      </header>
      {records.length ? (
        <div className="handover-cards">
          {records.map((row) => (
            <RecordCard key={row.id} row={row} definitions={definitions} onOpen={onOpen} />
          ))}
        </div>
      ) : (
        <p className="handover-group-empty">
          暂无记录{kind === 'candidate' ? '，运行 AI 分析后可在这里审核候选。' : '。'}
        </p>
      )}
    </section>
  );
}
