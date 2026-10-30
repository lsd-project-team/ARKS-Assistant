const starterQuestions = [
  { label: '了解项目结构', question: '这个项目的模块如何组织？' },
  { label: '解释选中代码', question: '帮我理解选中的代码' },
  { label: '开始开发模块', question: '如何开始开发一个新模块？' },
];

export function ChatWelcome({ onQuestion }: { onQuestion: (question: string) => void }) {
  return (
    <div className="chat-welcome">
      <div className="welcome-hero">
        <img className="welcome-mark" src="/brand/arks-assistant-icon.png" alt="" />
        <h2>想从哪里开始？</h2>
      </div>
      <div className="welcome-support">
        <p>解释代码、追踪模块，或聊聊你的想法。</p>
        <div className="welcome-suggestions" role="group" aria-label="推荐问题">
          {starterQuestions.map(({ label, question }) => (
            <button
              key={question}
              type="button"
              title={question}
              onClick={() => onQuestion(question)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
