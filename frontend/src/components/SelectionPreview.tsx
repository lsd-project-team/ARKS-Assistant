import { useProjectApi } from '../hooks/useProjectApi';
import { useQuery } from '@tanstack/react-query';
import { query } from '../lib/api';
import { useSourceCitation } from '../hooks/useSourceCitation';
import type { Selection, SourceFile } from '../types';
import { Modal, Button, ErrorText } from './ui';
import { CodeBlock } from './CodeBlock';

export function SelectionPreview({
  selection,
  onClose,
  onRemove,
}: {
  selection: Selection;
  onClose: () => void;
  onRemove?: () => void;
}) {
  const api = useProjectApi();
  const locate = useSourceCitation();
  const current = useQuery({
    queryKey: ['selection-current', selection.path, selection.source_workspace_id],
    queryFn: () =>
      api<SourceFile>(
        selection.source_workspace_id
          ? `/sources/${selection.source_workspace_id}/file?path=${query(selection.path)}`
          : `/file?path=${query(selection.path)}`,
      ),
    staleTime: 0,
  });
  const stale =
    selection.stale ||
    (!!current.data && current.data.version !== selection.version) ||
    !!current.error;
  return (
    <Modal
      open
      onClose={onClose}
      title="代码选区"
      description="发送时保存的源码快照"
      className="selection-preview-dialog"
    >
      <div className="dialog-body selection-preview-body">
        <div className="selection-preview-path">
          {selection.path}
          <span>
            L{selection.start_line}–{selection.end_line} · {selection.version.slice(0, 12)}
          </span>
        </div>
        {stale && <p className="selection-stale">这是旧版本快照，当前源码已经变化或无法读取。</p>}
        <CodeBlock>
          <code>{selection.content}</code>
        </CodeBlock>
        <ErrorText error={current.error} />
      </div>
      <div className="modal-footer selection-preview-actions">
        {onRemove && (
          <Button
            onClick={() => {
              onRemove();
              onClose();
            }}
          >
            移除选区
          </Button>
        )}
        <Button
          disabled={current.isPending || !!current.error}
          onClick={() =>
            void locate(
              selection.path,
              selection.start_line,
              selection.end_line,
              selection.version,
              selection.source_workspace_id,
            ).then((opened) => {
              if (opened) onClose();
            })
          }
        >
          {onRemove ? '打开源码重新选取' : '查看当前源码'}
        </Button>
      </div>
    </Modal>
  );
}
