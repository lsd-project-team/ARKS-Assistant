export const feedbackCategories = {
  incorrect: '内容错误',
  off_topic: '答非所问',
  incomplete: '内容不完整',
  source: '来源有误',
  display: '显示异常',
  other: '其他',
} as const;

export type FeedbackCategory = '' | keyof typeof feedbackCategories;
