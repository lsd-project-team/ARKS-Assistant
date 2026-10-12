import { Check } from 'lucide-react';
import { useCurrentProject } from '../hooks/useProjects';
import type { useSourcePreferences } from '../hooks/useSourcePreferences';
import { SourceOptionsControl } from './SourceOptionsControl';
import { Button, ErrorText } from './ui';

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
          <p className="muted">这些关联随项目切换，可在项目设置中调整。</p>
        </div>
      )}
      {controller.saved.isPending && <p className="muted">正在读取知识来源…</p>}
      {controller.draft && (
        <SourceOptionsControl
          compact={false}
          legend="默认知识来源"
          description="本地源码始终可读。保存后，新问题自动使用这些资料；历史回复和已排队的问题保留原来的配置。"
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
