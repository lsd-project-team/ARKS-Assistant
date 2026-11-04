import { useId, useRef, useState, type FormEvent } from 'react';
import { api, jsonBody } from '../../../app/api/client';
import { Button, ErrorText, Modal } from '../../../shared/ui/ui';
import { Select } from '../../../shared/ui/Select';
import { toast } from '../../../shared/utils/toasts';
import { feedbackCategories, type FeedbackCategory } from '../lib/answerFeedback';
import '../styles/answer-feedback.css';

export interface FeedbackTarget {
  messageId: string;
  threadId: string;
  projectId: string;
}

export function FeedbackDialog({
  target,
  onClose,
}: {
  target: FeedbackTarget;
  onClose: () => void;
}) {
  const formId = useId();
  const [content, setContent] = useState('');
  const [category, setCategory] = useState<FeedbackCategory>('');
  const [submissionId, setSubmissionId] = useState(() => crypto.randomUUID());
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const submitting = useRef(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (submitting.current) return;
    if (!content.trim() || content.length > 2000) {
      setError('请填写 1～2000 字的反馈说明');
      return;
    }
    submitting.current = true;
    setPending(true);
    setError(undefined);
    try {
      // 固定打开弹窗时的项目和回答，切换项目或重新生成不能改变反馈对象。
      await api(
        `/threads/${target.threadId}/messages/${target.messageId}/feedback`,
        { method: 'POST', body: jsonBody({ submission_id: submissionId, category, content }) },
        target.projectId,
      );
      toast('反馈已提交');
      onClose();
    } catch (failure) {
      setError(failure);
    } finally {
      submitting.current = false;
      setPending(false);
    }
  }

  return (
    <Modal
      open
      title="反馈回复"
      className="answer-feedback-dialog"
      onClose={() => !submitting.current && onClose()}
    >
      <form id={formId} onSubmit={(event) => void submit(event)}>
        <div className="dialog-body answer-feedback-fields">
          <label>问题类型（选填）</label>
          <Select
            aria-label="问题类型（选填）"
            value={category}
            disabled={pending}
            onValueChange={(value) => {
              setCategory(value as FeedbackCategory);
              setSubmissionId(crypto.randomUUID());
            }}
          >
            <option value="">请选择</option>
            {Object.entries(feedbackCategories).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
          <label htmlFor={`${formId}-content`}>反馈说明</label>
          <textarea
            id={`${formId}-content`}
            required
            maxLength={2000}
            rows={6}
            value={content}
            disabled={pending}
            placeholder="请描述具体问题，也可以补充你期望的回答"
            onChange={(event) => {
              setContent(event.target.value);
              setSubmissionId(crypto.randomUUID());
            }}
          />
          <small className="muted answer-feedback-count">{content.length} / 2000</small>
          <ErrorText error={error} />
        </div>
        <div className="modal-footer">
          <Button type="button" disabled={pending} onClick={onClose}>
            取消
          </Button>
          <Button type="submit" className="primary" disabled={pending || !content.trim()}>
            {pending ? '正在提交…' : '提交'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
