import type { ReactNode } from 'react';
import type { Message } from '../types';

export function MessageArchive({
  message,
  reveal,
  children,
}: {
  message: Message;
  reveal: boolean;
  children: ReactNode;
}) {
  if (message.context_active !== false) return children;
  return (
    <details className="superseded-message" open={reveal || undefined}>
      <summary>
        编辑前{message.role === 'user' ? '问题' : '回复'} · {message.content.slice(0, 50)}
      </summary>
      {children}
    </details>
  );
}
