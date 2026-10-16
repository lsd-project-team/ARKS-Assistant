import { useState } from 'react';
import { ProjectReadingPanel } from './ProjectReadingPanel';
import { CodeChangesPanel } from './CodeChangesPanel';
import '../styles/code-work.css';

export function CodeWork({ projectId, readOnly }: { projectId: string; readOnly: boolean }) {
  const [section, setSection] = useState<'reading' | 'changes'>('reading');
  return (
    <div className="code-work">
      <div className="code-work-tabs" aria-label="代码工作内容">
        <button aria-pressed={section === 'reading'} onClick={() => setSection('reading')}>
          全项目阅读
        </button>
        <button aria-pressed={section === 'changes'} onClick={() => setSection('changes')}>
          隔离修改
        </button>
      </div>
      {readOnly && <p className="muted">项目已归档，当前只可查看已有成果和差异。</p>}
      {/* 两块都保持挂载，切换查看阅读成果时不丢失未保存的副本编辑。 */}
      <div hidden={section !== 'reading'}>
        <ProjectReadingPanel projectId={projectId} readOnly={readOnly} />
      </div>
      <div hidden={section !== 'changes'}>
        <CodeChangesPanel projectId={projectId} readOnly={readOnly} />
      </div>
    </div>
  );
}
