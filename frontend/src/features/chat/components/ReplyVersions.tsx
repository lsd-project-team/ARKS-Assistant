import { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { Message, Run } from '../../../shared/types/api';
import { MessageBubble } from './MessageBubble';

export function ReplyVersions({
  versions,
  selectedMessage,
  canRegenerate,
  onRegenerate,
}: {
  versions: { message: Message; run: Run }[];
  selectedMessage: string;
  canRegenerate: boolean;
  onRegenerate: (id: string) => void;
}) {
  const [chosen, setChosen] = useState('');
  const wanted = chosen || selectedMessage;
  const found = versions.findIndex((version) => version.message.id === wanted);
  const index = found < 0 ? versions.length - 1 : found;
  const current = versions[index];
  return (
    <div className="reply-versions">
      <div className="reply-version-switch">
        <button
          aria-label="上一版回复"
          disabled={index === 0}
          onClick={() => setChosen(versions[index - 1].message.id)}
        >
          <ChevronLeft size={13} />
        </button>
        <span>
          {index + 1} / {versions.length}
        </span>
        <button
          aria-label="下一版回复"
          disabled={index === versions.length - 1}
          onClick={() => setChosen(versions[index + 1].message.id)}
        >
          <ChevronRight size={13} />
        </button>
        <span>回复版本 · {current.run.status === 'completed' ? '已完成' : current.run.status}</span>
      </div>
      <MessageBubble
        message={current.message}
        run={current.run}
        canRegenerate={canRegenerate && index === versions.length - 1}
        onRegenerate={onRegenerate}
      />
    </div>
  );
}
