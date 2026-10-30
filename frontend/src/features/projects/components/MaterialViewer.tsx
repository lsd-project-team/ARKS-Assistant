import type { ProjectMaterial } from '../../../shared/types/api';
import { Modal } from '../../../shared/ui/ui';

export function MaterialViewer({
  material,
  start = 0,
  end = 0,
  onClose,
}: {
  material: ProjectMaterial;
  start?: number;
  end?: number;
  onClose: () => void;
}) {
  return (
    <Modal
      open
      onClose={onClose}
      title={material.title}
      description={`${material.kind === 'conclusion' ? '用户确认的共享结论' : '项目文档'} · 引用版本 ${material.version}${material.state === 'deleted' ? ' · 已移入回收站' : ''}`}
      className="historical-source-dialog"
    >
      <div className="historical-source-lines material-view-lines">
        {material.content?.split('\n').map((line, index) => (
          <div key={index} className={index + 1 >= start && index + 1 <= end ? 'cited' : ''}>
            <span>{index + 1}</span>
            <code>{line || ' '}</code>
          </div>
        ))}
      </div>
    </Modal>
  );
}
