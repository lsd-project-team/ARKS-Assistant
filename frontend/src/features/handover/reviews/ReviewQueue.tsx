import { useState } from 'react';
import { Button } from '../../../shared/ui/ui';
import { EmptyState } from '../shared/Presentation';
import { RecordCard } from '../shared/RecordCard';
import type { Definitions, Event, HandoverRecord } from '../shared/types';
import './review-queue.css';
import {
  reviewCategories,
  reviewCounts,
  reviewReason,
  selectReviewRows,
  type ReviewCategory,
} from './reviewRecords';

export function ReviewQueue({
  rows,
  events,
  definitions,
  onOpen,
}: {
  rows: HandoverRecord[];
  events: Event[];
  definitions: Definitions;
  onOpen: (id: string) => void;
}) {
  const [category, setCategory] = useState<ReviewCategory>('all');
  const counts = reviewCounts(rows);
  const visible = selectReviewRows(rows, category);
  const label = reviewCategories.find((item) => item.id === category)!.label;
  return (
    <section className="handover-panel handover-review-queue">
      <h2>待审核记录</h2>
      <div className="handover-review-filters" role="group" aria-label="待审核记录分类">
        {reviewCategories.map((item) => (
          <Button
            key={item.id}
            type="button"
            aria-pressed={category === item.id}
            aria-label={`${item.label}，${counts[item.id]} 条待审核`}
            onClick={() => setCategory(item.id)}
          >
            {item.label}
            <span>{counts[item.id]}</span>
          </Button>
        ))}
      </div>
      <p className="handover-review-count" role="status">
        {label} · {visible.length} 条待审核
      </p>
      <div className="handover-cards">
        {visible.map((row) => (
          <RecordCard
            key={row.id}
            row={row}
            definitions={definitions}
            onOpen={onOpen}
            reviewReason={reviewReason(row, events, rows)}
          />
        ))}
      </div>
      {!visible.length && (
        <EmptyState title={counts.all ? `暂无待审核的${label}` : '暂无待审核记录'}>
          {counts.all
            ? '可以切换其他分类查看。'
            : '新增待确认记录或已确认内容发生变化后，会在这里显示。'}
        </EmptyState>
      )}
    </section>
  );
}
