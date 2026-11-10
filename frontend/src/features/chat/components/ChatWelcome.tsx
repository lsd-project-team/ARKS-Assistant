import { CodeXml, Workflow, Wrench } from 'lucide-react';

export function ChatWelcome({
  hasSelection,
  disabled,
  onQuestion,
}: {
  hasSelection: boolean;
  disabled: boolean;
  onQuestion: (question: string) => void;
}) {
  const starterQuestions = [
    {
      label: '了解功能流程',
      question: '请说明【功能名称】的操作步骤、运行流程和关键条件。',
      Icon: Workflow,
    },
    {
      label: '排查设备问题',
      question: '请结合调试经验和相关源码，帮我分析这个问题：【异常现象】。',
      Icon: Wrench,
    },
    {
      label: hasSelection ? '解释选中代码' : '分析业务代码',
      question: hasSelection
        ? '请解释选中代码的作用、执行逻辑和相关调用。'
        : '请帮我分析【模块或方法】的作用、执行逻辑和调用关系。',
      Icon: CodeXml,
    },
  ];
  return (
    <div className="chat-welcome">
      <div className="welcome-hero">
        <img className="welcome-mark" src="/brand/arks-assistant-icon.png" alt="" />
        <h2>想从哪里开始？</h2>
      </div>
      <div className="welcome-support">
        <p>了解设备流程、查找调试经验，或结合源码分析问题。</p>
        <div className="welcome-suggestions" role="group" aria-label="推荐问题">
          {starterQuestions.map(({ label, question, Icon }) => (
            <button
              key={question}
              type="button"
              disabled={disabled}
              title={question}
              onClick={() => onQuestion(question)}
            >
              <Icon size={14} aria-hidden="true" />
              <span>{label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
