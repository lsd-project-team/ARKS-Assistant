import { Check } from 'lucide-react';
import { useCurrentProject } from '../../projects/hooks/useProjects';
import type { useSourcePreferences } from '../../chat/hooks/useSourcePreferences';
import { SourceOptionsControl } from '../../chat/components/SourceOptionsControl';
import { Button, ErrorText } from '../../../shared/ui/ui';

export function KnowledgeSourceSettings({
  controller,
}: {
  controller: ReturnType<typeof useSourcePreferences>;
}) {
  const project = useCurrentProject();
  return (
    <div className="settings-content knowledge-source-settings">
      <p className="muted">适用于：{project.data?.name || '独立对话'}</p>
      {project.data && (
        <div className="knowledge-source-binding">
          <p className="muted">源码目录：{project.data.source_root || '未关联主目录'}</p>
          <p className="muted">DeepWiki 仓库：{project.data.deepwiki_repo || '未关联'}</p>
        </div>
      )}
      {controller.saved.isPending && <p className="muted">正在读取知识来源…</p>}
      {controller.draft && (
        <SourceOptionsControl
          compact
          legend="默认知识来源"
          value={controller.draft.source_options}
          onChange={controller.change}
          disabled={controller.busy}
        />
      )}
      <ErrorText error={controller.error || controller.saved.error} reveal={!!controller.error} />
      {!!(controller.error || controller.saved.error) && (
        <Button disabled={controller.busy} onClick={controller.reload}>
          读取最新知识来源
        </Button>
      )}
      {controller.feedback && (
        <p className="success-text">
          <Check size={14} />
          {controller.feedback}
        </p>
      )}
    </div>
  );
}
