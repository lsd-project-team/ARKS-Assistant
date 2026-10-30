import type { ComponentProps } from 'react';
import { RichContentRenderer } from '../rich/RichContentRenderer';

export function AnswerMarkdown(props: ComponentProps<typeof RichContentRenderer>) {
  return <RichContentRenderer {...props} />;
}
