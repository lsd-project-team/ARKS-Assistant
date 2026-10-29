import { CodeChangesPanel } from './CodeChangesPanel';
import { ReadinessPanel } from './ReadinessPanel';
import '../styles/code-work.css';

export function CodeWork({ projectId, readOnly }: { projectId: string; readOnly: boolean }) {
  return (
    <div className="code-work">
      <ReadinessPanel projectId={projectId} readOnly={readOnly} />
      {readOnly && <p className="muted">项目已归档，当前只可查看已有副本和差异。</p>}
      <CodeChangesPanel projectId={projectId} readOnly={readOnly} />
    </div>
  );
}
