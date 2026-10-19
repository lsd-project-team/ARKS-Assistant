import type { ComponentProps } from 'react';
import { Markdown } from '../../../app/components/Markdown';
import { remarkRecordAnswer } from '../lib/recordAnswerPresentation';

const answerPlugins = [remarkRecordAnswer];

export function AnswerMarkdown(props: ComponentProps<typeof Markdown>) {
  return <Markdown {...props} remarkPlugins={answerPlugins} />;
}
