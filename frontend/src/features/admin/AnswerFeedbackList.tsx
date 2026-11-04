import { feedbackCategories } from '../chat/lib/answerFeedback';
import { dateTime } from './client';
import type { RecordedFeedback } from './types';

export function AnswerFeedbackList({ items }: { items: RecordedFeedback[] }) {
  if (!items.length) return null;
  return (
    <section className="admin-answer-feedback" aria-label="用户反馈">
      <strong>用户反馈（{items.length}）</strong>
      {items.map((item) => (
        <div className="admin-feedback-item" key={item.id}>
          <div className="admin-message-heading">
            <strong>{item.actor.display_name || item.actor.username || '用户'}</strong>
            <span>{dateTime(item.created_at)}</span>
          </div>
          {item.category && (
            <small className="admin-badge">
              {feedbackCategories[item.category as keyof typeof feedbackCategories] ||
                item.category}
            </small>
          )}
          <p>{item.content}</p>
        </div>
      ))}
    </section>
  );
}
