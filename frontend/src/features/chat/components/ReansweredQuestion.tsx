import type { Message } from '../../../shared/types/api';

export function ReansweredQuestion({ message }: { message: Message }) {
  return (
    <div className="reanswered-question" aria-label="重新回答的问题">
      <span>重新回答：</span>
      {message.content}
    </div>
  );
}
